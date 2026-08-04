#!/usr/bin/env python3
"""Evaluate sparse extraction predictions against a selected content-gold split."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from full_corpus_pipeline.content_projection import validate_record


ROOT = Path(__file__).resolve().parents[1]
GOLD_DIR = ROOT / "evaluation_sets/easa_airbus_ad_content_gold_50_v2"
SCHEMA = json.loads((Path(__file__).with_name("content_record.schema.json")).read_text(encoding="utf-8"))
STRUCTURED_SECTIONS = {
    "ad_identity",
    "publication",
    "applicability",
    "referenced_publications",
    "supersedure",
}
RAW_DIFFICULT_SECTIONS = {
    "definitions",
    "reason",
    "required_actions",
    "remarks",
}


def normalize(value: Any) -> str:
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip().casefold()
    return json.dumps(value, ensure_ascii=False, sort_keys=True).casefold()


def flatten(value: Any, path: str = "") -> set[tuple[str, str]]:
    if isinstance(value, dict):
        return {item for key, child in value.items() for item in flatten(child, f"{path}/{key}")}
    if isinstance(value, list):
        # List order is not scored as a separate fact; item content and parent path are.
        return {item for child in value for item in flatten(child, f"{path}[]")}
    return {(path, normalize(value))}


def prf(predicted: set[Any], gold: set[Any]) -> dict[str, float]:
    true_positive = len(predicted & gold)
    precision = true_positive / len(predicted) if predicted else float(not gold)
    recall = true_positive / len(gold) if gold else float(not predicted)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions", type=Path, help="Directory of individual content JSON records")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=("development", "test"), default="test")
    args = parser.parse_args()
    split = json.loads((GOLD_DIR / "split_manifest.json").read_text(encoding="utf-8"))
    selected = [row for row in split if row["split"] == args.split]
    record_count = len(selected)
    rows = []
    section_scores: dict[str, list[float]] = defaultdict(list)
    raw_predicted_presence: set[tuple[str, str]] = set()
    raw_gold_presence: set[tuple[str, str]] = set()
    schema_valid = 0
    for item in selected:
        gold_path = GOLD_DIR / "records" / item["derived_filename"]
        prediction_path = args.predictions / item["derived_filename"]
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
        for section in RAW_DIFFICULT_SECTIONS:
            if section in gold:
                raw_gold_presence.add((item["ad_number"], section))
        if not prediction_path.exists():
            rows.append({"ad_number": item["ad_number"], "missing": True, "precision": 0.0, "recall": 0.0, "f1": 0.0, "exact_match": False})
            continue
        prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
        valid = not validate_record(prediction, SCHEMA)
        schema_valid += int(valid)
        structured_prediction = {
            key: value for key, value in prediction.items() if key in STRUCTURED_SECTIONS
        }
        structured_gold = {
            key: value for key, value in gold.items() if key in STRUCTURED_SECTIONS
        }
        score = prf(flatten(structured_prediction), flatten(structured_gold))
        exact = normalize(structured_prediction) == normalize(structured_gold)
        rows.append({"ad_number": item["ad_number"], "missing": False, "schema_valid": valid, **score, "exact_match": exact})
        for section in sorted(set(gold) | set(prediction)):
            section_scores[section].append(prf(flatten(prediction.get(section, {})), flatten(gold.get(section, {})))["f1"])
        for section in RAW_DIFFICULT_SECTIONS:
            if section in prediction:
                raw_predicted_presence.add((item["ad_number"], section))
    structured_scores = {
        key: values for key, values in section_scores.items() if key in STRUCTURED_SECTIONS
    }
    report = {
        "split": args.split,
        "record_count": record_count,
        "prediction_coverage": sum(not row["missing"] for row in rows) / record_count,
        "schema_valid_percentage": schema_valid / record_count,
        "field_precision": sum(row["precision"] for row in rows) / record_count,
        "field_recall": sum(row["recall"] for row in rows) / record_count,
        "field_f1": sum(row["f1"] for row in rows) / record_count,
        "normalized_exact_match": sum(row["exact_match"] for row in rows) / record_count,
        "core_field_macro_f1": sum(
            sum(values) / len(values) for values in structured_scores.values()
        ) / max(len(structured_scores), 1),
        "raw_section_presence": prf(raw_predicted_presence, raw_gold_presence),
        "raw_section_boundary_policy": (
            "score presence automatically; assess boundary completeness and source-text "
            "containment by PDF spot check, not semantic exact match"
        ),
        "section_f1": {key: sum(values) / len(values) for key, values in sorted(section_scores.items())},
        "records": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key not in {"records", "section_f1"}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
