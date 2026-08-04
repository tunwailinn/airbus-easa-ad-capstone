#!/usr/bin/env python3
"""Add/rebuild projection lineage for an existing cleaned dataset."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from full_corpus_pipeline.content_projection import projection_lineage


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evaluation_sets/easa_airbus_ad_content_gold_50_v2"


def main() -> int:
    manifest = pd.read_parquet(DATASET / "projection_manifest.parquet")
    rows = []
    for item in manifest.to_dict(orient="records"):
        record = json.loads((DATASET / "records" / item["derived_filename"]).read_text(encoding="utf-8"))
        rows.append(projection_lineage(item["derived_filename"], item["source_gold_filename"], record))
    path = DATASET / "projection_lineage.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote retained-value lineage for {len(rows)} projected records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
