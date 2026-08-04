#!/usr/bin/env python3
"""Score saved QA outputs for answer, source/page citation, and abstention."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "evaluation_sets/easa_airbus_ad_qa_50_v2/questions.jsonl"


def tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9][a-z0-9./-]*", value.casefold()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("answers", type=Path, help="JSONL with question_id, answer, citations, insufficient_information")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    references = {item["question_id"]: item for item in (json.loads(line) for line in QUESTIONS.read_text().splitlines() if line.strip())}
    predictions = {item["question_id"]: item for item in (json.loads(line) for line in args.answers.read_text().splitlines() if line.strip())}
    rows = []
    for question_id, reference in references.items():
        prediction = predictions.get(question_id, {"answer": "", "citations": [], "insufficient_information": True})
        expected_abstention = not reference["answerable_from_ad"]
        abstention_correct = bool(prediction.get("insufficient_information")) == expected_abstention
        expected_tokens = tokens(reference["reference_answer"])
        answer_tokens = tokens(prediction.get("answer", ""))
        overlap = len(expected_tokens & answer_tokens) / max(len(expected_tokens), 1)
        citation_correct = expected_abstention or any(
            citation.get("ad_number", "").casefold() == reference["target_ad_number"].casefold()
            and citation.get("page") in reference["reference_pages"]
            for citation in prediction.get("citations", [])
        )
        rows.append({"question_id": question_id, "token_recall": overlap, "citation_correct": citation_correct, "abstention_correct": abstention_correct})
    count = len(rows)
    report = {
        "question_count": count,
        "automatic_answer_token_recall": sum(row["token_recall"] for row in rows) / count,
        "page_citation_correctness": sum(row["citation_correct"] for row in rows) / count,
        "abstention_accuracy": sum(row["abstention_correct"] for row in rows) / count,
        "note": "Final QA correctness requires human grading; token recall is diagnostic only.",
        "questions": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "questions"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
