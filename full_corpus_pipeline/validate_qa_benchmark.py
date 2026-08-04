#!/usr/bin/env python3
"""Validate the locked 50-question QA benchmark."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from full_corpus_pipeline.build_qa_benchmark import CATEGORY_COUNTS


ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "evaluation_sets/easa_airbus_ad_qa_50_v2/questions.jsonl"


def main() -> int:
    questions = [json.loads(line) for line in DEFAULT.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(questions) == 50, len(questions)
    assert len({item["question_id"] for item in questions}) == 50
    assert Counter(item["category"] for item in questions) == Counter(CATEGORY_COUNTS)
    assert all("evidence" not in key.casefold() for item in questions for key in item)
    assert all(item["reference_pages"] for item in questions if item["answerable_from_ad"])
    assert all(not item["reference_pages"] for item in questions if not item["answerable_from_ad"])
    print("Validated 50 locked QA questions and category counts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
