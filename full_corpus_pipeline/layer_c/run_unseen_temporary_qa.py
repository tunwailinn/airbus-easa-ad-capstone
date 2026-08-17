#!/usr/bin/env python3
"""Run the locked five-PDF temporary-document QA generalization probe.

The five PDFs remain outside permanent corpus/index state. For each human-verified
question, candidate passages come only from that PDF's non-destructive preparation
packet. Because each held-out PDF has <=20 section chunks, all prepared chunks are
passed to the pinned E5-D Qwen reranker; the top five are then supplied to the exact
frozen Layer C DeepSeek configuration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from full_corpus_pipeline.e5d_retrieval import (
    RERANKER_INSTRUCTION,
    RERANKER_MODEL_NAME,
    RERANKER_MODEL_REVISION,
    apply_reranker_scores,
)
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
DEFAULT_LOCK = UNSEEN_ROOT / "unseen_lock.json"
DEFAULT_PREPARATION = ROOT / "data_processed/evaluations/unseen_5/preparation"
DEFAULT_OUTPUT = ROOT / "data_processed/evaluations/unseen_5/temporary_primary"
DEFAULT_HOSTED_FREEZE = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json"
RUNNER_VERSION = "unseen-5-temporary-qa-runner-v1.0"
EVIDENCE_PACK_VERSION = "unseen-5-temporary-evidence-pack-v1.0"
FINAL_K = 5
MAX_CANDIDATES = 20


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value: Any) -> str:
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(rendered).hexdigest()


def load_questions(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def reference_page_rank(candidates: list[dict[str, Any]], pages: list[int]) -> int | None:
    wanted = {int(page) for page in pages}
    for rank, item in enumerate(candidates, 1):
        covered = set(range(int(item["page_start"]), int(item["page_end"]) + 1))
        if covered & wanted:
            return rank
    return None


def all_reference_pages_covered(candidates: list[dict[str, Any]], pages: list[int]) -> bool:
    covered: set[int] = set()
    for item in candidates:
        covered.update(range(int(item["page_start"]), int(item["page_end"]) + 1))
    return {int(page) for page in pages}.issubset(covered)


def build_evidence(question: dict[str, Any], reranked: list[dict[str, Any]]) -> dict[str, Any]:
    evidence = []
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
        "evidence_condition": "temporary_document_all_chunks_qwen3_reranked_top5",
        "question_id": str(question["question_id"]),
        "file_instance_id": str(question["file_instance_id"]),
        "source_pdf": str(question["source_pdf"]),
        "evidence_depth": len(evidence),
        "prompt_payload": payload,
        "prompt_payload_sha256": canonical_sha(payload),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--preparation-dir", type=Path, default=DEFAULT_PREPARATION)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--reranker-device", default="auto")
    parser.add_argument("--reranker-batch-size", type=int, default=2)
    args = parser.parse_args()

    subprocess.run(
        [sys.executable, "-m", "full_corpus_pipeline.layer_c.validate_unseen_question_lock"],
        cwd=ROOT,
        check=True,
    )

    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError(f"refusing to overwrite/repeat unseen temporary primary run: {args.output_dir}")
    questions = load_questions(args.questions)
    if len(questions) != 15:
        raise ValueError("unseen temporary runner requires exactly 15 locked questions")

    # Validate credentials/config before creating the immutable output directory.
    provider = DeepSeekProvider(reasoning_effort="high", thinking_enabled=True, max_tokens=4096)

    generated: list[dict[str, Any]] = []
    worker_pairs: list[dict[str, Any]] = []
    for position, question in enumerate(questions, 1):
        qid = str(question["question_id"])
        packet_path = args.preparation_dir / str(question["source_packet"])
        if not packet_path.is_file():
            raise FileNotFoundError(packet_path)
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        selection = packet.get("selection") or {}
        if str(selection.get("file_instance_id")) != str(question["file_instance_id"]):
            raise ValueError(f"{qid}: source packet file_instance_id mismatch")
        if str(selection.get("ad_number")) != str(question["target_ad_number"]):
            raise ValueError(f"{qid}: source packet AD mismatch")
        candidates = list(packet.get("temporary_chunks") or [])
        if not candidates or len(candidates) > MAX_CANDIDATES:
            raise ValueError(f"{qid}: expected 1..{MAX_CANDIDATES} prepared chunks, found {len(candidates)}")
        print(f"[progress] unseen temporary candidates: {position}/15 ({qid}, {len(candidates)} chunks)", flush=True)
        generated.append({"question": question, "candidates": candidates, "packet_path": packet_path})
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

    print(f"[progress] unseen temporary: reranking {len(worker_pairs)} question/passage pairs", flush=True)
    score_map, reranker_meta = score_candidate_pool(
        worker_pairs,
        device=args.reranker_device,
        batch_size=args.reranker_batch_size,
    )
    if reranker_meta.get("model") != RERANKER_MODEL_NAME:
        raise ValueError("unseen run used unexpected reranker model")
    if reranker_meta.get("model_revision") != RERANKER_MODEL_REVISION:
        raise ValueError("unseen run used unexpected reranker revision")
    if reranker_meta.get("instruction") != RERANKER_INSTRUCTION:
        raise ValueError("unseen run used unexpected reranker instruction")

    retrieval_rows = []
    packs = []
    for bundle in generated:
        question = bundle["question"]
        qid = str(question["question_id"])
        candidates = bundle["candidates"]
        scores = [score_map[(qid, i, str(candidate["chunk_id"]))] for i, candidate in enumerate(candidates, 1)]
        reranked = apply_reranker_scores(candidates, scores, limit=len(candidates))
        top5 = reranked[:FINAL_K]
        pages = [int(page) for page in question.get("reference_pages", [])]
        retrieval_rows.append(
            {
                "question_id": qid,
                "category": question["category"],
                "stratum": question["stratum"],
                "answerable_from_ad": bool(question["answerable_from_ad"]),
                "target_ad_number": question["target_ad_number"],
                "reference_pages": pages,
                "candidate_count": len(reranked),
                "reference_page_rank": reference_page_rank(reranked, pages),
                "reference_page_any_at_5": reference_page_rank(top5, pages) is not None,
                "reference_page_all_covered_at_5": all_reference_pages_covered(top5, pages),
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
                    for rank, item in enumerate(top5, 1)
                ],
            }
        )
        packs.append(build_evidence(question, reranked))

    answerable_rows = [row for row in retrieval_rows if row["answerable_from_ad"]]
    retrieval_report = {
        "evaluation_version": "unseen-5-temporary-retrieval-eval-v1.0",
        "experiment": "five-PDF temporary-document generalization",
        "question_count": len(questions),
        "answerable_count": len(answerable_rows),
        "reference_page_any_recall_at_5": sum(bool(r["reference_page_any_at_5"]) for r in answerable_rows) / len(answerable_rows),
        "reference_page_full_coverage_at_5": sum(bool(r["reference_page_all_covered_at_5"]) for r in answerable_rows) / len(answerable_rows),
        "configuration": {
            "candidate_generation": "all prepared section chunks from the selected temporary PDF",
            "candidate_limit": MAX_CANDIDATES,
            "reranker_model": RERANKER_MODEL_NAME,
            "reranker_revision": RERANKER_MODEL_REVISION,
            "reranker_instruction": RERANKER_INSTRUCTION,
            "final_evidence_depth": FINAL_K,
            "corpus_wide_retrieval": False,
            "permanent_index_update": False,
        },
        "questions": retrieval_rows,
        "policy": "Post-final unseen generalization result; no tuning may replace the first-pass temporary result.",
    }

    args.output_dir.mkdir(parents=True, exist_ok=False)
    retrieval_path = args.output_dir / "retrieval_report.json"
    retrieval_path.write_text(json.dumps(retrieval_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    packs_path = args.output_dir / "evidence_packs.jsonl"
    with packs_path.open("w", encoding="utf-8") as handle:
        for pack in packs:
            handle.write(json.dumps(pack, ensure_ascii=False) + "\n")

    manifest = {
        "runner_version": RUNNER_VERSION,
        "scope": "five frozen unseen PDFs — temporary-document primary",
        "status": "started",
        "unseen_questions_sha256": sha256(args.questions),
        "unseen_lock_sha256": sha256(args.lock),
        "preparation_manifest_sha256": sha256(args.preparation_dir / "preparation_manifest.json"),
        "hosted_qa_freeze_sha256": sha256(DEFAULT_HOSTED_FREEZE),
        "provider": "deepseek",
        "provider_version": DEEPSEEK_PROVIDER_VERSION,
        "model": DEEPSEEK_MODEL,
        "thinking": "enabled",
        "reasoning_effort": "high",
        "max_tokens": 4096,
        "prompt_version": PROMPT_VERSION,
        "hosted_qa_runner_version": HOSTED_QA_RUNNER_VERSION,
        "reranker_model": RERANKER_MODEL_NAME,
        "reranker_revision": RERANKER_MODEL_REVISION,
        "evidence_depth": FINAL_K,
        "permanent_ingestion": False,
        "semantic_retry": "prohibited",
    }
    (args.output_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    responses_path = args.output_dir / "responses.jsonl"
    failures_path = args.output_dir / "failures.jsonl"
    success_count = 0
    failure_count = 0
    qa_started = time.monotonic()
    with responses_path.open("w", encoding="utf-8") as response_handle, failures_path.open("w", encoding="utf-8") as failure_handle:
        for position, pack in enumerate(packs, 1):
            qid = str(pack["question_id"])
            payload = pack["prompt_payload"]
            evidence_objects = [Evidence.from_dict(item) for item in payload["evidence"]]
            print(f"[progress] unseen temporary Layer C QA: {position}/15 ({qid})", flush=True)
            started = time.monotonic()
            try:
                answer = call_hosted_qa(
                    str(payload["question"]),
                    evidence_objects,
                    model=DEEPSEEK_MODEL,
                    provider=provider,
                    reasoning_effort="high",
                    max_tokens=4096,
                    request_metadata={
                        "unseen_temporary_primary": True,
                        "question_id": qid,
                        "prompt_payload_sha256": pack["prompt_payload_sha256"],
                        "unseen_lock_sha256": manifest["unseen_lock_sha256"],
                    },
                )
            except Exception as exc:
                failure_count += 1
                failure_handle.write(json.dumps({
                    "question_id": qid,
                    "prompt_payload_sha256": pack["prompt_payload_sha256"],
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "elapsed_seconds": time.monotonic() - started,
                }, ensure_ascii=False) + "\n")
                failure_handle.flush()
                continue
            success_count += 1
            response_handle.write(json.dumps({
                "question_id": qid,
                "prompt_payload_sha256": pack["prompt_payload_sha256"],
                "answer": answer,
                "elapsed_seconds": time.monotonic() - started,
            }, ensure_ascii=False) + "\n")
            response_handle.flush()

    summary = {
        **manifest,
        "status": "completed_with_failures" if failure_count else "completed",
        "retrieval_report_sha256": sha256(retrieval_path),
        "evidence_packs_sha256": sha256(packs_path),
        "reference_page_any_recall_at_5": retrieval_report["reference_page_any_recall_at_5"],
        "reference_page_full_coverage_at_5": retrieval_report["reference_page_full_coverage_at_5"],
        "qa_success_count": success_count,
        "qa_failure_count": failure_count,
        "qa_elapsed_seconds": time.monotonic() - qa_started,
        "responses_sha256": sha256(responses_path),
        "failures_sha256": sha256(failures_path),
        "permanent_ingestion_started": False,
    }
    (args.output_dir / "run_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if failure_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
