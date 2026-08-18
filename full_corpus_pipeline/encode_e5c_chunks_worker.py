#!/usr/bin/env python3
"""Isolated Qwen3 chunk-embedding worker for E5-C ingestion derivatives.

This worker pins the same E5-C document embedding model/revision and float32
L2-renormalization policy used by the frozen E5-C build. It never imports FAISS.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from full_corpus_pipeline.build_e5c_dense_embeddings import (
    MODEL_NAME,
    MODEL_REVISION,
    choose_device,
    normalize_rows_float32,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata-output", type=Path, required=True)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    texts = payload.get("texts", [])
    if not isinstance(texts, list) or not texts or not all(isinstance(text, str) for text in texts):
        raise ValueError("E5-C chunk encoder input 'texts' must be a non-empty list of strings")

    device = choose_device(args.device)
    from sentence_transformers import SentenceTransformer

    print(
        f"[progress] E5-C ingestion encoder: loading {MODEL_NAME}@{MODEL_REVISION} on {device}",
        flush=True,
    )
    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, device=device)
    encoded = model.encode(
        texts,
        batch_size=args.batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    vectors, raw_norms, post_norms = normalize_rows_float32(
        np.asarray(encoded), label="E5-C ingestion document embeddings"
    )
    np.save(args.output, vectors)
    args.metadata_output.write_text(
        json.dumps(
            {
                "model": MODEL_NAME,
                "model_revision": MODEL_REVISION,
                "device": device,
                "text_count": len(texts),
                "embedding_dimension": int(vectors.shape[1]),
                "pre_renormalization_norm_min": float(raw_norms.min()),
                "pre_renormalization_norm_max": float(raw_norms.max()),
                "post_renormalization_norm_min": float(post_norms.min()),
                "post_renormalization_norm_max": float(post_norms.max()),
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
                "model": MODEL_NAME,
                "revision": MODEL_REVISION,
                "text_count": len(texts),
                "device": device,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
