#!/usr/bin/env python3
"""E5-B two-stage lexical discovery and evidence assembly.

E5-B preserves E5-A for explicit known-document questions, where development
Recall@5 is already 1.0. For corpus-wide discovery it adds four transparent,
non-neural stages:

1. signal-preserving BM25 discovery over a wider chunk pool;
2. document-level aggregation of sparse hits;
3. a second BM25 search restricted to each candidate AD;
4. evidence assembly that emits one primary passage per candidate AD before
   adjacent/section-diverse secondary passages.

The final-test families remain sealed. This module is tuned only on the E5
60-question development benchmark.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from full_corpus_pipeline.e5_query_router import QueryRoute, route_query
from full_corpus_pipeline.e5_retrieval import DEFAULT_INDEX, EngineeringAwareRetriever
from full_corpus_pipeline.retrieval import TOKEN_RE


DISCOVERY_POOL_LIMIT = 80
DOCUMENT_LIMIT = 12
WITHIN_DOCUMENT_LIMIT = 6
FINAL_CANDIDATE_LIMIT = 20
MAX_SIGNAL_TERMS = 48
DOCUMENT_SUPPORT_HITS = 3


@dataclass(frozen=True)
class E5BDocumentCandidate:
    ad_number: str
    document_rank: int
    best_global_rank: int
    support_rrf: float
    global_hit_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvidenceAssemblyRetriever:
    """Two-stage lexical retriever used by the E5-B ablation."""

    def __init__(self, index_dir: Path = DEFAULT_INDEX):
        self.base = EngineeringAwareRetriever(Path(index_dir))
        self.index = self.base.index
        self._by_id = self.base._by_id

    @staticmethod
    def _signal_terms(query: str) -> list[str]:
        """Keep late numeric/identifier terms instead of truncating first-20 tokens.

        E5-A intentionally reused the frozen FTS helper, which keeps only the
        first 20 tokens. Development error analysis showed that critical later
        thresholds/identifiers can therefore be omitted. E5-B de-duplicates all
        query terms, always keeps digit-bearing signals first, then fills the
        remaining budget with the original lexical terms.
        """
        raw = [term.lower() for term in TOKEN_RE.findall(query) if len(term) > 1]
        seen: set[str] = set()
        deduped: list[str] = []
        for term in raw:
            if term not in seen:
                seen.add(term)
                deduped.append(term)
        numeric = [term for term in deduped if any(char.isdigit() for char in term)]
        lexical = [term for term in deduped if term not in set(numeric)]
        return (numeric + lexical)[:MAX_SIGNAL_TERMS]

    @classmethod
    def _fts_query(cls, query: str) -> str:
        terms = cls._signal_terms(query)
        return " OR ".join(f'"{term.replace(chr(34), "")}"' for term in terms)

    def _sparse_search(
        self,
        query: str,
        *,
        limit: int,
        ad_number: str | None = None,
    ) -> list[dict[str, Any]]:
        fts_query = self._fts_query(query)
        if not fts_query:
            return []
        connection = sqlite3.connect(self.index.sqlite_path)
        connection.row_factory = sqlite3.Row
        try:
            if ad_number is None:
                rows = connection.execute(
                    "SELECT chunk_id, bm25(chunks) AS score "
                    "FROM chunks WHERE chunks MATCH ? ORDER BY score LIMIT ?",
                    (fts_query, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT chunk_id, bm25(chunks) AS score "
                    "FROM chunks WHERE chunks MATCH ? AND lower(ad_number) = lower(?) "
                    "ORDER BY score LIMIT ?",
                    (fts_query, ad_number, limit),
                ).fetchall()
        finally:
            connection.close()
        return [
            {"chunk_id": row["chunk_id"], "score": -float(row["score"])}
            for row in rows
        ]

    def _rank_documents(
        self,
        rows: list[dict[str, Any]],
    ) -> list[E5BDocumentCandidate]:
        grouped: dict[str, list[int]] = defaultdict(list)
        for rank, row in enumerate(rows, 1):
            chunk = self._by_id[row["chunk_id"]]
            grouped[chunk.ad_number].append(rank)

        scored: list[tuple[str, int, float, int]] = []
        for ad_number, ranks in grouped.items():
            ordered = sorted(ranks)
            support = sum(
                1.0 / (60 + rank)
                for rank in ordered[:DOCUMENT_SUPPORT_HITS]
            )
            scored.append((ad_number, ordered[0], support, len(ordered)))

        # Accumulated sparse support ranks documents first; best individual hit
        # is the deterministic tie-break. Limiting support to three hits avoids
        # long documents winning simply because they contain more chunks.
        scored.sort(key=lambda item: (-item[2], item[1], item[0]))
        return [
            E5BDocumentCandidate(
                ad_number=ad_number,
                document_rank=position,
                best_global_rank=best_rank,
                support_rrf=support,
                global_hit_count=hit_count,
            )
            for position, (ad_number, best_rank, support, hit_count) in enumerate(scored, 1)
        ]

    def _materialize_raw(
        self,
        rows: list[dict[str, Any]],
        *,
        route: QueryRoute,
    ) -> list[dict[str, Any]]:
        # E5-A's _materialize intentionally hard-partitions preferred sections.
        # E5-B discovery keeps raw BM25 passage order and records section
        # preference only as metadata; this prevents a weak intent classification
        # from hiding the best lexical page.
        preferred = {section.casefold() for section in route.preferred_sections}
        output: list[dict[str, Any]] = []
        for sparse_rank, row in enumerate(rows, 1):
            chunk = self._by_id[row["chunk_id"]]
            output.append(
                {
                    **asdict(chunk),
                    "sparse_score": float(row["score"]),
                    "sparse_rank": sparse_rank,
                    "preferred_section": chunk.section.casefold() in preferred,
                    "route_mode": route.mode,
                }
            )
        return output

    @staticmethod
    def _secondary_order(
        primary: dict[str, Any],
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        primary_pages = range(int(primary["page_start"]), int(primary["page_end"]) + 1)
        primary_set = set(primary_pages)

        def key(item: dict[str, Any]) -> tuple[int, int, int, str]:
            item_pages = set(range(int(item["page_start"]), int(item["page_end"]) + 1))
            adjacent = any(
                abs(page - primary_page) <= 1
                for page in item_pages
                for primary_page in primary_set
            )
            section_diverse = item["section"].casefold() != primary["section"].casefold()
            return (
                0 if adjacent else 1,
                0 if section_diverse else 1,
                int(item["sparse_rank"]),
                str(item["chunk_id"]),
            )

        return sorted(candidates, key=key)

    def retrieve(
        self,
        question: str,
        *,
        discovery_pool_limit: int = DISCOVERY_POOL_LIMIT,
        document_limit: int = DOCUMENT_LIMIT,
        within_document_limit: int = WITHIN_DOCUMENT_LIMIT,
        final_candidate_limit: int = FINAL_CANDIDATE_LIMIT,
    ) -> dict[str, Any]:
        route = route_query(question)

        # Preserve the successful E5-A behavior for explicit-document queries.
        if route.mode != "discovery":
            result = self.base.retrieve_lexical(
                question,
                per_route_limit=final_candidate_limit,
            )
            candidates = []
            for item in result.get("candidates", []):
                candidates.append(
                    {
                        **item,
                        "document_rank": 1,
                        "assembly_role": "e5a_preserved",
                        "global_best_rank": None,
                        "document_support_rrf": None,
                    }
                )
            return {
                **result,
                "e5b_mode": "e5a_preserved_known_document",
                "document_candidates": [],
                "candidates": candidates,
            }

        ranking_query = self.base._ranking_query(question, route)
        global_rows = self._sparse_search(
            ranking_query,
            limit=discovery_pool_limit,
        )
        ranked_documents = self._rank_documents(global_rows)
        selected_documents = ranked_documents[:document_limit]

        primaries: list[dict[str, Any]] = []
        secondaries: list[dict[str, Any]] = []
        route_errors: list[str] = []

        for document in selected_documents:
            rows = self._sparse_search(
                ranking_query,
                ad_number=document.ad_number,
                limit=within_document_limit,
            )
            passages = self._materialize_raw(rows, route=route)
            if not passages:
                route_errors.append(
                    f"no within-document lexical passage for candidate AD {document.ad_number}"
                )
                continue

            primary = {
                **passages[0],
                "document_rank": document.document_rank,
                "assembly_role": "primary",
                "global_best_rank": document.best_global_rank,
                "document_support_rrf": document.support_rrf,
            }
            primaries.append(primary)

            extras = self._secondary_order(primary, passages[1:])
            for item in extras:
                secondaries.append(
                    {
                        **item,
                        "document_rank": document.document_rank,
                        "assembly_role": "secondary",
                        "global_best_rank": document.best_global_rank,
                        "document_support_rrf": document.support_rrf,
                    }
                )

        # One primary passage per candidate document comes first. This preserves
        # broad source recall in the top ranks; adjacent/section-diverse evidence
        # is then added for multi-passage QA context.
        assembled = primaries + sorted(
            secondaries,
            key=lambda item: (
                int(item["document_rank"]),
                int(item["sparse_rank"]),
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
            "configuration": {
                "discovery_pool_limit": discovery_pool_limit,
                "document_limit": document_limit,
                "within_document_limit": within_document_limit,
                "final_candidate_limit": final_candidate_limit,
                "max_signal_terms": MAX_SIGNAL_TERMS,
                "document_support_hits": DOCUMENT_SUPPORT_HITS,
            },
            "document_candidates": [item.to_dict() for item in selected_documents],
            "candidate_count": len(unique),
            "candidates": unique,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--discovery-pool-limit", type=int, default=DISCOVERY_POOL_LIMIT)
    parser.add_argument("--document-limit", type=int, default=DOCUMENT_LIMIT)
    parser.add_argument("--within-document-limit", type=int, default=WITHIN_DOCUMENT_LIMIT)
    parser.add_argument("--limit", type=int, default=FINAL_CANDIDATE_LIMIT)
    args = parser.parse_args()

    retriever = EvidenceAssemblyRetriever(args.index)
    result = retriever.retrieve(
        args.question,
        discovery_pool_limit=args.discovery_pool_limit,
        document_limit=args.document_limit,
        within_document_limit=args.within_document_limit,
        final_candidate_limit=args.limit,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
