#!/usr/bin/env python3
"""Promote one complete, validated extraction run to canonical corpus outputs."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from full_corpus_pipeline.content_projection import forbidden_paths, validate_record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--expected-count", type=int, required=True)
    args = parser.parse_args()
    failures = args.run_dir / "extraction_failures.csv"
    if failures.exists() and len(failures.read_text(encoding="utf-8").splitlines()) > 1:
        raise ValueError("run contains extraction failures")
    source_records = sorted((args.run_dir / "records").glob("*.json"))
    if len(source_records) != args.expected_count:
        raise ValueError(f"expected {args.expected_count} records, found {len(source_records)}")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError(f"refusing to overwrite canonical output: {args.output_dir}")
    target_records = args.output_dir / "extracted_records"
    target_records.mkdir(parents=True)
    schema = json.loads(
        (Path(__file__).with_name("content_record.schema.json")).read_text(encoding="utf-8")
    )
    records = []
    seen = set()
    for source in source_records:
        record = json.loads(source.read_text(encoding="utf-8"))
        errors = validate_record(record, schema)
        if errors:
            raise ValueError(f"{source}: {'; '.join(errors[:5])}")
        forbidden = forbidden_paths(record)
        if forbidden:
            raise ValueError(f"{source}: forbidden content keys: {forbidden[:5]}")
        key = (record["ad_identity"]["ad_number"], source.name.split("__")[-1].removesuffix(".json"))
        if key in seen:
            raise ValueError(f"duplicate content record: {key}")
        seen.add(key)
        shutil.copy2(source, target_records / source.name)
        records.append(record)
    with (args.output_dir / "extracted_ad_records_v1.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    for name in (
        "extraction_manifest.parquet",
        "lifecycle_manifest.parquet",
        "extraction_failures.csv",
        "run_config.json",
    ):
        source = args.run_dir / name
        if source.exists():
            shutil.copy2(source, args.output_dir / name)
    print(f"Promoted {len(records)} records to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
