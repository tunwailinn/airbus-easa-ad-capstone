#!/usr/bin/env python3
"""Evaluate E5-A engineering-aware lexical retrieval on the E5 development set.

E5-A uses deterministic query routing, exact-document filtering when the target
AD is explicitly supplied, corpus-wide SQLite FTS5/BM25 discovery otherwise,
and transparent section-preference ordering. This evaluator opens only the
human-reviewed 60-question E5 development benchmark. The 40-question final set
must remain sealed while E5 is tuned.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

from full_corpus_pipeline.e5_retrieval import EngineeringAwareRetriever


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = ROOT / "data_processed/indexes/rag_v1_2/e4_section_hybrid"
DEFAULT_QUESTIONS = (
    ROOT
    / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1/development_questions.jsonl"
)
DEFAULT_OUTPUT = (
    ROOT / "data_processed/evaluations/e5/e5a_development_evaluation.json"
)
EVALUATION_VERSION = "e5-a-eval-v1.0"
EXPECTED_RETRIEVAL_BUILD_VERSION = "rag-index-build-v1.2"
EXPECTED_QUESTION_COUNT = 60
EXPECTED_ANSWERABLE_COUNT = 54
EXPECTED_ABSTENTION_COUNT = 6
EXPECTED_DOCUMENT_COUNT = 1786
EXPECTED_CHUNK_COUNT = 12634
CANDIDATE_LIMIT = 20
FINAL_K = 5


def load_questions(path: Path) -> list[dict[str, Any]]:
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(records) != EXPECTED_QUESTION_COUNT:
        raise ValueError(
            f"expected {EXPECTED_QUESTION_COUNT} E5 development questions, "
            f"found {len(records)}"
        )
    ids = [str(item.get("question_id", "")) for item in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate E5 development question IDs")
    if any(item.get("split") != "development" for item in records):
        raise ValueError("E5-A evaluator accepts development questions only")
    if any(item.get("review_status") != "human_verified" for item in records):
        raise ValueError("all E5 development questions must be human_verified")
    answerable = [item for item in records if bool(item.get("answerable_from_ad"))]
    abstention = [item for item in records if not bool(item.get("answerable_from_ad"))]
    if len(answerable) != EXPECTED_ANSWERABLE_COUNT:
        raise ValueError(
            f"expected {EXPECTED_ANSWERABLE_COUNT} answerable questions, "
            f"found {len(answerable)}"
        )
    if len(abstention) != EXPECTED_ABSTENTION_COUNT:
        raise ValueError(
            f"expected {EXPECTED_ABSTENTION_COUNT} abstention questions, "
            f"found {len(abstention)}"
        )
    return records


def validate_index(retriever: EngineeringAwareRetriever, index_dir: Path) -> dict[str, Any]:
    if len(retriever.index.chunks) != EXPECTED_CHUNK_COUNT:
        raise ValueError(
            f"expected {EXPECTED_CHUNK_COUNT} frozen E4 chunks, "
            f"found {len(retriever.index.chunks)}"
        )
    document_count = len({chunk.file_instance_id for chunk in retriever.index.chunks})
    if document_count != EXPECTED_DOCUMENT_COUNT:
        raise ValueError(
            f"expected {EXPECTED_DOCUMENT_COUNT} indexed documents, found {document_count}"
        )

    config = json.loads(retriever.index.config_path.read_text(encoding="utf-8"))
    if config.get("sparse_backend") != "sqlite_fts5_bm25":
        raise ValueError("E5-A requires the frozen E4 SQLite FTS5/BM25 index")

    build_summary_path = index_dir.parent / "build_summary.json"
    if not build_summary_path.exists():
        raise FileNotFoundError(f"missing frozen build summary: {build_summary_path}")
    build_summary = json.loads(build_summary_path.read_text(encoding="utf-8"))
    if build_summary.get("retrieval_build_version") != EXPECTED_RETRIEVAL_BUILD_VERSION:
        raise ValueError(
            f"expected retrieval build {EXPECTED_RETRIEVAL_BUILD_VERSION}, got "
            f"{build_summary.get('retrieval_build_version')!r}"
        )
    return {
        "document_count": document_count,
        "chunk_count": len(retriever.index.chunks),
        "sparse_backend": config.get("sparse_backend"),
        "retrieval_build_version": build_summary.get("retrieval_build_version"),
    }


def _overlaps_reference_page(candidate: dict[str, Any], pages: set[int]) -> bool:
    return any(
        int(candidate["page_start"]) <= page <= int(candidate["page_end"])
        for page in pages
    )


def relevance_rank(
    candidates: list[dict[str, Any]], question: dict[str, Any]
) -> int | None:
    target = str(question["target_ad_number"]).casefold()
    pages = {int(page) for page in question.get("reference_pages", [])}
    for rank, candidate in enumerate(candidates, 1):
        if (
            str(candidate["ad_number"]).casefold() == target
            and _overlaps_reference_page(candidate, pages)
        ):
            return rank
    return None


def source_rank(candidates: list[dict[str, Any]], question: dict[str, Any]) -> int | None:
    target = str(question["target_ad_number"]).casefold()
    for rank, candidate in enumerate(candidates, 1):
        if str(candidate["ad_number"]).casefold() == target:
            return rank
    return None


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"question_count": 0}
    count = len(rows)

    def hit_at(key: str, k: int) -> int:
        return sum(
            row[key] is not None and int(row[key]) <= k
            for row in rows
        )

    ranks_at_20 = [int(row["rank_at_20"]) for row in rows if row["rank_at_20"]]
    source_ranks_at_20 = [
        int(row["source_rank_at_20"])
        for row in rows
        if row["source_rank_at_20"]
    ]
    return {
        "question_count": count,
        "recall_at_1": hit_at("rank_at_20", 1) / count,
        "recall_at_3": hit_at("rank_at_20", 3) / count,
        "recall_at_5": hit_at("rank_at_20", 5) / count,
        "mrr_at_5": sum(
            1.0 / int(row["rank_at_20"])
            if row["rank_at_20"] and int(row["rank_at_20"]) <= FINAL_K
            else 0.0
            for row in rows
        )
        / count,
        "ndcg_at_5": sum(
            1.0 / math.log2(int(row["rank_at_20"]) + 1)
            if row["rank_at_20"] and int(row["rank_at_20"]) <= FINAL_K
            else 0.0
            for row in rows
        )
        / count,
        "correct_source_at_1": hit_at("source_rank_at_20", 1) / count,
        "correct_source_at_5": hit_at("source_rank_at_20", 5) / count,
        "correct_source_and_page_at_1": hit_at("rank_at_20", 1) / count,
        "correct_source_and_page_at_5": hit_at("rank_at_20", 5) / count,
        "candidate_source_recall_at_20": hit_at("source_rank_at_20", CANDIDATE_LIMIT) / count,
        "candidate_source_and_page_recall_at_20": hit_at("rank_at_20", CANDIDATE_LIMIT) / count,
        "mean_relevant_rank_when_hit_at_20": (
            statistics.fmean(ranks_at_20) if ranks_at_20 else None
        ),
        "mean_source_rank_when_hit_at_20": (
            statistics.fmean(source_ranks_at_20) if source_ranks_at_20 else None
        ),
    }


def route_matches_declared(question: dict[str, Any], route: dict[str, Any]) -> bool | None:
    declared = str(question.get("query_mode", ""))
    target = str(question.get("target_ad_number", "")).casefold()
    mode = str(route.get("mode", ""))
    routed_ads = {str(value).casefold() for value in route.get("ad_numbers", [])}
    if declared == "known_document":
        return mode == "known_document" and target in routed_ads
    if declared == "discovery":
        return mode == "discovery"
    return None


def breakdown(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    values = sorted({str(row[key]) for row in rows})
    return {
        value: summarize([row for row in rows if str(row[key]) == value])
        for value in values
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--candidate-limit", type=int, default=CANDIDATE_LIMIT)
    args = parser.parse_args()
    if args.candidate_limit != CANDIDATE_LIMIT:
        raise ValueError(f"E5-A v1.0 requires candidate-limit={CANDIDATE_LIMIT}")

    print("[progress] E5-A: validating human-reviewed development benchmark", flush=True)
    questions = load_questions(args.questions)
    questions_sha = hashlib.sha256(args.questions.read_bytes()).hexdigest()

    print("[progress] E5-A: loading frozen E4 sparse index", flush=True)
    retriever = EngineeringAwareRetriever(args.index)
    index_meta = validate_index(retriever, args.index)
    print(
        f"[progress] E5-A: index ready ({index_meta['document_count']} docs / "
        f"{index_meta['chunk_count']} chunks)",
        flush=True,
    )

    answerable_rows: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []
    route_checks: list[bool] = []
    started = time.monotonic()

    for position, question in enumerate(questions, 1):
        qid = str(question["question_id"])
        print(
            f"[progress] E5-A retrieval: question {position}/{len(questions)} "
            f"({qid}, {question['query_mode']}, {question['category']})",
            flush=True,
        )
        result = retriever.retrieve_lexical(
            str(question["question"]),
            per_route_limit=CANDIDATE_LIMIT,
        )
        candidates = list(result.get("candidates", []))
        route_match = route_matches_declared(question, result["route"])
        if route_match is not None:
            route_checks.append(route_match)

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
            "candidate_count": len(candidates),
            "retrieved": [
                {
                    "rank": rank,
                    "chunk_id": item["chunk_id"],
                    "ad_number": item["ad_number"],
                    "page_start": item["page_start"],
                    "page_end": item["page_end"],
                    "section": item["section"],
                    "sparse_rank": item["sparse_rank"],
                    "preferred_section": item["preferred_section"],
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
    report = {
        "evaluation_version": EVALUATION_VERSION,
        "experiment": "E5-A",
        "retrieval_build_version": EXPECTED_RETRIEVAL_BUILD_VERSION,
        "benchmark": str(args.questions),
        "benchmark_sha256": questions_sha,
        "policy": (
            "Development-only E5 tuning benchmark. Final-test families/questions remain sealed. "
            "E5-A uses deterministic routing + SQLite FTS5/BM25 + transparent section ordering."
        ),
        "configuration": {
            "candidate_limit": CANDIDATE_LIMIT,
            "primary_final_k": FINAL_K,
            "explicit_ad_identifier_used_for_routing_only": True,
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

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("[progress] E5-A development evaluation: finished", flush=True)
    print(
        json.dumps(
            {
                "evaluation_version": EVALUATION_VERSION,
                "routing": report["routing"],
                "overall": overall,
                "by_query_mode": report["by_query_mode"],
                "elapsed_seconds": elapsed,
                "output": str(args.output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
