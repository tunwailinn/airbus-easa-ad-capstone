#!/usr/bin/env python3
"""Build deterministic Layer C evidence packs from frozen E5-D development output.

This module does not run retrieval. It consumes the frozen E5-D development
report and frozen E4 chunk store, restores the top-5 passage text by chunk ID,
and emits reproducible QA evidence packs. Benchmark labels and gold answers are
kept outside the prompt payload so they cannot leak expected behavior to the
hosted model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "data_processed/evaluations/e5/e5d_development_evaluation.json"
DEFAULT_CHUNKS = ROOT / "data_processed/indexes/rag_v1_2/e4_section_hybrid/chunks.jsonl"
DEFAULT_OUTPUT = ROOT / "data_processed/evaluations/e5/layer_c/development/evidence_packs.jsonl"
EVIDENCE_PACK_VERSION = "e5-evidence-pack-v1.0"
EVIDENCE_DEPTH = 5


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def load_chunk_map(path: Path) -> dict[str, dict[str, Any]]:
    chunk_map: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            chunk_id = str(row["chunk_id"])
            if chunk_id in chunk_map:
                raise ValueError(f"duplicate chunk_id in frozen chunk store: {chunk_id}")
            chunk_map[chunk_id] = row
    return chunk_map


def build_evidence_pack(
    question_row: dict[str, Any],
    *,
    chunk_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    retrieved = list(question_row.get("retrieved", []))[:EVIDENCE_DEPTH]
    evidence: list[dict[str, Any]] = []
    for position, item in enumerate(retrieved, 1):
        chunk_id = str(item["chunk_id"])
        source = chunk_map.get(chunk_id)
        if source is None:
            raise ValueError(f"retrieved chunk not found in frozen chunk store: {chunk_id}")

        for field in ("ad_number", "source_pdf", "page_start", "page_end", "section"):
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
        "question_id": str(question_row["question_id"]),
        "question": str(question_row["question"]),
        "evidence": evidence,
    }
    return {
        "evidence_pack_version": EVIDENCE_PACK_VERSION,
        "retrieval_freeze_version": "e5-retrieval-freeze-v1.0",
        "evidence_depth": EVIDENCE_DEPTH,
        "question_id": str(question_row["question_id"]),
        "prompt_payload": prompt_payload,
        "prompt_payload_sha256": sha256_bytes(canonical_json_bytes(prompt_payload)),
        "evaluation_metadata": {
            "category": question_row.get("category"),
            "query_mode": question_row.get("query_mode"),
            "answerable_from_ad": question_row.get("answerable_from_ad"),
            "target_ad_number": question_row.get("target_ad_number"),
            "reference_pages": question_row.get("reference_pages", []),
            "rank_at_20": question_row.get("rank_at_20"),
            "source_rank_at_20": question_row.get("source_rank_at_20"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    if report.get("evaluation_version") != "e5-d-eval-v1.0":
        raise ValueError("Layer C requires the frozen e5-d-eval-v1.0 development report")
    if int(report.get("configuration", {}).get("primary_final_k", -1)) != EVIDENCE_DEPTH:
        raise ValueError("frozen E5-D primary evidence depth is not 5")

    chunk_map = load_chunk_map(args.chunks)
    packs = [
        build_evidence_pack(question_row, chunk_map=chunk_map)
        for question_row in report.get("questions", [])
    ]
    if len(packs) != 60:
        raise ValueError(f"expected 60 E5 development evidence packs, found {len(packs)}")
    if len({row["question_id"] for row in packs}) != len(packs):
        raise ValueError("duplicate question IDs in Layer C evidence packs")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in packs:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    manifest = {
        "evidence_pack_version": EVIDENCE_PACK_VERSION,
        "retrieval_freeze_version": "e5-retrieval-freeze-v1.0",
        "source_report": str(args.report),
        "source_report_sha256": sha256_bytes(args.report.read_bytes()),
        "source_chunks": str(args.chunks),
        "source_chunks_sha256": sha256_bytes(args.chunks.read_bytes()),
        "question_count": len(packs),
        "evidence_depth": EVIDENCE_DEPTH,
        "output": str(args.output),
        "output_sha256": sha256_bytes(args.output.read_bytes()),
        "policy": (
            "Prompt payload contains only question text and frozen top-5 source evidence. "
            "Gold target, category, query mode, answerability, and reference pages remain "
            "outside the hosted-model prompt."
        ),
    }
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[progress] Layer C evidence packs written: {args.output}", flush=True)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
