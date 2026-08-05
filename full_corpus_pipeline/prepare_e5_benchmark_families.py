#!/usr/bin/env python3
"""Prepare a deterministic family-level split for the E5 benchmark.

This selects NEW base AD families from the verified 1,786-document retrieval
manifest. It excludes every target family already exposed by QA-v2 and writes a
locked 24-development / 16-final-test family split, stratified by publication era.

The script does not author questions. Question authoring/review is a separate
source-grounded step after family membership is frozen.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    ROOT / "data_processed/page_text_v1_1/operational_airbus/retrieval_manifest.csv"
)
DEFAULT_OLD_QUESTIONS = (
    ROOT / "evaluation_sets/easa_airbus_ad_qa_50_v2/questions.jsonl"
)
DEFAULT_OUTPUT_DIR = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1"
DEFAULT_SEED = 20260805
DEV_FAMILIES = 24
FINAL_FAMILIES = 16
TOTAL_FAMILIES = DEV_FAMILIES + FINAL_FAMILIES


REVISION_SUFFIX_RE = re.compile(r"R\d+$", re.IGNORECASE)


def base_ad_number(value: str) -> str:
    normalized = str(value).strip().upper()
    return REVISION_SUFFIX_RE.sub("", normalized)


def era_for_year(year: int) -> str:
    if year <= 2009:
        return "2003-2009"
    if year <= 2015:
        return "2010-2015"
    if year <= 2020:
        return "2016-2020"
    return "2021-2026"


def load_exposed_families(path: Path) -> set[str]:
    exposed: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        target = item.get("target_ad_number")
        if target:
            exposed.add(base_ad_number(str(target)))
    return exposed


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    return str(value).strip().casefold() in {"true", "1", "yes", "y"}


def representative_rows(manifest: pd.DataFrame) -> pd.DataFrame:
    frame = manifest.copy()
    if "base_ad_number" in frame.columns:
        frame["base_ad_number_e5"] = frame["base_ad_number"].astype(str).str.upper()
    else:
        frame["base_ad_number_e5"] = frame["ad_number"].map(base_ad_number)

    frame["year"] = frame["base_ad_number_e5"].str.slice(0, 4).astype(int)
    frame["era"] = frame["year"].map(era_for_year)

    if "is_latest_version" in frame.columns:
        frame["_latest"] = frame["is_latest_version"].map(_as_bool)
    else:
        frame["_latest"] = False

    frame["_revision_number"] = (
        frame["ad_number"]
        .astype(str)
        .str.extract(r"R(\d+)$", expand=False)
        .fillna("0")
        .astype(int)
    )
    frame = frame.sort_values(
        ["base_ad_number_e5", "_latest", "_revision_number", "ad_number"],
        ascending=[True, False, False, False],
    )
    return frame.drop_duplicates("base_ad_number_e5", keep="first")


def select_families(frame: pd.DataFrame, *, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    era_order = ["2003-2009", "2010-2015", "2016-2020", "2021-2026"]
    selected_rows: list[pd.Series] = []

    for era in era_order:
        candidates = frame.loc[frame["era"] == era].copy()
        records = candidates.to_dict("records")
        rng.shuffle(records)
        if len(records) < 10:
            raise ValueError(
                f"E5 benchmark needs at least 10 eligible families in {era}; "
                f"found {len(records)}"
            )
        chosen = records[:10]
        for position, record in enumerate(chosen):
            record["split"] = "development" if position < 6 else "final_test"
            selected_rows.append(pd.Series(record))

    selected = pd.DataFrame(selected_rows)
    if len(selected) != TOTAL_FAMILIES:
        raise AssertionError("unexpected E5 family count")
    if int((selected["split"] == "development").sum()) != DEV_FAMILIES:
        raise AssertionError("unexpected E5 development-family count")
    if int((selected["split"] == "final_test").sum()) != FINAL_FAMILIES:
        raise AssertionError("unexpected E5 final-family count")

    keep = [
        "split",
        "era",
        "year",
        "base_ad_number_e5",
        "ad_number",
        "file_instance_id",
        "relative_path",
    ]
    optional = [column for column in ("is_latest_version", "page_count") if column in selected.columns]
    result = selected[keep + optional].rename(
        columns={
            "base_ad_number_e5": "base_ad_number",
            "ad_number": "representative_ad_number",
            "file_instance_id": "representative_file_instance_id",
            "relative_path": "representative_relative_path",
        }
    )
    return result.sort_values(["split", "era", "base_ad_number"]).reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--old-questions", type=Path, default=DEFAULT_OLD_QUESTIONS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    print("[progress] loading verified retrieval manifest", flush=True)
    manifest = pd.read_csv(
        args.manifest,
        dtype={"file_instance_id": str, "ad_number": str},
    )
    required = {"file_instance_id", "ad_number", "relative_path"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"retrieval manifest missing required columns: {sorted(missing)}")

    print("[progress] loading exposed QA-v2 target families", flush=True)
    exposed = load_exposed_families(args.old_questions)
    representatives = representative_rows(manifest)
    eligible = representatives.loc[
        ~representatives["base_ad_number_e5"].isin(exposed)
    ].copy()

    print(
        f"[progress] selecting {TOTAL_FAMILIES} new families from "
        f"{len(eligible)} eligible families with seed {args.seed}",
        flush=True,
    )
    selected = select_families(eligible, seed=args.seed)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "family_split.csv"
    selected.to_csv(csv_path, index=False)
    csv_bytes = csv_path.read_bytes()
    split_hash = hashlib.sha256(csv_bytes).hexdigest()

    lock = {
        "benchmark_version": "easa-airbus-ad-e5-benchmark-v1",
        "seed": args.seed,
        "source_manifest": str(args.manifest),
        "excluded_qa_v2_base_families": sorted(exposed),
        "development_family_count": DEV_FAMILIES,
        "final_test_family_count": FINAL_FAMILIES,
        "total_family_count": TOTAL_FAMILIES,
        "era_policy": {
            "2003-2009": {"development": 6, "final_test": 4},
            "2010-2015": {"development": 6, "final_test": 4},
            "2016-2020": {"development": 6, "final_test": 4},
            "2021-2026": {"development": 6, "final_test": 4},
        },
        "family_split_sha256": split_hash,
        "questions": {
            "development_target": 60,
            "final_test_target": 40,
        },
    }
    (args.output_dir / "split_lock.json").write_text(
        json.dumps(lock, indent=2) + "\n", encoding="utf-8"
    )

    print("[progress] E5 family split created", flush=True)
    print(selected.groupby(["split", "era"]).size().to_string())
    print(f"[progress] family split: {csv_path}", flush=True)
    print(f"[progress] SHA256: {split_hash}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
