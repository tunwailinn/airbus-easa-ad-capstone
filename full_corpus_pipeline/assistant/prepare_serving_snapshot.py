#!/usr/bin/env python3
"""Create a non-destructive serving snapshot from the validated post-ingestion derivative."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_ROOT = (
    ROOT / "data_processed/evaluations/unseen_5/permanent_ingestion/isolated_index"
)
DEFAULT_SOURCE_INDEX = DEFAULT_SOURCE_ROOT / "e4_section_hybrid"
DEFAULT_SOURCE_DENSE = DEFAULT_SOURCE_ROOT / "e5c_qwen3_embedding_0_6b"
DEFAULT_OUTPUT = ROOT / "data_processed/serving/assistant_v1"
EXPECTED_DOCUMENT_COUNT = 1791
EXPECTED_CHUNK_COUNT = 12670


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def count_chunks(path: Path) -> tuple[int, int]:
    chunks = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return len(chunks), len({str(row["file_instance_id"]) for row in chunks})


def validate_final_lock() -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "full_corpus_pipeline.layer_c.validate_unseen_final_generalization",
        ],
        cwd=ROOT,
        check=True,
    )


def validate_source(index_dir: Path, dense_dir: Path) -> dict[str, Any]:
    chunk_path = index_dir / "chunks.jsonl"
    index_config = index_dir / "index_config.json"
    sparse_path = index_dir / "sparse.sqlite"
    dense_meta_path = dense_dir / "metadata.json"
    dense_path = dense_dir / "dense_embeddings.npy"
    for path in (
        chunk_path,
        index_config,
        sparse_path,
        dense_meta_path,
        dense_path,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    chunk_count, document_count = count_chunks(chunk_path)
    if chunk_count != EXPECTED_CHUNK_COUNT:
        raise ValueError(
            f"expected {EXPECTED_CHUNK_COUNT} validated serving chunks, found {chunk_count}"
        )
    if document_count != EXPECTED_DOCUMENT_COUNT:
        raise ValueError(
            f"expected {EXPECTED_DOCUMENT_COUNT} validated serving documents, found {document_count}"
        )

    dense_meta = json.loads(dense_meta_path.read_text(encoding="utf-8"))
    embeddings = np.load(dense_path, mmap_mode="r")
    if embeddings.ndim != 2 or int(embeddings.shape[0]) != chunk_count:
        raise ValueError(
            f"dense row alignment mismatch: {embeddings.shape} for {chunk_count} chunks"
        )

    chunk_sha = sha256(chunk_path)
    if dense_meta.get("chunk_source_sha256") != chunk_sha:
        raise ValueError("validated E5-C dense metadata does not match source chunks.jsonl")

    return {
        "document_count": document_count,
        "chunk_count": chunk_count,
        "dense_row_count": int(embeddings.shape[0]),
        "dense_dimension": int(embeddings.shape[1]),
        "sparse_backend": json.loads(index_config.read_text(encoding="utf-8")).get(
            "sparse_backend"
        ),
        "embedding_model": dense_meta.get("model"),
        "embedding_revision": dense_meta.get("model_revision"),
        "source_hashes": {
            "chunks_jsonl": chunk_sha,
            "index_config_json": sha256(index_config),
            "sparse_sqlite": sha256(sparse_path),
            "dense_metadata_json": sha256(dense_meta_path),
            "dense_embeddings_npy": sha256(dense_path),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-index", type=Path, default=DEFAULT_SOURCE_INDEX)
    parser.add_argument("--source-dense-dir", type=Path, default=DEFAULT_SOURCE_DENSE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Replace only the existing serving snapshot directory.",
    )
    args = parser.parse_args()

    validate_final_lock()
    source_meta = validate_source(args.source_index, args.source_dense_dir)

    if args.output.exists():
        if not args.reset:
            raise ValueError(
                f"serving snapshot already exists: {args.output}; use --reset to replace it"
            )
        if args.output.resolve() == ROOT.resolve():
            raise ValueError("refusing to reset repository root")
        shutil.rmtree(args.output)

    args.output.mkdir(parents=True, exist_ok=False)
    target_index = args.output / "e4_section_hybrid"
    target_dense = args.output / "e5c_qwen3_embedding_0_6b"
    print("[progress] copying validated post-ingestion E4 serving index", flush=True)
    shutil.copytree(args.source_index, target_index)
    print("[progress] copying validated post-ingestion E5-C dense store", flush=True)
    shutil.copytree(args.source_dense_dir, target_dense)

    target_meta = validate_source(target_index, target_dense)
    if target_meta["source_hashes"] != source_meta["source_hashes"]:
        raise ValueError("serving snapshot copy differs from validated source artifacts")

    manifest = {
        "version": "aviation-assistant-serving-snapshot-v1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ready",
        "source_condition": "validated post-ingestion unseen derivative after U0-U8 lock",
        "source_index": str(args.source_index),
        "source_dense_dir": str(args.source_dense_dir),
        "serving_index": str(target_index),
        "serving_dense_dir": str(target_dense),
        **target_meta,
        "frozen_e5_results_modified": False,
        "policy": (
            "Post-evaluation serving copy only. This snapshot may be used by the live assistant, "
            "but it must not be treated as a replacement benchmark artifact or used to rewrite "
            "the frozen E5 or unseen evaluation results."
        ),
    }
    manifest_path = args.output / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
