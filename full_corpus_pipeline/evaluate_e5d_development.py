#!/usr/bin/env python3
"""Evaluate E5-D Qwen3 reranking on the E5 development benchmark.

E5-D keeps E5-C candidate generation fixed and reranks only those top-20
passages with the pinned Qwen3-Reranker-0.6B. The final 40-question E5 test
remains sealed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from full_corpus_pipeline.build_e5c_dense_embeddings import DEFAULT_OUTPUT as DEFAULT_DENSE_DIR
from full_corpus_pipeline.e5_retrieval import DEFAULT_INDEX
from full_corpus_pipeline.e5c_retrieval import DenseEvidenceAssemblyRetriever
from full_corpus_pipeline.e5d_retrieval import (
    RERANKER_CANDIDATE_LIMIT,
    RERANKER_INSTRUCTION,
    RERANKER_MODEL_NAME,
    RERANKER_MODEL_REVISION,
    apply_reranker_scores,
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
from full_corpus_pipeline.evaluate_e5c_development import encode_queries, paired_vs_report


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUESTIONS = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1/development_questions.jsonl"
DEFAULT_E5B_REPORT = ROOT / "data_processed/evaluations/e5/e5b_development_evaluation.json"
DEFAULT_E5C_REPORT = ROOT / "data_processed/evaluations/e5/e5c_development_evaluation.json"
DEFAULT_OUTPUT = ROOT / "data_processed/evaluations/e5/e5d_development_evaluation.json"
EVALUATION_VERSION = "e5-d-eval-v1.0"
FINAL_K = 5


def score_candidate_pool(
    rows: list[dict[str, Any]],
    *,
    device: str,
    batch_size: int,
) -> tuple[dict[tuple[str, int, str], float], dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="e5d_rerank_") as temp_dir_value:
        temp_dir = Path(temp_dir_value)
        input_path = temp_dir / "pairs.jsonl"
        output_path = temp_dir / "scores.jsonl"
        metadata_path = temp_dir / "metadata.json"
        with input_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

        command = [
            sys.executable,
            "-m",
            "full_corpus_pipeline.e5d_rerank_worker",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--metadata-output",
            str(metadata_path),
            "--device",
            device,
            "--batch-size",
            str(batch_size),
        ]
        subprocess.run(command, check=True, cwd=ROOT)
        scored_rows = [
            json.loads(line)
            for line in output_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    score_map: dict[tuple[str, int, str], float] = {}
    for row in scored_rows:
        key = (
            str(row["question_id"]),
            int(row["candidate_position"]),
            str(row["chunk_id"]),
        )
        if key in score_map:
            raise ValueError(f"duplicate E5-D reranker score for {key}")
        score_map[key] = float(row["score"])
    expected_keys = {
        (str(row["question_id"]), int(row["candidate_position"]), str(row["chunk_id"]))
        for row in rows
    }
    if set(score_map) != expected_keys:
        raise ValueError("E5-D reranker output membership differs from candidate pool")
    return score_map, metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--dense-dir", type=Path, default=DEFAULT_DENSE_DIR)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--e5b-report", type=Path, default=DEFAULT_E5B_REPORT)
    parser.add_argument("--e5c-report", type=Path, default=DEFAULT_E5C_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--query-device", default="auto")
    parser.add_argument("--query-batch-size", type=int, default=8)
    parser.add_argument("--reranker-device", default="auto")
    parser.add_argument("--reranker-batch-size", type=int, default=2)
    args = parser.parse_args()

    print("[progress] E5-D: validating human-reviewed development benchmark", flush=True)
    questions = load_questions(args.questions)
    benchmark_sha = hashlib.sha256(args.questions.read_bytes()).hexdigest()

    print("[progress] E5-D: loading frozen E4 sparse chunks + E5-C dense artifact", flush=True)
    retriever = DenseEvidenceAssemblyRetriever(args.index, args.dense_dir)
    index_meta = validate_index(retriever.base.base, args.index)
    print(
        f"[progress] E5-D: candidate generator ready ({index_meta['document_count']} docs / "
        f"{index_meta['chunk_count']} chunks)",
        flush=True,
    )

    print("[progress] E5-D: encoding development queries in isolated Qwen embedding worker", flush=True)
    query_vectors, query_meta = encode_queries(
        questions,
        device=args.query_device,
        batch_size=args.query_batch_size,
    )

    generated: list[dict[str, Any]] = []
    worker_pairs: list[dict[str, Any]] = []
    route_checks: list[bool] = []
    retrieval_started = time.monotonic()
    for position, question in enumerate(questions, 1):
        qid = str(question["question_id"])
        print(
            f"[progress] E5-D candidate generation: question {position}/{len(questions)} "
            f"({qid}, {question['query_mode']}, {question['category']})",
            flush=True,
        )
        result = retriever.retrieve(str(question["question"]), query_vectors[qid])
        candidates = list(result.get("candidates", []))[:RERANKER_CANDIDATE_LIMIT]
        route_match = route_matches_declared(question, result["route"])
        if route_match is not None:
            route_checks.append(bool(route_match))
        generated.append(
            {
                "question": question,
                "result": result,
                "candidates": candidates,
                "route_match": route_match,
            }
        )
        for candidate_position, candidate in enumerate(candidates, 1):
            worker_pairs.append(
                {
                    "question_id": qid,
                    "candidate_position": candidate_position,
                    "chunk_id": str(candidate["chunk_id"]),
                    "question": str(question["question"]),
                    "text": str(candidate["text"]),
                }
            )
    retrieval_elapsed = int(time.monotonic() - retrieval_started)

    print(
        f"[progress] E5-D: reranking {len(worker_pairs)} fixed E5-C query/passage pairs",
        flush=True,
    )
    rerank_started = time.monotonic()
    score_map, reranker_meta = score_candidate_pool(
        worker_pairs,
        device=args.reranker_device,
        batch_size=args.reranker_batch_size,
    )
    rerank_elapsed = int(time.monotonic() - rerank_started)
    if reranker_meta.get("model") != RERANKER_MODEL_NAME:
        raise ValueError("E5-D worker used unexpected reranker model")
    if reranker_meta.get("model_revision") != RERANKER_MODEL_REVISION:
        raise ValueError("E5-D worker used unexpected reranker revision")
    if reranker_meta.get("instruction") != RERANKER_INSTRUCTION:
        raise ValueError("E5-D worker used unexpected reranker instruction")

    all_rows: list[dict[str, Any]] = []
    answerable_rows: list[dict[str, Any]] = []
    for position, bundle in enumerate(generated, 1):
        question = bundle["question"]
        result = bundle["result"]
        candidates = bundle["candidates"]
        qid = str(question["question_id"])
        scores = [
            score_map[(qid, pre_rank, str(candidate["chunk_id"]))]
            for pre_rank, candidate in enumerate(candidates, 1)
        ]
        reranked = apply_reranker_scores(candidates, scores)
        print(
            f"[progress] E5-D scoring: question {position}/{len(generated)} ({qid})",
            flush=True,
        )

        row: dict[str, Any] = {
            "question_id": qid,
            "category": question["category"],
            "query_mode": question["query_mode"],
            "answerable_from_ad": bool(question["answerable_from_ad"]),
            "target_ad_number": question.get("target_ad_number"),
            "reference_pages": question.get("reference_pages", []),
            "route": result["route"],
            "route_matches_declared_mode": bundle["route_match"],
            "ranking_query": result.get("ranking_query"),
            "route_errors": result.get("route_errors", []),
            "e5c_mode": result.get("e5c_mode"),
            "e5d_mode": "qwen3_reranked_fixed_e5c_candidates",
            "candidate_count": len(reranked),
            "retrieved": [
                {
                    "rank": rank,
                    "pre_rerank_rank": item["pre_rerank_rank"],
                    "reranker_score": item["reranker_score"],
                    "chunk_id": item["chunk_id"],
                    "ad_number": item["ad_number"],
                    "page_start": item["page_start"],
                    "page_end": item["page_end"],
                    "section": item["section"],
                    "document_rank": item.get("document_rank"),
                    "assembly_role": item.get("assembly_role"),
                    "lexical_document_rank": item.get("lexical_document_rank"),
                    "dense_document_rank": item.get("dense_document_rank"),
                    "document_fusion_score": item.get("document_fusion_score"),
                    "lexical_passage_rank": item.get("lexical_passage_rank"),
                    "dense_passage_rank": item.get("dense_passage_rank"),
                    "passage_fusion_rank": item.get("passage_fusion_rank"),
                }
                for rank, item in enumerate(reranked, 1)
            ],
        }
        if bool(question["answerable_from_ad"]):
            row["rank_at_20"] = relevance_rank(reranked, question)
            row["source_rank_at_20"] = source_rank(reranked, question)
            answerable_rows.append(row)
        else:
            row["rank_at_20"] = None
            row["source_rank_at_20"] = None
        all_rows.append(row)

    overall = summarize(answerable_rows)
    report: dict[str, Any] = {
        "evaluation_version": EVALUATION_VERSION,
        "experiment": "E5-D",
        "retrieval_build_version": EXPECTED_RETRIEVAL_BUILD_VERSION,
        "benchmark": str(args.questions),
        "benchmark_sha256": benchmark_sha,
        "policy": (
            "Development-only E5 tuning benchmark. Final-test families/questions remain sealed. "
            "E5-D keeps E5-C top-20 candidate membership fixed and applies only the pinned "
            "Qwen3-Reranker-0.6B passage reranker."
        ),
        "configuration": {
            "candidate_generation": "E5-C fixed top-20",
            "candidate_limit": RERANKER_CANDIDATE_LIMIT,
            "primary_final_k": FINAL_K,
            "embedding_model": query_meta.get("model"),
            "embedding_revision": query_meta.get("model_revision"),
            "reranker": True,
            "reranker_model": RERANKER_MODEL_NAME,
            "reranker_revision": RERANKER_MODEL_REVISION,
            "reranker_instruction": RERANKER_INSTRUCTION,
            "reranker_score_type": reranker_meta.get("score_type"),
            "reranker_execution": "isolated_subprocess_without_faiss",
            "reranker_device": reranker_meta.get("device"),
            "reranker_batch_size": args.reranker_batch_size,
            "index": str(args.index),
            "dense_dir": str(args.dense_dir),
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
        "elapsed_seconds_candidate_generation": retrieval_elapsed,
        "elapsed_seconds_reranker": rerank_elapsed,
        "questions": all_rows,
    }

    if not args.e5c_report.exists():
        raise FileNotFoundError(f"missing E5-C development report: {args.e5c_report}")
    e5c_report = json.loads(args.e5c_report.read_text(encoding="utf-8"))
    report["paired_vs_e5c"] = paired_vs_report(
        baseline_report=e5c_report,
        current_rows=answerable_rows,
        benchmark_sha256=benchmark_sha,
        baseline_label="e5c",
        current_label="e5d",
    )
    if args.e5b_report.exists():
        e5b_report = json.loads(args.e5b_report.read_text(encoding="utf-8"))
        report["paired_vs_e5b"] = paired_vs_report(
            baseline_report=e5b_report,
            current_rows=answerable_rows,
            benchmark_sha256=benchmark_sha,
            baseline_label="e5b",
            current_label="e5d",
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("[progress] E5-D development evaluation: finished", flush=True)
    print(
        json.dumps(
            {
                "evaluation_version": EVALUATION_VERSION,
                "routing": report["routing"],
                "overall": overall,
                "by_query_mode": report["by_query_mode"],
                "paired_vs_e5c": report["paired_vs_e5c"],
                "paired_vs_e5b": report.get("paired_vs_e5b"),
                "elapsed_seconds_candidate_generation": retrieval_elapsed,
                "elapsed_seconds_reranker": rerank_elapsed,
                "output": str(args.output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
