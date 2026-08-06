#!/usr/bin/env python3
"""Score E5-D query/passage pairs in an isolated Qwen3 reranker process."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from full_corpus_pipeline.build_e5c_dense_embeddings import choose_device
from full_corpus_pipeline.e5d_retrieval import (
    RERANKER_INSTRUCTION,
    RERANKER_MODEL_NAME,
    RERANKER_MODEL_REVISION,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata-output", type=Path, required=True)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch-size", type=int, default=2)
    args = parser.parse_args()

    rows = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise ValueError("no E5-D reranker pairs supplied")

    pair_keys = [
        (str(row["question_id"]), int(row["candidate_position"]), str(row["chunk_id"]))
        for row in rows
    ]
    if len(pair_keys) != len(set(pair_keys)):
        raise ValueError("duplicate E5-D reranker pair keys")

    device = choose_device(args.device)
    print(
        f"[progress] E5-D reranker: loading {RERANKER_MODEL_NAME}@"
        f"{RERANKER_MODEL_REVISION} on {device}",
        flush=True,
    )
    from sentence_transformers import CrossEncoder

    model = CrossEncoder(
        RERANKER_MODEL_NAME,
        revision=RERANKER_MODEL_REVISION,
        device=device,
        prompts={"aviation": RERANKER_INSTRUCTION},
        default_prompt_name="aviation",
    )
    pairs = [(str(row["question"]), str(row["text"])) for row in rows]
    scores = model.predict(
        pairs,
        batch_size=args.batch_size,
        show_progress_bar=True,
    )
    scores = np.asarray(scores, dtype="float32").reshape(-1)
    if scores.shape[0] != len(rows):
        raise ValueError("E5-D reranker output row mismatch")
    if not np.isfinite(scores).all():
        raise ValueError("E5-D reranker produced non-finite scores")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row, score in zip(rows, scores):
            handle.write(
                json.dumps(
                    {
                        "question_id": str(row["question_id"]),
                        "candidate_position": int(row["candidate_position"]),
                        "chunk_id": str(row["chunk_id"]),
                        "score": float(score),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    metadata = {
        "model": RERANKER_MODEL_NAME,
        "model_revision": RERANKER_MODEL_REVISION,
        "instruction": RERANKER_INSTRUCTION,
        "score_type": "raw_logit_difference",
        "device": device,
        "pair_count": len(rows),
        "batch_size": args.batch_size,
    }
    args.metadata_output.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(
        f"[progress] E5-D reranker: scored {len(rows)}/{len(rows)} query/passage pairs",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
