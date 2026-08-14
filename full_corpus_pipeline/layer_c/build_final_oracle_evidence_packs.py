#!/usr/bin/env python3
"""Build diagnostic oracle/reference evidence packs for the frozen E5 final benchmark.

This command is valid only after the one-time primary final run has been preserved.
It never reruns or changes retrieval. For the 36 answerable final questions it
selects frozen E4 chunks from the private human-reviewed target AD/reference pages.
For the 4 abstention/conflict questions it retains the exact primary frozen top-5
prompt evidence as a negative control.

Only question_id, question and evidence enter the hosted prompt. Reference answers,
private labels and scoring metadata remain outside the prompt payload. Oracle results
are post-hoc diagnostics and must never replace the strict primary final result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from full_corpus_pipeline.layer_c.build_oracle_evidence_packs import (
    ORACLE_EVIDENCE_MAX_DEPTH,
    canonical_json_bytes,
    load_jsonl,
    map_unique,
    render_evidence,
    select_answerable_oracle_chunks,
    sha256_bytes,
)
from full_corpus_pipeline.layer_c.run_final_benchmark import (
    FINAL_EVIDENCE_PACK_VERSION,
    FINAL_RETRIEVAL_EVAL_VERSION,
)


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_ROOT = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1"
PRIMARY_DIR = ROOT / "data_processed/evaluations/e5/layer_c/final/primary"
ORACLE_DIR = ROOT / "data_processed/evaluations/e5/layer_c/final/oracle"

DEFAULT_QUESTIONS = BENCHMARK_ROOT / "final_questions.jsonl"
DEFAULT_FINAL_LOCK = BENCHMARK_ROOT / "final_lock.json"
DEFAULT_HOSTED_FREEZE = BENCHMARK_ROOT / "hosted_qa_freeze.json"
DEFAULT_CHUNKS = ROOT / "data_processed/indexes/rag_v1_2/e4_section_hybrid/chunks.jsonl"
DEFAULT_RETRIEVAL_REPORT = PRIMARY_DIR / "retrieval_report.json"
DEFAULT_RETRIEVED_PACKS = PRIMARY_DIR / "evidence_packs.jsonl"
DEFAULT_OUTPUT = ORACLE_DIR / "evidence_packs.jsonl"

FINAL_ORACLE_EVIDENCE_PACK_VERSION = "e5-final-oracle-evidence-pack-v1.0"
FINAL_QUESTION_COUNT = 40
FINAL_ANSWERABLE_COUNT = 36
FINAL_NEGATIVE_COUNT = 4


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_final_lock() -> None:
    subprocess.run(
        [sys.executable, "-m", "full_corpus_pipeline.layer_c.validate_final_benchmark_lock"],
        cwd=ROOT,
        check=True,
    )


def validate_hosted_freeze(path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "full_corpus_pipeline.layer_c.validate_hosted_qa_freeze",
            "--freeze",
            str(path),
        ],
        cwd=ROOT,
        check=True,
    )


def build_final_oracle_pack(
    question: dict[str, Any],
    *,
    chunks: list[dict[str, Any]],
    retrieved_pack: dict[str, Any],
    retrieval_row: dict[str, Any],
    final_questions_sha256: str,
) -> dict[str, Any]:
    qid = str(question["question_id"])
    answerable = bool(question["answerable_from_ad"])

    if answerable:
        selected_chunks, chosen_source = select_answerable_oracle_chunks(question, chunks)
        evidence = render_evidence(selected_chunks)
        evidence_source = "oracle_reference_pages"
    else:
        original_payload = retrieved_pack.get("prompt_payload") or {}
        original_evidence = original_payload.get("evidence", [])
        if not isinstance(original_evidence, list):
            raise ValueError(f"{qid}: primary negative-control evidence is malformed")
        evidence = [dict(item) for item in original_evidence]
        chosen_source = None
        evidence_source = "primary_frozen_top5_negative_control"

    payload = {
        "question_id": qid,
        "question": str(question["question"]),
        "evidence": evidence,
    }
    return {
        "evidence_pack_version": FINAL_ORACLE_EVIDENCE_PACK_VERSION,
        "evidence_condition": "oracle_reference_evidence",
        "evidence_source": evidence_source,
        "evidence_depth": len(evidence),
        "evidence_max_depth": ORACLE_EVIDENCE_MAX_DEPTH,
        "final_questions_sha256": final_questions_sha256,
        "question_id": qid,
        "prompt_payload": payload,
        "prompt_payload_sha256": sha256_bytes(canonical_json_bytes(payload)),
        "evaluation_metadata": {
            "category": question.get("category"),
            "query_mode": question.get("query_mode"),
            "answerable_from_ad": answerable,
            "target_ad_number": question.get("target_ad_number"),
            "reference_pages": question.get("reference_pages", []),
            "reference_sections": question.get("reference_sections", []),
            "oracle_source_pdf": chosen_source,
            "primary_retrieval_rank_at_20": retrieval_row.get("rank_at_20"),
            "primary_retrieval_source_rank_at_20": retrieval_row.get("source_rank_at_20"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--final-lock", type=Path, default=DEFAULT_FINAL_LOCK)
    parser.add_argument("--hosted-freeze", type=Path, default=DEFAULT_HOSTED_FREEZE)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    parser.add_argument("--retrieval-report", type=Path, default=DEFAULT_RETRIEVAL_REPORT)
    parser.add_argument("--retrieved-packs", type=Path, default=DEFAULT_RETRIEVED_PACKS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    # Both locks must remain valid before any diagnostic oracle artifact is built.
    validate_final_lock()
    validate_hosted_freeze(args.hosted_freeze)

    for path in (
        args.questions,
        args.final_lock,
        args.hosted_freeze,
        args.chunks,
        args.retrieval_report,
        args.retrieved_packs,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    final_lock = json.loads(args.final_lock.read_text(encoding="utf-8"))
    if final_lock.get("lock_version") != "e5-final-benchmark-lock-v1.0":
        raise ValueError("unexpected final benchmark lock version")
    if final_lock.get("status") != "human_verified_and_locked":
        raise ValueError("final benchmark is not human_verified_and_locked")

    questions_sha = sha256(args.questions)
    locked_questions = final_lock.get("questions", {})
    if questions_sha != locked_questions.get("sha256"):
        raise ValueError("final question hash differs from final benchmark lock")

    questions = load_jsonl(args.questions)
    if len(questions) != FINAL_QUESTION_COUNT:
        raise ValueError(f"expected {FINAL_QUESTION_COUNT} final questions, found {len(questions)}")
    if any(row.get("split") != "final_test" for row in questions):
        raise ValueError("final oracle accepts final_test questions only")
    if any(row.get("review_status") != "human_verified" for row in questions):
        raise ValueError("all final oracle questions must remain human_verified")
    question_map = map_unique(questions, "question_id", "final question")

    retrieval_report = json.loads(args.retrieval_report.read_text(encoding="utf-8"))
    if retrieval_report.get("evaluation_version") != FINAL_RETRIEVAL_EVAL_VERSION:
        raise ValueError("final oracle requires the preserved frozen final E5-D retrieval report")
    if retrieval_report.get("benchmark_sha256") != questions_sha:
        raise ValueError("primary final retrieval report benchmark hash mismatch")
    retrieval_map = map_unique(
        list(retrieval_report.get("questions", [])), "question_id", "primary retrieval row"
    )

    retrieved_pack_rows = load_jsonl(args.retrieved_packs)
    retrieved_pack_map = map_unique(
        retrieved_pack_rows, "question_id", "primary final evidence pack"
    )
    if len(retrieved_pack_rows) != FINAL_QUESTION_COUNT:
        raise ValueError("primary final evidence-pack count is not 40")
    for row in retrieved_pack_rows:
        if row.get("evidence_pack_version") != FINAL_EVIDENCE_PACK_VERSION:
            raise ValueError("unexpected primary final evidence-pack version")
        if row.get("evidence_condition") != "frozen_e5d_top5":
            raise ValueError("primary final evidence-pack condition is not frozen_e5d_top5")

    if set(question_map) != set(retrieval_map) or set(question_map) != set(retrieved_pack_map):
        raise ValueError("final oracle inputs disagree on question membership")

    chunks = load_jsonl(args.chunks)
    packs = [
        build_final_oracle_pack(
            question_map[qid],
            chunks=chunks,
            retrieved_pack=retrieved_pack_map[qid],
            retrieval_row=retrieval_map[qid],
            final_questions_sha256=questions_sha,
        )
        for qid in question_map
    ]

    answerable_count = sum(bool(question_map[qid]["answerable_from_ad"]) for qid in question_map)
    negative_count = len(packs) - answerable_count
    if answerable_count != FINAL_ANSWERABLE_COUNT or negative_count != FINAL_NEGATIVE_COUNT:
        raise ValueError(
            f"unexpected final oracle accounting: {answerable_count} answerable / {negative_count} negative"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise ValueError(f"refusing to overwrite final oracle evidence packs: {args.output}")
    with args.output.open("w", encoding="utf-8") as handle:
        for row in packs:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "evidence_pack_version": FINAL_ORACLE_EVIDENCE_PACK_VERSION,
        "evidence_condition": "oracle_reference_evidence",
        "diagnostic_only": True,
        "final_benchmark_lock_version": final_lock["lock_version"],
        "final_benchmark_lock_sha256": sha256(args.final_lock),
        "hosted_qa_freeze_sha256": sha256(args.hosted_freeze),
        "source_questions": str(args.questions),
        "source_questions_sha256": questions_sha,
        "source_chunks": str(args.chunks),
        "source_chunks_sha256": sha256(args.chunks),
        "source_primary_retrieval_report": str(args.retrieval_report),
        "source_primary_retrieval_report_sha256": sha256(args.retrieval_report),
        "source_primary_evidence_packs": str(args.retrieved_packs),
        "source_primary_evidence_packs_sha256": sha256(args.retrieved_packs),
        "question_count": len(packs),
        "answerable_reference_page_oracle_count": answerable_count,
        "negative_control_count": negative_count,
        "evidence_max_depth": ORACLE_EVIDENCE_MAX_DEPTH,
        "output": str(args.output),
        "output_sha256": sha256(args.output),
        "policy": (
            "Post-hoc final diagnostic only. No retrieval is rerun or changed. The 36 answerable questions "
            "receive source chunks from the human-reviewed target AD/reference pages; the 4 abstention "
            "questions retain their exact primary frozen top-5 evidence as negative controls. Reference "
            "answers and private scoring labels never enter the hosted prompt. This condition cannot replace "
            "the strict primary final score."
        ),
    }
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("[progress] final oracle evidence packs written", flush=True)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
