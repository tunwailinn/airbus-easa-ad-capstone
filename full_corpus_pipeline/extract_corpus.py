#!/usr/bin/env python3
"""Extract section-complete content records from the frozen Airbus EASA AD corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from full_corpus_pipeline import CONTENT_SCHEMA_VERSION
from full_corpus_pipeline.local_extractor_v216 import PARSER_VERSION, extract_local_record


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = Path(__file__).with_name("content_record.schema.json")
DEFAULT_TEXT = ROOT / "step3_pilot/source_metadata/corpus_extracted_text.parquet"
DEFAULT_MANIFEST = ROOT / "step3_pilot/source_metadata/corpus_manifest.parquet"
DEFAULT_UNSEEN = ROOT / "evaluation_sets/unseen_incoming_5_v1/selection.csv"
DEFAULT_SPLIT = ROOT / "evaluation_sets/easa_airbus_ad_content_gold_50_v2/split_manifest.json"
DEFAULT_OUTPUT = ROOT / "data_processed"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text-parquet", type=Path, default=DEFAULT_TEXT)
    parser.add_argument("--manifest-parquet", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--exclude-selection", type=Path, default=DEFAULT_UNSEEN)
    parser.add_argument("--split-manifest", type=Path, default=DEFAULT_SPLIT)
    parser.add_argument("--evaluation-split", choices=("development", "test"))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--run-id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--include-held-out", action="store_true")
    return parser.parse_args()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def record_filename(ad_number: str, file_instance_id: str) -> str:
    safe_ad = re.sub(r"[^A-Za-z0-9-]", "_", ad_number)
    return f"{safe_ad}__{file_instance_id}.json"


def load_inputs(text_path: Path, manifest_path: Path) -> pd.DataFrame:
    text = pd.read_parquet(text_path)[["file_instance_id", "text"]]
    manifest = pd.read_parquet(manifest_path)
    frame = manifest.merge(text, on="file_instance_id", how="left", validate="one_to_one")
    if frame["text"].isna().any():
        missing = frame.loc[frame["text"].isna(), "file_instance_id"].tolist()[:5]
        raise ValueError(f"missing extracted text for {missing}")
    return frame.sort_values(["ad_number", "file_instance_id"]).reset_index(drop=True)


def main() -> int:
    args = parse_args()
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.output_dir / "runs" / run_id
    if run_dir.exists():
        raise ValueError(f"refusing to overwrite run directory: {run_dir}")
    records_dir = run_dir / "records"
    records_dir.mkdir(parents=True)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    frame = load_inputs(args.text_parquet, args.manifest_parquet)
    held_out: set[str] = set()
    if args.exclude_selection.exists() and not args.include_held_out:
        held_out = set(pd.read_csv(args.exclude_selection)["file_instance_id"].astype(str))
        frame = frame[~frame["file_instance_id"].isin(held_out)]
    if args.evaluation_split:
        split_rows = json.loads(args.split_manifest.read_text(encoding="utf-8"))
        included = {
            str(item["file_instance_id"])
            for item in split_rows
            if item["split"] == args.evaluation_split
        }
        frame = frame[frame["file_instance_id"].astype(str).isin(included)]
        if len(frame) != len(included):
            raise ValueError(
                f"split requested {len(included)} records but {len(frame)} were available after exclusions"
            )
    if args.limit is not None:
        frame = frame.head(args.limit)
    manifest_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []

    for row in frame.to_dict(orient="records"):
        started = time.monotonic()
        try:
            record, detail = extract_local_record(row, schema)
            encoded = (json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
            filename = record_filename(record["ad_identity"]["ad_number"], row["file_instance_id"])
            (records_dir / filename).write_bytes(encoded)
            records.append(record)
            manifest_rows.append(
                {
                    "file_instance_id": row["file_instance_id"], "ad_number": row["ad_number"],
                    "source_pdf_sha256": row["file_sha256"], "derived_filename": filename,
                    "derived_sha256": sha256_bytes(encoded),
                    "method": detail["method"],
                    "parser_version": detail.get("parser_version"),
                    "model": None, "temperature": None, "prompt_version": None,
                    "attempts": detail["attempts"], "request_id": detail["request_id"],
                    "usage_json": json.dumps(detail["usage"], sort_keys=True),
                    "latency_seconds": round(time.monotonic() - started, 3), "status": "success",
                }
            )
        except Exception as exc:
            failures.append(
                {"file_instance_id": row["file_instance_id"], "ad_number": row["ad_number"],
                 "error": str(exc), "latency_seconds": round(time.monotonic() - started, 3)}
            )

    with (run_dir / "records.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    pd.DataFrame(manifest_rows).to_parquet(run_dir / "extraction_manifest.parquet", index=False)
    lifecycle_columns = [
        "file_instance_id", "ad_number", "base_ad_number", "revision_number",
        "is_correction", "logical_version_key", "previous_version", "next_version",
        "latest_version", "is_latest_version", "requires_manual_review",
    ]
    lifecycle = frame[[column for column in lifecycle_columns if column in frame.columns]].copy()
    lifecycle["operational_selection"] = (
        lifecycle.get("is_latest_version", False).astype(bool)
        & ~lifecycle.get("requires_manual_review", False).astype(bool)
    )
    lifecycle["relationship_status"] = lifecycle.get("requires_manual_review", False).map(
        {True: "requires_manual_review", False: "snapshot_manifest_candidate"}
    )
    lifecycle.to_parquet(run_dir / "lifecycle_manifest.parquet", index=False)
    pd.DataFrame(failures, columns=["file_instance_id", "ad_number", "error", "latency_seconds"]).to_csv(
        run_dir / "extraction_failures.csv", index=False
    )
    run_config = {
        "run_id": run_id, "content_schema_version": CONTENT_SCHEMA_VERSION,
        "method": "local",
        "parser_version": PARSER_VERSION,
        "model": None, "temperature": None, "max_attempts": 1,
        "requested_count": len(frame), "success_count": len(records), "failure_count": len(failures),
        "held_out_count": len(held_out), "evaluation_split": args.evaluation_split,
        "hosted_execution": False,
    }
    (run_dir / "run_config.json").write_text(json.dumps(run_config, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run_config, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
