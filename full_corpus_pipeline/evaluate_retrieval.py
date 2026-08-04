#!/usr/bin/env python3
"""Evaluate dense-only or hybrid retrieval on the locked QA benchmark."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from full_corpus_pipeline.retrieval import HybridIndex


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "evaluation_sets/easa_airbus_ad_qa_50_v2/questions.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index_dir", type=Path)
    parser.add_argument("--mode", choices=("dense", "hybrid"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    questions = [json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8").splitlines() if line.strip()]
    answerable = [item for item in questions if item["answerable_from_ad"]]
    index = HybridIndex(args.index_dir)
    rows = []
    for question in answerable:
        if args.mode == "dense":
            results = index.search_dense_only(question["question"], limit=5)
        else:
            results = index.search(question["question"], limit=5)
        relevance = [
            result["ad_number"].casefold() == question["target_ad_number"].casefold()
            and any(result["page_start"] <= page <= result["page_end"] for page in question["reference_pages"])
            for result in results
        ]
        rank = next((position for position, relevant in enumerate(relevance, 1) if relevant), None)
        rows.append(
            {
                "question_id": question["question_id"], "rank": rank,
                "correct_source_at_5": any(result["ad_number"].casefold() == question["target_ad_number"].casefold() for result in results),
                "retrieved_chunk_ids": [result["chunk_id"] for result in results],
            }
        )
    count = len(rows)
    report = {
        "mode": args.mode, "answerable_question_count": count,
        "recall_at_1": sum(row["rank"] == 1 for row in rows) / count,
        "recall_at_3": sum(row["rank"] is not None and row["rank"] <= 3 for row in rows) / count,
        "recall_at_5": sum(row["rank"] is not None and row["rank"] <= 5 for row in rows) / count,
        "mrr": sum(1 / row["rank"] if row["rank"] else 0 for row in rows) / count,
        "ndcg_at_5": sum(1 / math.log2(row["rank"] + 1) if row["rank"] else 0 for row in rows) / count,
        "correct_source_at_5": sum(row["correct_source_at_5"] for row in rows) / count,
        "questions": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "questions"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
