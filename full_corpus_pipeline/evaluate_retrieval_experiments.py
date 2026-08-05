#!/usr/bin/env python3
"""Evaluate frozen E0/E4 on the locked retrieval benchmark.

E0 is flat dense-only retrieval. E4 is section-aware BM25 + dense + RRF +
cross-encoder reranking. The retrieval configuration is frozen.

macOS/ARM runtime policy: PyTorch/SentenceTransformers, FAISS, and the
cross-encoder never share a Python process. The parent process orchestrates
three isolated workers:

1. SentenceTransformer-only query encoding;
2. FAISS-only IndexFlatIP search over the frozen indexes;
3. CPU CrossEncoder-only reranking of the exact E4 RRF candidates.

This preserves the frozen algorithms and model names while avoiding the known
native OpenMP conflict between macOS ARM PyTorch and FAISS wheels.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from full_corpus_pipeline.retrieval import HybridIndex, TOKEN_RE


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX_ROOT = ROOT / "data_processed/indexes/rag_v1_2"
DEFAULT_QUESTIONS = ROOT / "evaluation_sets/easa_airbus_ad_qa_50_v2/questions.jsonl"
DEFAULT_OUTPUT = DEFAULT_INDEX_ROOT / "retrieval_comparison.json"
EXPECTED_BUILD_VERSION = "rag-index-build-v1.2"
EVALUATION_VERSION = "retrieval-eval-v1.3"
FROZEN_CANDIDATE_LIMIT = 20
RERANKER_DEVICE = "cpu"


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


def _run_command(command: list[str], label: str) -> None:
    print(f"[progress] {label}: launching isolated process", flush=True)
    started = time.monotonic()
    completed = subprocess.run(command, check=False)
    elapsed = int(time.monotonic() - started)
    if completed.returncode != 0:
        raise RuntimeError(
            f"{label} failed with child-process exit code {completed.returncode}"
        )
    print(f"[progress] {label}: isolated process finished ({elapsed}s)", flush=True)


def encode_queries_isolated(
    *, texts: list[str], model: str, directory: Path, prefix: str
) -> tuple[Path, dict[str, Any]]:
    input_path = directory / f"{prefix}_encoder_input.json"
    vectors_path = directory / f"{prefix}_query_vectors.npy"
    metadata_path = directory / f"{prefix}_encoder_metadata.json"
    input_path.write_text(
        json.dumps({"texts": texts}, ensure_ascii=False), encoding="utf-8"
    )
    _run_command(
        [
            sys.executable,
            "-m",
            "full_corpus_pipeline.encode_queries_worker",
            "--input",
            str(input_path),
            "--output",
            str(vectors_path),
            "--metadata-output",
            str(metadata_path),
            "--model",
            model,
        ],
        f"{prefix} SentenceTransformer query encoding (FAISS not imported)",
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return vectors_path, metadata


def faiss_search_isolated(
    *,
    index_path: Path,
    vectors_path: Path,
    limit: int,
    directory: Path,
    prefix: str,
) -> list[list[dict[str, Any]]]:
    output_path = directory / f"{prefix}_faiss_results.json"
    _run_command(
        [
            sys.executable,
            "-m",
            "full_corpus_pipeline.faiss_search_worker",
            "--index",
            str(index_path),
            "--vectors",
            str(vectors_path),
            "--output",
            str(output_path),
            "--limit",
            str(limit),
        ],
        f"{prefix} FAISS IndexFlatIP search (PyTorch not imported)",
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    rows = payload.get("results", [])
    if not isinstance(rows, list):
        raise ValueError("FAISS worker output 'results' must be a list")
    return rows


def dense_results_from_positions(
    index: HybridIndex, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    chunks = index.chunks
    results: list[dict[str, Any]] = []
    for item in rows:
        position = int(item["index"])
        if position < 0 or position >= len(chunks):
            raise ValueError(f"FAISS result index out of bounds: {position}")
        results.append(
            {
                **asdict(chunks[position]),
                "score": float(item["score"]),
            }
        )
    return results


def hybrid_candidates_from_dense(
    index: HybridIndex,
    query: str,
    dense_row: list[dict[str, Any]],
    *,
    candidate_limit: int,
) -> list[dict[str, Any]]:
    sparse = index.sparse_search(query, candidate_limit)
    dense = [
        {
            "chunk_id": index.chunks[int(item["index"])].chunk_id,
            "score": float(item["score"]),
        }
        for item in dense_row
    ]
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
        candidates.append(
            {
                **asdict(chunk),
                "retrieval_score": score,
                "lexical_overlap": len(query_terms & chunk_terms)
                / max(len(query_terms), 1),
            }
        )
    return candidates


def run_isolated_reranker(
    *,
    items: list[dict[str, Any]],
    model: str,
    limit: int,
    directory: Path,
    prefix: str,
) -> list[dict[str, Any]]:
    input_path = directory / f"{prefix}_rerank_input.json"
    output_path = directory / f"{prefix}_rerank_output.json"
    input_path.write_text(
        json.dumps({"items": items}, ensure_ascii=False), encoding="utf-8"
    )
    _run_command(
        [
            sys.executable,
            "-m",
            "full_corpus_pipeline.rerank_candidates_worker",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--model",
            model,
            "--device",
            RERANKER_DEVICE,
            "--limit",
            str(limit),
        ],
        f"{prefix} CPU cross-encoder reranking (FAISS not imported)",
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    output_items = payload.get("items", [])
    if not isinstance(output_items, list):
        raise ValueError("reranker worker output 'items' must be a list")
    return output_items


def relevance_rank(results: list[dict[str, Any]], question: dict[str, Any]) -> int | None:
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


def _row_for_results(
    question: dict[str, Any], results: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "question_id": question["question_id"],
        "category": question["category"],
        "rank": relevance_rank(results, question),
        "source_rank": source_rank(results, question),
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


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(rows)
    if count == 0:
        raise ValueError("no answerable retrieval questions")
    return {
        "answerable_question_count": count,
        "recall_at_1": sum(row["rank"] == 1 for row in rows) / count,
        "recall_at_3": sum(row["rank"] is not None and row["rank"] <= 3 for row in rows) / count,
        "recall_at_5": sum(row["rank"] is not None and row["rank"] <= 5 for row in rows) / count,
        "mrr": sum(1 / row["rank"] if row["rank"] else 0 for row in rows) / count,
        "ndcg_at_5": sum(1 / math.log2(row["rank"] + 1) if row["rank"] else 0 for row in rows) / count,
        "correct_source_at_1": sum(row["source_rank"] == 1 for row in rows) / count,
        "correct_source_at_5": sum(row["source_rank"] is not None and row["source_rank"] <= 5 for row in rows) / count,
        "correct_source_and_page_at_1": sum(row["rank"] == 1 for row in rows) / count,
        "correct_source_and_page_at_5": sum(row["rank"] is not None and row["rank"] <= 5 for row in rows) / count,
    }


def paired_comparison(e0_rows: list[dict[str, Any]], e4_rows: list[dict[str, Any]]) -> dict[str, Any]:
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


def run_runtime_smoke(
    *,
    e4: HybridIndex,
    embedding_model: str,
    reranker_model: str,
    directory: Path,
) -> dict[str, Any]:
    query = "airworthiness directive compliance inspection"
    print("[progress] pre-benchmark fully isolated E4 smoke test: started", flush=True)
    vectors_path, encoder_meta = encode_queries_isolated(
        texts=[query], model=embedding_model, directory=directory, prefix="smoke"
    )
    dense_rows = faiss_search_isolated(
        index_path=e4.faiss_path,
        vectors_path=vectors_path,
        limit=FROZEN_CANDIDATE_LIMIT,
        directory=directory,
        prefix="smoke_e4",
    )
    if len(dense_rows) != 1:
        raise RuntimeError("smoke FAISS search returned unexpected query count")
    candidates = hybrid_candidates_from_dense(
        e4,
        query,
        dense_rows[0],
        candidate_limit=FROZEN_CANDIDATE_LIMIT,
    )
    if not candidates:
        raise RuntimeError("smoke E4 candidate generation returned no results")
    reranked = run_isolated_reranker(
        items=[{"item_id": "smoke", "query": query, "candidates": candidates}],
        model=reranker_model,
        limit=1,
        directory=directory,
        prefix="smoke",
    )
    if not reranked or not reranked[0].get("results"):
        raise RuntimeError("smoke isolated reranker returned no results")
    print("[progress] pre-benchmark fully isolated E4 smoke test: PASSED", flush=True)
    return encoder_meta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-root", type=Path, default=DEFAULT_INDEX_ROOT)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--candidate-limit", type=int, default=FROZEN_CANDIDATE_LIMIT)
    args = parser.parse_args()
    if args.candidate_limit != FROZEN_CANDIDATE_LIMIT:
        raise ValueError(
            f"locked evaluation requires candidate-limit={FROZEN_CANDIDATE_LIMIT}"
        )

    print("[progress] validating frozen retrieval build", flush=True)
    validate_build_summary(args.index_root)
    e0 = HybridIndex(args.index_root / "e0_flat_dense")
    e4 = HybridIndex(args.index_root / "e4_section_hybrid")
    e0_config, e4_config = validate_index_pair(e0, e4)
    embedding_model = str(e0_config["embedding_model"])
    reranker_model = str(e4_config["reranker_model"])

    with tempfile.TemporaryDirectory(prefix="retrieval-eval-") as temporary:
        work = Path(temporary)
        smoke_encoder_meta = run_runtime_smoke(
            e4=e4,
            embedding_model=embedding_model,
            reranker_model=reranker_model,
            directory=work,
        )

        # Locked questions are loaded only after the full isolated runtime path passes.
        questions = load_questions(args.questions)
        queries = [str(question["question"]) for question in questions]
        print(f"[progress] locked benchmark opened: {len(questions)} answerable questions", flush=True)

        vectors_path, encoder_meta = encode_queries_isolated(
            texts=queries,
            model=embedding_model,
            directory=work,
            prefix="benchmark",
        )
        e0_dense_rows = faiss_search_isolated(
            index_path=e0.faiss_path,
            vectors_path=vectors_path,
            limit=5,
            directory=work,
            prefix="benchmark_e0",
        )
        e4_dense_rows = faiss_search_isolated(
            index_path=e4.faiss_path,
            vectors_path=vectors_path,
            limit=FROZEN_CANDIDATE_LIMIT,
            directory=work,
            prefix="benchmark_e4",
        )
        if len(e0_dense_rows) != len(questions) or len(e4_dense_rows) != len(questions):
            raise RuntimeError("FAISS worker returned unexpected benchmark query count")

        e0_rows: list[dict[str, Any]] = []
        e4_items: list[dict[str, Any]] = []
        started = time.monotonic()
        for position, (question, e0_dense, e4_dense) in enumerate(
            zip(questions, e0_dense_rows, e4_dense_rows), 1
        ):
            print(
                f"[progress] assembling frozen retrieval results: question "
                f"{position}/{len(questions)} ({question['question_id']})",
                flush=True,
            )
            e0_results = dense_results_from_positions(e0, e0_dense)
            e0_rows.append(_row_for_results(question, e0_results))
            e4_items.append(
                {
                    "item_id": question["question_id"],
                    "query": question["question"],
                    "candidates": hybrid_candidates_from_dense(
                        e4,
                        question["question"],
                        e4_dense,
                        candidate_limit=FROZEN_CANDIDATE_LIMIT,
                    ),
                }
            )
        print(
            f"[progress] frozen dense/RRF assembly finished "
            f"({int(time.monotonic() - started)}s)",
            flush=True,
        )

        reranked_items = run_isolated_reranker(
            items=e4_items,
            model=reranker_model,
            limit=5,
            directory=work,
            prefix="benchmark_e4",
        )
        by_id = {str(item["item_id"]): item for item in reranked_items}
        e4_rows: list[dict[str, Any]] = []
        for question in questions:
            item = by_id.get(str(question["question_id"]))
            if item is None:
                raise ValueError(f"missing reranked output for {question['question_id']}")
            e4_rows.append(_row_for_results(question, list(item.get("results", []))))

    e0_metrics = summarize(e0_rows)
    e4_metrics = summarize(e4_rows)
    report = {
        "evaluation_version": EVALUATION_VERSION,
        "retrieval_build_version": EXPECTED_BUILD_VERSION,
        "benchmark": str(args.questions),
        "policy": "Frozen E0/E4 configuration; report results without tuning on locked questions.",
        "embedding_model": embedding_model,
        "reranker_model": reranker_model,
        "candidate_limit": FROZEN_CANDIDATE_LIMIT,
        "runtime": {
            "query_encoder_execution": "isolated_subprocess_without_faiss",
            "query_encoder_device": encoder_meta.get("device"),
            "smoke_query_encoder_device": smoke_encoder_meta.get("device"),
            "faiss_execution": "isolated_subprocess_without_pytorch",
            "faiss_backend": "faiss_index_flat_ip",
            "reranker_execution": "isolated_subprocess_without_faiss",
            "reranker_device": RERANKER_DEVICE,
            "reason": "macOS ARM PyTorch/FAISS OpenMP process isolation",
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
