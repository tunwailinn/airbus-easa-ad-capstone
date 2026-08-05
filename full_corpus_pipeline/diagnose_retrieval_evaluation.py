#!/usr/bin/env python3
"""Diagnose frozen retrieval plumbing without changing or rerunning benchmark policy.

This is an error-analysis tool, not a tuning tool. It verifies:

1. FAISS row positions still align with chunks.jsonl / dense_embeddings.npy;
2. stored dense embeddings match fresh encodings from the frozen model;
3. locked benchmark target ADs are actually present in each frozen index;
4. whether target AD numbers are literal terms in benchmark questions; and
5. source/page candidate recall at depth 20 for E0 dense, E4 dense, and E4 BM25.

On macOS ARM, SentenceTransformer encoding and FAISS search remain isolated in
separate child processes to avoid the PyTorch/FAISS OpenMP crash encountered by the
main evaluation runtime.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

from full_corpus_pipeline.evaluate_retrieval_experiments import (
    FROZEN_CANDIDATE_LIMIT,
    encode_queries_isolated,
    faiss_search_isolated,
    load_questions,
    validate_build_summary,
    validate_index_pair,
)
from full_corpus_pipeline.retrieval import HybridIndex


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX_ROOT = ROOT / "data_processed/indexes/rag_v1_2"
DEFAULT_QUESTIONS = ROOT / "evaluation_sets/easa_airbus_ad_qa_50_v2/questions.jsonl"
DEFAULT_OUTPUT = DEFAULT_INDEX_ROOT / "retrieval_plumbing_diagnostic.json"
DIAGNOSTIC_VERSION = "retrieval-plumbing-diagnostic-v1.0"


def _source_rank_from_chunks(chunks: list[Any], positions: list[int], target: str) -> int | None:
    target_cf = target.casefold()
    for rank, position in enumerate(positions, 1):
        if position < 0 or position >= len(chunks):
            continue
        if chunks[position].ad_number.casefold() == target_cf:
            return rank
    return None


def _page_rank_from_chunks(
    chunks: list[Any], positions: list[int], target: str, reference_pages: list[int]
) -> int | None:
    target_cf = target.casefold()
    pages = {int(page) for page in reference_pages}
    for rank, position in enumerate(positions, 1):
        if position < 0 or position >= len(chunks):
            continue
        chunk = chunks[position]
        if chunk.ad_number.casefold() != target_cf:
            continue
        if any(int(chunk.page_start) <= page <= int(chunk.page_end) for page in pages):
            return rank
    return None


def _source_rank_sparse(results: list[dict[str, Any]], by_id: dict[str, Any], target: str) -> int | None:
    target_cf = target.casefold()
    for rank, item in enumerate(results, 1):
        chunk = by_id[item["chunk_id"]]
        if chunk.ad_number.casefold() == target_cf:
            return rank
    return None


def _page_rank_sparse(
    results: list[dict[str, Any]], by_id: dict[str, Any], target: str, reference_pages: list[int]
) -> int | None:
    target_cf = target.casefold()
    pages = {int(page) for page in reference_pages}
    for rank, item in enumerate(results, 1):
        chunk = by_id[item["chunk_id"]]
        if chunk.ad_number.casefold() != target_cf:
            continue
        if any(int(chunk.page_start) <= page <= int(chunk.page_end) for page in pages):
            return rank
    return None


def _summary(ranks: list[int | None]) -> dict[str, Any]:
    total = len(ranks)
    return {
        "question_count": total,
        "hit_count": sum(rank is not None for rank in ranks),
        "recall_at_20": sum(rank is not None and rank <= 20 for rank in ranks) / total if total else 0.0,
        "mean_rank_when_hit": (
            sum(rank for rank in ranks if rank is not None) / sum(rank is not None for rank in ranks)
            if any(rank is not None for rank in ranks)
            else None
        ),
    }


def _sample_positions(count: int, sample_count: int) -> list[int]:
    if count <= 0:
        return []
    sample_count = max(1, min(sample_count, count))
    if sample_count == 1:
        return [0]
    return sorted({round(i * (count - 1) / (sample_count - 1)) for i in range(sample_count)})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-root", type=Path, default=DEFAULT_INDEX_ROOT)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sample-count", type=int, default=20)
    args = parser.parse_args()

    print("[progress] validating frozen retrieval build", flush=True)
    validate_build_summary(args.index_root)
    e0 = HybridIndex(args.index_root / "e0_flat_dense")
    e4 = HybridIndex(args.index_root / "e4_section_hybrid")
    e0_config, e4_config = validate_index_pair(e0, e4)
    embedding_model = str(e0_config["embedding_model"])
    questions = load_questions(args.questions)
    targets = sorted({str(question["target_ad_number"]) for question in questions})

    e0_ads = {chunk.ad_number.casefold() for chunk in e0.chunks}
    e4_ads = {chunk.ad_number.casefold() for chunk in e4.chunks}
    target_presence = {
        target: {
            "e0_present": target.casefold() in e0_ads,
            "e4_present": target.casefold() in e4_ads,
        }
        for target in targets
    }

    literal_target_flags = [
        str(question["target_ad_number"]).casefold() in str(question["question"]).casefold()
        for question in questions
    ]

    with tempfile.TemporaryDirectory(prefix="retrieval-diagnostic-") as temporary:
        work = Path(temporary)

        alignment: dict[str, Any] = {}
        encoding_consistency: dict[str, Any] = {}
        for label, index in (("e0", e0), ("e4", e4)):
            print(f"[progress] checking {label.upper()} FAISS/chunk row alignment", flush=True)
            stored = np.load(index.embedding_path).astype("float32", copy=False)
            if stored.ndim != 2 or stored.shape[0] != len(index.chunks):
                raise ValueError(
                    f"{label}: dense_embeddings rows {stored.shape[0]} != chunk rows {len(index.chunks)}"
                )
            positions = _sample_positions(len(index.chunks), args.sample_count)
            vector_path = work / f"{label}_stored_sample_vectors.npy"
            np.save(vector_path, stored[positions])
            faiss_rows = faiss_search_isolated(
                index_path=index.faiss_path,
                vectors_path=vector_path,
                limit=1,
                directory=work,
                prefix=f"diag_{label}_self",
            )
            returned_positions = [row[0]["index"] if row else None for row in faiss_rows]
            alignment[label] = {
                "sample_positions": positions,
                "returned_top1_positions": returned_positions,
                "exact_top1_match_count": sum(a == b for a, b in zip(positions, returned_positions)),
                "sample_count": len(positions),
                "pass": positions == returned_positions,
            }

            print(f"[progress] re-encoding {label.upper()} sample chunk text", flush=True)
            encoded_path, encoder_meta = encode_queries_isolated(
                texts=[index.chunks[position].text for position in positions],
                model=embedding_model,
                directory=work,
                prefix=f"diag_{label}_reencode",
            )
            encoded = np.load(encoded_path).astype("float32", copy=False)
            same_row_cosines = np.sum(encoded * stored[positions], axis=1)
            encoding_consistency[label] = {
                "encoder_device": encoder_meta.get("device"),
                "sample_count": len(positions),
                "min_same_row_cosine": float(np.min(same_row_cosines)),
                "mean_same_row_cosine": float(np.mean(same_row_cosines)),
                "max_same_row_cosine": float(np.max(same_row_cosines)),
                "all_above_0_99": bool(np.all(same_row_cosines > 0.99)),
            }

        print(f"[progress] encoding {len(questions)} locked queries for diagnostic branch analysis", flush=True)
        query_vectors_path, query_encoder_meta = encode_queries_isolated(
            texts=[str(question["question"]) for question in questions],
            model=embedding_model,
            directory=work,
            prefix="diag_benchmark",
        )
        e0_dense_rows = faiss_search_isolated(
            index_path=e0.faiss_path,
            vectors_path=query_vectors_path,
            limit=FROZEN_CANDIDATE_LIMIT,
            directory=work,
            prefix="diag_e0_dense20",
        )
        e4_dense_rows = faiss_search_isolated(
            index_path=e4.faiss_path,
            vectors_path=query_vectors_path,
            limit=FROZEN_CANDIDATE_LIMIT,
            directory=work,
            prefix="diag_e4_dense20",
        )

        e4_by_id = {chunk.chunk_id: chunk for chunk in e4.chunks}
        rows: list[dict[str, Any]] = []
        started = time.monotonic()
        for position, (question, e0_dense, e4_dense) in enumerate(
            zip(questions, e0_dense_rows, e4_dense_rows), 1
        ):
            print(
                f"[progress] branch diagnostic: question {position}/{len(questions)} "
                f"({question['question_id']})",
                flush=True,
            )
            e0_positions = [int(item["index"]) for item in e0_dense]
            e4_positions = [int(item["index"]) for item in e4_dense]
            sparse = e4.sparse_search(str(question["question"]), FROZEN_CANDIDATE_LIMIT)
            target = str(question["target_ad_number"])
            ref_pages = [int(page) for page in question.get("reference_pages", [])]
            rows.append(
                {
                    "question_id": question["question_id"],
                    "category": question["category"],
                    "target_ad_number": target,
                    "target_literal_in_question": target.casefold() in str(question["question"]).casefold(),
                    "e0_dense_source_rank_at_20": _source_rank_from_chunks(e0.chunks, e0_positions, target),
                    "e0_dense_source_page_rank_at_20": _page_rank_from_chunks(e0.chunks, e0_positions, target, ref_pages),
                    "e4_dense_source_rank_at_20": _source_rank_from_chunks(e4.chunks, e4_positions, target),
                    "e4_dense_source_page_rank_at_20": _page_rank_from_chunks(e4.chunks, e4_positions, target, ref_pages),
                    "e4_bm25_source_rank_at_20": _source_rank_sparse(sparse, e4_by_id, target),
                    "e4_bm25_source_page_rank_at_20": _page_rank_sparse(sparse, e4_by_id, target, ref_pages),
                }
            )
        print(
            f"[progress] branch diagnostic finished ({int(time.monotonic() - started)}s)",
            flush=True,
        )

    report = {
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "retrieval_build_version": "rag-index-build-v1.2",
        "evaluation_version_reviewed": "retrieval-eval-v1.3",
        "policy": "Post-evaluation plumbing/error analysis only; do not tune frozen retrieval from these diagnostics.",
        "embedding_model": embedding_model,
        "answerable_question_count": len(questions),
        "target_presence": target_presence,
        "question_target_literal": {
            "literal_count": sum(literal_target_flags),
            "question_count": len(literal_target_flags),
            "fraction": sum(literal_target_flags) / len(literal_target_flags) if literal_target_flags else 0.0,
        },
        "faiss_chunk_alignment": alignment,
        "stored_embedding_reencode_consistency": encoding_consistency,
        "query_encoder_device": query_encoder_meta.get("device"),
        "branch_summary": {
            "e0_dense_source_at_20": _summary([row["e0_dense_source_rank_at_20"] for row in rows]),
            "e0_dense_source_page_at_20": _summary([row["e0_dense_source_page_rank_at_20"] for row in rows]),
            "e4_dense_source_at_20": _summary([row["e4_dense_source_rank_at_20"] for row in rows]),
            "e4_dense_source_page_at_20": _summary([row["e4_dense_source_page_rank_at_20"] for row in rows]),
            "e4_bm25_source_at_20": _summary([row["e4_bm25_source_rank_at_20"] for row in rows]),
            "e4_bm25_source_page_at_20": _summary([row["e4_bm25_source_page_rank_at_20"] for row in rows]),
        },
        "questions": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "target_presence": target_presence,
        "question_target_literal": report["question_target_literal"],
        "faiss_chunk_alignment": alignment,
        "stored_embedding_reencode_consistency": encoding_consistency,
        "branch_summary": report["branch_summary"],
    }, indent=2))
    print(f"[progress] diagnostic report written: {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
