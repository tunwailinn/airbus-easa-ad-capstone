#!/usr/bin/env python3
"""E5-D local Qwen3 reranking utilities.

E5-D consumes the fixed top-20 candidate pool produced by E5-C and reorders
those passages with Qwen3-Reranker-0.6B. Candidate generation is unchanged;
therefore reranking cannot recover evidence that E5-C did not retrieve.
"""

from __future__ import annotations

import math
from typing import Any


RERANKER_MODEL_NAME = "Qwen/Qwen3-Reranker-0.6B"
RERANKER_MODEL_REVISION = "e61197e"
RERANKER_CANDIDATE_LIMIT = 20
RERANKER_INSTRUCTION = (
    "Given an aviation airworthiness-directive maintenance query, rank passages "
    "by how directly and completely they answer the query. Preserve exact "
    "applicability, compliance thresholds, timing, exceptions, identifiers, "
    "lifecycle statements, and referenced publications."
)


def apply_reranker_scores(
    candidates: list[dict[str, Any]],
    scores: list[float],
    *,
    limit: int = RERANKER_CANDIDATE_LIMIT,
) -> list[dict[str, Any]]:
    """Return candidates ordered by descending reranker score.

    Original E5-C rank is the deterministic tie-break. The function never adds,
    drops, or substitutes candidates except for applying the requested output
    limit to the already-generated candidate pool.
    """
    if len(candidates) != len(scores):
        raise ValueError(
            f"candidate/score length mismatch: {len(candidates)} != {len(scores)}"
        )
    ranked: list[dict[str, Any]] = []
    for pre_rank, (candidate, raw_score) in enumerate(zip(candidates, scores), 1):
        score = float(raw_score)
        if not math.isfinite(score):
            raise ValueError(f"non-finite E5-D reranker score at candidate {pre_rank}")
        ranked.append(
            {
                **candidate,
                "pre_rerank_rank": pre_rank,
                "reranker_score": score,
            }
        )
    ranked.sort(
        key=lambda item: (
            -float(item["reranker_score"]),
            int(item["pre_rerank_rank"]),
            str(item["chunk_id"]),
        )
    )
    output = ranked[: min(int(limit), len(ranked))]
    for rerank_rank, item in enumerate(output, 1):
        item["rerank_rank"] = rerank_rank
    return output
