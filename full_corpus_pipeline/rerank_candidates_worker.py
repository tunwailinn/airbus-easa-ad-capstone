#!/usr/bin/env python3
"""Isolated cross-encoder reranking worker.

This process intentionally never imports FAISS or the retrieval module. On
Apple Silicon, PyTorch and FAISS wheels can load incompatible OpenMP runtimes
in one process and cause native segmentation faults. The parent evaluator
therefore computes frozen sparse+dense+RRF candidate sets, then sends those
candidates here for CPU cross-encoder reranking in a clean Python process.
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path
from typing import Any, Callable, TypeVar


T = TypeVar("T")


def _run_with_progress(label: str, function: Callable[[], T]) -> T:
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


def rerank_items(
    items: list[dict[str, Any]],
    model: Any,
    *,
    limit: int,
    device: str,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    total = len(items)
    started = time.monotonic()
    for position, item in enumerate(items, 1):
        print(
            f"[progress] isolated reranker: item {position}/{total} "
            f"({item.get('item_id', position)})",
            flush=True,
        )
        candidates = list(item.get("candidates", []))
        if candidates:
            scores = model.predict(
                [(str(item["query"]), candidate["text"]) for candidate in candidates],
                show_progress_bar=False,
                device=device,
            )
            for candidate, score in zip(candidates, scores):
                candidate["rerank_score"] = float(score)
            candidates = sorted(
                candidates,
                key=lambda candidate: (-candidate["rerank_score"], candidate["chunk_id"]),
            )[:limit]
        output.append(
            {
                "item_id": item.get("item_id"),
                "results": candidates,
            }
        )
    elapsed = int(time.monotonic() - started)
    print(
        f"[progress] isolated reranker: finished {total} items ({elapsed}s)",
        flush=True,
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    if not isinstance(items, list):
        raise ValueError("reranker worker input 'items' must be a list")

    # Import only inside the isolated worker. Do not import the retrieval module
    # or FAISS in this process.
    from sentence_transformers import CrossEncoder

    model = _run_with_progress(
        f"isolated {args.device} cross-encoder load",
        lambda: CrossEncoder(args.model, device=args.device),
    )
    # Warm the exact prediction path before processing any benchmark item.
    _run_with_progress(
        "isolated cross-encoder warm-up",
        lambda: model.predict(
            [("test query", "test passage")],
            show_progress_bar=False,
            device=args.device,
        ),
    )

    results = rerank_items(items, model, limit=args.limit, device=args.device)
    args.output.write_text(
        json.dumps({"items": results}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
