#!/usr/bin/env python3
"""Prepare review packets and draft annotation copies for the 20-record extension.

The generated annotations contain frozen source identity and provenance only.
Substantive annotation fields remain blank for independent human review. Queue
copies are treated as immutable inputs; working copies are the editable review
surface. Nothing generated here is human-confirmed or gold.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any


EXTENSION_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = EXTENSION_ROOT.parent
SELECTION_PATH = EXTENSION_ROOT / "selection" / "extension_selection.json"
PDF_DIR = EXTENSION_ROOT / "source_pdfs"
PAGE_TEXT_DIR = EXTENSION_ROOT / "page_text"
TEMPLATE_PATH = PROJECT_ROOT / "step2_ad_schema" / "blank_ad_annotation.json"

EXPECTED_RECORDS = 20
EXPECTED_SUPERSEDURE_LINKS = 0

sys.path.insert(0, str(PROJECT_ROOT))
from step3_pilot.prepare_annotation_packets import (  # noqa: E402
    build_annotation_template,
    build_blind_packet,
    build_reviewer_packet,
    load_page_records,
    verify_source_pdf,
)


class PreparationError(RuntimeError):
    """Raised when frozen-input or safe-output invariants fail."""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def sha256_path(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no", ""}:
        return False
    raise PreparationError(f"Cannot parse boolean value {value!r}")


def split_pipe(value: Any) -> list[str]:
    return [part.strip() for part in str(value or "").split("|") if part.strip()]


def normalize_row(raw: dict[str, Any]) -> dict[str, Any]:
    row = dict(raw)
    ad_number = str(row["ad_number"]).strip()
    row.update(
        {
            "ad_number": ad_number,
            "base_ad_number": str(row["base_ad_number"]).strip(),
            "revision_number": int(row["revision_number"]),
            "is_emergency": ad_number.endswith("-E"),
            "is_correction": parse_bool(row["is_correction"]),
            "correction_date": None,
            "page_count": int(row["page_count"]),
            "file_instance_id": str(row["file_instance_id"]).strip().lower(),
            "content_id": str(row["content_id"]).strip().lower(),
            "file_sha256": str(row["file_sha256"]).strip().lower(),
            "normalized_text_sha256": str(
                row["normalized_text_sha256"]
            ).strip().lower(),
            "double_annotation": False,
            "selection_strata": split_pipe(row.get("strata")),
            "supersedure_candidates": [],
            "near_duplicate_cluster": None,
        }
    )
    return row


def validate_selection(rows: list[dict[str, Any]]) -> None:
    if len(rows) != EXPECTED_RECORDS:
        raise PreparationError(
            f"Expected {EXPECTED_RECORDS} selected records, found {len(rows)}"
        )
    unique_fields = (
        "ad_number",
        "logical_version_key",
        "file_instance_id",
        "file_name",
        "file_sha256",
    )
    for field in unique_fields:
        values = [row[field] for row in rows]
        if len(values) != len(set(values)):
            raise PreparationError(f"Selection contains duplicate {field} values")
    link_count = sum(len(row["supersedure_candidates"]) for row in rows)
    if link_count != EXPECTED_SUPERSEDURE_LINKS:
        raise PreparationError(
            f"Expected no supersedure links, found {link_count}"
        )
    for row in rows:
        if str(row.get("supersedure_header") or "").strip().lower() != "none":
            raise PreparationError(
                f"{row['ad_number']}: supersedure_header is not explicit None"
            )
        if str(row.get("superseded_by_ad_numbers") or "").strip():
            raise PreparationError(
                f"{row['ad_number']}: superseded_by_ad_numbers is not empty"
            )
        if row["is_correction"] or row["revision_number"] != 0:
            raise PreparationError(
                f"{row['ad_number']}: extension must contain original, uncorrected records"
            )


def safe_replace_directory(stage: Path, destination: Path) -> None:
    if destination.exists() and any(destination.iterdir()):
        raise PreparationError(
            f"Refusing to overwrite non-empty output directory: {destination}"
        )
    if destination.exists():
        destination.rmdir()
    os.replace(stage, destination)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def checklist_text() -> str:
    return """# Human review checklist

These 20 records are identity/provenance-prefilled drafts. They are not
machine-completed annotations, human-approved records, or gold.

For every `*.annotation.json` working copy:

1. Compare the complete original PDF with every annotation field.
2. Complete applicability, definitions, unsafe condition, requirements,
   compliance times, exceptions, credit, publications, contacts, and
   classification.
3. Add exact page-grounded evidence spans for every populated safety-critical
   value.
4. Confirm the source explicitly states `Supersedure: None`; do not infer or
   add a supersedure relationship.
5. Resolve every field assertion as accepted or corrected.
6. Keep `human_confirmed=false` and `gold_record=false` until explicit approval.
7. Run schema, evidence-quote, and Step 3 validators before gold promotion.

Edit files only in `human_review_working/`. Keep `human_review_queue/`
unchanged as the source review queue.
"""


def main() -> int:
    raw_selection = load_json(SELECTION_PATH)
    if not isinstance(raw_selection, list):
        raise PreparationError("Extension selection must be a JSON array")
    rows = [normalize_row(item) for item in raw_selection]
    validate_selection(rows)

    blank_template = load_json(TEMPLATE_PATH)
    selection_sha256 = sha256_path(SELECTION_PATH)

    outputs = {
        "packets": EXTENSION_ROOT / "packets",
        "annotations": EXTENSION_ROOT / "annotations",
        "human_review_queue": EXTENSION_ROOT / "human_review_queue",
        "human_review_working": EXTENSION_ROOT / "human_review_working",
    }

    with tempfile.TemporaryDirectory(
        prefix=".extension-review-stage-", dir=EXTENSION_ROOT
    ) as temporary:
        stage_root = Path(temporary)
        inventory: list[dict[str, Any]] = []
        queue_manifest: list[dict[str, Any]] = []
        working_manifest: list[dict[str, Any]] = []

        for row in rows:
            pdf_path = verify_source_pdf(row, PDF_DIR)
            pages = load_page_records(row, PAGE_TEXT_DIR)
            blind = build_blind_packet(row, pdf_path, pages)
            reviewer = build_reviewer_packet(row, rows, pdf_path, pages)
            annotation = build_annotation_template(row, blank_template)

            annotation_name = (
                f"{row['ad_number']}__{row['file_instance_id']}.annotation.json"
            )
            blind_name = (
                f"{row['ad_number']}__{row['file_instance_id']}.blind-packet.json"
            )
            reviewer_name = (
                f"{row['ad_number']}__{row['file_instance_id']}"
                ".reviewer-qc-packet.json"
            )

            artifacts = (
                (Path("packets/blind") / blind_name, blind, "blind_packet"),
                (
                    Path("packets/reviewer_qc") / reviewer_name,
                    reviewer,
                    "reviewer_qc_packet",
                ),
                (
                    Path("annotations/annotator_a") / annotation_name,
                    annotation,
                    "identity_prefilled_annotation_template",
                ),
                (
                    Path("human_review_queue") / annotation_name,
                    annotation,
                    "immutable_human_review_queue_copy",
                ),
                (
                    Path("human_review_working") / annotation_name,
                    annotation,
                    "editable_human_review_working_copy",
                ),
            )
            for relative, value, artifact_type in artifacts:
                path = stage_root / relative
                write_json(path, value)
                inventory.append(
                    {
                        "ad_number": row["ad_number"],
                        "file_instance_id": row["file_instance_id"],
                        "artifact_type": artifact_type,
                        "path": str(relative),
                        "sha256": sha256_path(path),
                    }
                )

            queue_manifest.append(
                {
                    "ad_number": row["ad_number"],
                    "file_instance_id": row["file_instance_id"],
                    "queue_file": annotation_name,
                    "human_review_status": "pending",
                    "record_status": "draft",
                    "human_confirmed": "false",
                    "gold_record": "false",
                    "supersedure_links": 0,
                }
            )
            working_manifest.append(
                {
                    "ad_number": row["ad_number"],
                    "file_instance_id": row["file_instance_id"],
                    "working_file": annotation_name,
                    "copied_from_queue_sha256": sha256_path(
                        stage_root / "human_review_queue" / annotation_name
                    ),
                    "review_status": "not_started",
                }
            )

        write_csv(
            stage_root / "human_review_queue" / "review_queue_manifest.csv",
            queue_manifest,
        )
        write_csv(
            stage_root / "human_review_working" / "working_copy_manifest.csv",
            working_manifest,
        )
        checklist = checklist_text()
        for directory in ("human_review_queue", "human_review_working"):
            (stage_root / directory / "HUMAN_REVIEW_CHECKLIST.md").write_text(
                checklist, encoding="utf-8"
            )

        packet_inventory = {
            "inventory_version": "1.0.0",
            "selection_file": str(SELECTION_PATH.relative_to(PROJECT_ROOT)),
            "selection_sha256": selection_sha256,
            "selected_records": len(rows),
            "supersedure_links": 0,
            "counts": {
                "blind_packets": len(rows),
                "reviewer_qc_packets": len(rows),
                "annotation_templates": len(rows),
                "human_review_queue_records": len(rows),
                "human_review_working_records": len(rows),
            },
            "artifacts": sorted(inventory, key=lambda item: item["path"]),
        }
        write_json(stage_root / "packets" / "packet_inventory.json", packet_inventory)

        for name, destination in outputs.items():
            safe_replace_directory(stage_root / name, destination)

    print(
        "Prepared 20 queue records, 20 working copies, 20 annotation templates, "
        "and 40 source-review packets; human review remains pending."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, KeyError, ValueError, json.JSONDecodeError, PreparationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
