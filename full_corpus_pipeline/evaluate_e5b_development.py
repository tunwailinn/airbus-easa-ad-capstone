#!/usr/bin/env python3
"""Evaluate E5-B on the human-reviewed E5 development benchmark.

E5-B is development-only tuning. The final 40-question benchmark remains sealed.
The evaluator uses the same relevance/source/page definitions as E5-A and adds a
paired rank comparison against the saved E5-A report when available.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any

from full_corpus_pipeline.e5b_retrieval import (
    DISCOVERY_POOL_LIMIT,
    DOCUMENT_LIMIT,
    FINAL_CANDIDATE_LIMIT,
    WITHIN_DOCUMENT_LIMIT,
    EvidenceAssemblyRetriever,
)
from full_corpus_pipeline.evaluate_e5a_development import (
    EXPECTED_RETRIEVAL_BUILD_VERSION,
    breakdown,
    load_questions,
    relevance_rank,
    route_matches_declared,
    source_rank,
    summarize,
    validate_index,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = ROOT / "data_processed/indexes/rag_v1_2/e4_section_hybrid"
DEFAULT_QUESTIONS = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1/development_questions.jsonl"
DEFAULT_E5A_REPORT = ROOT / "data_processed/evaluations/e5/e5a_development_evaluation.json"
DEFAULT_OUTPUT = ROOT / "data_processed/evaluations/e5/e5b_development_evaluation.json"
EVALUATION_VERSION = "e5-b-eval-v1.0"
FINAL_K = 5


def _rank_or_inf(value: Any) -> float:
    return float(value) if value is not None else math.inf


def paired_vs_e5a(
    *,
    e5a_report: dict[str, Any],
    e5b_rows: list[dict[str, Any]],
    benchmark_sha256: str,
) -> dict[str, Any]:
    if e5a_report.get("benchmark_sha256") != benchmark_sha256:
        raise ValueError("E5-A report benchmark SHA does not match E5-B benchmark")
    e5a_rows = {
        str(row["question_id"]): row
        for row in e5a_report.get("questions", [])
        if bool(row.get("answerable_from_ad"))
    }
    e5b_by_id = {str(row["question_id"]): row for row in e5b_rows}
    if set(e5a_rows) != set(e5b_by_id):
        raise ValueError("E5-A/E5-B answerable question membership differs")

    better_b = better_a = ties = 0
    top5_gain = top5_loss = 0
    per_question: list[dict[str, Any]] = []
    for question_id in sorted(e5b_by_id):
        a_rank = _rank_or_inf(e5a_rows[question_id].get("rank_at_20"))
        b_rank = _rank_or_inf(e5b_by_id[question_id].get("rank_at_20"))
        if b_rank < a_rank:
            better_b += 1
            relation = "e5b_better"
        elif a_rank < b_rank:
            better_a += 1
            relation = "e5a_better"
        else:
            ties += 1
            relation = "tie"
        a_top5 = a_rank <= FINAL_K
        b_top5 = b_rank <= FINAL_K
        if b_top5 and not a_top5:
            top5_gain += 1
        elif a_top5 and not b_top5:
            top5_loss += 1
        per_question.append(
            {
                "question_id": question_id,
                "e5a_rank": None if math.isinf(a_rank) else int(a_rank),
                "e5b_rank": None if math.isinf(b_rank) else int(b_rank),
                "comparison": relation,
            }
        )

    return {
        "e5b_better_rank_count": better_b,
        "e5a_better_rank_count": better_a,
        "tie_count": ties,
        "top5_gain_count": top5_gain,
        "top5_loss_count": top5_loss,
        "questions": per_question,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--e5a-report", type=Path, default=DEFAULT_E5A_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--discovery-pool-limit", type=int, default=DISCOVERY_POOL_LIMIT)
    parser.add_argument("--document-limit", type=int, default=DOCUMENT_LIMIT)
    parser.add_argument("--within-document-limit", type=int, default=WITHIN_DOCUMENT_LIMIT)
    parser.add_argument("--candidate-limit", type=int, default=FINAL_CANDIDATE_LIMIT)
    args = parser.parse_args()

    print("[progress] E5-B: validating human-reviewed development benchmark", flush=True)
    questions = load_questions(args.questions)
    questions_sha = hashlib.sha256(args.questions.read_bytes()).hexdigest()

    print("[progress] E5-B: loading frozen E4 sparse index", flush=True)
    retriever = EvidenceAssemblyRetriever(args.index)
    index_meta = validate_index(retriever.base, args.index)
    print(
        f"[progress] E5-B: index ready ({index_meta['document_count']} docs / "
        f"{index_meta['chunk_count']} chunks)",
        flush=True,
    )

    all_rows: list[dict[str, Any]] = []
    answerable_rows: list[dict[str, Any]] = []
    route_checks: list[bool] = []
    started = time.monotonic()

    for position, question in enumerate(questions, 1):
        qid = str(question["question_id"])
        print(
            f"[progress] E5-B retrieval: question {position}/{len(questions)} "
            f"({qid}, {question['query_mode']}, {question['category']})",
            flush=True,
        )
        result = retriever.retrieve(
            str(question["question"]),
            discovery_pool_limit=args.discovery_pool_limit,
            document_limit=args.document_limit,
            within_document_limit=args.within_document_limit,
            final_candidate_limit=args.candidate_limit,
        )
        candidates = list(result.get("candidates", []))
        route_match = route_matches_declared(question, result["route"])
        if route_match is not None:
            route_checks.append(bool(route_match))

        row: dict[str, Any] = {
            "question_id": qid,
            "category": question["category"],
            "query_mode": question["query_mode"],
            "answerable_from_ad": bool(question["answerable_from_ad"]),
            "target_ad_number": question.get("target_ad_number"),
            "reference_pages": question.get("reference_pages", []),
            "route": result["route"],
            "route_matches_declared_mode": route_match,
            "ranking_query": result.get("ranking_query"),
            "route_errors": result.get("route_errors", []),
            "e5b_mode": result.get("e5b_mode"),
            "document_candidates": result.get("document_candidates", []),
            "candidate_count": len(candidates),
            "retrieved": [
                {
                    "rank": rank,
                    "chunk_id": item["chunk_id"],
                    "ad_number": item["ad_number"],
                    "page_start": item["page_start"],
                    "page_end": item["page_end"],
                    "section": item["section"],
                    "sparse_rank": item.get("sparse_rank"),
                    "preferred_section": item.get("preferred_section"),
                    "document_rank": item.get("document_rank"),
                    "assembly_role": item.get("assembly_role"),
                    "global_best_rank": item.get("global_best_rank"),
                    "document_support_rrf": item.get("document_support_rrf"),
                }
                for rank, item in enumerate(candidates, 1)
            ],
        }
        if bool(question["answerable_from_ad"]):
            row["rank_at_20"] = relevance_rank(candidates, question)
            row["source_rank_at_20"] = source_rank(candidates, question)
            answerable_rows.append(row)
        else:
            row["rank_at_20"] = None
            row["source_rank_at_20"] = None
        all_rows.append(row)

    elapsed = int(time.monotonic() - started)
    overall = summarize(answerable_rows)
    report: dict[str, Any] = {
        "evaluation_version": EVALUATION_VERSION,
        "experiment": "E5-B",
        "retrieval_build_version": EXPECTED_RETRIEVAL_BUILD_VERSION,
        "benchmark": str(args.questions),
        "benchmark_sha256": questions_sha,
        "policy": (
            "Development-only E5 tuning benchmark. Final-test families/questions remain sealed. "
            "E5-B preserves E5-A known-document retrieval and uses two-stage sparse discovery "
            "plus evidence assembly for discovery queries."
        ),
        "configuration": {
            "discovery_pool_limit": args.discovery_pool_limit,
            "document_limit": args.document_limit,
            "within_document_limit": args.within_document_limit,
            "candidate_limit": args.candidate_limit,
            "primary_final_k": FINAL_K,
            "dense_retrieval": False,
            "reranker": False,
            "index": str(args.index),
            **index_meta,
        },
        "question_accounting": {
            "total": len(questions),
            "answerable_retrieval": len(answerable_rows),
            "abstention_reserved_for_qa": len(questions) - len(answerable_rows),
        },
        "routing": {
            "checked_question_count": len(route_checks),
            "correct_count": sum(route_checks),
            "accuracy": sum(route_checks) / len(route_checks) if route_checks else None,
        },
        "overall": overall,
        "by_query_mode": breakdown(answerable_rows, "query_mode"),
        "by_category": breakdown(answerable_rows, "category"),
        "elapsed_seconds": elapsed,
        "questions": all_rows,
    }

    if args.e5a_report.exists():
        e5a_report = json.loads(args.e5a_report.read_text(encoding="utf-8"))
        report["paired_vs_e5a"] = paired_vs_e5a(
            e5a_report=e5a_report,
            e5b_rows=answerable_rows,
            benchmark_sha256=questions_sha,
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("[progress] E5-B development evaluation: finished", flush=True)
    print(
        json.dumps(
            {
                "evaluation_version": EVALUATION_VERSION,
                "routing": report["routing"],
                "overall": overall,
                "by_query_mode": report["by_query_mode"],
                "paired_vs_e5a": report.get("paired_vs_e5a"),
                "elapsed_seconds": elapsed,
                "output": str(args.output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
