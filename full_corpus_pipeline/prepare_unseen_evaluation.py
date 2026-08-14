#!/usr/bin/env python3
"""Prepare the five frozen unseen PDFs for post-final evaluation without ingestion.

This is the first stage of the unseen-document experiment. It is intentionally
non-destructive: source PDFs, corpus manifests, retrieval indexes, and incoming
stores are read-only. The script validates the locked five-case selection against
the frozen corpus manifest, verifies each source PDF hash and page count, runs the
frozen deterministic parser, creates temporary section-aware chunks, and writes
source-grounded authoring packets for later human-reviewed unseen QA questions.

It does NOT call a hosted model and does NOT permanently ingest or index a PDF.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from full_corpus_pipeline.document_io import file_sha256, joined_page_text, read_pdf_pages
from full_corpus_pipeline.extract_corpus import SCHEMA_PATH
from full_corpus_pipeline.extract_page_text import build_pdf_index, resolve_pdf
from full_corpus_pipeline.local_extractor_v216 import PARSER_VERSION, extract_local_record
from full_corpus_pipeline.retrieval import chunk_pages


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SELECTION = ROOT / "evaluation_sets/unseen_incoming_5_v1/selection.csv"
DEFAULT_SELECTION_LOCK = ROOT / "evaluation_sets/unseen_incoming_5_v1/selection_lock.json"
DEFAULT_MANIFEST = ROOT / "step3_pilot/source_metadata/corpus_manifest.parquet"
DEFAULT_OUTPUT = ROOT / "data_processed/evaluations/unseen_5/preparation"
PREPARATION_VERSION = "unseen-5-preparation-v1.0"
EXPECTED_STRATA = {
    "corrected",
    "revised",
    "supersedure",
    "long_document",
    "simple_original",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not pd.isna(value):
        return bool(value)
    return text(value).casefold() in {"true", "1", "yes"}


def validate_selection(selection: pd.DataFrame, manifest: pd.DataFrame) -> pd.DataFrame:
    required = {
        "stratum",
        "ad_number",
        "base_ad_number",
        "file_instance_id",
        "relative_path",
        "file_sha256",
        "page_count",
        "revision_number",
        "is_correction",
    }
    missing = required - set(selection.columns)
    if missing:
        raise ValueError(f"unseen selection is missing columns: {sorted(missing)}")
    if len(selection) != 5:
        raise ValueError(f"expected exactly five unseen rows, found {len(selection)}")
    if set(selection["stratum"].astype(str)) != EXPECTED_STRATA:
        raise ValueError(
            "unseen strata differ from the frozen five-case design: "
            f"{sorted(selection['stratum'].astype(str))}"
        )
    if selection["file_instance_id"].astype(str).nunique() != 5:
        raise ValueError("unseen selection does not contain five unique file_instance_id values")
    if selection["base_ad_number"].astype(str).nunique() != 5:
        raise ValueError("unseen selection does not contain five distinct AD families")

    manifest = manifest.copy()
    manifest["file_instance_id"] = manifest["file_instance_id"].astype(str)
    selection = selection.copy()
    selection["file_instance_id"] = selection["file_instance_id"].astype(str)
    selected = selection.merge(
        manifest,
        on="file_instance_id",
        how="left",
        suffixes=("_selection", "_manifest"),
        validate="one_to_one",
        indicator=True,
    )
    if (selected["_merge"] != "both").any():
        missing_ids = selected.loc[selected["_merge"] != "both", "file_instance_id"].tolist()
        raise ValueError(f"unseen IDs missing from corpus manifest: {missing_ids}")

    checks = [
        ("ad_number", text),
        ("base_ad_number", text),
        ("relative_path", text),
        ("file_sha256", text),
    ]
    for field, normalizer in checks:
        left = selected[f"{field}_selection"].map(normalizer)
        right = selected[f"{field}_manifest"].map(normalizer)
        mismatch = left != right
        if mismatch.any():
            ids = selected.loc[mismatch, "file_instance_id"].tolist()
            raise ValueError(f"selection/manifest mismatch for {field}: {ids}")

    for field in ("page_count", "revision_number"):
        left = selected[f"{field}_selection"].astype(int)
        right = selected[f"{field}_manifest"].astype(int)
        mismatch = left != right
        if mismatch.any():
            ids = selected.loc[mismatch, "file_instance_id"].tolist()
            raise ValueError(f"selection/manifest mismatch for {field}: {ids}")

    left_correction = selected["is_correction_selection"].map(bool_value)
    right_correction = selected["is_correction_manifest"].map(bool_value)
    mismatch = left_correction != right_correction
    if mismatch.any():
        ids = selected.loc[mismatch, "file_instance_id"].tolist()
        raise ValueError(f"selection/manifest mismatch for is_correction: {ids}")
    return selected


def source_packet_name(ad_number: str, file_instance_id: str) -> str:
    safe = ad_number.replace("/", "_").replace(" ", "_")
    return f"{safe}__{file_instance_id}.authoring.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pdf-root",
        type=Path,
        default=ROOT,
        help="Directory containing the frozen source PDFs; defaults to recursively searching the project root.",
    )
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--selection-lock", type=Path, default=DEFAULT_SELECTION_LOCK)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    for path in (args.selection, args.selection_lock, args.manifest):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError(f"refusing to overwrite non-empty unseen preparation directory: {args.output_dir}")

    selection = pd.read_csv(args.selection)
    manifest = pd.read_parquet(args.manifest)
    lock = json.loads(args.selection_lock.read_text(encoding="utf-8"))
    if lock.get("count") != 5:
        raise ValueError("unseen selection lock does not declare count=5")
    if lock.get("distinct_family_count") != 5:
        raise ValueError("unseen selection lock does not declare five distinct families")
    if lock.get("corpus_manifest_sha256") != sha256(args.manifest):
        raise ValueError("frozen corpus manifest SHA-256 differs from unseen selection lock")

    merged = validate_selection(selection, manifest)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    packets_dir = args.output_dir / "authoring_packets"
    packets_dir.mkdir()
    by_name = build_pdf_index(args.pdf_root)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    results: list[dict[str, Any]] = []
    print("[progress] validating and opening five frozen unseen PDFs", flush=True)
    for position, joined in enumerate(merged.to_dict(orient="records"), 1):
        row = {
            key.removesuffix("_manifest"): value
            for key, value in joined.items()
            if key.endswith("_manifest")
        }
        file_id = text(joined["file_instance_id"])
        stratum = text(joined["stratum"])
        expected_ad = text(joined["ad_number_selection"])
        expected_hash = text(joined["file_sha256_selection"])
        expected_pages = int(joined["page_count_selection"])
        print(f"[progress] unseen source {position}/5: {expected_ad} ({stratum})", flush=True)

        pdf_path = resolve_pdf(row, pdf_root=args.pdf_root, by_name=by_name)
        actual_hash = file_sha256(pdf_path)
        if actual_hash != expected_hash:
            raise ValueError(f"source hash mismatch for {expected_ad}: {actual_hash}")
        pages = read_pdf_pages(pdf_path)
        if len(pages) != expected_pages:
            raise ValueError(
                f"page-count mismatch for {expected_ad}: expected {expected_pages}, found {len(pages)}"
            )
        weak_pages = [int(page["page"]) for page in pages if page.get("needs_ocr")]
        if weak_pages:
            raise ValueError(
                f"unseen source {expected_ad} contains native-text pages requiring review/OCR: {weak_pages}"
            )

        extraction_row = {
            "file_instance_id": file_id,
            "file_sha256": actual_hash,
            "text": joined_page_text(pages),
            "ad_number": expected_ad,
            "relative_path": text(joined["relative_path_selection"]),
            "is_emergency": bool_value(row.get("is_emergency")),
            "correction_date": text(row.get("correction_date")),
            "issue_date": text(row.get("issue_date")),
        }
        record, detail = extract_local_record(extraction_row, schema)
        extracted_ad = text((record.get("ad_identity") or {}).get("ad_number"))
        if extracted_ad.casefold() != expected_ad.casefold():
            raise ValueError(
                f"frozen parser AD identity mismatch for {expected_ad}: extracted {extracted_ad!r}"
            )
        if detail.get("parser_version") != PARSER_VERSION:
            raise ValueError(
                f"unexpected parser version for {expected_ad}: {detail.get('parser_version')}"
            )

        chunks = chunk_pages(
            pages,
            file_instance_id=file_id,
            ad_number=expected_ad,
            source_pdf=text(joined["relative_path_selection"]),
            lifecycle_status="temporary",
        )
        packet = {
            "preparation_version": PREPARATION_VERSION,
            "evaluation_role": "frozen_unseen_post_final",
            "stratum": stratum,
            "selection": {
                "ad_number": expected_ad,
                "base_ad_number": text(joined["base_ad_number_selection"]),
                "file_instance_id": file_id,
                "relative_path": text(joined["relative_path_selection"]),
                "file_sha256": expected_hash,
                "page_count": expected_pages,
                "revision_number": int(joined["revision_number_selection"]),
                "is_correction": bool_value(joined["is_correction_selection"]),
            },
            "source_validation": {
                "resolved_pdf": str(pdf_path),
                "actual_sha256": actual_hash,
                "hash_match": True,
                "actual_page_count": len(pages),
                "page_count_match": True,
                "needs_ocr_pages": [],
            },
            "frozen_extraction": {
                "parser_version": detail.get("parser_version"),
                "method": detail.get("method"),
                "record": record,
            },
            "pages": [
                {
                    "page": int(page["page"]),
                    "needs_ocr": bool(page.get("needs_ocr", False)),
                    "text": str(page.get("text", "")),
                }
                for page in pages
            ],
            "temporary_chunks": [asdict(chunk) for chunk in chunks],
            "policy": (
                "Opened only after the frozen E5 primary and oracle evaluation. This packet is for post-final "
                "unseen-document evaluation and may not be used to retune the frozen parser, E5 retrieval, or Layer C configuration."
            ),
        }
        packet_path = packets_dir / source_packet_name(expected_ad, file_id)
        packet_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        results.append(
            {
                "stratum": stratum,
                "ad_number": expected_ad,
                "base_ad_number": text(joined["base_ad_number_selection"]),
                "file_instance_id": file_id,
                "source_pdf": str(pdf_path),
                "source_pdf_sha256": actual_hash,
                "page_count": len(pages),
                "parser_version": detail.get("parser_version"),
                "extraction_status": "success",
                "schema_status": "valid",
                "temporary_chunk_count": len(chunks),
                "authoring_packet": str(packet_path),
                "authoring_packet_sha256": sha256(packet_path),
            }
        )

    manifest_path = args.output_dir / "preparation_manifest.json"
    manifest_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = {
        "preparation_version": PREPARATION_VERSION,
        "status": "ready_for_human_question_authoring",
        "question_inference_started": False,
        "permanent_ingestion_started": False,
        "selection_sha256": sha256(args.selection),
        "selection_lock_sha256": sha256(args.selection_lock),
        "corpus_manifest_sha256": sha256(args.manifest),
        "parser_version": PARSER_VERSION,
        "document_count": len(results),
        "source_hash_match_count": sum(1 for item in results if item["source_pdf_sha256"]),
        "page_count": sum(int(item["page_count"]) for item in results),
        "extraction_success_count": sum(item["extraction_status"] == "success" for item in results),
        "schema_valid_count": sum(item["schema_status"] == "valid" for item in results),
        "strata": [item["stratum"] for item in results],
        "preparation_manifest": str(manifest_path),
        "preparation_manifest_sha256": sha256(manifest_path),
        "policy": (
            "Non-destructive unseen preparation only. No hosted QA, permanent ingestion, persistent index update, "
            "or system retuning occurs in this stage."
        ),
    }
    summary_path = args.output_dir / "preparation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("[progress] unseen preparation finished", flush=True)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
