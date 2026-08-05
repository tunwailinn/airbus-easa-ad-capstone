#!/usr/bin/env python3
"""Isolated SentenceTransformer query-encoding worker.

This worker intentionally never imports FAISS or the retrieval module. On
Apple Silicon, PyTorch/SentenceTransformers and FAISS wheels can load conflicting
OpenMP runtimes in one process and trigger a native segmentation fault. Query
vectors are therefore produced here and consumed later by a FAISS-only worker.
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
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata-output", type=Path, required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    texts = payload.get("texts", [])
    if not isinstance(texts, list) or not all(isinstance(text, str) for text in texts):
        raise ValueError("encoder worker input 'texts' must be a list of strings")
    if not texts:
        raise ValueError("encoder worker received zero texts")

    # Import only inside this PyTorch-only worker. Never import FAISS here.
    from sentence_transformers import SentenceTransformer

    model = _run_with_progress(
        "isolated sentence-transformer load",
        lambda: SentenceTransformer(args.model),
    )
    device = str(getattr(model, "device", "auto"))
    vectors = _run_with_progress(
        f"isolated query encoding ({len(texts)} texts)",
        lambda: np.asarray(
            model.encode(texts, normalize_embeddings=True, show_progress_bar=False),
            dtype="float32",
        ),
    )
    if vectors.ndim != 2 or vectors.shape[0] != len(texts):
        raise ValueError("encoder worker produced an unexpected embedding shape")
    np.save(args.output, vectors)
    args.metadata_output.write_text(
        json.dumps(
            {
                "model": args.model,
                "device": device,
                "text_count": len(texts),
                "embedding_dimension": int(vectors.shape[1]),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"[progress] isolated query encoder wrote {len(texts)} vectors on {device}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
