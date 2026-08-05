#!/usr/bin/env python3
"""Evaluate E5-C Qwen3 dense augmentation on the E5 development benchmark.

The 40-question E5 final test remains sealed. Query embeddings are generated once
in an isolated SentenceTransformers worker; the evaluator itself uses only NumPy
for dense similarity and never imports PyTorch or FAISS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

from full_corpus_pipeline.build_e5c_dense_embeddings import (
    DEFAULT_OUTPUT as DEFAULT_DENSE_DIR,
    MODEL_NAME,
    MODEL_REVISION,
)
from full_corpus_pipeline.e5_retrieval import DEFAULT_INDEX
from full_corpus_pipeline.e5b_retrieval import (
    DISCOVERY_POOL_LIMIT,
    DOCUMENT_LIMIT,
    FINAL_CANDIDATE_LIMIT,
    WITHIN_DOCUMENT_LIMIT,
)
from full_corpus_pipeline.e5c_retrieval import (
    DENSE_POOL_LIMIT,
    DOCUMENT_FUSION_DEPTH,
    RRF_K,
    DenseEvidenceAssemblyRetriever,
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
DEFAULT_QUESTIONS = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1/development_questions.jsonl"
DEFAULT_E5B_REPORT = ROOT / "data_processed/evaluations/e5/e5b_development_evaluation.json"
DEFAULT_OUTPUT = ROOT / "data_processed/evaluations/e5/e5c_development_evaluation.json"
EVALUATION_VERSION = "e5-c-eval-v1.0"
FINAL_K = 5


def _rank_or_inf(value: Any) -> float:
    return float(value) if value is not None else math.inf


def paired_vs_report(
    *,
    baseline_report: dict[str, Any],
    current_rows: list[dict[str, Any]],
    benchmark_sha256: str,
    baseline_label: str,
    current_label: str,
) -> dict[str, Any]:
    if baseline_report.get("benchmark_sha256") != benchmark_sha256:
        raise ValueError("baseline report benchmark SHA does not match E5-C benchmark")
    baseline = {
        str(row["question_id"]): row
        for row in baseline_report.get("questions", [])
        if bool(row.get("answerable_from_ad"))
    }
    current = {str(row["question_id"]): row for row in current_rows}
    if set(baseline) != set(current):
        raise ValueError("baseline/E5-C answerable question membership differs")

    current_better = baseline_better = ties = 0
    top5_gain = top5_loss = 0
    questions: list[dict[str, Any]] = []
    for question_id in sorted(current):
        base_rank = _rank_or_inf(baseline[question_id].get("rank_at_20"))
        current_rank = _rank_or_inf(current[question_id].get("rank_at_20"))
        if current_rank < base_rank:
            current_better += 1
            relation = f"{current_label}_better"
        elif base_rank < current_rank:
            baseline_better += 1
            relation = f"{baseline_label}_better"
        else:
            ties += 1
            relation = "tie"
        base_top5 = base_rank <= FINAL_K
        current_top5 = current_rank <= FINAL_K
        if current_top5 and not base_top5:
            top5_gain += 1
        elif base_top5 and not current_top5:
            top5_loss += 1
        questions.append(
            {
                "question_id": question_id,
                f"{baseline_label}_rank": None if math.isinf(base_rank) else int(base_rank),
                f"{current_label}_rank": None if math.isinf(current_rank) else int(current_rank),
                "comparison": relation,
            }
        )
    return {
        f"{current_label}_better_rank_count": current_better,
        f"{baseline_label}_better_rank_count": baseline_better,
        "tie_count": ties,
        "top5_gain_count": top5_gain,
        "top5_loss_count": top5_loss,
        "questions": questions,
    }


def encode_queries(
    questions: list[dict[str, Any]],
    *,
    device: str,
    batch_size: int,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="e5c_queries_") as temp_dir_value:
        temp_dir = Path(temp_dir_value)
        input_path = temp_dir / "queries.jsonl"
        output_path = temp_dir / "queries.npy"
        metadata_path = temp_dir / "queries_metadata.json"
        with input_path.open("w", encoding="utf-8") as handle:
            for question in questions:
                handle.write(
                    json.dumps(
                        {
                            "question_id": question["question_id"],
                            "question": question["question"],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        command = [
            sys.executable,
            "-m",
            "full_corpus_pipeline.e5c_encode_queries_worker",
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
        vectors = np.load(output_path)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        ids = [str(value) for value in metadata.get("question_ids", [])]
        if len(ids) != len(questions) or vectors.shape[0] != len(ids):
            raise ValueError("E5-C query worker output row mismatch")
        return {
            question_id: np.asarray(vectors[index], dtype="float32")
            for index, question_id in enumerate(ids)
        }, metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--dense-dir", type=Path, default=DEFAULT_DENSE_DIR)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--e5b-report", type=Path, default=DEFAULT_E5B_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--query-device", default="auto")
    parser.add_argument("--query-batch-size", type=int, default=8)
    parser.add_argument("--lexical-pool-limit", type=int, default=DISCOVERY_POOL_LIMIT)
    parser.add_argument("--dense-pool-limit", type=int, default=DENSE_POOL_LIMIT)
    parser.add_argument("--document-limit", type=int, default=DOCUMENT_LIMIT)
    parser.add_argument("--within-document-limit", type=int, default=WITHIN_DOCUMENT_LIMIT)
    parser.add_argument("--candidate-limit", type=int, default=FINAL_CANDIDATE_LIMIT)
    args = parser.parse_args()

    print("[progress] E5-C: validating human-reviewed development benchmark", flush=True)
    questions = load_questions(args.questions)
    questions_sha = hashlib.sha256(args.questions.read_bytes()).hexdigest()

    print("[progress] E5-C: loading frozen E4 sparse chunks + Qwen dense artifact", flush=True)
    retriever = DenseEvidenceAssemblyRetriever(args.index, args.dense_dir)
    index_meta = validate_index(retriever.base.base, args.index)
    print(
        f"[progress] E5-C: index ready ({index_meta['document_count']} docs / "
        f"{index_meta['chunk_count']} chunks)",
        flush=True,
    )

    print("[progress] E5-C: encoding all development queries in isolated Qwen worker", flush=True)
    query_vectors, query_meta = encode_queries(
        questions,
        device=args.query_device,
        batch_size=args.query_batch_size,
    )
    if query_meta.get("model") != MODEL_NAME:
        raise ValueError("E5-C query worker used unexpected embedding model")
    if query_meta.get("model_revision") != MODEL_REVISION:
        raise ValueError("E5-C query worker used unexpected embedding revision")
    if int(query_meta.get("embedding_dimension", -1)) != retriever.dense.embeddings.shape[1]:
        raise ValueError("E5-C query/document embedding dimension mismatch")

    all_rows: list[dict[str, Any]] = []
    answerable_rows: list[dict[str, Any]] = []
    route_checks: list[bool] = []
    started = time.monotonic()
    for position, question in enumerate(questions, 1):
        qid = str(question["question_id"])
        print(
            f"[progress] E5-C retrieval: question {position}/{len(questions)} "
            f"({qid}, {question['query_mode']}, {question['category']})",
            flush=True,
        )
        result = retriever.retrieve(
            str(question["question"]),
            query_vectors[qid],
            discovery_pool_limit=args.lexical_pool_limit,
            dense_pool_limit=args.dense_pool_limit,
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
            "e5c_mode": result.get("e5c_mode"),
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
                    "document_rank": item.get("document_rank"),
                    "assembly_role": item.get("assembly_role"),
                    "lexical_document_rank": item.get("lexical_document_rank"),
                    "dense_document_rank": item.get("dense_document_rank"),
                    "document_fusion_score": item.get("document_fusion_score"),
                    "lexical_passage_rank": item.get("lexical_passage_rank"),
                    "dense_passage_rank": item.get("dense_passage_rank"),
                    "passage_fusion_rank": item.get("passage_fusion_rank"),
                    "passage_fusion_score": item.get("passage_fusion_score"),
                    "sparse_rank": item.get("sparse_rank"),
                    "preferred_section": item.get("preferred_section"),
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
        "experiment": "E5-C",
        "retrieval_build_version": EXPECTED_RETRIEVAL_BUILD_VERSION,
        "benchmark": str(args.questions),
        "benchmark_sha256": questions_sha,
        "policy": (
            "Development-only E5 tuning benchmark. Final-test families/questions remain sealed. "
            "E5-C preserves E5-B known-document retrieval and adds the pinned Qwen3-Embedding-0.6B "
            "document/passage dense RRF fusion for discovery queries."
        ),
        "configuration": {
            "lexical_pool_limit": args.lexical_pool_limit,
            "dense_pool_limit": args.dense_pool_limit,
            "document_fusion_depth": DOCUMENT_FUSION_DEPTH,
            "document_limit": args.document_limit,
            "within_document_limit": args.within_document_limit,
            "candidate_limit": args.candidate_limit,
            "primary_final_k": FINAL_K,
            "dense_retrieval": True,
            "embedding_model": MODEL_NAME,
            "embedding_revision": MODEL_REVISION,
            "query_prompt_name": "query",
            "dense_similarity": "normalized_inner_product_cosine",
            "fusion": "reciprocal_rank_fusion",
            "rrf_k": RRF_K,
            "reranker": False,
            "index": str(args.index),
            "dense_dir": str(args.dense_dir),
            "query_encoder_execution": "isolated_subprocess_without_faiss",
            "query_encoder_device": query_meta.get("device"),
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
        "elapsed_seconds_retrieval_only": elapsed,
        "questions": all_rows,
    }

    if not args.e5b_report.exists():
        raise FileNotFoundError(f"missing E5-B development report: {args.e5b_report}")
    e5b_report = json.loads(args.e5b_report.read_text(encoding="utf-8"))
    report["paired_vs_e5b"] = paired_vs_report(
        baseline_report=e5b_report,
        current_rows=answerable_rows,
        benchmark_sha256=questions_sha,
        baseline_label="e5b",
        current_label="e5c",
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("[progress] E5-C development evaluation: finished", flush=True)
    print(
        json.dumps(
            {
                "evaluation_version": EVALUATION_VERSION,
                "routing": report["routing"],
                "overall": overall,
                "by_query_mode": report["by_query_mode"],
                "paired_vs_e5b": report["paired_vs_e5b"],
                "output": str(args.output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
