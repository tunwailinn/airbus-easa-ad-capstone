#!/usr/bin/env python3
"""Isolated FAISS append worker for persistent-index updates.

This worker imports FAISS but never PyTorch or SentenceTransformers. It appends
already-computed float32 vectors to a copied FAISS index and writes a new index
file, leaving the input index untouched.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--vectors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata-output", type=Path, required=True)
    parser.add_argument("--expected-before", type=int, required=True)
    args = parser.parse_args()

    if args.output.exists():
        raise ValueError(f"refusing to overwrite FAISS output: {args.output}")

    # Import FAISS only in this worker. Never import torch/sentence-transformers.
    import faiss

    index = faiss.read_index(str(args.index))
    before = int(index.ntotal)
    if before != int(args.expected_before):
        raise ValueError(
            f"FAISS row count before append differs from expected: {before} != {args.expected_before}"
        )

    vectors = np.asarray(np.load(args.vectors), dtype="float32")
    if vectors.ndim != 2 or vectors.shape[0] <= 0:
        raise ValueError("FAISS append vectors must be a non-empty 2D matrix")
    if int(index.d) != int(vectors.shape[1]):
        raise ValueError(
            f"FAISS/vector dimension mismatch: {index.d} != {vectors.shape[1]}"
        )
    if not np.isfinite(vectors).all():
        raise ValueError("FAISS append vectors contain non-finite values")

    index.add(np.ascontiguousarray(vectors))
    after = int(index.ntotal)
    expected_after = before + int(vectors.shape[0])
    if after != expected_after:
        raise ValueError(
            f"FAISS row count after append differs from expected: {after} != {expected_after}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(args.output))
    args.metadata_output.write_text(
        json.dumps(
            {
                "before_count": before,
                "added_count": int(vectors.shape[0]),
                "after_count": after,
                "dimension": int(vectors.shape[1]),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "before": before,
                "added": int(vectors.shape[0]),
                "after": after,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
