#!/usr/bin/env python3
"""Assemble the 30 machine candidates that an independent human must review.

Single-annotation records come from Annotator A. Double-annotation records come
from the separately reconciled machine-candidate directory. Inputs are copied;
they are never edited or promoted to gold by this script.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--selection",
        type=Path,
        default=Path("step3_pilot/selection/pilot_selection.json"),
    )
    parser.add_argument(
        "--annotator-a",
        type=Path,
        default=Path("step3_pilot/submitted/annotator_a"),
    )
    parser.add_argument(
        "--machine-candidates",
        type=Path,
        default=Path("step3_pilot/adjudication/machine_candidates"),
    )
    parser.add_argument(
        "--single-review-candidates",
        type=Path,
        default=Path("step3_pilot/adjudication/single_review_candidates"),
        help="optional corrected copies for non-double-annotation records",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("step3_pilot/human_review_queue"),
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="replace an existing queue only; never modifies submitted A/B files",
    )
    return parser.parse_args()


def index(directory: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    result = {}
    for path in sorted(directory.glob("*.annotation.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        file_id = (record.get("source_document") or {}).get("file_instance_id")
        if not file_id or file_id in result:
            raise ValueError(f"{path}: missing or duplicate file_instance_id")
        result[file_id] = (path, record)
    return result


def main() -> int:
    args = parse_args()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    if not isinstance(selection, list) or len(selection) != 30:
        raise ValueError("selection must contain exactly 30 rows")
    a_records = index(args.annotator_a)
    machine_records = index(args.machine_candidates)
    single_review_records = index(args.single_review_candidates)
    if len(a_records) != 30:
        raise ValueError(f"Annotator A directory must contain 30 records; found {len(a_records)}")
    if sum(bool(row.get("double_annotation")) for row in selection) != 10:
        raise ValueError("selection must identify exactly ten double annotations")
    selected_ids = {row["file_instance_id"] for row in selection}
    double_ids = {
        row["file_instance_id"] for row in selection if bool(row.get("double_annotation"))
    }
    if set(single_review_records) - selected_ids:
        raise ValueError("single-review directory contains an unselected record")
    if set(single_review_records) & double_ids:
        raise ValueError("single-review overrides cannot replace double-annotation candidates")

    if args.output_dir.exists():
        existing = list(args.output_dir.glob("*.annotation.json"))
        if existing and not args.replace:
            raise ValueError(
                f"review queue already contains {len(existing)} records; pass --replace"
            )
        if args.replace:
            shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    for row in selection:
        file_id = row["file_instance_id"]
        if bool(row.get("double_annotation")):
            source_item = machine_records.get(file_id)
            source_stream = "machine_adjudicated_candidate"
            if source_item is None:
                raise ValueError(f"{row['ad_number']}: missing machine adjudication candidate")
        else:
            if file_id in single_review_records:
                source_item = single_review_records[file_id]
                source_stream = "machine_reviewed_single_candidate"
            else:
                source_item = a_records.get(file_id)
                source_stream = "annotator_a_first_pass"
        if source_item is None:
            raise ValueError(f"{row['ad_number']}: missing source annotation")
        source_path, record = source_item
        identity = record.get("ad_identity") or {}
        source = record.get("source_document") or {}
        if identity.get("logical_version_key") != row["logical_version_key"]:
            raise ValueError(f"{row['ad_number']}: logical version mismatch")
        if source.get("file_sha256") != row["file_sha256"]:
            raise ValueError(f"{row['ad_number']}: source hash mismatch")
        destination = args.output_dir / source_path.name
        shutil.copy2(source_path, destination)
        manifest.append(
            {
                "ad_number": row["ad_number"],
                "file_instance_id": file_id,
                "double_annotation": bool(row.get("double_annotation")),
                "queue_source": source_stream,
                "queue_file": destination.name,
                "human_review_status": "pending",
                "strict_gold_status": "blocked_pending_human_review",
            }
        )

    manifest_path = args.output_dir / "review_queue_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest[0]))
        writer.writeheader()
        writer.writerows(manifest)
    print(f"Assembled {len(manifest)} records in {args.output_dir}; human review remains pending")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
