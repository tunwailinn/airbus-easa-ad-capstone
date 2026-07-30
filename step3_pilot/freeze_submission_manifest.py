#!/usr/bin/env python3
"""Hash and freeze the independent A/B submission inventory."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
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
        "--roster",
        type=Path,
        default=Path("step3_pilot/selection/annotation_assignment_roster.csv"),
    )
    parser.add_argument(
        "--annotator-a",
        type=Path,
        default=Path("step3_pilot/submitted/annotator_a"),
    )
    parser.add_argument(
        "--annotator-b",
        type=Path,
        default=Path("step3_pilot/submitted/annotator_b"),
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=Path("step3_pilot/submitted/submission_manifest"),
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_stream(directory: Path, stream: str) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(directory.glob("*.annotation.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        source = record.get("source_document") or {}
        identity = record.get("ad_identity") or {}
        metadata = record.get("annotation_metadata") or {}
        annotators = [item.get("annotator_id") for item in metadata.get("annotators", [])]
        rows.append(
            {
                "stream": stream,
                "ad_number": identity.get("ad_number"),
                "logical_version_key": identity.get("logical_version_key"),
                "file_instance_id": source.get("file_instance_id"),
                "source_file_sha256": source.get("file_sha256"),
                "annotation_file": path.name,
                "annotation_sha256": sha256(path),
                "annotator_ids": "|".join(item for item in annotators if item),
                "record_status": metadata.get("record_status"),
                "human_confirmed": (record.get("classification") or {}).get("human_confirmed"),
                "gold_record": (record.get("benchmark_metadata") or {}).get("gold_record"),
            }
        )
    return rows


def main() -> int:
    args = parse_args()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    with args.roster.open("r", encoding="utf-8", newline="") as handle:
        roster = {row["ad_number"]: row for row in csv.DictReader(handle)}
    selected = {row["file_instance_id"]: row for row in selection}
    rows = load_stream(args.annotator_a, "annotator_a") + load_stream(
        args.annotator_b, "annotator_b"
    )
    if len(selection) != 30 or len(roster) != 30:
        raise ValueError("selection and roster must each contain 30 records")
    if sum(row["stream"] == "annotator_a" for row in rows) != 30:
        raise ValueError("Annotator A stream must contain exactly 30 records")
    if sum(row["stream"] == "annotator_b" for row in rows) != 10:
        raise ValueError("Annotator B stream must contain exactly 10 records")
    seen = set()
    for row in rows:
        file_id = row["file_instance_id"]
        key = (row["stream"], file_id)
        if not file_id or key in seen or file_id not in selected:
            raise ValueError(f"invalid or duplicate stream/file key: {key}")
        seen.add(key)
        expected = selected[file_id]
        if row["ad_number"] != expected["ad_number"]:
            raise ValueError(f"{key}: AD number mismatch")
        if row["logical_version_key"] != expected["logical_version_key"]:
            raise ValueError(f"{key}: logical version mismatch")
        if row["source_file_sha256"] != expected["file_sha256"]:
            raise ValueError(f"{key}: source hash mismatch")
        expected_annotator = roster[row["ad_number"]][
            "annotator_a" if row["stream"] == "annotator_a" else "annotator_b"
        ]
        if expected_annotator not in row["annotator_ids"].split("|"):
            raise ValueError(f"{key}: missing expected annotator {expected_annotator}")
        if row["record_status"] != "first_pass_complete":
            raise ValueError(f"{key}: submission is not first_pass_complete")
        if row["human_confirmed"] is not False or row["gold_record"] is not False:
            raise ValueError(f"{key}: a machine submission cannot be human/gold")

    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_prefix.with_suffix(".csv")
    json_path = args.output_prefix.with_suffix(".json")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "manifest_version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "selection_sha256": sha256(args.selection),
        "roster_sha256": sha256(args.roster),
        "annotator_a_count": 30,
        "annotator_b_count": 10,
        "submissions": rows,
    }
    json_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Frozen 40 independent submissions: {json_path}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
