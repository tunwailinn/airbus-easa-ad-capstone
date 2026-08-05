#!/usr/bin/env python3
"""E5-C: E5-B plus Qwen3 dense retrieval for discovery queries.

Known-document and multi-document routes are preserved exactly from E5-B. For
identifier-free discovery, E5-C combines document ranks from BM25 and normalized
Qwen3-Embedding-0.6B cosine similarity using reciprocal-rank fusion, then fuses
BM25 and Qwen passage ranks inside each shortlisted AD before E5-B-style evidence
assembly.

No FAISS or PyTorch is imported here. Dense document vectors are precomputed by
``build_e5c_dense_embeddings`` and query vectors are supplied by an isolated
SentenceTransformers worker.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from full_corpus_pipeline.build_e5c_dense_embeddings import (
    BUILD_VERSION,
    DEFAULT_OUTPUT as DEFAULT_DENSE_DIR,
    MODEL_NAME,
)
from full_corpus_pipeline.e5_query_router import QueryRoute, route_query
from full_corpus_pipeline.e5_retrieval import DEFAULT_INDEX
from full_corpus_pipeline.e5b_retrieval import (
    DISCOVERY_POOL_LIMIT,
    DOCUMENT_LIMIT,
    FINAL_CANDIDATE_LIMIT,
    WITHIN_DOCUMENT_LIMIT,
    EvidenceAssemblyRetriever,
)


DENSE_POOL_LIMIT = 80
DOCUMENT_FUSION_DEPTH = 24
RRF_K = 60


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _top_indexes(scores: np.ndarray, limit: int) -> np.ndarray:
    if scores.ndim != 1:
        raise ValueError("dense scores must be one-dimensional")
    limit = min(int(limit), int(scores.shape[0]))
    if limit <= 0:
        return np.asarray([], dtype=np.int64)
    if limit == scores.shape[0]:
        indexes = np.arange(scores.shape[0])
    else:
        indexes = np.argpartition(-scores, limit - 1)[:limit]
    return indexes[np.argsort(-scores[indexes], kind="stable")]


@dataclass(frozen=True)
class DenseDocumentCandidate:
    ad_number: str
    dense_document_rank: int
    best_dense_chunk_rank: int
    support_rrf: float
    dense_hit_count: int


class QwenDenseStore:
    def __init__(self, dense_dir: Path, *, chunk_path: Path, chunks: list[Any]):
        self.directory = Path(dense_dir)
        metadata_path = self.directory / "metadata.json"
        embedding_path = self.directory / "dense_embeddings.npy"
        if not metadata_path.exists() or not embedding_path.exists():
            raise FileNotFoundError(
                f"missing E5-C dense artifact under {self.directory}; run build_e5c_dense_embeddings first"
            )
        self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if self.metadata.get("build_version") != BUILD_VERSION:
            raise ValueError(
                f"expected E5-C dense build {BUILD_VERSION}, got {self.metadata.get('build_version')!r}"
            )
        if self.metadata.get("model") != MODEL_NAME:
            raise ValueError("unexpected E5-C dense embedding model")
        if self.metadata.get("chunk_source_sha256") != sha256_file(chunk_path):
            raise ValueError("E5-C dense artifact does not match frozen E4 chunks.jsonl")
        chunk_id_sha = hashlib.sha256(
            "\n".join(str(chunk.chunk_id) for chunk in chunks).encode("utf-8")
        ).hexdigest()
        if self.metadata.get("chunk_id_order_sha256") != chunk_id_sha:
            raise ValueError("E5-C dense artifact chunk row order does not match frozen E4 chunks")
        if not bool(self.metadata.get("normalized")):
            raise ValueError("E5-C requires normalized document embeddings")

        self.embeddings = np.load(embedding_path, mmap_mode="r")
        if self.embeddings.ndim != 2 or self.embeddings.shape[0] != len(chunks):
            raise ValueError("E5-C dense embedding/chunk row alignment mismatch")
        if int(self.metadata.get("embedding_dimension", -1)) != self.embeddings.shape[1]:
            raise ValueError("E5-C dense embedding dimension metadata mismatch")

        self._chunks = chunks
        self._by_ad: dict[str, np.ndarray] = {}
        grouped: dict[str, list[int]] = defaultdict(list)
        for index, chunk in enumerate(chunks):
            grouped[str(chunk.ad_number).casefold()].append(index)
        for ad_number, indexes in grouped.items():
            self._by_ad[ad_number] = np.asarray(indexes, dtype=np.int64)

    def validate_query_vector(self, vector: np.ndarray) -> np.ndarray:
        vector = np.asarray(vector, dtype="float32").reshape(-1)
        if vector.shape[0] != self.embeddings.shape[1]:
            raise ValueError(
                f"query vector dimension {vector.shape[0]} != document dimension {self.embeddings.shape[1]}"
            )
        if not np.isfinite(vector).all():
            raise ValueError("query vector contains non-finite values")
        return vector

    def search(self, query_vector: np.ndarray, *, limit: int) -> list[dict[str, Any]]:
        vector = self.validate_query_vector(query_vector)
        scores = np.asarray(self.embeddings @ vector, dtype="float32")
        indexes = _top_indexes(scores, limit)
        return [
            {
                "chunk_id": self._chunks[int(index)].chunk_id,
                "score": float(scores[int(index)]),
                "row_index": int(index),
            }
            for index in indexes
        ]

    def search_within_ad(
        self,
        query_vector: np.ndarray,
        ad_number: str,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        vector = self.validate_query_vector(query_vector)
        indexes = self._by_ad.get(ad_number.casefold())
        if indexes is None or not len(indexes):
            return []
        scores = np.asarray(self.embeddings[indexes] @ vector, dtype="float32")
        local = _top_indexes(scores, limit)
        return [
            {
                "chunk_id": self._chunks[int(indexes[int(position)])].chunk_id,
                "score": float(scores[int(position)]),
                "row_index": int(indexes[int(position)]),
            }
            for position in local
        ]


class DenseEvidenceAssemblyRetriever:
    def __init__(
        self,
        index_dir: Path = DEFAULT_INDEX,
        dense_dir: Path = DEFAULT_DENSE_DIR,
    ):
        self.base = EvidenceAssemblyRetriever(index_dir)
        self.index = self.base.index
        self._by_id = self.base._by_id
        self.dense = QwenDenseStore(
            dense_dir,
            chunk_path=self.index.chunk_path,
            chunks=self.index.chunks,
        )

    def _rank_dense_documents(
        self,
        rows: list[dict[str, Any]],
    ) -> list[DenseDocumentCandidate]:
        grouped: dict[str, list[int]] = defaultdict(list)
        for rank, row in enumerate(rows, 1):
            grouped[self._by_id[row["chunk_id"]].ad_number].append(rank)
        scored: list[tuple[str, int, float, int]] = []
        for ad_number, ranks in grouped.items():
            ordered = sorted(ranks)
            support = sum(1.0 / (RRF_K + rank) for rank in ordered[:3])
            scored.append((ad_number, ordered[0], support, len(ordered)))
        scored.sort(key=lambda item: (-item[2], item[1], item[0]))
        return [
            DenseDocumentCandidate(
                ad_number=ad_number,
                dense_document_rank=position,
                best_dense_chunk_rank=best_rank,
                support_rrf=support,
                dense_hit_count=hit_count,
            )
            for position, (ad_number, best_rank, support, hit_count) in enumerate(scored, 1)
        ]

    @staticmethod
    def _fuse_document_rankings(
        lexical: list[Any],
        dense: list[DenseDocumentCandidate],
        *,
        depth: int = DOCUMENT_FUSION_DEPTH,
    ) -> list[dict[str, Any]]:
        lex_rank = {
            item.ad_number: rank
            for rank, item in enumerate(lexical[:depth], 1)
        }
        dense_rank = {
            item.ad_number: rank
            for rank, item in enumerate(dense[:depth], 1)
        }
        ads = set(lex_rank) | set(dense_rank)
        fused: list[dict[str, Any]] = []
        for ad_number in ads:
            score = 0.0
            if ad_number in lex_rank:
                score += 1.0 / (RRF_K + lex_rank[ad_number])
            if ad_number in dense_rank:
                score += 1.0 / (RRF_K + dense_rank[ad_number])
            fused.append(
                {
                    "ad_number": ad_number,
                    "fusion_score": score,
                    "lexical_document_rank": lex_rank.get(ad_number),
                    "dense_document_rank": dense_rank.get(ad_number),
                }
            )
        fused.sort(
            key=lambda item: (
                -float(item["fusion_score"]),
                int(item["lexical_document_rank"] or 10**9),
                int(item["dense_document_rank"] or 10**9),
                str(item["ad_number"]),
            )
        )
        for rank, item in enumerate(fused, 1):
            item["document_rank"] = rank
        return fused

    def _fuse_passages(
        self,
        *,
        lexical_rows: list[dict[str, Any]],
        dense_rows: list[dict[str, Any]],
        route: QueryRoute,
    ) -> list[dict[str, Any]]:
        lex_rank = {row["chunk_id"]: rank for rank, row in enumerate(lexical_rows, 1)}
        dense_rank = {row["chunk_id"]: rank for rank, row in enumerate(dense_rows, 1)}
        lexical_score = {row["chunk_id"]: float(row["score"]) for row in lexical_rows}
        dense_score = {row["chunk_id"]: float(row["score"]) for row in dense_rows}
        preferred = {section.casefold() for section in route.preferred_sections}
        chunk_ids = set(lex_rank) | set(dense_rank)
        output: list[dict[str, Any]] = []
        for chunk_id in chunk_ids:
            score = 0.0
            if chunk_id in lex_rank:
                score += 1.0 / (RRF_K + lex_rank[chunk_id])
            if chunk_id in dense_rank:
                score += 1.0 / (RRF_K + dense_rank[chunk_id])
            chunk = self._by_id[chunk_id]
            output.append(
                {
                    **asdict(chunk),
                    "passage_fusion_score": score,
                    "lexical_passage_rank": lex_rank.get(chunk_id),
                    "dense_passage_rank": dense_rank.get(chunk_id),
                    "sparse_rank": lex_rank.get(chunk_id, 10**9),
                    "sparse_score": lexical_score.get(chunk_id),
                    "dense_score": dense_score.get(chunk_id),
                    "preferred_section": chunk.section.casefold() in preferred,
                    "route_mode": route.mode,
                }
            )
        output.sort(
            key=lambda item: (
                -float(item["passage_fusion_score"]),
                int(item["lexical_passage_rank"] or 10**9),
                int(item["dense_passage_rank"] or 10**9),
                str(item["chunk_id"]),
            )
        )
        for rank, item in enumerate(output, 1):
            item["passage_fusion_rank"] = rank
        return output

    def retrieve(
        self,
        question: str,
        query_vector: np.ndarray | None,
        *,
        discovery_pool_limit: int = DISCOVERY_POOL_LIMIT,
        dense_pool_limit: int = DENSE_POOL_LIMIT,
        document_limit: int = DOCUMENT_LIMIT,
        within_document_limit: int = WITHIN_DOCUMENT_LIMIT,
        final_candidate_limit: int = FINAL_CANDIDATE_LIMIT,
    ) -> dict[str, Any]:
        route = route_query(question)
        if route.mode != "discovery":
            result = self.base.retrieve(
                question,
                discovery_pool_limit=discovery_pool_limit,
                document_limit=document_limit,
                within_document_limit=within_document_limit,
                final_candidate_limit=final_candidate_limit,
            )
            return {**result, "e5c_mode": "e5b_preserved_known_document"}
        if query_vector is None:
            raise ValueError("E5-C discovery retrieval requires a Qwen query vector")

        ranking_query = self.base.base._ranking_query(question, route)
        lexical_global = self.base._sparse_search(ranking_query, limit=discovery_pool_limit)
        lexical_documents = self.base._rank_documents(lexical_global)
        dense_global = self.dense.search(query_vector, limit=dense_pool_limit)
        dense_documents = self._rank_dense_documents(dense_global)
        fused_documents = self._fuse_document_rankings(lexical_documents, dense_documents)
        selected_documents = fused_documents[:document_limit]

        primaries: list[dict[str, Any]] = []
        secondaries: list[dict[str, Any]] = []
        route_errors: list[str] = []
        for document in selected_documents:
            ad_number = str(document["ad_number"])
            lexical_rows = self.base._sparse_search(
                ranking_query,
                ad_number=ad_number,
                limit=within_document_limit,
            )
            dense_rows = self.dense.search_within_ad(
                query_vector,
                ad_number,
                limit=within_document_limit,
            )
            passages = self._fuse_passages(
                lexical_rows=lexical_rows,
                dense_rows=dense_rows,
                route=route,
            )
            if not passages:
                route_errors.append(f"no E5-C passage for candidate AD {ad_number}")
                continue
            primary = {
                **passages[0],
                "document_rank": int(document["document_rank"]),
                "assembly_role": "primary",
                "document_fusion_score": float(document["fusion_score"]),
                "lexical_document_rank": document["lexical_document_rank"],
                "dense_document_rank": document["dense_document_rank"],
            }
            primaries.append(primary)

            # Reuse E5-B adjacency/section-diversity ordering for the remaining
            # fused passages inside the document.
            extras = self.base._secondary_order(primary, passages[1:])
            for item in extras:
                secondaries.append(
                    {
                        **item,
                        "document_rank": int(document["document_rank"]),
                        "assembly_role": "secondary",
                        "document_fusion_score": float(document["fusion_score"]),
                        "lexical_document_rank": document["lexical_document_rank"],
                        "dense_document_rank": document["dense_document_rank"],
                    }
                )

        assembled = primaries + sorted(
            secondaries,
            key=lambda item: (
                int(item["document_rank"]),
                int(item["passage_fusion_rank"]),
                str(item["chunk_id"]),
            ),
        )
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for item in assembled:
            if item["chunk_id"] in seen:
                continue
            seen.add(item["chunk_id"])
            unique.append(item)
            if len(unique) >= final_candidate_limit:
                break

        return {
            "route": route.to_dict(),
            "ranking_query": ranking_query,
            "route_errors": route_errors,
            "e5b_mode": "two_stage_discovery",
            "e5c_mode": "qwen3_dense_fused_discovery",
            "configuration": {
                "lexical_pool_limit": discovery_pool_limit,
                "dense_pool_limit": dense_pool_limit,
                "document_fusion_depth": DOCUMENT_FUSION_DEPTH,
                "document_limit": document_limit,
                "within_document_limit": within_document_limit,
                "final_candidate_limit": final_candidate_limit,
                "rrf_k": RRF_K,
                "embedding_model": MODEL_NAME,
            },
            "document_candidates": selected_documents,
            "candidate_count": len(unique),
            "candidates": unique,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--query-vector", type=Path, required=True)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--dense-dir", type=Path, default=DEFAULT_DENSE_DIR)
    args = parser.parse_args()
    vector = np.load(args.query_vector)
    retriever = DenseEvidenceAssemblyRetriever(args.index, args.dense_dir)
    result = retriever.retrieve(args.question, vector)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
