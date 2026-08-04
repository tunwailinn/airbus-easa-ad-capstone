#!/usr/bin/env python3
"""Validate a content-only AD dataset and its JSONL representation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from full_corpus_pipeline.content_projection import forbidden_paths, leaf_json_paths, validate_record


SCHEMA_PATH = Path(__file__).with_name("content_record.schema.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", type=Path)
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--require-unique-ad-number", action="store_true")
    parser.add_argument("--require-lineage", action="store_true")
    return parser.parse_args()


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def main() -> int:
    args = parse_args()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    records_dir = args.dataset_dir / "records"
    if not records_dir.exists():
        records_dir = args.dataset_dir / "extracted_records"
    paths = sorted(records_dir.glob("*.json"))
    errors: list[str] = []
    if len(paths) != args.expected_count:
        errors.append(f"expected {args.expected_count} JSON records, found {len(paths)}")
    records: list[dict[str, Any]] = []
    ad_numbers: set[str] = set()
    for path in paths:
        value = json.loads(path.read_text(encoding="utf-8"))
        records.append(value)
        for error in validate_record(value, schema):
            errors.append(f"{path}: {error}")
        forbidden = forbidden_paths(value)
        if forbidden:
            errors.extend(f"{path}: forbidden {item}" for item in forbidden)
        ad_number = (value.get("ad_identity") or {}).get("ad_number")
        if args.require_unique_ad_number and ad_number in ad_numbers:
            errors.append(f"duplicate AD number {ad_number}")
        ad_numbers.add(ad_number)

    jsonl_path = args.dataset_dir / "records.jsonl"
    if not jsonl_path.exists():
        jsonl_path = args.dataset_dir / "extracted_ad_records_v1.jsonl"
    jsonl_records = [
        json.loads(line)
        for line in jsonl_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(jsonl_records) != args.expected_count:
        errors.append(
            f"expected {args.expected_count} JSONL records, found {len(jsonl_records)}"
        )
    if sorted(map(canonical, records)) != sorted(map(canonical, jsonl_records)):
        errors.append("individual JSON and JSONL records differ")

    lineage_path = args.dataset_dir / "projection_lineage.jsonl"
    if lineage_path.exists():
        lineage = [json.loads(line) for line in lineage_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(lineage) != args.expected_count:
            errors.append(f"expected {args.expected_count} lineage rows, found {len(lineage)}")
        lineage_by_name = {item["derived_filename"]: item for item in lineage}
        for path, record in zip(paths, records):
            mapped = {item["derived_path"] for item in lineage_by_name.get(path.name, {}).get("mappings", [])}
            missing = set(leaf_json_paths(record)) - mapped
            if missing:
                errors.append(f"{path}: {len(missing)} retained scalar values lack source paths")
    elif args.require_lineage:
        errors.append("projection_lineage.jsonl is missing")

    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 2
    print(f"Validated {len(records)} content records with no forbidden fields")
    return 0


if __name__ == "__main__":
    sys.exit(main())
