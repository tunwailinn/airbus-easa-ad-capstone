#!/usr/bin/env python3
"""Build deterministic Layer C evidence packs from frozen E5-D development output.

This module does not run retrieval. It consumes the frozen E5-D development
report, the frozen human-reviewed development questions, and the frozen E4 chunk
store. It restores the top-5 passage text by chunk ID and emits reproducible QA
evidence packs. Benchmark labels and gold/reference fields remain outside the
hosted-model prompt payload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = ROOT / "data_processed/evaluations/e5/e5d_development_evaluation.json"
DEFAULT_QUESTIONS = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1/development_questions.jsonl"
DEFAULT_FREEZE = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1/retrieval_freeze.json"
DEFAULT_CHUNKS = ROOT / "data_processed/indexes/rag_v1_2/e4_section_hybrid/chunks.jsonl"
DEFAULT_OUTPUT = ROOT / "data_processed/evaluations/e5/layer_c/development/evidence_packs.jsonl"
EVIDENCE_PACK_VERSION = "e5-evidence-pack-v1.0"
EVIDENCE_DEPTH = 5


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_jsonl_map(path: Path, *, key: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            value = str(row[key])
            if value in rows:
                raise ValueError(f"duplicate {key} in {path}: {value}")
            rows[value] = row
    return rows


def build_evidence_pack(
    retrieval_row: dict[str, Any],
    benchmark_row: dict[str, Any],
    *,
    chunk_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    qid = str(retrieval_row["question_id"])
    if str(benchmark_row["question_id"]) != qid:
        raise ValueError(f"question ID mismatch while building evidence pack: {qid}")

    retrieved = list(retrieval_row.get("retrieved", []))[:EVIDENCE_DEPTH]
    evidence: list[dict[str, Any]] = []
    for position, item in enumerate(retrieved, 1):
        chunk_id = str(item["chunk_id"])
        source = chunk_map.get(chunk_id)
        if source is None:
            raise ValueError(f"retrieved chunk not found in frozen chunk store: {chunk_id}")

        for field in ("ad_number", "page_start", "page_end", "section"):
            if str(item.get(field)) != str(source.get(field)):
                raise ValueError(
                    f"frozen E5-D metadata mismatch for {chunk_id}: {field} "
                    f"report={item.get(field)!r} chunk_store={source.get(field)!r}"
                )

        evidence.append(
            {
                "evidence_id": f"EV{position}",
                "rank": position,
                "chunk_id": chunk_id,
                "ad_number": str(source["ad_number"]),
                "source_pdf": str(source["source_pdf"]),
                "page_start": int(source["page_start"]),
                "page_end": int(source["page_end"]),
                "section": str(source["section"]),
                "text": str(source["text"]),
            }
        )

    prompt_payload = {
        "question_id": qid,
        "question": str(benchmark_row["question"]),
        "evidence": evidence,
    }
    return {
        "evidence_pack_version": EVIDENCE_PACK_VERSION,
        "retrieval_freeze_version": "e5-retrieval-freeze-v1.0",
        "evidence_depth": EVIDENCE_DEPTH,
        "question_id": qid,
        "prompt_payload": prompt_payload,
        "prompt_payload_sha256": sha256_bytes(canonical_json_bytes(prompt_payload)),
        "evaluation_metadata": {
            "category": benchmark_row.get("category"),
            "query_mode": benchmark_row.get("query_mode"),
            "answerable_from_ad": benchmark_row.get("answerable_from_ad"),
            "target_ad_number": benchmark_row.get("target_ad_number"),
            "reference_pages": benchmark_row.get("reference_pages", []),
            "rank_at_20": retrieval_row.get("rank_at_20"),
            "source_rank_at_20": retrieval_row.get("source_rank_at_20"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--retrieval-freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    freeze = json.loads(args.retrieval_freeze.read_text(encoding="utf-8"))
    if freeze.get("freeze_version") != "e5-retrieval-freeze-v1.0":
        raise ValueError("unexpected E5 retrieval freeze version")

    expected_benchmark = freeze.get("development_benchmark", {})
    actual_questions_sha = sha256_bytes(args.questions.read_bytes())
    if actual_questions_sha != expected_benchmark.get("sha256"):
        raise ValueError("development question benchmark hash differs from retrieval freeze")

    report = json.loads(args.report.read_text(encoding="utf-8"))
    if report.get("evaluation_version") != "e5-d-eval-v1.0":
        raise ValueError("Layer C requires the frozen e5-d-eval-v1.0 development report")
    if report.get("benchmark_sha256") != actual_questions_sha:
        raise ValueError("E5-D report benchmark hash differs from frozen development questions")
    if int(report.get("configuration", {}).get("primary_final_k", -1)) != EVIDENCE_DEPTH:
        raise ValueError("frozen E5-D primary evidence depth is not 5")

    benchmark_map = load_jsonl_map(args.questions, key="question_id")
    chunk_map = load_jsonl_map(args.chunks, key="chunk_id")
    retrieval_rows = list(report.get("questions", []))
    if len(retrieval_rows) != int(expected_benchmark.get("question_count", -1)):
        raise ValueError("E5-D report question count differs from retrieval freeze")
    if set(benchmark_map) != {str(row["question_id"]) for row in retrieval_rows}:
        raise ValueError("development benchmark and E5-D report question IDs differ")

    packs = [
        build_evidence_pack(
            retrieval_row,
            benchmark_map[str(retrieval_row["question_id"])],
            chunk_map=chunk_map,
        )
        for retrieval_row in retrieval_rows
    ]
    if len({row["question_id"] for row in packs}) != len(packs):
        raise ValueError("duplicate question IDs in Layer C evidence packs")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in packs:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    manifest = {
        "evidence_pack_version": EVIDENCE_PACK_VERSION,
        "retrieval_freeze_version": "e5-retrieval-freeze-v1.0",
        "retrieval_freeze_sha256": sha256_bytes(args.retrieval_freeze.read_bytes()),
        "source_report": str(args.report),
        "source_report_sha256": sha256_bytes(args.report.read_bytes()),
        "source_questions": str(args.questions),
        "source_questions_sha256": actual_questions_sha,
        "source_chunks": str(args.chunks),
        "source_chunks_sha256": sha256_bytes(args.chunks.read_bytes()),
        "question_count": len(packs),
        "evidence_depth": EVIDENCE_DEPTH,
        "output": str(args.output),
        "output_sha256": sha256_bytes(args.output.read_bytes()),
        "policy": (
            "Prompt payload contains only question ID/text and frozen top-5 source evidence. "
            "Category, query mode, answerability, target AD, reference pages, and retrieval "
            "evaluation labels remain outside the hosted-model prompt."
        ),
    }
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[progress] Layer C evidence packs written: {args.output}", flush=True)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
