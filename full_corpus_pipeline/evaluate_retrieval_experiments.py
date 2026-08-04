#!/usr/bin/env python3
"""Evaluate the frozen E0 and E4 indexes on the locked QA retrieval benchmark.

This evaluator is intentionally strict. E0 uses dense-only ranking. E4 uses
BM25 + dense + RRF followed by the configured local cross-encoder. Reranker
failure aborts evaluation; there is no lexical fallback in the frozen thesis
measurement.

Runtime note: E0 and E4 share one dense query encoder because they use the same
frozen embedding model. The cross-encoder is pinned to CPU so Apple MPS does not
hold both the dense encoder and reranker simultaneously. This is a runtime
stability policy only; retrieval architecture, models, candidate depth, and
ranking logic remain frozen.
"""

from __future__ import annotations

import argparse
import json
import math
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, TypeVar

from full_corpus_pipeline.retrieval import DenseEncoder, HybridIndex, TOKEN_RE


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX_ROOT = ROOT / "data_processed/indexes/rag_v1_2"
DEFAULT_QUESTIONS = ROOT / "evaluation_sets/easa_airbus_ad_qa_50_v2/questions.jsonl"
DEFAULT_OUTPUT = DEFAULT_INDEX_ROOT / "retrieval_comparison.json"
EXPECTED_BUILD_VERSION = "rag-index-build-v1.2"
EVALUATION_VERSION = "retrieval-eval-v1.1"
RERANKER_DEVICE = "cpu"
T = TypeVar("T")


def _run_with_progress(label: str, function: Callable[[], T]) -> T:
    """Run a potentially long local phase with an elapsed-time heartbeat."""
    started = time.monotonic()
    stop = threading.Event()

    def heartbeat() -> None:
        while not stop.wait(2.0):
            elapsed = int(time.monotonic() - started)
            print(f"[progress] {label}: working ({elapsed}s elapsed)", flush=True)

    print(f"[progress] {label}: started", flush=True)
    worker = threading.Thread(target=heartbeat, daemon=True)
    worker.start()
    try:
        return function()
    finally:
        stop.set()
        worker.join(timeout=1.0)
        elapsed = int(time.monotonic() - started)
        print(f"[progress] {label}: finished ({elapsed}s)", flush=True)


def load_questions(path: Path) -> list[dict[str, Any]]:
    questions = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [item for item in questions if bool(item.get("answerable_from_ad"))]


def validate_build_summary(index_root: Path) -> dict[str, Any]:
    summary_path = index_root / "build_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"missing retrieval build summary: {summary_path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("retrieval_build_version") != EXPECTED_BUILD_VERSION:
        raise ValueError(
            f"expected {EXPECTED_BUILD_VERSION}, got "
            f"{summary.get('retrieval_build_version')!r}"
        )
    if int(summary.get("document_count", -1)) != 1786:
        raise ValueError("retrieval build summary document_count is not 1786")
    policy = summary.get("chunk_size_policy", {})
    if policy.get("count_method") != "whitespace_split":
        raise ValueError("retrieval build does not use frozen whitespace_split chunk policy")
    if int(policy.get("e0_max_tokens", -1)) != 350:
        raise ValueError("retrieval build E0 chunk limit is not 350")
    if int(policy.get("e4_max_tokens", -1)) != 450:
        raise ValueError("retrieval build E4 chunk limit is not 450")
    experiments = summary.get("experiments", {})
    for name, maximum in (("e0", 350), ("e4", 450)):
        report = experiments.get(name)
        if not isinstance(report, dict):
            raise ValueError(f"retrieval build summary missing {name} report")
        stats = report.get("chunk_stats", {})
        if int(stats.get("document_count", -1)) != 1786:
            raise ValueError(f"{name} does not cover 1786 documents")
        if int(stats.get("max_tokens", maximum + 1)) > maximum:
            raise ValueError(f"{name} exceeds frozen chunk limit {maximum}")
    return summary


def validate_index_pair(
    e0: HybridIndex, e4: HybridIndex
) -> tuple[dict[str, Any], dict[str, Any]]:
    e0_config = json.loads(e0.config_path.read_text(encoding="utf-8"))
    e4_config = json.loads(e4.config_path.read_text(encoding="utf-8"))
    for name, config in (("E0", e0_config), ("E4", e4_config)):
        if config.get("dense_backend") != "sentence_transformers":
            raise ValueError(f"{name} did not use sentence-transformers")
        if config.get("dense_index_backend") != "faiss_index_flat_ip":
            raise ValueError(f"{name} did not use the frozen FAISS backend")
    if e0_config.get("embedding_model") != e4_config.get("embedding_model"):
        raise ValueError("E0 and E4 must use the same embedding model")
    if e4_config.get("sparse_backend") != "sqlite_fts5_bm25":
        raise ValueError("E4 sparse backend is not SQLite FTS5/BM25")
    if e4_config.get("fusion") != "reciprocal_rank_fusion":
        raise ValueError("E4 fusion is not reciprocal-rank fusion")
    return e0_config, e4_config


def share_dense_query_encoder(e0: HybridIndex, e4: HybridIndex, encoder: Any) -> None:
    """Attach one frozen dense query encoder to both indexes for evaluation."""
    e0._encoder = encoder
    e4._encoder = encoder


def strict_hybrid_search(
    index: HybridIndex,
    reranker: Any,
    query: str,
    *,
    limit: int = 5,
    candidate_limit: int = 20,
) -> list[dict[str, Any]]:
    sparse = index.sparse_search(query, candidate_limit)
    dense = index.dense_search(query, candidate_limit)
    rrf: dict[str, float] = {}
    for ranking in (sparse, dense):
        for rank, item in enumerate(ranking, 1):
            rrf[item["chunk_id"]] = rrf.get(item["chunk_id"], 0.0) + 1.0 / (60 + rank)

    by_id = {chunk.chunk_id: chunk for chunk in index.chunks}
    query_terms = set(TOKEN_RE.findall(query.lower()))
    candidates: list[dict[str, Any]] = []
    for chunk_id, score in rrf.items():
        chunk = by_id[chunk_id]
        chunk_terms = set(TOKEN_RE.findall(chunk.text.lower()))
        lexical_overlap = len(query_terms & chunk_terms) / max(len(query_terms), 1)
        candidates.append(
            {
                **asdict(chunk),
                "retrieval_score": score,
                "lexical_overlap": lexical_overlap,
            }
        )
    if not candidates:
        return []

    scores = reranker.predict(
        [(query, item["text"]) for item in candidates],
        show_progress_bar=False,
        device=RERANKER_DEVICE,
    )
    for item, score in zip(candidates, scores):
        item["rerank_score"] = float(score)
    return sorted(
        candidates,
        key=lambda item: (-item["rerank_score"], item["chunk_id"]),
    )[:limit]


def relevance_rank(
    results: list[dict[str, Any]], question: dict[str, Any]
) -> int | None:
    target = str(question["target_ad_number"]).casefold()
    pages = {int(page) for page in question.get("reference_pages", [])}
    for position, result in enumerate(results, 1):
        source_ok = str(result["ad_number"]).casefold() == target
        page_ok = any(
            int(result["page_start"]) <= page <= int(result["page_end"])
            for page in pages
        )
        if source_ok and page_ok:
            return position
    return None


def source_rank(results: list[dict[str, Any]], question: dict[str, Any]) -> int | None:
    target = str(question["target_ad_number"]).casefold()
    for position, result in enumerate(results, 1):
        if str(result["ad_number"]).casefold() == target:
            return position
    return None


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(rows)
    if count == 0:
        raise ValueError("no answerable retrieval questions")
    return {
        "answerable_question_count": count,
        "recall_at_1": sum(row["rank"] == 1 for row in rows) / count,
        "recall_at_3": sum(
            row["rank"] is not None and row["rank"] <= 3 for row in rows
        )
        / count,
        "recall_at_5": sum(
            row["rank"] is not None and row["rank"] <= 5 for row in rows
        )
        / count,
        "mrr": sum(1 / row["rank"] if row["rank"] else 0 for row in rows) / count,
        "ndcg_at_5": sum(
            1 / math.log2(row["rank"] + 1) if row["rank"] else 0 for row in rows
        )
        / count,
        "correct_source_at_1": sum(row["source_rank"] == 1 for row in rows) / count,
        "correct_source_at_5": sum(
            row["source_rank"] is not None and row["source_rank"] <= 5 for row in rows
        )
        / count,
        "correct_source_and_page_at_1": sum(row["rank"] == 1 for row in rows) / count,
        "correct_source_and_page_at_5": sum(
            row["rank"] is not None and row["rank"] <= 5 for row in rows
        )
        / count,
    }


def evaluate_system(
    *,
    label: str,
    questions: list[dict[str, Any]],
    search_fn: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    total = len(questions)
    started = time.monotonic()
    for position, question in enumerate(questions, 1):
        print(
            f"[progress] {label}: question {position}/{total} "
            f"({question['question_id']})",
            flush=True,
        )
        results = search_fn(question["question"])
        rank = relevance_rank(results, question)
        src_rank = source_rank(results, question)
        rows.append(
            {
                "question_id": question["question_id"],
                "category": question["category"],
                "rank": rank,
                "source_rank": src_rank,
                "target_ad_number": question["target_ad_number"],
                "reference_pages": question["reference_pages"],
                "retrieved": [
                    {
                        "chunk_id": item["chunk_id"],
                        "ad_number": item["ad_number"],
                        "page_start": item["page_start"],
                        "page_end": item["page_end"],
                        "section": item["section"],
                    }
                    for item in results
                ],
            }
        )
    elapsed = int(time.monotonic() - started)
    print(f"[progress] {label}: finished {total} questions ({elapsed}s)", flush=True)
    return summarize(rows), rows


def paired_comparison(
    e0_rows: list[dict[str, Any]], e4_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    e0_by_id = {row["question_id"]: row for row in e0_rows}
    e4_by_id = {row["question_id"]: row for row in e4_rows}
    if set(e0_by_id) != set(e4_by_id):
        raise ValueError("E0/E4 evaluated different question membership")
    better_e0 = better_e4 = ties = 0
    for question_id in sorted(e0_by_id):
        e0_rank = e0_by_id[question_id]["rank"] or math.inf
        e4_rank = e4_by_id[question_id]["rank"] or math.inf
        if e4_rank < e0_rank:
            better_e4 += 1
        elif e0_rank < e4_rank:
            better_e0 += 1
        else:
            ties += 1
    return {
        "e4_better_rank_count": better_e4,
        "e0_better_rank_count": better_e0,
        "tie_count": ties,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-root", type=Path, default=DEFAULT_INDEX_ROOT)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--candidate-limit", type=int, default=20)
    args = parser.parse_args()

    print("[progress] validating frozen retrieval build", flush=True)
    validate_build_summary(args.index_root)
    e0 = HybridIndex(args.index_root / "e0_flat_dense")
    e4 = HybridIndex(args.index_root / "e4_section_hybrid")
    e0_config, e4_config = validate_index_pair(e0, e4)

    embedding_model = str(e0_config["embedding_model"])
    shared_dense_encoder = _run_with_progress(
        "loading shared dense query encoder",
        lambda: DenseEncoder(embedding_model, allow_fallback=False),
    )
    share_dense_query_encoder(e0, e4, shared_dense_encoder)
    dense_device = str(getattr(shared_dense_encoder.model, "device", "auto"))
    print(f"[progress] shared dense query encoder ready on {dense_device}", flush=True)

    from sentence_transformers import CrossEncoder

    reranker_model = str(e4_config["reranker_model"])

    def load_reranker() -> Any:
        model = CrossEncoder(reranker_model, device=RERANKER_DEVICE)
        model.predict(
            [("test query", "test passage")],
            show_progress_bar=False,
            device=RERANKER_DEVICE,
        )
        return model

    reranker = _run_with_progress(
        f"loading and warming {RERANKER_DEVICE} cross-encoder reranker",
        load_reranker,
    )
    print(f"[progress] reranker ready on {RERANKER_DEVICE}", flush=True)

    smoke_results = _run_with_progress(
        "pre-benchmark E4 runtime smoke test",
        lambda: strict_hybrid_search(
            e4,
            reranker,
            "airworthiness directive compliance inspection",
            limit=1,
            candidate_limit=args.candidate_limit,
        ),
    )
    if not smoke_results:
        raise RuntimeError("pre-benchmark E4 runtime smoke test returned no results")
    print("[progress] pre-benchmark E4 runtime smoke test passed", flush=True)

    # Locked questions are loaded only after the full E4 runtime path succeeds.
    questions = load_questions(args.questions)

    e0_metrics, e0_rows = evaluate_system(
        label="E0 dense-only",
        questions=questions,
        search_fn=lambda query: e0.search_dense_only(query, limit=5),
    )
    e4_metrics, e4_rows = evaluate_system(
        label="E4 hybrid + reranker",
        questions=questions,
        search_fn=lambda query: strict_hybrid_search(
            e4,
            reranker,
            query,
            limit=5,
            candidate_limit=args.candidate_limit,
        ),
    )

    report = {
        "evaluation_version": EVALUATION_VERSION,
        "retrieval_build_version": EXPECTED_BUILD_VERSION,
        "benchmark": str(args.questions),
        "policy": "Frozen E0/E4 configuration; report results without tuning on locked questions.",
        "embedding_model": embedding_model,
        "reranker_model": reranker_model,
        "candidate_limit": args.candidate_limit,
        "runtime": {
            "dense_query_encoder": "shared_between_e0_e4",
            "dense_query_device": dense_device,
            "reranker_device": RERANKER_DEVICE,
            "multiprocessing": False,
            "pre_benchmark_e4_smoke_test": True,
        },
        "e0": {"metrics": e0_metrics, "questions": e0_rows},
        "e4": {"metrics": e4_metrics, "questions": e4_rows},
        "paired": paired_comparison(e0_rows, e4_rows),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "e0": e0_metrics,
                "e4": e4_metrics,
                "paired": report["paired"],
                "runtime": report["runtime"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
