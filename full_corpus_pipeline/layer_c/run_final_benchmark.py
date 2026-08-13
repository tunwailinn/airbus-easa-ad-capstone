#!/usr/bin/env python3
"""Run the one-time frozen E5 final retrieval + Layer C hosted-QA benchmark.

This command is the primary final-test runner. It validates the committed hosted-QA
freeze before opening the local sealed 40-question final benchmark, runs the frozen
E5-D retrieval configuration, assembles only the reranked top-5 source passages,
and immediately executes the frozen DeepSeek Layer C configuration.

The model receives only question text and evidence. Private target/reference labels
are used only for offline retrieval scoring and later final evaluation. The runner
never retunes retrieval or generation and refuses to overwrite a prior primary run.
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

from full_corpus_pipeline.build_e5c_dense_embeddings import DEFAULT_OUTPUT as DEFAULT_DENSE_DIR
from full_corpus_pipeline.e5_retrieval import DEFAULT_INDEX
from full_corpus_pipeline.e5c_retrieval import DenseEvidenceAssemblyRetriever
from full_corpus_pipeline.e5d_retrieval import (
    RERANKER_CANDIDATE_LIMIT,
    RERANKER_INSTRUCTION,
    RERANKER_MODEL_NAME,
    RERANKER_MODEL_REVISION,
    apply_reranker_scores,
)
from full_corpus_pipeline.evaluate_e5a_development import (
    EXPECTED_RETRIEVAL_BUILD_VERSION,
    breakdown,
    relevance_rank,
    route_matches_declared,
    source_rank,
    summarize,
    validate_index,
)
from full_corpus_pipeline.evaluate_e5c_development import encode_queries
from full_corpus_pipeline.evaluate_e5d_development import score_candidate_pool
from full_corpus_pipeline.layer_c.hosted_qa import (
    HOSTED_QA_RUNNER_VERSION,
    PROMPT_VERSION,
    call_hosted_qa,
)
from full_corpus_pipeline.layer_c.providers.deepseek import (
    DEEPSEEK_MODEL,
    DEEPSEEK_PROVIDER_VERSION,
    DeepSeekProvider,
)


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_ROOT = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1"
DEFAULT_QUESTIONS = BENCHMARK_ROOT / "final_questions.jsonl"
DEFAULT_FREEZE = BENCHMARK_ROOT / "hosted_qa_freeze.json"
DEFAULT_OUTPUT_DIR = ROOT / "data_processed/evaluations/e5/layer_c/final/primary"
FINAL_RUNNER_VERSION = "e5-layer-c-final-primary-runner-v1.0"
FINAL_RETRIEVAL_EVAL_VERSION = "e5-d-final-eval-v1.0"
FINAL_EVIDENCE_PACK_VERSION = "e5-final-evidence-pack-v1.0"
FINAL_QUESTION_COUNT = 40
FINAL_ANSWERABLE_COUNT = 36
FINAL_ABSTENTION_COUNT = 4
FINAL_K = 5

EXPECTED_CATEGORY_COUNTS = {
    "identity_lifecycle": 5,
    "applicability": 7,
    "required_action_compliance": 14,
    "referenced_publication": 5,
    "conditional_multi_passage": 5,
    "insufficient_conflict_abstention": 4,
}
EXPECTED_MODE_COUNTS = {
    "known_document": 24,
    "discovery": 12,
    "abstention_conflict": 4,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value: Any) -> str:
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(rendered).hexdigest()


def load_final_questions(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != FINAL_QUESTION_COUNT:
        raise ValueError(f"expected {FINAL_QUESTION_COUNT} final questions, found {len(rows)}")
    ids = [str(row.get("question_id", "")) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate final question IDs")
    if any(row.get("split") != "final_test" for row in rows):
        raise ValueError("final runner accepts final_test questions only")
    if any(row.get("review_status") != "human_verified" for row in rows):
        raise ValueError("all final questions must remain human_verified")
    answerable = [row for row in rows if bool(row.get("answerable_from_ad"))]
    if len(answerable) != FINAL_ANSWERABLE_COUNT:
        raise ValueError(f"expected {FINAL_ANSWERABLE_COUNT} answerable final questions")
    if len(rows) - len(answerable) != FINAL_ABSTENTION_COUNT:
        raise ValueError(f"expected {FINAL_ABSTENTION_COUNT} final abstention/conflict questions")
    categories = Counter(str(row.get("category", "")) for row in rows)
    modes = Counter(str(row.get("query_mode", "")) for row in rows)
    if dict(categories) != EXPECTED_CATEGORY_COUNTS:
        raise ValueError(f"unexpected final category counts: {dict(categories)}")
    if dict(modes) != EXPECTED_MODE_COUNTS:
        raise ValueError(f"unexpected final query-mode counts: {dict(modes)}")
    return rows


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
        "evidence_pack_version": FINAL_EVIDENCE_PACK_VERSION,
        "evidence_condition": "frozen_e5d_top5",
        "evidence_depth": FINAL_K,
        "question_id": str(question["question_id"]),
        "prompt_payload": payload,
        "prompt_payload_sha256": canonical_sha(payload),
    }


def validate_freeze_before_opening(path: Path) -> dict[str, Any]:
    subprocess.run(
        [sys.executable, "-m", "full_corpus_pipeline.layer_c.validate_hosted_qa_freeze", "--freeze", str(path)],
        cwd=ROOT,
        check=True,
    )
    freeze = json.loads(path.read_text(encoding="utf-8"))
    if freeze.get("status") != "frozen":
        raise ValueError("hosted-QA configuration is not frozen")
    return freeze


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--dense-dir", type=Path, default=DEFAULT_DENSE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--query-device", default="auto")
    parser.add_argument("--query-batch-size", type=int, default=8)
    parser.add_argument("--reranker-device", default="auto")
    parser.add_argument("--reranker-batch-size", type=int, default=2)
    args = parser.parse_args()

    # The freeze must validate before the sealed final benchmark is read.
    freeze = validate_freeze_before_opening(args.freeze)
    if not args.questions.is_file():
        raise FileNotFoundError(args.questions)

    run_dir = args.output_dir
    if run_dir.exists() and any(run_dir.iterdir()):
        raise ValueError(
            f"refusing to overwrite or repeat the primary final run: {run_dir}. "
            "Any permitted exact transport retry must use a separate audited retry path."
        )

    questions = load_final_questions(args.questions)
    final_questions_sha = sha256(args.questions)

    # Validate provider credentials before creating the immutable primary run directory.
    provider = DeepSeekProvider(reasoning_effort="high", thinking_enabled=True, max_tokens=4096)

    run_dir.mkdir(parents=True, exist_ok=False)
    manifest = {
        "final_runner_version": FINAL_RUNNER_VERSION,
        "scope": "E5 one-time final benchmark",
        "status": "started",
        "hosted_qa_freeze_path": str(args.freeze.relative_to(ROOT)),
        "hosted_qa_freeze_sha256": sha256(args.freeze),
        "final_questions_path": str(args.questions.relative_to(ROOT)),
        "final_questions_sha256": final_questions_sha,
        "final_question_count": len(questions),
        "provider": "deepseek",
        "provider_version": DEEPSEEK_PROVIDER_VERSION,
        "model": DEEPSEEK_MODEL,
        "thinking": "enabled",
        "reasoning_effort": "high",
        "max_tokens": 4096,
        "prompt_version": PROMPT_VERSION,
        "hosted_qa_runner_version": HOSTED_QA_RUNNER_VERSION,
        "retrieval_experiment": "E5-D",
        "evidence_depth": FINAL_K,
        "policy": (
            "Primary final benchmark opened only after committed hosted-QA freeze validation. "
            "Retrieval and Layer C settings are immutable; no semantic retry, no retuning, and no "
            "configuration change is permitted after observing final results."
        ),
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print("[progress] final: loading frozen E4 sparse chunks + E5-C dense artifact", flush=True)
    retriever = DenseEvidenceAssemblyRetriever(args.index, args.dense_dir)
    index_meta = validate_index(retriever.base.base, args.index)

    print("[progress] final: encoding 40 queries using the pinned Qwen embedding model", flush=True)
    query_vectors, query_meta = encode_queries(
        questions,
        device=args.query_device,
        batch_size=args.query_batch_size,
    )

    generated: list[dict[str, Any]] = []
    worker_pairs: list[dict[str, Any]] = []
    route_checks: list[bool] = []
    retrieval_started = time.monotonic()
    for position, question in enumerate(questions, 1):
        qid = str(question["question_id"])
        print(f"[progress] final E5-D candidate generation: {position}/{len(questions)} ({qid})", flush=True)
        result = retriever.retrieve(str(question["question"]), query_vectors[qid])
        candidates = list(result.get("candidates", []))[:RERANKER_CANDIDATE_LIMIT]
        route_match = route_matches_declared(question, result["route"])
        if route_match is not None:
            route_checks.append(bool(route_match))
        generated.append({"question": question, "result": result, "candidates": candidates, "route_match": route_match})
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
    retrieval_elapsed = time.monotonic() - retrieval_started

    print(f"[progress] final: reranking {len(worker_pairs)} fixed candidate pairs", flush=True)
    rerank_started = time.monotonic()
    score_map, reranker_meta = score_candidate_pool(
        worker_pairs,
        device=args.reranker_device,
        batch_size=args.reranker_batch_size,
    )
    rerank_elapsed = time.monotonic() - rerank_started
    if reranker_meta.get("model") != RERANKER_MODEL_NAME:
        raise ValueError("final run used unexpected reranker model")
    if reranker_meta.get("model_revision") != RERANKER_MODEL_REVISION:
        raise ValueError("final run used unexpected reranker revision")
    if reranker_meta.get("instruction") != RERANKER_INSTRUCTION:
        raise ValueError("final run used unexpected reranker instruction")

    retrieval_rows: list[dict[str, Any]] = []
    answerable_rows: list[dict[str, Any]] = []
    packs: list[dict[str, Any]] = []
    for bundle in generated:
        question = bundle["question"]
        qid = str(question["question_id"])
        candidates = bundle["candidates"]
        scores = [
            score_map[(qid, pre_rank, str(candidate["chunk_id"]))]
            for pre_rank, candidate in enumerate(candidates, 1)
        ]
        reranked = apply_reranker_scores(candidates, scores)
        row: dict[str, Any] = {
            "question_id": qid,
            "category": question["category"],
            "query_mode": question["query_mode"],
            "answerable_from_ad": bool(question["answerable_from_ad"]),
            "target_ad_number": question.get("target_ad_number"),
            "reference_pages": question.get("reference_pages", []),
            "route": bundle["result"]["route"],
            "route_matches_declared_mode": bundle["route_match"],
            "candidate_count": len(reranked),
            "retrieved": [
                {
                    "rank": rank,
                    "pre_rerank_rank": item["pre_rerank_rank"],
                    "reranker_score": item["reranker_score"],
                    "chunk_id": item["chunk_id"],
                    "ad_number": item["ad_number"],
                    "page_start": item["page_start"],
                    "page_end": item["page_end"],
                    "section": item["section"],
                }
                for rank, item in enumerate(reranked, 1)
            ],
        }
        if bool(question["answerable_from_ad"]):
            row["rank_at_20"] = relevance_rank(reranked, question)
            row["source_rank_at_20"] = source_rank(reranked, question)
            answerable_rows.append(row)
        else:
            row["rank_at_20"] = None
            row["source_rank_at_20"] = None
        retrieval_rows.append(row)
        packs.append(build_evidence(question, reranked))

    retrieval_report = {
        "evaluation_version": FINAL_RETRIEVAL_EVAL_VERSION,
        "experiment": "E5-D frozen final",
        "retrieval_build_version": EXPECTED_RETRIEVAL_BUILD_VERSION,
        "benchmark": str(args.questions),
        "benchmark_sha256": final_questions_sha,
        "question_accounting": {
            "total": len(questions),
            "answerable_retrieval": len(answerable_rows),
            "abstention_reserved_for_qa": len(questions) - len(answerable_rows),
        },
        "routing": {
            "checked_question_count": len(route_checks),
            "correct_count": sum(route_checks),
            "accuracy": sum(route_checks) / len(route_checks) if route_checks else None,
        },
        "overall": summarize(answerable_rows),
        "by_query_mode": breakdown(answerable_rows, "query_mode"),
        "by_category": breakdown(answerable_rows, "category"),
        "configuration": {
            "candidate_generation": "E5-C fixed top-20",
            "candidate_limit": RERANKER_CANDIDATE_LIMIT,
            "primary_final_k": FINAL_K,
            "embedding_model": query_meta.get("model"),
            "embedding_revision": query_meta.get("model_revision"),
            "reranker_model": RERANKER_MODEL_NAME,
            "reranker_revision": RERANKER_MODEL_REVISION,
            "reranker_instruction": RERANKER_INSTRUCTION,
            "index": str(args.index),
            "dense_dir": str(args.dense_dir),
            **index_meta,
        },
        "elapsed_seconds_candidate_generation": retrieval_elapsed,
        "elapsed_seconds_reranker": rerank_elapsed,
        "questions": retrieval_rows,
        "policy": "One-time final retrieval result. No post-test retrieval tuning may replace this report.",
    }
    retrieval_path = run_dir / "retrieval_report.json"
    retrieval_path.write_text(json.dumps(retrieval_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    packs_path = run_dir / "evidence_packs.jsonl"
    with packs_path.open("w", encoding="utf-8") as handle:
        for pack in packs:
            handle.write(json.dumps(pack, ensure_ascii=False) + "\n")

    # Hosted inference immediately follows frozen retrieval. No private reference fields enter the prompt.
    responses_path = run_dir / "responses.jsonl"
    failures_path = run_dir / "failures.jsonl"
    success_count = 0
    failure_count = 0
    qa_started = time.monotonic()
    with responses_path.open("w", encoding="utf-8") as response_handle, failures_path.open("w", encoding="utf-8") as failure_handle:
        for position, pack in enumerate(packs, 1):
            qid = str(pack["question_id"])
            payload = pack["prompt_payload"]
            evidence = payload["evidence"]
            from full_corpus_pipeline.layer_c.hosted_qa import Evidence
            evidence_objects = [Evidence.from_dict(item) for item in evidence]
            print(f"[progress] final Layer C QA: {position}/{len(packs)} ({qid})", flush=True)
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
                        "final_primary_run": True,
                        "question_id": qid,
                        "prompt_payload_sha256": pack["prompt_payload_sha256"],
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
        "retrieval_by_query_mode": retrieval_report["by_query_mode"],
        "qa_success_count": success_count,
        "qa_failure_count": failure_count,
        "qa_elapsed_seconds": time.monotonic() - qa_started,
        "responses_path": str(responses_path),
        "responses_sha256": sha256(responses_path),
        "failures_path": str(failures_path),
        "failures_sha256": sha256(failures_path),
    }
    (run_dir / "run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("[progress] one-time final benchmark finished", flush=True)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if failure_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
