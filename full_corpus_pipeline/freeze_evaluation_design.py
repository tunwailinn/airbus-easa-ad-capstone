#!/usr/bin/env python3
"""Freeze the 30/20 content-gold split and five unseen incoming PDFs.

The split is grouped by AD family and selected with a deterministic, seeded
greedy stratifier. The unseen set is drawn only from non-gold corpus families
and is represented by immutable manifest rows; source PDFs are not copied or
modified by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = ROOT / "gold_releases/easa_airbus_ad_gold_v2/annotations"
DEFAULT_CONTENT = ROOT / "evaluation_sets/easa_airbus_ad_content_gold_50_v2"
DEFAULT_CORPUS_MANIFEST = ROOT / "step3_pilot/source_metadata/corpus_manifest.parquet"
DEFAULT_UNSEEN = ROOT / "evaluation_sets/unseen_incoming_5_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-dir", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--content-dir", type=Path, default=DEFAULT_CONTENT)
    parser.add_argument("--corpus-manifest", type=Path, default=DEFAULT_CORPUS_MANIFEST)
    parser.add_argument("--unseen-dir", type=Path, default=DEFAULT_UNSEEN)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def source_features(record: dict[str, Any]) -> set[str]:
    identity = record.get("ad_identity") or {}
    classification = record.get("classification") or {}
    benchmark = record.get("benchmark_metadata") or {}
    features = {str(value) for value in benchmark.get("selection_strata", [])}
    complexity = classification.get("compliance_complexity")
    if complexity:
        features.add(f"complexity:{complexity}")
    features.add("table_heavy" if classification.get("table_or_appendix_present") else "not_table_heavy")
    features.add("revised" if int(identity.get("revision_number") or 0) > 0 else "original")
    features.add("corrected" if identity.get("is_correction") else "not_corrected")
    features.add("complex_applicability" if len(record.get("applicability_groups", [])) > 1 else "single_applicability")
    return features


def choose_test(records: list[dict[str, Any]], *, count: int, seed: int) -> set[str]:
    """Choose a reproducible test set that approximately preserves feature rates."""
    if len({record["base_ad_number"] for record in records}) != len(records):
        raise ValueError("gold release contains more than one record in an AD family")
    totals = Counter(feature for record in records for feature in record["features"])
    targets = {feature: total * count / len(records) for feature, total in totals.items()}
    chosen: list[dict[str, Any]] = []
    remaining = list(records)
    rng = random.Random(seed)
    tie_break = {record["file_instance_id"]: rng.random() for record in remaining}

    while len(chosen) < count:
        current = Counter(feature for record in chosen for feature in record["features"])

        def score(record: dict[str, Any]) -> tuple[float, float, str]:
            gain = sum(
                max(0.0, targets[feature] - current[feature]) / max(targets[feature], 1.0)
                for feature in record["features"]
            )
            overfill = sum(
                max(0.0, current[feature] + 1 - targets[feature]) / max(targets[feature], 1.0)
                for feature in record["features"]
            )
            return (gain - 0.35 * overfill, tie_break[record["file_instance_id"]], record["file_instance_id"])

        selected = max(remaining, key=score)
        chosen.append(selected)
        remaining.remove(selected)
    return {record["file_instance_id"] for record in chosen}


def freeze_split(gold_dir: Path, content_dir: Path, seed: int) -> set[str]:
    projection = pd.read_parquet(content_dir / "projection_manifest.parquet")
    by_source = {row["source_gold_filename"]: row for row in projection.to_dict(orient="records")}
    rows: list[dict[str, Any]] = []
    source_files = sorted(gold_dir.glob("*.json"))
    if len(source_files) != 50:
        raise ValueError(f"expected 50 gold sources, found {len(source_files)}")
    for path in source_files:
        source = json.loads(path.read_text(encoding="utf-8"))
        mapping = by_source.get(path.name)
        if not mapping:
            raise ValueError(f"projection manifest does not map {path.name}")
        identity = source.get("ad_identity") or {}
        rows.append(
            {
                "ad_number": identity.get("ad_number"),
                "base_ad_number": identity.get("base_ad_number") or identity.get("ad_number"),
                "file_instance_id": source["source_document"]["file_instance_id"],
                "source_gold_filename": path.name,
                "derived_filename": mapping["derived_filename"],
                "original_annotation_sha256": sha256(path),
                "derived_json_sha256": mapping["derived_json_sha256"],
                "features": sorted(source_features(source)),
            }
        )

    test_ids = choose_test(rows, count=20, seed=seed)
    frozen_rows = []
    for row in sorted(rows, key=lambda item: (item["ad_number"], item["file_instance_id"])):
        frozen_rows.append({**row, "split": "test" if row["file_instance_id"] in test_ids else "development"})
    counts = Counter(row["split"] for row in frozen_rows)
    if counts != {"development": 30, "test": 20}:
        raise ValueError(f"unexpected split counts: {dict(counts)}")

    tabular = [{**row, "features": "|".join(row["features"])} for row in frozen_rows]
    pd.DataFrame(tabular).to_csv(content_dir / "split_manifest.csv", index=False)
    pd.DataFrame(tabular).to_parquet(content_dir / "split_manifest.parquet", index=False)
    write_json(content_dir / "split_manifest.json", frozen_rows)
    lock = {
        "name": "easa_airbus_ad_content_gold_50_split_v2",
        "seed": seed,
        "grouping_key": "base_ad_number",
        "development_count": 30,
        "test_count": 20,
        "test_record_policy": "locked after creation; no prompt or extraction-rule tuning",
        "source_annotation_hashes": {row["source_gold_filename"]: row["original_annotation_sha256"] for row in frozen_rows},
        "derived_record_hashes": {row["derived_filename"]: row["derived_json_sha256"] for row in frozen_rows},
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    write_json(content_dir / "split_lock.json", lock)
    return {row["file_instance_id"] for row in frozen_rows}


def freeze_unseen(corpus_manifest: Path, unseen_dir: Path, gold_ids: set[str], seed: int) -> None:
    frame = pd.read_parquet(corpus_manifest).copy()
    eligible = frame[
        (~frame["file_instance_id"].isin(gold_ids))
        & (frame["extraction_status"] == "ok")
        & (~frame["needs_ocr"].astype(bool))
        & (~frame["requires_manual_review"].astype(bool))
        & (frame["duplicate_type"].fillna("") == "")
    ].copy()
    rng = random.Random(seed)
    eligible["seed_order"] = [rng.random() for _ in range(len(eligible))]

    used_families: set[str] = set()
    selections: list[dict[str, Any]] = []
    strata = [
        ("corrected", lambda df: df["is_correction"].astype(bool)),
        ("revised", lambda df: (df["revision_number"].astype(int) > 0) & (~df["is_correction"].astype(bool))),
        ("supersedure", lambda df: df["supersedes_ad_numbers"].fillna("").astype(str).str.len() > 0),
        ("long_document", lambda df: df["page_count"].astype(int) >= 8),
        ("simple_original", lambda df: (df["revision_number"].astype(int) == 0) & (df["page_count"].astype(int) <= 3)),
    ]
    for stratum, predicate in strata:
        candidates = eligible[~eligible["base_ad_number"].isin(used_families)]
        candidates = candidates[predicate(candidates)]
        if candidates.empty:
            raise ValueError(f"no eligible unseen candidate for {stratum}")
        row = candidates.sort_values(["seed_order", "ad_number", "file_instance_id"]).iloc[0]
        used_families.add(row["base_ad_number"])
        selections.append(
            {
                "stratum": stratum,
                "ad_number": row["ad_number"],
                "base_ad_number": row["base_ad_number"],
                "file_instance_id": row["file_instance_id"],
                "relative_path": row["relative_path"],
                "file_sha256": row["file_sha256"],
                "page_count": int(row["page_count"]),
                "revision_number": int(row["revision_number"]),
                "is_correction": bool(row["is_correction"]),
            }
        )

    unseen_dir.mkdir(parents=True, exist_ok=False)
    pd.DataFrame(selections).to_csv(unseen_dir / "selection.csv", index=False)
    write_json(unseen_dir / "selection.json", selections)
    write_json(
        unseen_dir / "selection_lock.json",
        {
            "name": "easa_airbus_ad_unseen_incoming_5_v1",
            "seed": seed,
            "count": 5,
            "distinct_family_count": len(used_families),
            "exclusion_policy": "exclude from extraction prompts, permanent indexes, and development testing until unseen-document evaluation",
            "corpus_manifest_sha256": sha256(corpus_manifest),
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    )
    (unseen_dir / "README.md").write_text(
        "# Unseen incoming AD set v1\n\n"
        "These five non-gold PDFs from distinct AD families are held out from the "
        "1,804-document development corpus. Do not use them in prompts, extraction "
        "development, or permanent retrieval indexes before temporary-upload testing. "
        "Their later confirmed permanent ingestion produces the final 1,809-record corpus.\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    gold_ids = freeze_split(args.gold_dir, args.content_dir, args.seed)
    if args.unseen_dir.exists() and any(args.unseen_dir.iterdir()):
        existing = pd.read_csv(args.unseen_dir / "selection.csv")
        if len(existing) != 5 or existing["base_ad_number"].nunique() != 5:
            raise ValueError("existing unseen set does not contain five distinct families")
        if set(existing["file_instance_id"].astype(str)) & gold_ids:
            raise ValueError("existing unseen set overlaps the 50-record gold release")
        unseen_status = "reused existing locked five-record unseen set"
    else:
        freeze_unseen(args.corpus_manifest, args.unseen_dir, gold_ids, args.seed)
        unseen_status = "created five-record unseen set"
    print(f"Frozen 30/20 split in {args.content_dir}; {unseen_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
