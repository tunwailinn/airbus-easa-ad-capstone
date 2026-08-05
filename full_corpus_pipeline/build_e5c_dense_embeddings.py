#!/usr/bin/env python3
"""Build the E5-C Qwen3 document-embedding artifact over frozen E4 chunks.

This is a separate E5 development artifact. It does not modify rag-index-build-v1.2,
E0, E4, or the E5-A/B sparse index. PyTorch/SentenceTransformers run in this
process, but FAISS is never imported or used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from importlib.metadata import version as package_version
from pathlib import Path

import numpy as np
from packaging.version import Version


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = ROOT / "data_processed/indexes/rag_v1_2/e4_section_hybrid"
DEFAULT_OUTPUT = ROOT / "data_processed/indexes/e5c_qwen3_embedding_0_6b"
MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
MODEL_REVISION = "97b0c61"
BUILD_VERSION = "e5c-dense-build-v1.0"
EXPECTED_CHUNK_COUNT = 12634
MIN_TRANSFORMERS_VERSION = Version("4.51.0")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def choose_device(requested: str) -> str:
    if requested != "auto":
        return requested
    import torch

    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def load_chunk_records(index_dir: Path) -> tuple[Path, list[dict[str, object]]]:
    chunk_path = index_dir / "chunks.jsonl"
    if not chunk_path.exists():
        raise FileNotFoundError(f"missing frozen E4 chunks: {chunk_path}")
    records = [
        json.loads(line)
        for line in chunk_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(records) != EXPECTED_CHUNK_COUNT:
        raise ValueError(
            f"expected {EXPECTED_CHUNK_COUNT} frozen E4 chunks, found {len(records)}"
        )
    return chunk_path, records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--heartbeat-size", type=int, default=128)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if Version(package_version("transformers")) < MIN_TRANSFORMERS_VERSION:
        raise RuntimeError(
            f"{MODEL_NAME} requires transformers>={MIN_TRANSFORMERS_VERSION}; "
            f"found {package_version('transformers')}"
        )

    chunk_path, records = load_chunk_records(args.index)
    chunk_sha = sha256_file(chunk_path)
    embeddings_path = args.output_dir / "dense_embeddings.npy"
    metadata_path = args.output_dir / "metadata.json"

    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        if not args.force:
            raise ValueError(
                f"refusing to overwrite non-empty E5-C dense artifact: {args.output_dir}; "
                "use --force only if intentionally rebuilding the development artifact"
            )
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    device = choose_device(args.device)
    print(
        f"[progress] E5-C dense build: loading {MODEL_NAME}@{MODEL_REVISION} on {device}",
        flush=True,
    )
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, device=device)
    texts = [str(record["text"]) for record in records]
    vectors: list[np.ndarray] = []
    total = len(texts)

    for start in range(0, total, args.heartbeat_size):
        stop = min(start + args.heartbeat_size, total)
        batch = texts[start:stop]
        encoded = model.encode(
            batch,
            batch_size=args.batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        encoded = np.asarray(encoded, dtype="float32")
        if encoded.ndim != 2 or not np.isfinite(encoded).all():
            raise ValueError(f"invalid dense embeddings for chunk rows {start}:{stop}")
        vectors.append(encoded)
        print(
            f"[progress] E5-C dense build: encoded {stop}/{total} chunks",
            flush=True,
        )

    embeddings = np.vstack(vectors).astype("float32", copy=False)
    if embeddings.shape[0] != EXPECTED_CHUNK_COUNT:
        raise ValueError("E5-C dense embedding row count mismatch")
    norms = np.linalg.norm(embeddings, axis=1)
    if not np.allclose(norms, 1.0, atol=2e-3):
        raise ValueError(
            f"E5-C document embeddings are not normalized: min={norms.min()} max={norms.max()}"
        )

    np.save(embeddings_path, embeddings)
    chunk_ids = [str(record["chunk_id"]) for record in records]
    chunk_id_sha = hashlib.sha256("\n".join(chunk_ids).encode("utf-8")).hexdigest()
    metadata = {
        "build_version": BUILD_VERSION,
        "model": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "document_prompt": None,
        "query_prompt_name": "query",
        "normalized": True,
        "similarity": "cosine_via_inner_product",
        "backend": "sentence_transformers",
        "device": device,
        "chunk_count": int(embeddings.shape[0]),
        "embedding_dimension": int(embeddings.shape[1]),
        "chunk_source": str(chunk_path),
        "chunk_source_sha256": chunk_sha,
        "chunk_id_order_sha256": chunk_id_sha,
        "transformers_version": package_version("transformers"),
        "sentence_transformers_version": package_version("sentence-transformers"),
        "numpy_version": np.__version__,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print("[progress] E5-C dense build: finished", flush=True)
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
