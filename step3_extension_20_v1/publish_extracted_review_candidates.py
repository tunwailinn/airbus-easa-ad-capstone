#!/usr/bin/env python3
"""Replace blank extension drafts with validated populated review candidates."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "annotations" / "extracted_candidates"
DESTINATIONS = {
    "annotator_a": ROOT / "annotations" / "annotator_a",
    "human_review_queue": ROOT / "human_review_queue",
    "human_review_working": ROOT / "human_review_working",
}
EXPECTED = 20


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records(directory: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    result = {}
    for path in sorted(directory.glob("*.annotation.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        ad_number = value["ad_identity"]["ad_number"]
        if ad_number in result:
            raise ValueError(f"duplicate AD number {ad_number} in {directory}")
        result[ad_number] = (path, value)
    return result


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    source_records = records(SOURCE)
    if len(source_records) != EXPECTED:
        raise ValueError(
            f"expected {EXPECTED} extracted candidates, found {len(source_records)}"
        )
    expected_names = {item[0].name for item in source_records.values()}

    for destination in DESTINATIONS.values():
        existing_names = {path.name for path in destination.glob("*.annotation.json")}
        if existing_names != expected_names:
            raise ValueError(
                f"{destination}: annotation membership differs from extracted candidates"
            )
        for path, _record in source_records.values():
            shutil.copy2(path, destination / path.name)

    queue_rows = []
    working_rows = []
    for ad_number, (path, record) in sorted(source_records.items()):
        source = record["source_document"]
        metadata = record["annotation_metadata"]
        queue_rows.append(
            {
                "ad_number": ad_number,
                "file_instance_id": source["file_instance_id"],
                "queue_file": path.name,
                "human_review_status": "pending",
                "record_status": metadata["record_status"],
                "creation_method": metadata["creation_method"],
                "requirements": len(record["requirements"]),
                "evidence_spans": len(record["evidence_spans"]),
                "field_assertions": len(record["field_assertions"]),
                "human_confirmed": "false",
                "gold_record": "false",
                "supersedure_links": len(record["relationships"]),
            }
        )
        queue_path = DESTINATIONS["human_review_queue"] / path.name
        working_rows.append(
            {
                "ad_number": ad_number,
                "file_instance_id": source["file_instance_id"],
                "working_file": path.name,
                "copied_from_queue_sha256": sha256(queue_path),
                "review_status": "not_started",
                "requirements": len(record["requirements"]),
                "evidence_spans": len(record["evidence_spans"]),
            }
        )

    write_csv(
        DESTINATIONS["human_review_queue"] / "review_queue_manifest.csv",
        queue_rows,
    )
    write_csv(
        DESTINATIONS["human_review_working"] / "working_copy_manifest.csv",
        working_rows,
    )

    for ad_number, (source_path, _record) in source_records.items():
        queue_path = DESTINATIONS["human_review_queue"] / source_path.name
        working_path = DESTINATIONS["human_review_working"] / source_path.name
        if sha256(source_path) != sha256(queue_path) or sha256(queue_path) != sha256(
            working_path
        ):
            raise ValueError(f"{ad_number}: published copies differ")

    print(
        "Published 20 populated candidates to annotator_a, human_review_queue, "
        "and human_review_working."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
