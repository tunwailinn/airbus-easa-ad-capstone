#!/usr/bin/env python3
"""Append new chunk embeddings to an isolated E5-C dense-store derivative.

The frozen E5-C artifact is never modified. This helper is intended for an
isolated post-final ingestion evaluation clone whose E4 chunks.jsonl has already
received new documents. It pins the frozen Qwen model/revision and updates only
the clone's row-alignment metadata.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from full_corpus_pipeline.build_e5c_dense_embeddings import (
    BUILD_VERSION,
    MODEL_NAME,
    MODEL_REVISION,
    POST_NORMALIZATION_ATOL,
    sha256_file,
)
from full_corpus_pipeline.retrieval import Chunk


def _chunk_id_order_sha(chunk_path: Path) -> tuple[int, str]:
    ids: list[str] = []
    for line in chunk_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            ids.append(str(json.loads(line)["chunk_id"]))
    digest = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
    return len(ids), digest


def _run(command: list[str], label: str) -> None:
    print(f"[progress] {label}: launching isolated process", flush=True)
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"{label} failed with child-process exit code {completed.returncode}"
        )
    print(f"[progress] {label}: finished", flush=True)


def append_e5c_dense_isolated(
    *,
    dense_dir: Path,
    index_dir: Path,
    chunks: list[Chunk],
    device: str = "auto",
    batch_size: int = 8,
) -> dict[str, Any]:
    dense_dir = Path(dense_dir)
    index_dir = Path(index_dir)
    if not chunks:
        return json.loads((dense_dir / "metadata.json").read_text(encoding="utf-8"))

    metadata_path = dense_dir / "metadata.json"
    embeddings_path = dense_dir / "dense_embeddings.npy"
    chunk_path = index_dir / "chunks.jsonl"
    for path in (metadata_path, embeddings_path, chunk_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("build_version") != BUILD_VERSION:
        raise ValueError("unexpected E5-C dense build version in isolated clone")
    if metadata.get("model") != MODEL_NAME:
        raise ValueError("unexpected E5-C dense model in isolated clone")
    if metadata.get("model_revision") != MODEL_REVISION:
        raise ValueError("unexpected E5-C dense model revision in isolated clone")
    if metadata.get("normalized") is not True:
        raise ValueError("E5-C dense clone is not marked normalized")

    old_embeddings = np.load(embeddings_path, mmap_mode="r")
    if old_embeddings.ndim != 2:
        raise ValueError("E5-C dense embeddings must be a 2D matrix")
    before = int(old_embeddings.shape[0])
    if int(metadata.get("chunk_count", -1)) != before:
        raise ValueError("E5-C metadata/embedding row count mismatch before append")

    current_chunk_count, current_order_sha = _chunk_id_order_sha(chunk_path)
    expected_after = before + len(chunks)
    if current_chunk_count != expected_after:
        raise ValueError(
            f"E5-C append expects E4 chunks to be appended first: {current_chunk_count} != {expected_after}"
        )
    trailing_ids = [
        str(json.loads(line)["chunk_id"])
        for line in chunk_path.read_text(encoding="utf-8").splitlines()[-len(chunks):]
        if line.strip()
    ]
    expected_ids = [chunk.chunk_id for chunk in chunks]
    if trailing_ids != expected_ids:
        raise ValueError("E5-C append batch does not match trailing E4 chunk order")

    base_metadata_sha = sha256_file(metadata_path)
    with tempfile.TemporaryDirectory(prefix="e5c-dense-append-", dir=dense_dir.parent) as temporary:
        work = Path(temporary)
        input_path = work / "encoder_input.json"
        vectors_path = work / "new_vectors.npy"
        encoder_meta_path = work / "encoder_metadata.json"
        input_path.write_text(
            json.dumps({"texts": [chunk.text for chunk in chunks]}, ensure_ascii=False),
            encoding="utf-8",
        )
        _run(
            [
                sys.executable,
                "-m",
                "full_corpus_pipeline.encode_e5c_chunks_worker",
                "--input",
                str(input_path),
                "--output",
                str(vectors_path),
                "--metadata-output",
                str(encoder_meta_path),
                "--device",
                device,
                "--batch-size",
                str(batch_size),
            ],
            "E5-C Qwen chunk encoding",
        )
        encoder_meta = json.loads(encoder_meta_path.read_text(encoding="utf-8"))
        if encoder_meta.get("model") != MODEL_NAME or encoder_meta.get("model_revision") != MODEL_REVISION:
            raise ValueError("E5-C ingestion worker used unexpected model/revision")

        new_vectors = np.asarray(np.load(vectors_path), dtype="float32")
        if new_vectors.ndim != 2 or int(new_vectors.shape[0]) != len(chunks):
            raise ValueError("E5-C ingestion vector shape mismatch")
        if int(new_vectors.shape[1]) != int(old_embeddings.shape[1]):
            raise ValueError("E5-C ingestion vector dimension mismatch")
        norms = np.linalg.norm(new_vectors, axis=1)
        if not np.allclose(
            norms,
            1.0,
            rtol=POST_NORMALIZATION_ATOL,
            atol=POST_NORMALIZATION_ATOL,
        ):
            raise ValueError("E5-C appended vectors are not float32 L2-normalized")

        next_embeddings = work / "dense_embeddings.npy"
        combined = np.vstack(
            [np.asarray(old_embeddings, dtype="float32"), new_vectors]
        ).astype("float32", copy=False)
        np.save(next_embeddings, combined)
        if int(combined.shape[0]) != expected_after:
            raise ValueError("E5-C combined embedding row count mismatch")

        normalization = dict(metadata.get("normalization") or {})
        prior_pre_min = float(normalization.get("pre_renormalization_norm_min", 1.0))
        prior_pre_max = float(normalization.get("pre_renormalization_norm_max", 1.0))
        prior_post_min = float(normalization.get("post_renormalization_norm_min", 1.0))
        prior_post_max = float(normalization.get("post_renormalization_norm_max", 1.0))
        normalization.update(
            {
                "pre_renormalization_norm_min": min(
                    prior_pre_min,
                    float(encoder_meta["pre_renormalization_norm_min"]),
                ),
                "pre_renormalization_norm_max": max(
                    prior_pre_max,
                    float(encoder_meta["pre_renormalization_norm_max"]),
                ),
                "post_renormalization_norm_min": min(
                    prior_post_min,
                    float(encoder_meta["post_renormalization_norm_min"]),
                ),
                "post_renormalization_norm_max": max(
                    prior_post_max,
                    float(encoder_meta["post_renormalization_norm_max"]),
                ),
            }
        )

        updated = dict(metadata)
        updated.update(
            {
                "chunk_count": expected_after,
                "chunk_source": str(chunk_path),
                "chunk_source_sha256": sha256_file(chunk_path),
                "chunk_id_order_sha256": current_order_sha,
                "embedding_dimension": int(combined.shape[1]),
                "device": encoder_meta.get("device"),
                "normalization": normalization,
                "evaluation_derivative": True,
                "base_frozen_metadata_sha256": metadata.get(
                    "base_frozen_metadata_sha256", base_metadata_sha
                ),
                "appended_chunk_count": int(metadata.get("appended_chunk_count", 0))
                + len(chunks),
            }
        )
        next_metadata = work / "metadata.json"
        next_metadata.write_text(
            json.dumps(updated, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        backup_embeddings = work / "backup_dense_embeddings.npy"
        backup_metadata = work / "backup_metadata.json"
        import shutil

        shutil.copy2(embeddings_path, backup_embeddings)
        shutil.copy2(metadata_path, backup_metadata)
        try:
            os.replace(next_embeddings, embeddings_path)
            os.replace(next_metadata, metadata_path)
        except Exception:
            shutil.copy2(backup_embeddings, embeddings_path)
            shutil.copy2(backup_metadata, metadata_path)
            raise

    final = json.loads(metadata_path.read_text(encoding="utf-8"))
    if final.get("chunk_source_sha256") != sha256_file(chunk_path):
        raise ValueError("post-append E5-C chunk-source hash mismatch")
    final_count, final_order_sha = _chunk_id_order_sha(chunk_path)
    if int(final.get("chunk_count", -1)) != final_count:
        raise ValueError("post-append E5-C chunk count mismatch")
    if final.get("chunk_id_order_sha256") != final_order_sha:
        raise ValueError("post-append E5-C chunk-order hash mismatch")
    if int(np.load(embeddings_path, mmap_mode="r").shape[0]) != final_count:
        raise ValueError("post-append E5-C embedding row count mismatch")

    return {
        **final,
        "before_chunk_count": before,
        "added_chunk_count_current_call": len(chunks),
        "after_chunk_count": final_count,
        "encoder_metadata": encoder_meta,
    }
