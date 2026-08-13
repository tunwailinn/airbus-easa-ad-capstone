#!/usr/bin/env python3
"""Build development-only Layer C oracle/reference-page evidence packs.

The hosted model never receives benchmark answers or labels. For answerable
questions, oracle evidence is selected deterministically from the benchmark's
target AD and human-reviewed reference pages, with reference sections used only
to prioritize source chunks. For negative/abstention questions, which
intentionally have no answer-bearing reference pages, the original frozen E5-D
top-5 evidence is retained as a negative control.

This module never runs retrieval and never opens the final benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUESTIONS = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1/development_questions.jsonl"
DEFAULT_FREEZE = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1/retrieval_freeze.json"
DEFAULT_CHUNKS = ROOT / "data_processed/indexes/rag_v1_2/e4_section_hybrid/chunks.jsonl"
DEFAULT_RETRIEVAL_REPORT = ROOT / "data_processed/evaluations/e5/e5d_development_evaluation.json"
DEFAULT_RETRIEVED_PACKS = ROOT / "data_processed/evaluations/e5/layer_c/development/evidence_packs.jsonl"
DEFAULT_OUTPUT = ROOT / "data_processed/evaluations/e5/layer_c/development/oracle_evidence_packs.jsonl"
ORACLE_EVIDENCE_PACK_VERSION = "e5-oracle-evidence-pack-v1.0"
ORACLE_EVIDENCE_MAX_DEPTH = 5


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def map_unique(rows: list[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = str(row[key])
        if value in mapped:
            raise ValueError(f"duplicate {label} {key}: {value}")
        mapped[value] = row
    return mapped


def pages_overlap(chunk: dict[str, Any], reference_pages: list[int]) -> bool:
    start = int(chunk.get("page_start") or 0)
    end = int(chunk.get("page_end") or start)
    return any(start <= int(page) <= end for page in reference_pages)


def section_key(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def section_matches(chunk: dict[str, Any], reference_sections: list[str]) -> bool:
    if not reference_sections:
        return False
    current = section_key(chunk.get("section"))
    expected = {section_key(value) for value in reference_sections}
    return current in expected


def oracle_sort_key(
    chunk: dict[str, Any], reference_pages: list[int], reference_sections: list[str]
) -> tuple[Any, ...]:
    start = int(chunk.get("page_start") or 0)
    end = int(chunk.get("page_end") or start)
    covered = sum(start <= int(page) <= end for page in reference_pages)
    return (
        0 if section_matches(chunk, reference_sections) else 1,
        -covered,
        start,
        end,
        str(chunk.get("chunk_id", "")),
    )


def select_answerable_oracle_chunks(
    question: dict[str, Any], chunks: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], str]:
    qid = str(question["question_id"])
    target_ad = str(question.get("target_ad_number") or "").strip()
    reference_pages = [int(page) for page in question.get("reference_pages", [])]
    reference_sections = [str(value) for value in question.get("reference_sections", [])]
    if not target_ad:
        raise ValueError(f"{qid}: answerable oracle question has no target_ad_number")
    if not reference_pages:
        raise ValueError(f"{qid}: answerable oracle question has no reference_pages")

    target_chunks = [row for row in chunks if str(row.get("ad_number")) == target_ad]
    overlapping = [row for row in target_chunks if pages_overlap(row, reference_pages)]
    if not overlapping:
        raise ValueError(
            f"{qid}: no frozen chunks for target AD {target_ad} overlap reference pages {reference_pages}"
        )

    source_pdfs = {str(row.get("source_pdf")) for row in overlapping}
    if len(source_pdfs) != 1:
        section_overlapping = [row for row in overlapping if section_matches(row, reference_sections)]
        section_sources = {str(row.get("source_pdf")) for row in section_overlapping}
        if len(section_sources) == 1:
            chosen_source = next(iter(section_sources))
            overlapping = [row for row in overlapping if str(row.get("source_pdf")) == chosen_source]
        else:
            raise ValueError(
                f"{qid}: oracle source is ambiguous across physical PDFs for {target_ad}: "
                f"{sorted(source_pdfs)}"
            )
    else:
        chosen_source = next(iter(source_pdfs))

    ordered = sorted(
        overlapping,
        key=lambda row: oracle_sort_key(row, reference_pages, reference_sections),
    )

    # Guarantee reference-page coverage before filling the remaining oracle slots.
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for page in reference_pages:
        candidates = [
            row
            for row in ordered
            if int(row.get("page_start") or 0) <= page <= int(row.get("page_end") or row.get("page_start") or 0)
        ]
        if not candidates:
            raise ValueError(f"{qid}: reference page {page} is not covered by oracle chunks")
        chosen = candidates[0]
        chunk_id = str(chosen["chunk_id"])
        if chunk_id not in selected_ids:
            selected.append(chosen)
            selected_ids.add(chunk_id)

    for row in ordered:
        if len(selected) >= ORACLE_EVIDENCE_MAX_DEPTH:
            break
        chunk_id = str(row["chunk_id"])
        if chunk_id not in selected_ids:
            selected.append(row)
            selected_ids.add(chunk_id)

    if len(selected) > ORACLE_EVIDENCE_MAX_DEPTH:
        raise ValueError(
            f"{qid}: reference-page coverage needs more than {ORACLE_EVIDENCE_MAX_DEPTH} chunks"
        )
    return selected, chosen_source


def render_evidence(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for position, source in enumerate(chunks, 1):
        evidence.append(
            {
                "evidence_id": f"EV{position}",
                "rank": position,
                "chunk_id": str(source["chunk_id"]),
                "ad_number": str(source["ad_number"]),
                "source_pdf": str(source["source_pdf"]),
                "page_start": int(source["page_start"]),
                "page_end": int(source["page_end"]),
                "section": str(source["section"]),
                "text": str(source["text"]),
            }
        )
    return evidence


def build_oracle_pack(
    question: dict[str, Any],
    *,
    chunks: list[dict[str, Any]],
    retrieved_pack: dict[str, Any],
    retrieval_row: dict[str, Any],
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
            raise ValueError(f"{qid}: frozen negative-control evidence is malformed")
        evidence = [dict(item) for item in original_evidence]
        chosen_source = None
        evidence_source = "frozen_top5_negative_control"

    prompt_payload = {
        "question_id": qid,
        "question": str(question["question"]),
        "evidence": evidence,
    }
    return {
        "evidence_pack_version": ORACLE_EVIDENCE_PACK_VERSION,
        "retrieval_freeze_version": "e5-retrieval-freeze-v1.0",
        "evidence_condition": "oracle_reference_evidence",
        "evidence_source": evidence_source,
        "evidence_depth": len(evidence),
        "evidence_max_depth": ORACLE_EVIDENCE_MAX_DEPTH,
        "question_id": qid,
        "prompt_payload": prompt_payload,
        "prompt_payload_sha256": sha256_bytes(canonical_json_bytes(prompt_payload)),
        "evaluation_metadata": {
            "category": question.get("category"),
            "query_mode": question.get("query_mode"),
            "answerable_from_ad": answerable,
            "target_ad_number": question.get("target_ad_number"),
            "reference_pages": question.get("reference_pages", []),
            "reference_sections": question.get("reference_sections", []),
            "oracle_source_pdf": chosen_source,
            "frozen_retrieval_rank_at_20": retrieval_row.get("rank_at_20"),
            "frozen_retrieval_source_rank_at_20": retrieval_row.get("source_rank_at_20"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--retrieval-freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    parser.add_argument("--retrieval-report", type=Path, default=DEFAULT_RETRIEVAL_REPORT)
    parser.add_argument("--retrieved-packs", type=Path, default=DEFAULT_RETRIEVED_PACKS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    freeze = json.loads(args.retrieval_freeze.read_text(encoding="utf-8"))
    if freeze.get("freeze_version") != "e5-retrieval-freeze-v1.0":
        raise ValueError("unexpected E5 retrieval freeze version")
    expected_benchmark = freeze.get("development_benchmark", {})
    questions_sha = sha256_bytes(args.questions.read_bytes())
    if questions_sha != expected_benchmark.get("sha256"):
        raise ValueError("development question benchmark hash differs from retrieval freeze")

    questions = load_jsonl(args.questions)
    if len(questions) != int(expected_benchmark.get("question_count", -1)):
        raise ValueError("development question count differs from retrieval freeze")
    question_map = map_unique(questions, "question_id", "question")

    retrieval_report = json.loads(args.retrieval_report.read_text(encoding="utf-8"))
    if retrieval_report.get("evaluation_version") != "e5-d-eval-v1.0":
        raise ValueError("oracle condition requires frozen e5-d-eval-v1.0 report")
    if retrieval_report.get("benchmark_sha256") != questions_sha:
        raise ValueError("retrieval report benchmark hash differs from development questions")
    retrieval_map = map_unique(list(retrieval_report.get("questions", [])), "question_id", "retrieval row")

    retrieved_pack_rows = load_jsonl(args.retrieved_packs)
    retrieved_pack_map = map_unique(retrieved_pack_rows, "question_id", "retrieved evidence pack")
    if set(question_map) != set(retrieval_map) or set(question_map) != set(retrieved_pack_map):
        raise ValueError("oracle inputs disagree on development question membership")

    chunks = load_jsonl(args.chunks)
    packs = [
        build_oracle_pack(
            question_map[qid],
            chunks=chunks,
            retrieved_pack=retrieved_pack_map[qid],
            retrieval_row=retrieval_map[qid],
        )
        for qid in question_map
    ]

    answerable_count = sum(bool(question_map[qid]["answerable_from_ad"]) for qid in question_map)
    negative_count = len(packs) - answerable_count
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in packs:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "evidence_pack_version": ORACLE_EVIDENCE_PACK_VERSION,
        "evidence_condition": "oracle_reference_evidence",
        "retrieval_freeze_version": "e5-retrieval-freeze-v1.0",
        "retrieval_freeze_sha256": sha256_bytes(args.retrieval_freeze.read_bytes()),
        "source_questions": str(args.questions),
        "source_questions_sha256": questions_sha,
        "source_chunks": str(args.chunks),
        "source_chunks_sha256": sha256_bytes(args.chunks.read_bytes()),
        "source_retrieval_report": str(args.retrieval_report),
        "source_retrieval_report_sha256": sha256_bytes(args.retrieval_report.read_bytes()),
        "source_retrieved_packs": str(args.retrieved_packs),
        "source_retrieved_packs_sha256": sha256_bytes(args.retrieved_packs.read_bytes()),
        "question_count": len(packs),
        "answerable_reference_page_oracle_count": answerable_count,
        "negative_control_count": negative_count,
        "evidence_max_depth": ORACLE_EVIDENCE_MAX_DEPTH,
        "output": str(args.output),
        "output_sha256": sha256_bytes(args.output.read_bytes()),
        "policy": (
            "The hosted model receives no reference answer, required-condition label, category, query mode, "
            "answerability label, target label, or reference-page label. Answerable questions receive source "
            "chunks from the private target AD on human-reviewed reference pages, prioritized by reference "
            "section. Negative/abstention questions retain frozen top-5 evidence because the benchmark "
            "intentionally defines no answer-bearing reference page. No retrieval is run or retuned."
        ),
    }
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[progress] Layer C oracle evidence packs written: {args.output}", flush=True)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
