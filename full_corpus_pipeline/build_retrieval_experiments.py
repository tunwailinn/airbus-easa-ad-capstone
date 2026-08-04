#!/usr/bin/env python3
"""Build the frozen E0 and E4 retrieval experiments from verified page-text v1.1.

E0 is the flat-chunk dense-only baseline. E4 is the section-aware hybrid system.
Both consume the exact same strict Airbus-only retrieval manifest and verified
page-preserving source text. This builder is intentionally strict: unresolved
page-text review, manifest drift, dense fallback, missing FAISS, or chunk-size
drift aborts the research build rather than silently changing the experiment.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import shutil
import statistics
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, TypeVar

import pandas as pd

from full_corpus_pipeline.document_io import read_page_jsonl
from full_corpus_pipeline.retrieval import (
    Chunk,
    HybridIndex,
    build_chunks_from_directory,
    make_chunk_id,
    section_blocks,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAGE_TEXT_ROOT = ROOT / "data_processed/page_text_v1_1/operational_airbus"
DEFAULT_OUTPUT_ROOT = ROOT / "data_processed/indexes/rag_v1_2"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EXPECTED_DOCUMENT_COUNT = 1786
EXPECTED_PAGE_TEXT_VERSION = "page-text-v1.1"
RETRIEVAL_BUILD_VERSION = "rag-index-build-v1.2"
E0_MAX_CHUNK_TOKENS = 350
E4_MIN_CHUNK_TOKENS = 250
E4_MAX_CHUNK_TOKENS = 450
T = TypeVar("T")


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _as_bool(value: Any) -> bool:
    """Parse manifest boolean values without treating the string 'False' as true."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().casefold()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n", ""}:
        return False
    raise ValueError(f"unrecognized boolean value in retrieval manifest: {value!r}")


def _run_with_progress(label: str, function: Callable[[], T]) -> T:
    """Run a long local phase with a lightweight elapsed-time heartbeat."""
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


def validate_page_source(
    page_text_root: Path, *, expected_count: int
) -> tuple[pd.DataFrame, dict[str, Any]]:
    audit_path = page_text_root / "page_extraction_audit.json"
    manifest_path = page_text_root / "retrieval_manifest.csv"
    pages_dir = page_text_root / "pages"
    if not audit_path.exists():
        raise FileNotFoundError(f"missing page-text audit: {audit_path}")
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing retrieval manifest: {manifest_path}")
    if not pages_dir.is_dir():
        raise FileNotFoundError(f"missing page-text directory: {pages_dir}")

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("page_text_version") != EXPECTED_PAGE_TEXT_VERSION:
        raise ValueError(
            f"expected {EXPECTED_PAGE_TEXT_VERSION}, got {audit.get('page_text_version')!r}"
        )
    if not bool(audit.get("ready_for_indexing", False)):
        raise ValueError("page-text audit is not ready_for_indexing")
    if int(audit.get("selected_document_count", -1)) != expected_count:
        raise ValueError("page-text selected_document_count does not match expected corpus")
    if int(audit.get("successful_document_count", -1)) != expected_count:
        raise ValueError("page-text successful_document_count does not match expected corpus")
    if int(audit.get("failure_count", -1)) != 0:
        raise ValueError("page-text extraction failures remain")
    if int(audit.get("needs_ocr_document_count", -1)) != 0 or int(
        audit.get("needs_ocr_page_count", -1)
    ) != 0:
        raise ValueError("unresolved OCR/visual-review pages remain")

    manifest = pd.read_csv(
        manifest_path,
        dtype={"file_instance_id": str, "ad_number": str},
    )
    required_columns = {"file_instance_id", "ad_number", "relative_path"}
    missing_columns = required_columns - set(manifest.columns)
    if missing_columns:
        raise ValueError(
            f"retrieval manifest missing required columns: {sorted(missing_columns)}"
        )
    if len(manifest) != expected_count:
        raise ValueError(f"expected {expected_count} retrieval rows, found {len(manifest)}")
    if manifest["file_instance_id"].duplicated().any():
        duplicates = manifest.loc[
            manifest["file_instance_id"].duplicated(keep=False), "file_instance_id"
        ].tolist()
        raise ValueError(
            f"duplicate file_instance_id values in retrieval manifest: {duplicates[:5]}"
        )
    if "is_latest_version" in manifest.columns:
        manifest["is_latest_version"] = manifest["is_latest_version"].map(_as_bool)
    else:
        manifest["is_latest_version"] = False

    page_files = list(pages_dir.glob("*.pages.jsonl"))
    if len(page_files) != expected_count:
        raise ValueError(
            f"expected {expected_count} page JSONL files, found {len(page_files)}"
        )
    return manifest, audit


def strict_section_chunk_pages(
    pages: list[dict[str, Any]],
    *,
    file_instance_id: str,
    ad_number: str,
    source_pdf: str,
    lifecycle_status: str = "historical",
    minimum_tokens: int = E4_MIN_CHUNK_TOKENS,
    maximum_tokens: int = E4_MAX_CHUNK_TOKENS,
) -> list[Chunk]:
    """Section-aware chunking using the frozen whitespace-delimited size policy.

    The original section chunker used TOKEN_RE for block accounting but
    whitespace splitting for oversized blocks. That mismatch allowed chunks
    larger than the declared 450-unit limit. This implementation uses the same
    whitespace units for accounting, splitting, and build reporting.
    """
    chunks: list[Chunk] = []
    pending: list[dict[str, Any]] = []
    pending_tokens = 0

    def flush() -> None:
        nonlocal pending, pending_tokens
        if not pending:
            return
        text = "\n\n".join(item["text"] for item in pending)
        first = pending[0]
        last = pending[-1]
        chunks.append(
            Chunk(
                chunk_id=make_chunk_id(
                    file_instance_id, int(first["page"]), str(first["section"]), text
                ),
                file_instance_id=file_instance_id,
                ad_number=ad_number,
                source_pdf=source_pdf,
                page_start=int(first["page"]),
                page_end=int(last["page"]),
                section=str(first["section"]),
                text=text,
                lifecycle_status=lifecycle_status,
            )
        )
        pending = []
        pending_tokens = 0

    for block in section_blocks(pages):
        units = str(block["text"]).split()
        if len(units) > maximum_tokens:
            flush()
            for offset in range(0, len(units), maximum_tokens):
                part = " ".join(units[offset : offset + maximum_tokens])
                pending = [{**block, "text": part}]
                pending_tokens = len(part.split())
                flush()
            continue

        if pending and (
            block["section"] != pending[-1]["section"]
            or pending_tokens + len(units) > maximum_tokens
        ):
            flush()

        pending.append(block)
        pending_tokens += len(units)
        if pending_tokens >= minimum_tokens:
            flush()

    flush()
    return chunks


def build_strict_section_chunks_from_directory(
    page_text_dir: Path, manifest_rows: Iterable[dict[str, Any]]
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for row in manifest_rows:
        file_id = str(row["file_instance_id"])
        candidates = list(page_text_dir.glob(f"*{file_id}*.jsonl"))
        if len(candidates) != 1:
            raise ValueError(
                f"expected one page-text JSONL for {file_id}, found {len(candidates)}"
            )
        pages = read_page_jsonl(candidates[0])
        chunks.extend(
            strict_section_chunk_pages(
                pages,
                file_instance_id=file_id,
                ad_number=str(row["ad_number"]),
                source_pdf=str(row["relative_path"]),
                lifecycle_status=(
                    "operational"
                    if bool(row.get("is_latest_version", False))
                    else "historical"
                ),
            )
        )
    return chunks


def chunk_stats(chunks: list[Any]) -> dict[str, Any]:
    """Summarize the whitespace-delimited units used by frozen chunk limits."""
    if not chunks:
        raise ValueError("chunk build produced zero chunks")
    token_counts = [len(chunk.text.split()) for chunk in chunks]
    page_spans = [chunk.page_end - chunk.page_start + 1 for chunk in chunks]
    ids = [chunk.chunk_id for chunk in chunks]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate chunk IDs detected")
    return {
        "chunk_count": len(chunks),
        "document_count": len({chunk.file_instance_id for chunk in chunks}),
        "token_count_method": "whitespace_split",
        "min_tokens": min(token_counts),
        "median_tokens": statistics.median(token_counts),
        "mean_tokens": statistics.fmean(token_counts),
        "max_tokens": max(token_counts),
        "multi_page_chunk_count": sum(span > 1 for span in page_spans),
        "max_page_span": max(page_spans),
    }


def _validate_existing_report(
    *,
    output_dir: Path,
    experiment: str,
    embedding_model: str,
    expected_count: int,
    maximum_chunk_tokens: int,
) -> dict[str, Any]:
    report_path = output_dir / "build_report.json"
    required_files = (
        "build_report.json",
        "index_config.json",
        "chunks.jsonl",
        "dense_embeddings.npy",
        "dense.faiss",
        "sparse.sqlite",
        "chunk_manifest.parquet",
    )
    missing = [name for name in required_files if not (output_dir / name).exists()]
    if missing:
        raise ValueError(
            f"cannot reuse incomplete {experiment} index at {output_dir}; "
            f"missing {missing}"
        )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("experiment") != experiment:
        raise ValueError(f"existing index experiment mismatch at {output_dir}")
    if report.get("embedding_model") != embedding_model:
        raise ValueError(f"existing index embedding model mismatch at {output_dir}")
    if int(report.get("maximum_chunk_tokens", -1)) != maximum_chunk_tokens:
        raise ValueError(f"existing index chunk-limit mismatch at {output_dir}")

    stats = report.get("chunk_stats") or {}
    if int(stats.get("document_count", -1)) != expected_count:
        raise ValueError(f"existing index document-count mismatch at {output_dir}")
    if stats.get("token_count_method") != "whitespace_split":
        raise ValueError(f"existing index token-count policy mismatch at {output_dir}")
    if int(stats.get("max_tokens", maximum_chunk_tokens + 1)) > maximum_chunk_tokens:
        raise ValueError(f"existing index exceeds chunk limit at {output_dir}")

    config = report.get("index_config") or {}
    if config.get("dense_backend") != "sentence_transformers":
        raise ValueError(f"existing index did not use sentence-transformers: {output_dir}")
    if config.get("dense_index_backend") != "faiss_index_flat_ip":
        raise ValueError(f"existing index did not use FAISS: {output_dir}")

    print(f"[progress] reusing validated {experiment} index: {output_dir}", flush=True)
    return report


def build_one(
    *,
    experiment: str,
    chunks: list[Any],
    output_dir: Path,
    embedding_model: str,
    expected_count: int,
    maximum_chunk_tokens: int,
) -> dict[str, Any]:
    stats = chunk_stats(chunks)
    if stats["document_count"] != expected_count:
        raise ValueError(
            f"{experiment}: chunks cover {stats['document_count']} documents; "
            f"expected {expected_count}"
        )
    if int(stats["max_tokens"]) > maximum_chunk_tokens:
        raise ValueError(
            f"{experiment}: max chunk size {stats['max_tokens']} exceeds "
            f"frozen limit {maximum_chunk_tokens}"
        )

    config = _run_with_progress(
        f"{experiment} embedding + FAISS/FTS index ({len(chunks)} chunks)",
        lambda: HybridIndex(output_dir).build(
            chunks,
            embedding_model=embedding_model,
            allow_dense_fallback=False,
        ),
    )
    if config.get("dense_backend") != "sentence_transformers":
        raise RuntimeError(f"{experiment}: dense fallback is not permitted")
    if config.get("dense_index_backend") != "faiss_index_flat_ip":
        raise RuntimeError(f"{experiment}: FAISS is required for the frozen experiment")
    pd.DataFrame([asdict(chunk) for chunk in chunks]).to_parquet(
        output_dir / "chunk_manifest.parquet", index=False
    )
    report = {
        "experiment": experiment,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "embedding_model": embedding_model,
        "maximum_chunk_tokens": maximum_chunk_tokens,
        "index_config": config,
        "chunk_stats": stats,
    }
    (output_dir / "build_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def _prepare_reused_e0(
    *,
    reuse_e0_from: Path,
    destination: Path,
    embedding_model: str,
    expected_count: int,
) -> dict[str, Any]:
    source_report = _validate_existing_report(
        output_dir=reuse_e0_from,
        experiment="E0-flat-dense",
        embedding_model=embedding_model,
        expected_count=expected_count,
        maximum_chunk_tokens=E0_MAX_CHUNK_TOKENS,
    )
    if destination.exists():
        if any(destination.iterdir()):
            return _validate_existing_report(
                output_dir=destination,
                experiment="E0-flat-dense",
                embedding_model=embedding_model,
                expected_count=expected_count,
                maximum_chunk_tokens=E0_MAX_CHUNK_TOKENS,
            )
        destination.rmdir()
    print(
        f"[progress] copying validated E0 index into v1.2 workspace: {destination}",
        flush=True,
    )
    shutil.copytree(reuse_e0_from, destination)
    _validate_existing_report(
        output_dir=destination,
        experiment="E0-flat-dense",
        embedding_model=embedding_model,
        expected_count=expected_count,
        maximum_chunk_tokens=E0_MAX_CHUNK_TOKENS,
    )
    return source_report


def build_experiments(
    *,
    page_text_root: Path,
    output_root: Path,
    embedding_model: str,
    expected_count: int = EXPECTED_DOCUMENT_COUNT,
    experiment: str = "all",
    reuse_e0_from: Path | None = None,
) -> dict[str, Any]:
    print("[progress] validating verified page-text source", flush=True)
    manifest, audit = validate_page_source(page_text_root, expected_count=expected_count)
    pages_dir = page_text_root / "pages"
    manifest_rows = manifest.to_dict(orient="records")

    try:
        import faiss  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("install faiss-cpu before building frozen E0/E4") from exc
    try:
        import sentence_transformers  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "install sentence-transformers before building frozen E0/E4"
        ) from exc

    output_root.mkdir(parents=True, exist_ok=True)
    reports: dict[str, Any] = {}

    if experiment in {"e0", "all"}:
        e0_dir = output_root / "e0_flat_dense"
        if e0_dir.exists() and any(e0_dir.iterdir()):
            reports["e0"] = _validate_existing_report(
                output_dir=e0_dir,
                experiment="E0-flat-dense",
                embedding_model=embedding_model,
                expected_count=expected_count,
                maximum_chunk_tokens=E0_MAX_CHUNK_TOKENS,
            )
        elif reuse_e0_from is not None:
            reports["e0"] = _prepare_reused_e0(
                reuse_e0_from=reuse_e0_from,
                destination=e0_dir,
                embedding_model=embedding_model,
                expected_count=expected_count,
            )
        else:
            print(f"[progress] E0 chunking {expected_count} documents", flush=True)
            e0_chunks = build_chunks_from_directory(
                pages_dir, manifest_rows, chunking="flat"
            )
            reports["e0"] = build_one(
                experiment="E0-flat-dense",
                chunks=e0_chunks,
                output_dir=e0_dir,
                embedding_model=embedding_model,
                expected_count=expected_count,
                maximum_chunk_tokens=E0_MAX_CHUNK_TOKENS,
            )

    if experiment in {"e4", "all"}:
        e4_dir = output_root / "e4_section_hybrid"
        if e4_dir.exists() and any(e4_dir.iterdir()):
            reports["e4"] = _validate_existing_report(
                output_dir=e4_dir,
                experiment="E4-section-hybrid",
                embedding_model=embedding_model,
                expected_count=expected_count,
                maximum_chunk_tokens=E4_MAX_CHUNK_TOKENS,
            )
        else:
            print(
                f"[progress] E4 strict section chunking {expected_count} documents",
                flush=True,
            )
            e4_chunks = build_strict_section_chunks_from_directory(
                pages_dir, manifest_rows
            )
            reports["e4"] = build_one(
                experiment="E4-section-hybrid",
                chunks=e4_chunks,
                output_dir=e4_dir,
                embedding_model=embedding_model,
                expected_count=expected_count,
                maximum_chunk_tokens=E4_MAX_CHUNK_TOKENS,
            )

    summary = {
        "retrieval_build_version": RETRIEVAL_BUILD_VERSION,
        "page_text_version": audit["page_text_version"],
        "page_text_root": str(page_text_root),
        "retrieval_manifest": str(page_text_root / "retrieval_manifest.csv"),
        "document_count": expected_count,
        "embedding_model": embedding_model,
        "chunk_size_policy": {
            "count_method": "whitespace_split",
            "e0_max_tokens": E0_MAX_CHUNK_TOKENS,
            "e4_min_tokens": E4_MIN_CHUNK_TOKENS,
            "e4_max_tokens": E4_MAX_CHUNK_TOKENS,
        },
        "package_versions": {
            "sentence-transformers": _package_version("sentence-transformers"),
            "faiss-cpu": _package_version("faiss-cpu"),
            "numpy": _package_version("numpy"),
            "pandas": _package_version("pandas"),
        },
        "experiments": reports,
    }
    (output_root / "build_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(f"[progress] build complete: {output_root}", flush=True)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--page-text-root", type=Path, default=DEFAULT_PAGE_TEXT_ROOT
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--expected-count", type=int, default=EXPECTED_DOCUMENT_COUNT)
    parser.add_argument("--experiment", choices=("e0", "e4", "all"), default="all")
    parser.add_argument(
        "--reuse-e0-from",
        type=Path,
        help=(
            "Reuse a previously validated E0 directory instead of recomputing "
            "the unchanged flat dense baseline."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_experiments(
        page_text_root=args.page_text_root,
        output_root=args.output_root,
        embedding_model=args.embedding_model,
        expected_count=args.expected_count,
        experiment=args.experiment,
        reuse_e0_from=args.reuse_e0_from,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
