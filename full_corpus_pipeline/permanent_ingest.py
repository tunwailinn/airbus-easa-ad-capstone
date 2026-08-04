#!/usr/bin/env python3
"""Permanently ingest one explicitly confirmed AD without model retraining."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from full_corpus_pipeline.document_io import file_sha256, joined_page_text, read_pdf_pages
from full_corpus_pipeline.extract_corpus import SCHEMA_PATH, record_filename
from full_corpus_pipeline.lifecycle import decide_lifecycle
from full_corpus_pipeline.local_extractor_v216 import PARSER_VERSION, extract_local_record
from full_corpus_pipeline.retrieval import HybridIndex, chunk_pages


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "step3_pilot/source_metadata/corpus_manifest.parquet"
DEFAULT_STORE = ROOT / "data_incoming"
DEFAULT_HELD_OUT = ROOT / "evaluation_sets/unseen_incoming_5_v1/selection.csv"


def load_sidecar(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def append_parquet(path: Path, row: dict[str, Any]) -> None:
    frame = load_sidecar(path)
    updated = pd.concat([frame, pd.DataFrame([row])], ignore_index=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    updated.to_parquet(path, index=False)


def active_corpus_frame(corpus_manifest: Path, held_out_selection: Path | None) -> pd.DataFrame:
    frame = pd.read_parquet(corpus_manifest)
    if held_out_selection is not None and held_out_selection.exists():
        held_out_ids = set(pd.read_csv(held_out_selection)["file_instance_id"].astype(str))
        frame = frame[~frame["file_instance_id"].astype(str).isin(held_out_ids)]
    return frame


def known_hashes(
    corpus_manifest: Path, incoming_manifest: Path, held_out_selection: Path | None
) -> set[str]:
    hashes = set(active_corpus_frame(corpus_manifest, held_out_selection)["file_sha256"].astype(str))
    incoming = load_sidecar(incoming_manifest)
    if not incoming.empty and "source_pdf_sha256" in incoming:
        hashes.update(incoming["source_pdf_sha256"].astype(str))
    return hashes


def ingest_pdf(
    pdf_path: Path, *, corpus_manifest: Path = DEFAULT_MANIFEST,
    store_dir: Path = DEFAULT_STORE, index_dir: Path | None = None,
    allow_dense_fallback: bool = False,
    held_out_selection: Path | None = DEFAULT_HELD_OUT,
) -> dict[str, Any]:
    pdf_path = Path(pdf_path)
    incoming_manifest = store_dir / "extraction_manifest.parquet"
    digest = file_sha256(pdf_path)
    if digest in known_hashes(corpus_manifest, incoming_manifest, held_out_selection):
        raise ValueError("exact duplicate rejected: source PDF SHA-256 already exists")
    pages = read_pdf_pages(pdf_path)
    if any(page["needs_ocr"] for page in pages):
        raise ValueError("native text is insufficient; create and verify an OCR derivative before permanent ingestion")

    file_id = digest[:16]
    source_dir = store_dir / "source_pdfs"
    source_dir.mkdir(parents=True, exist_ok=True)
    destination = source_dir / pdf_path.name
    if destination.exists():
        destination = source_dir / f"{pdf_path.stem}__{file_id}{pdf_path.suffix.lower()}"
    shutil.copy2(pdf_path, destination)

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    row = {
        "file_instance_id": file_id, "file_sha256": digest, "text": joined_page_text(pages),
        "ad_number": "", "relative_path": destination.name,
        "is_emergency": False, "correction_date": "", "issue_date": "",
    }
    try:
        record, detail = extract_local_record(row, schema)
    except Exception as exc:
        append_parquet(
            store_dir / "extraction_failures.parquet",
            {"file_instance_id": file_id, "source_pdf": destination.name, "source_pdf_sha256": digest,
             "error": str(exc), "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        )
        raise
    ad_number = record["ad_identity"]["ad_number"]
    filename = record_filename(ad_number, file_id)
    records_dir = store_dir / "extracted_records"
    records_dir.mkdir(parents=True, exist_ok=True)
    record_path = records_dir / filename
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    existing = active_corpus_frame(corpus_manifest, held_out_selection).to_dict(orient="records")
    incoming = load_sidecar(store_dir / "lifecycle_manifest.parquet")
    if not incoming.empty:
        existing.extend(incoming.to_dict(orient="records"))
    decision = decide_lifecycle(ad_number, existing)
    lifecycle_row = {
        "file_instance_id": file_id, "ad_number": ad_number,
        **decision.to_dict(), "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    append_parquet(store_dir / "lifecycle_manifest.parquet", lifecycle_row)
    append_parquet(
        incoming_manifest,
        {
            "file_instance_id": file_id, "ad_number": ad_number, "source_pdf": destination.name,
            "source_pdf_sha256": digest, "content_record": filename,
            "method": detail["method"], "parser_version": detail["parser_version"],
            "attempts": detail["attempts"], "request_id": detail["request_id"],
            "ingested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    )
    if index_dir is not None:
        index = HybridIndex(index_dir)
        chunks = chunk_pages(
            pages, file_instance_id=file_id, ad_number=ad_number, source_pdf=destination.name,
            lifecycle_status="operational" if decision.operational_selection else "historical",
        )
        index.add_chunks(chunks)
    return {
        "file_instance_id": file_id, "ad_number": ad_number, "source_pdf": str(destination),
        "record": str(record_path), "lifecycle": lifecycle_row,
        "extraction_method": "deterministic_local", "parser_version": PARSER_VERSION,
        "model_retrained": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--corpus-manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--index-dir", type=Path)
    parser.add_argument("--allow-dense-fallback", action="store_true")
    parser.add_argument("--held-out-selection", type=Path, default=DEFAULT_HELD_OUT)
    parser.add_argument("--confirm-add", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.confirm_add:
        raise SystemExit("Permanent ingestion requires --confirm-add")
    result = ingest_pdf(
        args.pdf, corpus_manifest=args.corpus_manifest, store_dir=args.store_dir,
        index_dir=args.index_dir, allow_dense_fallback=args.allow_dense_fallback,
        held_out_selection=args.held_out_selection,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
