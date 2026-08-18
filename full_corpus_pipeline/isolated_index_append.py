#!/usr/bin/env python3
"""Process-isolated append helper for section-aware persistent indexes.

The existing HybridIndex append path loads SentenceTransformers/PyTorch and FAISS
inside one Python process. On the project's macOS/ARM runtime that combination has
previously caused native segmentation faults. This module preserves the same
MiniLM normalized embeddings and FAISS IndexFlatIP append semantics while keeping
PyTorch and FAISS in separate child processes.

It is an implementation/runtime boundary change only; it does not alter chunking,
embedding model, sparse rows, vector normalization, or retrieval scoring.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from full_corpus_pipeline.retrieval import Chunk


REQUIRED_FILES = (
    "chunks.jsonl",
    "sparse.sqlite",
    "dense_embeddings.npy",
    "dense.faiss",
    "index_config.json",
)


def _run(command: list[str], label: str) -> None:
    print(f"[progress] {label}: launching isolated process", flush=True)
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"{label} failed with child-process exit code {completed.returncode}"
        )
    print(f"[progress] {label}: finished", flush=True)


def _load_chunk_rows(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def append_chunks_process_isolated(index_dir: Path, chunks: list[Chunk]) -> dict[str, Any]:
    """Append chunks while isolating SentenceTransformers and FAISS processes."""
    index_dir = Path(index_dir)
    if not chunks:
        return json.loads((index_dir / "index_config.json").read_text(encoding="utf-8"))

    missing = [name for name in REQUIRED_FILES if not (index_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"persistent index is incomplete: missing {missing}")

    chunk_path = index_dir / "chunks.jsonl"
    sparse_path = index_dir / "sparse.sqlite"
    embeddings_path = index_dir / "dense_embeddings.npy"
    faiss_path = index_dir / "dense.faiss"
    config_path = index_dir / "index_config.json"
    chunk_manifest_path = index_dir / "chunk_manifest.parquet"

    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("dense_backend") != "sentence_transformers":
        raise ValueError("process-isolated append requires sentence_transformers dense backend")
    if config.get("dense_index_backend") != "faiss_index_flat_ip":
        raise ValueError("process-isolated append requires FAISS IndexFlatIP backend")
    model = str(config.get("embedding_model") or "")
    if not model:
        raise ValueError("persistent index config is missing embedding_model")

    existing_rows = _load_chunk_rows(chunk_path)
    existing_count = len(existing_rows)
    configured_count = int(config.get("chunk_count", -1))
    if configured_count != existing_count:
        raise ValueError(
            f"index config/chunk JSONL count mismatch: {configured_count} != {existing_count}"
        )

    existing_ids = {str(row["chunk_id"]) for row in existing_rows}
    new_ids = [chunk.chunk_id for chunk in chunks]
    if len(new_ids) != len(set(new_ids)):
        raise ValueError("duplicate chunk IDs within append batch")
    overlap = existing_ids.intersection(new_ids)
    if overlap:
        raise ValueError(f"duplicate chunk ID during permanent ingestion: {sorted(overlap)[:3]}")

    existing_embeddings = np.load(embeddings_path, mmap_mode="r")
    if existing_embeddings.ndim != 2 or int(existing_embeddings.shape[0]) != existing_count:
        raise ValueError("dense embedding row count does not match chunks.jsonl")
    expected_after = existing_count + len(chunks)

    with tempfile.TemporaryDirectory(prefix="isolated-index-append-", dir=index_dir.parent) as temporary:
        work = Path(temporary)
        encoder_input = work / "encoder_input.json"
        vectors_path = work / "new_vectors.npy"
        encoder_metadata_path = work / "encoder_metadata.json"
        encoder_input.write_text(
            json.dumps({"texts": [chunk.text for chunk in chunks]}, ensure_ascii=False),
            encoding="utf-8",
        )
        _run(
            [
                sys.executable,
                "-m",
                "full_corpus_pipeline.encode_queries_worker",
                "--input",
                str(encoder_input),
                "--output",
                str(vectors_path),
                "--metadata-output",
                str(encoder_metadata_path),
                "--model",
                model,
            ],
            "SentenceTransformer chunk encoding (FAISS not imported)",
        )
        encoder_meta = json.loads(encoder_metadata_path.read_text(encoding="utf-8"))
        if encoder_meta.get("model") != model:
            raise ValueError("isolated encoder used an unexpected embedding model")
        if int(encoder_meta.get("text_count", -1)) != len(chunks):
            raise ValueError("isolated encoder text count mismatch")

        new_vectors = np.asarray(np.load(vectors_path), dtype="float32")
        if new_vectors.ndim != 2 or new_vectors.shape[0] != len(chunks):
            raise ValueError("isolated encoder produced unexpected vector shape")
        if int(new_vectors.shape[1]) != int(existing_embeddings.shape[1]):
            raise ValueError("new vector dimension differs from persistent index")

        next_faiss = work / "dense.faiss.next"
        faiss_meta_path = work / "faiss_append_metadata.json"
        _run(
            [
                sys.executable,
                "-m",
                "full_corpus_pipeline.faiss_add_worker",
                "--index",
                str(faiss_path),
                "--vectors",
                str(vectors_path),
                "--output",
                str(next_faiss),
                "--metadata-output",
                str(faiss_meta_path),
                "--expected-before",
                str(existing_count),
            ],
            "FAISS append (PyTorch not imported)",
        )
        faiss_meta = json.loads(faiss_meta_path.read_text(encoding="utf-8"))
        if int(faiss_meta.get("after_count", -1)) != expected_after:
            raise ValueError("FAISS append row count mismatch")

        next_embeddings = work / "dense_embeddings.npy"
        combined = np.vstack(
            [np.asarray(existing_embeddings, dtype="float32"), new_vectors]
        ).astype("float32", copy=False)
        np.save(next_embeddings, combined)
        if int(combined.shape[0]) != expected_after:
            raise ValueError("combined dense embedding row count mismatch")

        next_sparse = work / "sparse.sqlite"
        shutil.copy2(sparse_path, next_sparse)
        connection = sqlite3.connect(next_sparse)
        try:
            connection.executemany(
                "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        c.chunk_id,
                        c.ad_number,
                        c.source_pdf,
                        c.page_start,
                        c.page_end,
                        c.section,
                        c.text,
                        c.lifecycle_status,
                    )
                    for c in chunks
                ],
            )
            connection.commit()
            sparse_count = int(connection.execute("SELECT count(*) FROM chunks").fetchone()[0])
        finally:
            connection.close()
        if sparse_count != expected_after:
            raise ValueError(f"SQLite FTS row count mismatch: {sparse_count} != {expected_after}")

        next_chunks = work / "chunks.jsonl"
        with next_chunks.open("w", encoding="utf-8") as handle:
            for row in existing_rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            for chunk in chunks:
                handle.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")

        next_config = work / "index_config.json"
        updated_config = dict(config)
        updated_config["chunk_count"] = expected_after
        next_config.write_text(json.dumps(updated_config, indent=2) + "\n", encoding="utf-8")

        staged: list[tuple[Path, Path]] = [
            (chunk_path, next_chunks),
            (sparse_path, next_sparse),
            (embeddings_path, next_embeddings),
            (faiss_path, next_faiss),
            (config_path, next_config),
        ]

        if chunk_manifest_path.is_file():
            manifest = pd.read_parquet(chunk_manifest_path)
            next_manifest = work / "chunk_manifest.parquet"
            pd.concat(
                [manifest, pd.DataFrame([asdict(chunk) for chunk in chunks])],
                ignore_index=True,
            ).to_parquet(next_manifest, index=False)
            staged.append((chunk_manifest_path, next_manifest))

        backups: list[tuple[Path, Path]] = []
        try:
            for target, _ in staged:
                backup = work / f"backup__{target.name}"
                shutil.copy2(target, backup)
                backups.append((target, backup))
            for target, staged_path in staged:
                os.replace(staged_path, target)
        except Exception:
            for target, backup in backups:
                if backup.exists():
                    shutil.copy2(backup, target)
            raise

    final_config = json.loads(config_path.read_text(encoding="utf-8"))
    if int(final_config.get("chunk_count", -1)) != expected_after:
        raise ValueError("post-append index config validation failed")
    if len(_load_chunk_rows(chunk_path)) != expected_after:
        raise ValueError("post-append chunk JSONL validation failed")
    if int(np.load(embeddings_path, mmap_mode="r").shape[0]) != expected_after:
        raise ValueError("post-append dense embedding validation failed")

    return {
        **final_config,
        "append_mode": "process_isolated_sentence_transformer_plus_faiss",
        "before_chunk_count": existing_count,
        "added_chunk_count": len(chunks),
        "after_chunk_count": expected_after,
        "encoder_metadata": encoder_meta,
        "faiss_append_metadata": faiss_meta,
    }
