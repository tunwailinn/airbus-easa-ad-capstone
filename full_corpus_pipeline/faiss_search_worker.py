#!/usr/bin/env python3
"""Isolated FAISS IndexFlatIP search worker.

This worker intentionally never imports PyTorch, sentence-transformers, or the
retrieval module. It receives precomputed normalized query vectors and searches
the frozen FAISS index exactly as required by the benchmark configuration.
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path
from typing import Callable, TypeVar

import numpy as np


T = TypeVar("T")


def _run_with_progress(label: str, function: Callable[[], T]) -> T:
    started = time.monotonic()
    stop = threading.Event()

    def heartbeat() -> None:
        while not stop.wait(2.0):
            elapsed = int(time.monotonic() - started)
            print(f"[progress] {label}: working ({elapsed}s elapsed)", flush=True)

    print(f"[progress] {label}: started", flush=True)
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        return function()
    finally:
        stop.set()
        thread.join(timeout=1.0)
        elapsed = int(time.monotonic() - started)
        print(f"[progress] {label}: finished ({elapsed}s)", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--vectors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, required=True)
    args = parser.parse_args()

    if args.limit <= 0:
        raise ValueError("limit must be positive")

    # Import only inside this FAISS-only worker. Never import torch/ST here.
    import faiss

    vectors = np.load(args.vectors).astype("float32", copy=False)
    if vectors.ndim != 2 or vectors.shape[0] == 0:
        raise ValueError("FAISS worker expected a non-empty 2D query matrix")
    index = _run_with_progress(
        f"isolated FAISS index load ({args.index.name})",
        lambda: faiss.read_index(str(args.index)),
    )
    if int(index.d) != int(vectors.shape[1]):
        raise ValueError(
            f"query dimension {vectors.shape[1]} does not match FAISS index {index.d}"
        )
    scores, positions = _run_with_progress(
        f"isolated FAISS search ({vectors.shape[0]} queries, top {args.limit})",
        lambda: index.search(np.ascontiguousarray(vectors), args.limit),
    )
    rows = []
    for row_scores, row_positions in zip(scores, positions):
        rows.append(
            [
                {"index": int(position), "score": float(score)}
                for score, position in zip(row_scores, row_positions)
                if int(position) >= 0
            ]
        )
    args.output.write_text(
        json.dumps({"results": rows}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"[progress] isolated FAISS worker wrote results for {len(rows)} queries",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
