#!/usr/bin/env python3
"""Build the frozen E0 and E4 retrieval experiments from verified page-text v1.1.

E0 is the flat-chunk dense-only baseline. E4 is the section-aware hybrid system.
Both consume the exact same strict Airbus-only retrieval manifest and verified
page-preserving source text. This builder is intentionally strict: unresolved
page-text review, manifest drift, dense fallback, or missing FAISS aborts the
research build rather than silently changing the experiment.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import statistics
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from full_corpus_pipeline.retrieval import (
    HybridIndex,
    build_chunks_from_directory,
    token_count,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAGE_TEXT_ROOT = ROOT / "data_processed/page_text_v1_1/operational_airbus"
DEFAULT_OUTPUT_ROOT = ROOT / "data_processed/indexes/rag_v1"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EXPECTED_DOCUMENT_COUNT = 1786
EXPECTED_PAGE_TEXT_VERSION = "page-text-v1.1"


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
        # Missing lifecycle state is conservative: chunks remain historical rather
        # than being silently promoted to the operational view.
        manifest["is_latest_version"] = False

    page_files = list(pages_dir.glob("*.pages.jsonl"))
    if len(page_files) != expected_count:
        raise ValueError(
            f"expected {expected_count} page JSONL files, found {len(page_files)}"
        )
    return manifest, audit


def chunk_stats(chunks: list[Any]) -> dict[str, Any]:
    if not chunks:
        raise ValueError("chunk build produced zero chunks")
    token_counts = [token_count(chunk.text) for chunk in chunks]
    page_spans = [chunk.page_end - chunk.page_start + 1 for chunk in chunks]
    ids = [chunk.chunk_id for chunk in chunks]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate chunk IDs detected")
    return {
        "chunk_count": len(chunks),
        "document_count": len({chunk.file_instance_id for chunk in chunks}),
        "min_tokens": min(token_counts),
        "median_tokens": statistics.median(token_counts),
        "mean_tokens": statistics.fmean(token_counts),
        "max_tokens": max(token_counts),
        "multi_page_chunk_count": sum(span > 1 for span in page_spans),
        "max_page_span": max(page_spans),
    }


def build_one(
    *,
    experiment: str,
    chunks: list[Any],
    output_dir: Path,
    embedding_model: str,
    expected_count: int,
) -> dict[str, Any]:
    stats = chunk_stats(chunks)
    if stats["document_count"] != expected_count:
        raise ValueError(
            f"{experiment}: chunks cover {stats['document_count']} documents; "
            f"expected {expected_count}"
        )
    config = HybridIndex(output_dir).build(
        chunks,
        embedding_model=embedding_model,
        allow_dense_fallback=False,
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
        "index_config": config,
        "chunk_stats": stats,
    }
    (output_dir / "build_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def build_experiments(
    *,
    page_text_root: Path,
    output_root: Path,
    embedding_model: str,
    expected_count: int = EXPECTED_DOCUMENT_COUNT,
    experiment: str = "all",
) -> dict[str, Any]:
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
        e0_chunks = build_chunks_from_directory(
            pages_dir, manifest_rows, chunking="flat"
        )
        reports["e0"] = build_one(
            experiment="E0-flat-dense",
            chunks=e0_chunks,
            output_dir=output_root / "e0_flat_dense",
            embedding_model=embedding_model,
            expected_count=expected_count,
        )
    if experiment in {"e4", "all"}:
        e4_chunks = build_chunks_from_directory(
            pages_dir, manifest_rows, chunking="section"
        )
        reports["e4"] = build_one(
            experiment="E4-section-hybrid",
            chunks=e4_chunks,
            output_dir=output_root / "e4_section_hybrid",
            embedding_model=embedding_model,
            expected_count=expected_count,
        )

    summary = {
        "retrieval_build_version": "rag-index-build-v1.0",
        "page_text_version": audit["page_text_version"],
        "page_text_root": str(page_text_root),
        "retrieval_manifest": str(page_text_root / "retrieval_manifest.csv"),
        "document_count": expected_count,
        "embedding_model": embedding_model,
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_experiments(
        page_text_root=args.page_text_root,
        output_root=args.output_root,
        embedding_model=args.embedding_model,
        expected_count=args.expected_count,
        experiment=args.experiment,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
