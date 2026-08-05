#!/usr/bin/env python3
"""Encode E5-C query vectors with Qwen3 in an isolated worker process.

The parent evaluator never imports PyTorch/SentenceTransformers. The worker writes
normalized query vectors plus an order manifest, then exits.
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
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata-output", type=Path, required=True)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    rows = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise ValueError("no E5-C queries supplied")
    ids = [str(row["question_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate query IDs in E5-C query worker input")

    device = choose_device(args.device)
    print(
        f"[progress] E5-C query encoder: loading {MODEL_NAME}@{MODEL_REVISION} on {device}",
        flush=True,
    )
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, device=device)
    questions = [str(row["question"]) for row in rows]
    vectors = model.encode(
        questions,
        prompt_name="query",
        batch_size=args.batch_size,
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True,
    )
    vectors = np.asarray(vectors, dtype="float32")
    if vectors.shape[0] != len(rows) or vectors.ndim != 2:
        raise ValueError("E5-C query embedding shape mismatch")
    if not np.isfinite(vectors).all():
        raise ValueError("E5-C query embeddings contain non-finite values")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.save(args.output, vectors)
    metadata = {
        "model": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "prompt_name": "query",
        "normalized": True,
        "device": device,
        "question_ids": ids,
        "embedding_dimension": int(vectors.shape[1]),
    }
    args.metadata_output.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(
        f"[progress] E5-C query encoder: encoded {len(rows)}/{len(rows)} queries",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
