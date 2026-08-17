#!/usr/bin/env python3
"""Diagnose whether human-approved source quotations are literally present in unseen top-5 evidence.

This is a post-hoc diagnostic only. It does not alter the preserved temporary
retrieval report, evidence packs, questions, or hosted responses. The purpose is
to distinguish page overlap from answer-bearing passage support.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUESTIONS = ROOT / "evaluation_sets/unseen_incoming_5_v1/unseen_questions.jsonl"
DEFAULT_PACKS = ROOT / "data_processed/evaluations/unseen_5/temporary_primary/evidence_packs.jsonl"
DEFAULT_OUTPUT = ROOT / "data_processed/evaluations/unseen_5/temporary_primary/evaluation/reference_quote_containment_diagnostic.json"
VERSION = "unseen-5-reference-quote-containment-diagnostic-v1.0"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def norm(value: str) -> str:
    value = value.replace("\u00ad", "")
    value = re.sub(r"-\s*\n\s*", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip().casefold()


def unique_map(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = str(row[key])
        if value in out:
            raise ValueError(f"duplicate {key}: {value}")
        out[value] = row
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--evidence-packs", type=Path, default=DEFAULT_PACKS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    questions = load_jsonl(args.questions)
    packs = unique_map(load_jsonl(args.evidence_packs), "question_id")
    if len(questions) != 15 or set(packs) != {str(q["question_id"]) for q in questions}:
        raise ValueError("unseen question/evidence-pack membership mismatch")

    rows = []
    answerable_checks = 0
    all_quotes_contained_count = 0
    any_quote_contained_count = 0
    for question in questions:
        qid = str(question["question_id"])
        evidence = packs[qid].get("prompt_payload", {}).get("evidence", [])
        normalized_evidence = [norm(str(item.get("text", ""))) for item in evidence]
        quote_results = []
        for source in question.get("source_evidence", []):
            quote = str(source.get("quote", ""))
            normalized_quote = norm(quote)
            supporting = [
                str(item.get("evidence_id"))
                for item, text in zip(evidence, normalized_evidence)
                if normalized_quote and normalized_quote in text
            ]
            quote_results.append(
                {
                    "page": int(source.get("page", 0)),
                    "section": source.get("section"),
                    "quote_contained": bool(supporting),
                    "supporting_evidence_ids": supporting,
                }
            )
        any_contained = any(item["quote_contained"] for item in quote_results) if quote_results else False
        all_contained = all(item["quote_contained"] for item in quote_results) if quote_results else False
        if bool(question.get("answerable_from_ad")):
            answerable_checks += 1
            any_quote_contained_count += int(any_contained)
            all_quotes_contained_count += int(all_contained)
        rows.append(
            {
                "question_id": qid,
                "answerable_from_ad": bool(question.get("answerable_from_ad")),
                "reference_pages": question.get("reference_pages", []),
                "any_reference_quote_contained_in_top5": any_contained,
                "all_reference_quotes_contained_in_top5": all_contained,
                "quote_results": quote_results,
            }
        )

    report = {
        "version": VERSION,
        "scope": "post-hoc unseen temporary passage-support diagnostic",
        "answerable_question_count": answerable_checks,
        "any_reference_quote_containment_at_5": (
            any_quote_contained_count / answerable_checks if answerable_checks else None
        ),
        "all_reference_quotes_containment_at_5": (
            all_quotes_contained_count / answerable_checks if answerable_checks else None
        ),
        "rows": rows,
        "policy": (
            "Diagnostic only. This exact normalized-containment check distinguishes answer-bearing reference text "
            "from page-number overlap and does not replace or modify the frozen first-pass temporary retrieval metrics."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
