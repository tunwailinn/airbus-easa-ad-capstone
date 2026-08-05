#!/usr/bin/env python3
"""Validate E5 development/final benchmark question files.

This enforces benchmark bookkeeping and obvious leakage rules. It does not grant
human-review status or verify semantic correctness against the PDF; source review
remains mandatory.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from full_corpus_pipeline.prepare_e5_benchmark_families import base_ad_number


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1"

EXPECTED_COUNTS = {
    "development": {
        "total": 60,
        "categories": {
            "identity_lifecycle": 8,
            "applicability": 10,
            "required_action_compliance": 20,
            "referenced_publication": 8,
            "conditional_multi_passage": 8,
            "insufficient_conflict_abstention": 6,
        },
        "modes": {
            "known_document": 36,
            "discovery": 18,
            "abstention_conflict": 6,
        },
    },
    "final_test": {
        "total": 40,
        "categories": {
            "identity_lifecycle": 5,
            "applicability": 7,
            "required_action_compliance": 14,
            "referenced_publication": 5,
            "conditional_multi_passage": 5,
            "insufficient_conflict_abstention": 4,
        },
        "modes": {
            "known_document": 24,
            "discovery": 12,
            "abstention_conflict": 4,
        },
    },
}

REQUIRED_FIELDS = {
    "question_id",
    "split",
    "base_ad_number",
    "category",
    "query_mode",
    "question",
    "answerable_from_ad",
    "reference_pages",
    "reference_sections",
    "reference_answer",
    "review_status",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def validate_split(root: Path, split: str, path: Path) -> list[str]:
    errors: list[str] = []
    expected = EXPECTED_COUNTS[split]
    records = load_jsonl(path)
    family_split = pd.read_csv(root / "family_split.csv", dtype=str)
    allowed_families = set(
        family_split.loc[family_split["split"] == split, "base_ad_number"].astype(str)
    )
    other_families = set(
        family_split.loc[family_split["split"] != split, "base_ad_number"].astype(str)
    )

    if len(records) != expected["total"]:
        errors.append(
            f"{split}: expected {expected['total']} questions, found {len(records)}"
        )

    ids = [str(record.get("question_id", "")) for record in records]
    duplicates = [item for item, count in Counter(ids).items() if count > 1]
    if duplicates:
        errors.append(f"{split}: duplicate question IDs: {duplicates}")

    category_counts = Counter(str(record.get("category", "")) for record in records)
    if dict(category_counts) != expected["categories"]:
        errors.append(
            f"{split}: category counts {dict(category_counts)} != {expected['categories']}"
        )

    mode_counts = Counter(str(record.get("query_mode", "")) for record in records)
    if dict(mode_counts) != expected["modes"]:
        errors.append(
            f"{split}: query-mode counts {dict(mode_counts)} != {expected['modes']}"
        )

    for index, record in enumerate(records, 1):
        prefix = f"{split} record {index} ({record.get('question_id', '?')})"
        missing = REQUIRED_FIELDS - set(record)
        if missing:
            errors.append(f"{prefix}: missing fields {sorted(missing)}")
            continue
        if record["split"] != split:
            errors.append(f"{prefix}: split field is {record['split']!r}")

        family = base_ad_number(str(record["base_ad_number"]))
        if family not in allowed_families:
            errors.append(f"{prefix}: family {family} not in {split} family split")
        if family in other_families:
            errors.append(f"{prefix}: family {family} leaks across split boundary")

        question = str(record["question"])
        target = record.get("target_ad_number")
        mode = str(record["query_mode"])
        answerable = bool(record["answerable_from_ad"])

        if mode == "known_document":
            if not target:
                errors.append(f"{prefix}: known_document requires target_ad_number")
            elif str(target).casefold() not in question.casefold():
                errors.append(
                    f"{prefix}: known_document question must visibly name target AD {target}"
                )
        elif mode == "discovery":
            if not target:
                errors.append(f"{prefix}: discovery requires private target_ad_number")
            elif str(target).casefold() in question.casefold():
                errors.append(
                    f"{prefix}: discovery question leaks target AD identifier {target}"
                )
        elif mode == "abstention_conflict":
            if answerable:
                errors.append(f"{prefix}: abstention_conflict must not be answerable_from_ad")
        else:
            errors.append(f"{prefix}: unsupported query_mode {mode!r}")

        pages = record["reference_pages"]
        if answerable:
            if not isinstance(pages, list) or not pages:
                errors.append(f"{prefix}: answerable question requires reference_pages")
            elif any(int(page) <= 0 for page in pages):
                errors.append(f"{prefix}: reference pages must be positive")
            if not str(record["reference_answer"]).strip():
                errors.append(f"{prefix}: answerable question requires reference_answer")

        if record["review_status"] != "human_verified":
            errors.append(f"{prefix}: review_status must be human_verified")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--split", choices=["development", "final_test", "all"], default="all")
    args = parser.parse_args()

    splits = ["development", "final_test"] if args.split == "all" else [args.split]
    errors: list[str] = []
    for split in splits:
        file_name = "development_questions.jsonl" if split == "development" else "final_questions.jsonl"
        path = args.benchmark_root / file_name
        if not path.exists():
            errors.append(f"{split}: missing question file {path}")
            continue
        print(f"[progress] validating {split} questions: {path}", flush=True)
        errors.extend(validate_split(args.benchmark_root, split, path))

    if errors:
        print(json.dumps({"valid": False, "error_count": len(errors), "errors": errors}, indent=2))
        return 1
    print(json.dumps({"valid": True, "splits": splits}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
