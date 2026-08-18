#!/usr/bin/env python3
"""Run U7 post-ingestion E5-D retrieval + frozen Layer C QA on the 15 unseen questions.

This is a separate post-final generalization condition. It runs only after the
human-approved U3/U4 result and locked U5/U6 ingestion safeguards validate, and
only if the isolated five-document append is exactly compatible with the frozen
E4 strict section-chunk policy. The 15 human-reviewed unseen questions are not
changed. Their original temporary-document query_mode label is retained as
provenance; actual post-ingestion routing is derived deterministically from the
question text by the frozen E5 router.

The model receives only question text and reranked top-5 evidence. Private target
AD numbers, reference pages, source quotations and reference answers are used
only for offline scoring after inference.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from full_corpus_pipeline.e5c_retrieval import DenseEvidenceAssemblyRetriever
from full_corpus_pipeline.e5d_retrieval import (
    RERANKER_CANDIDATE_LIMIT,
    RERANKER_INSTRUCTION,
    RERANKER_MODEL_NAME,
    RERANKER_MODEL_REVISION,
    apply_reranker_scores,
)
from full_corpus_pipeline.evaluate_e5a_development import (
    breakdown,
    relevance_rank,
    source_rank,
    summarize,
)
from full_corpus_pipeline.evaluate_e5c_development import encode_queries
from full_corpus_pipeline.evaluate_e5d_development import score_candidate_pool
from full_corpus_pipeline.layer_c.hosted_qa import (
    HOSTED_QA_RUNNER_VERSION,
    PROMPT_VERSION,
    Evidence,
    call_hosted_qa,
)
from full_corpus_pipeline.layer_c.providers.deepseek import (
    DEEPSEEK_MODEL,
    DEEPSEEK_PROVIDER_VERSION,
    DeepSeekProvider,
)


ROOT = Path(__file__).resolve().parents[2]
UNSEEN_ROOT = ROOT / "evaluation_sets/unseen_incoming_5_v1"
DEFAULT_QUESTIONS = UNSEEN_ROOT / "unseen_questions.jsonl"
DEFAULT_INGESTION_LOCK = UNSEEN_ROOT / "unseen_permanent_ingestion_result_lock.json"
DEFAULT_FREEZE = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json"
DEFAULT_INGESTION_ROOT = ROOT / "data_processed/evaluations/unseen_5/permanent_ingestion"
DEFAULT_INDEX = DEFAULT_INGESTION_ROOT / "isolated_index/e4_section_hybrid"
DEFAULT_DENSE = DEFAULT_INGESTION_ROOT / "isolated_index/e5c_qwen3_embedding_0_6b"
DEFAULT_OUTPUT = ROOT / "data_processed/evaluations/unseen_5/post_ingestion_primary"
RUNNER_VERSION = "unseen-5-post-ingestion-e5d-layer-c-runner-v1.0"
RETRIEVAL_VERSION = "unseen-5-post-ingestion-e5d-retrieval-v1.0"
EVIDENCE_PACK_VERSION = "unseen-5-post-ingestion-evidence-pack-v1.0"
QUESTION_COUNT = 15
ANSWERABLE_COUNT = 14
ABSTENTION_COUNT = 1
FINAL_K = 5
EXPECTED_POST_INGESTION_CHUNK_COUNT = 12670


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha(value: Any) -> str:
    rendered = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(rendered).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def validate_questions(path: Path) -> list[dict[str, Any]]:
    rows = load_jsonl(path)
    if len(rows) != QUESTION_COUNT:
        raise ValueError(f"expected {QUESTION_COUNT} locked unseen questions, found {len(rows)}")
    ids = [str(row.get("question_id", "")) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate unseen question IDs")
    if any(row.get("review_status") != "human_verified" for row in rows):
        raise ValueError("all unseen questions must remain human_verified")
    if any(row.get("split") != "unseen_post_final" for row in rows):
        raise ValueError("U7 accepts the locked unseen_post_final questions only")
    if any(row.get("evaluation_role") != "temporary_document_generalization" for row in rows):
        raise ValueError("unexpected unseen question evaluation_role")
    if sum(bool(row.get("answerable_from_ad")) for row in rows) != ANSWERABLE_COUNT:
        raise ValueError("unexpected unseen answerable count")
    if sum(not bool(row.get("answerable_from_ad")) for row in rows) != ABSTENTION_COUNT:
        raise ValueError("unexpected unseen abstention count")
    return rows


def validate_gates(*, ingestion_lock: Path, freeze: Path) -> dict[str, Any]:
    subprocess.run(
        [sys.executable, "-m", "full_corpus_pipeline.layer_c.validate_unseen_question_lock"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "full_corpus_pipeline.layer_c.validate_unseen_permanent_ingestion_result",
            "--lock",
            str(ingestion_lock),
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "full_corpus_pipeline.layer_c.validate_hosted_qa_freeze",
            "--freeze",
            str(freeze),
        ],
        cwd=ROOT,
        check=True,
    )
    freeze_payload = json.loads(freeze.read_text(encoding="utf-8"))
    if freeze_payload.get("status") != "frozen":
        raise ValueError("hosted-QA configuration is not frozen")
    return freeze_payload


def _overlaps_page(candidate: dict[str, Any], page: int) -> bool:
    return int(candidate["page_start"]) <= int(page) <= int(candidate["page_end"])


def reference_page_coverage(
    candidates: list[dict[str, Any]], reference_pages: list[int], *, k: int
) -> tuple[bool, bool, list[int]]:
    pages = [int(page) for page in reference_pages]
    top = candidates[:k]
    covered = [
        page for page in pages if any(_overlaps_page(candidate, page) for candidate in top)
    ]
    any_hit = bool(covered) if pages else False
    all_hit = len(covered) == len(pages) if pages else False
    return any_hit, all_hit, covered


def build_evidence(question: dict[str, Any], reranked: list[dict[str, Any]]) -> dict[str, Any]:
    evidence: list[dict[str, Any]] = []
    for rank, item in enumerate(reranked[:FINAL_K], 1):
        evidence.append(
            {
                "evidence_id": f"EV{rank}",
                "rank": rank,
                "chunk_id": str(item["chunk_id"]),
                "ad_number": str(item["ad_number"]),
                "source_pdf": str(item["source_pdf"]),
                "page_start": int(item["page_start"]),
                "page_end": int(item["page_end"]),
                "section": str(item["section"]),
                "text": str(item["text"]),
            }
        )
    payload = {
        "question_id": str(question["question_id"]),
        "question": str(question["question"]),
        "evidence": evidence,
    }
    return {
        "evidence_pack_version": EVIDENCE_PACK_VERSION,
        "evidence_condition": "post_ingestion_e5d_top5",
        "evidence_depth": FINAL_K,
        "question_id": str(question["question_id"]),
        "prompt_payload": payload,
        "prompt_payload_sha256": canonical_sha(payload),
    }


def validate_derivative(retriever: DenseEvidenceAssemblyRetriever) -> dict[str, Any]:
    chunks = retriever.index.chunks
    if len(chunks) != EXPECTED_POST_INGESTION_CHUNK_COUNT:
        raise ValueError(
            "post-ingestion isolated E4 chunk count mismatch: "
            f"expected {EXPECTED_POST_INGESTION_CHUNK_COUNT}, found {len(chunks)}"
        )
    config = json.loads(retriever.index.config_path.read_text(encoding="utf-8"))
    if int(config.get("chunk_count", -1)) != EXPECTED_POST_INGESTION_CHUNK_COUNT:
        raise ValueError("post-ingestion E4 config chunk_count mismatch")
    if config.get("sparse_backend") != "sqlite_fts5_bm25":
        raise ValueError("post-ingestion derivative lost SQLite FTS5/BM25")
    if config.get("dense_backend") != "sentence_transformers":
        raise ValueError("post-ingestion derivative lost frozen MiniLM dense backend")
    if config.get("dense_index_backend") != "faiss_index_flat_ip":
        raise ValueError("post-ingestion derivative lost FAISS IndexFlatIP")
    if int(retriever.dense.embeddings.shape[0]) != EXPECTED_POST_INGESTION_CHUNK_COUNT:
        raise ValueError("post-ingestion E5-C dense row count mismatch")
    document_count = len({str(chunk.file_instance_id) for chunk in chunks})
    return {
        "document_count": document_count,
        "chunk_count": len(chunks),
        "sparse_backend": config.get("sparse_backend"),
        "legacy_dense_embedding_model": config.get("embedding_model"),
        "e5c_embedding_model": retriever.dense.metadata.get("model"),
        "e5c_embedding_revision": retriever.dense.metadata.get("model_revision"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--ingestion-lock", type=Path, default=DEFAULT_INGESTION_LOCK)
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--dense-dir", type=Path, default=DEFAULT_DENSE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--query-device", default="auto")
    parser.add_argument("--query-batch-size", type=int, default=8)
    parser.add_argument("--reranker-device", default="auto")
    parser.add_argument("--reranker-batch-size", type=int, default=2)
    parser.add_argument("--confirm-run", action="store_true")
    args = parser.parse_args()

    if not args.confirm_run:
        raise SystemExit("U7 post-ingestion primary requires --confirm-run")
    for path in (args.questions, args.ingestion_lock, args.freeze):
        if not path.is_file():
            raise FileNotFoundError(path)
    validate_gates(ingestion_lock=args.ingestion_lock, freeze=args.freeze)

    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError(
            f"refusing to overwrite or repeat U7 post-ingestion primary: {args.output_dir}"
        )
    questions = validate_questions(args.questions)
    questions_sha = sha256(args.questions)

    # Validate credentials before opening the immutable U7 output directory.
    provider = DeepSeekProvider(
        reasoning_effort="high", thinking_enabled=True, max_tokens=4096
    )

    print("[progress] U7: loading isolated post-ingestion E4 + E5-C derivative", flush=True)
    retriever = DenseEvidenceAssemblyRetriever(args.index, args.dense_dir)
    derivative_meta = validate_derivative(retriever)

    args.output_dir.mkdir(parents=True, exist_ok=False)
    manifest = {
        "runner_version": RUNNER_VERSION,
        "scope": "five frozen unseen PDFs — post-ingestion E5-D primary",
        "status": "started",
        "unseen_questions_sha256": questions_sha,
        "u5_u6_result_lock_path": str(args.ingestion_lock.relative_to(ROOT)),
        "u5_u6_result_lock_sha256": sha256(args.ingestion_lock),
        "hosted_qa_freeze_path": str(args.freeze.relative_to(ROOT)),
        "hosted_qa_freeze_sha256": sha256(args.freeze),
        "index": str(args.index),
        "dense_dir": str(args.dense_dir),
        "post_ingestion_derivative": derivative_meta,
        "question_count": len(questions),
        "answerable_count": ANSWERABLE_COUNT,
        "abstention_count": ABSTENTION_COUNT,
        "provider": "deepseek",
        "provider_version": DEEPSEEK_PROVIDER_VERSION,
        "model": DEEPSEEK_MODEL,
        "thinking": "enabled",
        "reasoning_effort": "high",
        "max_tokens": 4096,
        "prompt_version": PROMPT_VERSION,
        "hosted_qa_runner_version": HOSTED_QA_RUNNER_VERSION,
        "retrieval_experiment": "E5-D frozen algorithm over isolated post-ingestion derivative",
        "evidence_depth": FINAL_K,
        "permanent_ingestion_already_completed": True,
        "frozen_e5_artifacts_modified": False,
        "policy": (
            "Post-final U7 generalization condition. The 15 locked questions and frozen E5-C/E5-D/Layer C "
            "algorithms are unchanged. Only the isolated index membership differs because the five held-out PDFs "
            "were admitted in U5/U6. No retuning or semantic retry is permitted in this primary run."
        ),
    }
    (args.output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print("[progress] U7: encoding 15 queries with pinned Qwen3 embedding model", flush=True)
    query_vectors, query_meta = encode_queries(
        questions,
        device=args.query_device,
        batch_size=args.query_batch_size,
    )

    generated: list[dict[str, Any]] = []
    worker_pairs: list[dict[str, Any]] = []
    route_modes: Counter[str] = Counter()
    candidate_started = time.monotonic()
    for position, question in enumerate(questions, 1):
        qid = str(question["question_id"])
        print(f"[progress] U7 E5-C candidate generation: {position}/{len(questions)} ({qid})", flush=True)
        result = retriever.retrieve(str(question["question"]), query_vectors[qid])
        route = result.get("route") or {}
        route_modes[str(route.get("mode", "unknown"))] += 1
        candidates = list(result.get("candidates", []))[:RERANKER_CANDIDATE_LIMIT]
        generated.append(
            {"question": question, "result": result, "candidates": candidates}
        )
        for candidate_position, candidate in enumerate(candidates, 1):
            worker_pairs.append(
                {
                    "question_id": qid,
                    "candidate_position": candidate_position,
                    "chunk_id": str(candidate["chunk_id"]),
                    "question": str(question["question"]),
                    "text": str(candidate["text"]),
                }
            )
    candidate_elapsed = time.monotonic() - candidate_started

    print(f"[progress] U7: reranking {len(worker_pairs)} fixed E5-C candidate pairs", flush=True)
    rerank_started = time.monotonic()
    score_map, reranker_meta = score_candidate_pool(
        worker_pairs,
        device=args.reranker_device,
        batch_size=args.reranker_batch_size,
    )
    rerank_elapsed = time.monotonic() - rerank_started
    if reranker_meta.get("model") != RERANKER_MODEL_NAME:
        raise ValueError("U7 used unexpected reranker model")
    if reranker_meta.get("model_revision") != RERANKER_MODEL_REVISION:
        raise ValueError("U7 used unexpected reranker revision")
    if reranker_meta.get("instruction") != RERANKER_INSTRUCTION:
        raise ValueError("U7 used unexpected reranker instruction")

    retrieval_rows: list[dict[str, Any]] = []
    answerable_rows: list[dict[str, Any]] = []
    packs: list[dict[str, Any]] = []
    any_page_hits = all_page_hits = 0
    for bundle in generated:
        question = bundle["question"]
        qid = str(question["question_id"])
        candidates = bundle["candidates"]
        scores = [
            score_map[(qid, pre_rank, str(candidate["chunk_id"]))]
            for pre_rank, candidate in enumerate(candidates, 1)
        ]
        reranked = apply_reranker_scores(candidates, scores)
        route = bundle["result"].get("route") or {}
        target = str(question.get("target_ad_number", "")).casefold()
        routed_ads = {str(value).casefold() for value in route.get("ad_numbers", [])}
        route_target_consistent = (
            target in routed_ads
            if str(route.get("mode")) in {"known_document", "multi_document"}
            else True
        )
        ref_pages = [int(page) for page in question.get("reference_pages", [])]
        any_ref, all_ref, covered = reference_page_coverage(
            reranked, ref_pages, k=FINAL_K
        )
        row: dict[str, Any] = {
            "question_id": qid,
            "category": question["category"],
            "authoring_query_mode": question.get("query_mode"),
            "post_ingestion_route_mode": route.get("mode"),
            "route": route,
            "route_errors": bundle["result"].get("route_errors", []),
            "route_target_consistent_when_routed": route_target_consistent,
            "answerable_from_ad": bool(question["answerable_from_ad"]),
            "target_ad_number": question.get("target_ad_number"),
            "reference_pages": ref_pages,
            "candidate_count": len(reranked),
            "reference_page_any_at_5": any_ref,
            "reference_page_all_covered_at_5": all_ref,
            "reference_pages_covered_at_5": covered,
            "retrieved": [
                {
                    "rank": rank,
                    "pre_rerank_rank": int(item["pre_rerank_rank"]),
                    "reranker_score": float(item["reranker_score"]),
                    "chunk_id": str(item["chunk_id"]),
                    "file_instance_id": str(item["file_instance_id"]),
                    "ad_number": str(item["ad_number"]),
                    "source_pdf": str(item["source_pdf"]),
                    "page_start": int(item["page_start"]),
                    "page_end": int(item["page_end"]),
                    "section": str(item["section"]),
                }
                for rank, item in enumerate(reranked, 1)
            ],
        }
        if bool(question["answerable_from_ad"]):
            row["rank_at_20"] = relevance_rank(reranked, question)
            row["source_rank_at_20"] = source_rank(reranked, question)
            answerable_rows.append(row)
            any_page_hits += int(any_ref)
            all_page_hits += int(all_ref)
        else:
            row["rank_at_20"] = None
            row["source_rank_at_20"] = None
        retrieval_rows.append(row)
        packs.append(build_evidence(question, reranked))

    retrieval_report = {
        "evaluation_version": RETRIEVAL_VERSION,
        "experiment": "post-ingestion E5-D over isolated five-PDF derivative",
        "unseen_questions_sha256": questions_sha,
        "question_accounting": {
            "total": len(questions),
            "answerable_retrieval": len(answerable_rows),
            "abstention_reserved_for_qa": len(questions) - len(answerable_rows),
        },
        "post_ingestion_route_mode_counts": dict(route_modes),
        "route_target_consistency_count": sum(
            bool(row["route_target_consistent_when_routed"]) for row in retrieval_rows
        ),
        "overall": summarize(answerable_rows),
        "by_post_ingestion_route_mode": breakdown(
            answerable_rows, "post_ingestion_route_mode"
        ),
        "by_category": breakdown(answerable_rows, "category"),
        "reference_page_any_recall_at_5": (
            any_page_hits / len(answerable_rows) if answerable_rows else None
        ),
        "reference_page_full_coverage_at_5": (
            all_page_hits / len(answerable_rows) if answerable_rows else None
        ),
        "configuration": {
            "candidate_generation": "E5-C fixed top-20 over isolated post-ingestion derivative",
            "candidate_limit": RERANKER_CANDIDATE_LIMIT,
            "final_evidence_k": FINAL_K,
            "embedding_model": query_meta.get("model"),
            "embedding_revision": query_meta.get("model_revision"),
            "reranker_model": RERANKER_MODEL_NAME,
            "reranker_revision": RERANKER_MODEL_REVISION,
            "reranker_instruction": RERANKER_INSTRUCTION,
            "index": str(args.index),
            "dense_dir": str(args.dense_dir),
            **derivative_meta,
        },
        "elapsed_seconds_candidate_generation": candidate_elapsed,
        "elapsed_seconds_reranker": rerank_elapsed,
        "questions": retrieval_rows,
        "policy": (
            "Post-final U7 retrieval result. The algorithm is frozen; only the isolated corpus membership "
            "contains the five newly admitted unseen PDFs. No post-result tuning may replace this report."
        ),
    }
    retrieval_path = args.output_dir / "retrieval_report.json"
    retrieval_path.write_text(
        json.dumps(retrieval_report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    packs_path = args.output_dir / "evidence_packs.jsonl"
    with packs_path.open("w", encoding="utf-8") as handle:
        for pack in packs:
            handle.write(json.dumps(pack, ensure_ascii=False) + "\n")

    responses_path = args.output_dir / "responses.jsonl"
    failures_path = args.output_dir / "failures.jsonl"
    success_count = failure_count = 0
    qa_started = time.monotonic()
    with responses_path.open("w", encoding="utf-8") as response_handle, failures_path.open(
        "w", encoding="utf-8"
    ) as failure_handle:
        for position, pack in enumerate(packs, 1):
            qid = str(pack["question_id"])
            payload = pack["prompt_payload"]
            evidence_objects = [
                Evidence.from_dict(item) for item in payload.get("evidence", [])
            ]
            print(f"[progress] U7 Layer C QA: {position}/{len(packs)} ({qid})", flush=True)
            request_started = time.monotonic()
            try:
                answer = call_hosted_qa(
                    str(payload["question"]),
                    evidence_objects,
                    model=DEEPSEEK_MODEL,
                    provider=provider,
                    reasoning_effort="high",
                    max_tokens=4096,
                    request_metadata={
                        "unseen_post_ingestion_primary": True,
                        "question_id": qid,
                        "prompt_payload_sha256": pack["prompt_payload_sha256"],
                        "u5_u6_result_lock_sha256": manifest["u5_u6_result_lock_sha256"],
                        "hosted_qa_freeze_sha256": manifest["hosted_qa_freeze_sha256"],
                    },
                )
            except Exception as exc:
                failure_count += 1
                failure_handle.write(
                    json.dumps(
                        {
                            "question_id": qid,
                            "prompt_payload_sha256": pack["prompt_payload_sha256"],
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "elapsed_seconds": time.monotonic() - request_started,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                failure_handle.flush()
                continue
            success_count += 1
            response_handle.write(
                json.dumps(
                    {
                        "question_id": qid,
                        "prompt_payload_sha256": pack["prompt_payload_sha256"],
                        "answer": answer,
                        "elapsed_seconds": time.monotonic() - request_started,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            response_handle.flush()

    summary = {
        **manifest,
        "status": "completed_with_failures" if failure_count else "completed",
        "retrieval_report_path": str(retrieval_path),
        "retrieval_report_sha256": sha256(retrieval_path),
        "evidence_packs_path": str(packs_path),
        "evidence_packs_sha256": sha256(packs_path),
        "retrieval_overall": retrieval_report["overall"],
        "retrieval_by_post_ingestion_route_mode": retrieval_report[
            "by_post_ingestion_route_mode"
        ],
        "reference_page_any_recall_at_5": retrieval_report[
            "reference_page_any_recall_at_5"
        ],
        "reference_page_full_coverage_at_5": retrieval_report[
            "reference_page_full_coverage_at_5"
        ],
        "qa_success_count": success_count,
        "qa_failure_count": failure_count,
        "qa_elapsed_seconds": time.monotonic() - qa_started,
        "responses_path": str(responses_path),
        "responses_sha256": sha256(responses_path),
        "failures_path": str(failures_path),
        "failures_sha256": sha256(failures_path),
    }
    summary_path = args.output_dir / "run_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("[progress] U7 post-ingestion primary finished", flush=True)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if failure_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
