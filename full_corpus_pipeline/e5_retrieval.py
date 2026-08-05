#!/usr/bin/env python3
"""E5 engineering-aware retrieval primitives.

E5-A is intentionally simple and local:

- deterministic query routing;
- exact-document retrieval when the question names one AD;
- independent retrieval for multi-document questions;
- corpus-wide sparse discovery only when no AD identifier is supplied;
- section preferences as a transparent stable ordering signal.

Stronger dense/reranker stages are added as later E5 ablations and are tuned only
on the new E5 development benchmark.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from full_corpus_pipeline.e5_query_router import AD_RE, QueryRoute, route_query
from full_corpus_pipeline.retrieval import HybridIndex, TOKEN_RE


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = ROOT / "data_processed/indexes/rag_v1_2/e4_section_hybrid"


@dataclass(frozen=True)
class E5Candidate:
    chunk_id: str
    file_instance_id: str
    ad_number: str
    source_pdf: str
    page_start: int
    page_end: int
    section: str
    text: str
    lifecycle_status: str
    sparse_score: float
    sparse_rank: int
    preferred_section: bool
    route_mode: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EngineeringAwareRetriever:
    def __init__(self, index_dir: Path = DEFAULT_INDEX):
        self.index = HybridIndex(Path(index_dir))
        self._by_id = {chunk.chunk_id: chunk for chunk in self.index.chunks}
        self._ad_numbers = {chunk.ad_number.casefold() for chunk in self.index.chunks}

    @staticmethod
    def _fts_query(query: str) -> str:
        terms = [term for term in TOKEN_RE.findall(query.lower()) if len(term) > 1]
        if not terms:
            return ""
        return " OR ".join(f'"{term.replace(chr(34), "")}"' for term in terms[:20])

    @staticmethod
    def _ranking_query(question: str, route: QueryRoute) -> str:
        """Remove routed AD identifiers before lexical passage ranking.

        When the user explicitly supplies an AD number, E5 treats it only as a
        deterministic document-routing key. Leaving the identifier in BM25 would
        bias passage ranking toward header chunks that repeat the AD number, which
        contradicts the predeclared E5 architecture.
        """
        if route.mode not in {"known_document", "multi_document"}:
            return question
        stripped = AD_RE.sub(" ", question)
        return " ".join(stripped.split())

    def has_exact_ad(self, ad_number: str) -> bool:
        return ad_number.casefold() in self._ad_numbers

    def sparse_within_ad(
        self,
        query: str,
        ad_number: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """FTS/BM25 search restricted before ranking to one exact AD number."""
        fts_query = self._fts_query(query)
        if not fts_query:
            return []
        connection = sqlite3.connect(self.index.sqlite_path)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                "SELECT chunk_id, bm25(chunks) AS score "
                "FROM chunks "
                "WHERE chunks MATCH ? AND lower(ad_number) = lower(?) "
                "ORDER BY score LIMIT ?",
                (fts_query, ad_number, limit),
            ).fetchall()
        finally:
            connection.close()
        return [
            {"chunk_id": row["chunk_id"], "score": -float(row["score"])}
            for row in rows
        ]

    def _materialize(
        self,
        rows: list[dict[str, Any]],
        *,
        route: QueryRoute,
    ) -> list[E5Candidate]:
        preferred = {section.casefold() for section in route.preferred_sections}
        candidates: list[E5Candidate] = []
        for rank, row in enumerate(rows, 1):
            chunk = self._by_id[row["chunk_id"]]
            candidates.append(
                E5Candidate(
                    chunk_id=chunk.chunk_id,
                    file_instance_id=chunk.file_instance_id,
                    ad_number=chunk.ad_number,
                    source_pdf=chunk.source_pdf,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    section=chunk.section,
                    text=chunk.text,
                    lifecycle_status=chunk.lifecycle_status,
                    sparse_score=float(row["score"]),
                    sparse_rank=rank,
                    preferred_section=chunk.section.casefold() in preferred,
                    route_mode=route.mode,
                )
            )

        # Transparent E5-A ordering: preferred source sections first while
        # preserving BM25 order inside each partition. This is deliberately not
        # a learned or opaque score.
        return sorted(
            candidates,
            key=lambda item: (not item.preferred_section, item.sparse_rank),
        )

    def retrieve_lexical(
        self,
        question: str,
        *,
        per_route_limit: int = 20,
    ) -> dict[str, Any]:
        route = route_query(question)
        ranking_query = self._ranking_query(question, route)
        route_errors: list[str] = []
        candidates: list[E5Candidate] = []

        if route.mode == "known_document":
            ad_number = route.ad_numbers[0]
            if not self.has_exact_ad(ad_number):
                route_errors.append(f"exact AD not found in index: {ad_number}")
            else:
                rows = self.sparse_within_ad(
                    ranking_query,
                    ad_number,
                    limit=per_route_limit,
                )
                candidates.extend(self._materialize(rows, route=route))

        elif route.mode == "multi_document":
            for ad_number in route.ad_numbers:
                if not self.has_exact_ad(ad_number):
                    route_errors.append(f"exact AD not found in index: {ad_number}")
                    continue
                rows = self.sparse_within_ad(
                    ranking_query,
                    ad_number,
                    limit=per_route_limit,
                )
                candidates.extend(self._materialize(rows, route=route))

        else:
            rows = self.index.sparse_search(ranking_query, per_route_limit)
            candidates.extend(self._materialize(rows, route=route))

        return {
            "route": route.to_dict(),
            "ranking_query": ranking_query,
            "route_errors": route_errors,
            "candidate_count": len(candidates),
            "candidates": [candidate.to_dict() for candidate in candidates],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    retriever = EngineeringAwareRetriever(args.index)
    result = retriever.retrieve_lexical(args.question, per_route_limit=args.limit)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
