#!/usr/bin/env python3
"""Score extraction JSON records against the strictly validated Step 3 gold set.

The evaluator refuses to run when the gold directory fails the Step 3 strict
gate. Predictions may be incomplete JSON objects, which lets the same scorer
cover a narrow regex baseline and full schema-guided LLM output without giving
missing fields free credit.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
DEFAULT_GOLD_VALIDATOR = ROOT / "validate_step3_pilot.py"

SCALAR_FIELDS = (
    "/ad_identity/ad_number",
    "/ad_identity/base_ad_number",
    "/ad_identity/revision_number",
    "/ad_identity/is_emergency",
    "/ad_identity/is_correction",
    "/ad_identity/correction_date/value",
    "/ad_identity/design_approval_holder/value",
    "/ad_identity/supersedure_statement/state",
    "/ad_identity/supersedure_statement/value",
    "/publication/subject/value",
    "/publication/issue_date/value",
    "/publication/effective_date/value",
    "/publication/foreign_ad/value",
    "/unsafe_condition/state",
    "/classification/frequency",
    "/classification/emergency_status",
    "/classification/terminating_action_present",
    "/classification/table_or_appendix_present",
    "/classification/compliance_complexity",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gold_dir", type=Path)
    parser.add_argument("prediction_dir", type=Path)
    parser.add_argument("--method", required=True, help="regex, zero_shot, schema_guided, etc.")
    parser.add_argument(
        "--gold-validator", type=Path, default=DEFAULT_GOLD_VALIDATOR
    )
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "metrics"
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def pointer_get(document: Any, pointer: str, missing: Any = None) -> Any:
    current = document
    for raw in pointer.lstrip("/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            return missing
    return current


def normalize_scalar(value: Any) -> Any:
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip().casefold()
    return value


def token_counts(value: str | None) -> Counter[str]:
    return Counter(re.findall(r"[a-z0-9]+(?:[-/][a-z0-9]+)*", (value or "").casefold()))


def prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if tp + fp else 1.0 if fn == 0 else 0.0
    recall = tp / (tp + fn) if tp + fn else 1.0 if fp == 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def set_counts(gold: Iterable[Any], prediction: Iterable[Any]) -> tuple[int, int, int]:
    gold_set = {json.dumps(item, sort_keys=True, ensure_ascii=False) for item in gold}
    pred_set = {json.dumps(item, sort_keys=True, ensure_ascii=False) for item in prediction}
    return len(gold_set & pred_set), len(pred_set - gold_set), len(gold_set - pred_set)


def values(record: dict[str, Any], pointer: str) -> list[Any]:
    value = pointer_get(record, pointer, missing=[])
    return value if isinstance(value, list) else []


def extract_set(record: dict[str, Any], name: str) -> set[Any]:
    if name == "ata_chapters":
        return {
            normalize_scalar(item.get("code"))
            for item in values(record, "/publication/ata_chapters")
            if isinstance(item, dict) and item.get("code") is not None
        }
    if name == "manufacturers":
        return {
            normalize_scalar(item.get("normalized_name") or item.get("raw_name"))
            for item in values(record, "/publication/manufacturers")
            if isinstance(item, dict)
            and (item.get("normalized_name") or item.get("raw_name"))
        }
    if name == "models":
        return {
            normalize_scalar(item)
            for item in values(record, "/publication/type_model_designations")
        }
    if name == "tcds":
        return {
            normalize_scalar(item)
            for item in values(record, "/publication/tcds_numbers")
        }
    if name == "applicability_models":
        return {
            normalize_scalar(model)
            for group in values(record, "/applicability_groups")
            if isinstance(group, dict)
            for model in group.get("model_designations", [])
        }
    if name == "action_types":
        return {
            normalize_scalar(action)
            for requirement in values(record, "/requirements")
            if isinstance(requirement, dict)
            for action in requirement.get("action_types", [])
        }
    if name == "airbus_families":
        return {
            normalize_scalar(item)
            for item in values(record, "/classification/airbus_families")
        }
    if name == "publications":
        result = set()
        for item in values(record, "/referenced_publications"):
            if isinstance(item, dict):
                reference = item.get("normalized_reference") or item.get("raw_reference")
                if reference:
                    result.add(normalize_scalar(reference))
        return result
    if name == "relationships":
        return {
            (
                normalize_scalar(item.get("relationship_type")),
                normalize_scalar(item.get("target_ad_number")),
            )
            for item in values(record, "/relationships")
            if isinstance(item, dict)
        }
    raise KeyError(name)


SET_FIELDS = (
    "ata_chapters",
    "manufacturers",
    "models",
    "tcds",
    "applicability_models",
    "action_types",
    "airbus_families",
    "publications",
    "relationships",
)


def joined_text(record: dict[str, Any], name: str) -> str:
    if name == "unsafe_condition":
        unsafe = record.get("unsafe_condition") or {}
        pieces = [unsafe.get("raw_reason_text")]
        for key in (
            "observed_events_or_defects",
            "causes",
            "unsafe_conditions",
            "potential_consequences",
            "affected_components",
            "intended_risk_mitigation",
        ):
            pieces.extend(unsafe.get(key) or [])
        return " ".join(str(piece) for piece in pieces if piece)
    if name == "requirements":
        return " ".join(
            str(item.get("raw_action_text"))
            for item in values(record, "/requirements")
            if isinstance(item, dict) and item.get("raw_action_text")
        )
    if name == "compliance":
        return " ".join(
            str(rule.get("raw_text"))
            for item in values(record, "/requirements")
            if isinstance(item, dict)
            for rule in item.get("compliance_rules", [])
            if isinstance(rule, dict) and rule.get("raw_text")
        )
    if name == "applicability":
        return " ".join(
            str(item.get("raw_text"))
            for item in values(record, "/applicability_groups")
            if isinstance(item, dict) and item.get("raw_text")
        )
    raise KeyError(name)


TEXT_FIELDS = ("unsafe_condition", "requirements", "compliance", "applicability")


def token_f1(gold: str, prediction: str) -> tuple[int, int, int, float]:
    gold_counts = token_counts(gold)
    pred_counts = token_counts(prediction)
    shared = gold_counts & pred_counts
    tp = sum(shared.values())
    fp = sum((pred_counts - gold_counts).values())
    fn = sum((gold_counts - pred_counts).values())
    return tp, fp, fn, prf(tp, fp, fn)["f1"]


def index_records(directory: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    records: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in sorted(directory.glob("*.json")):
        value = load_json(path)
        if not isinstance(value, dict):
            continue
        source = value.get("source_document") or {}
        file_id = source.get("file_instance_id") or value.get("file_instance_id")
        if not file_id:
            raise ValueError(f"{path}: no file_instance_id")
        if file_id in records:
            raise ValueError(f"{directory}: duplicate file_instance_id {file_id}")
        records[file_id] = (path, value)
    return records


def validate_gold(gold_dir: Path, validator: Path, report: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(validator),
            str(gold_dir),
            "--report",
            str(report),
        ],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()
        raise ValueError(
            "strict gold validation failed; extraction scoring is blocked\n" + detail
        )


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    safe_method = re.sub(r"[^a-zA-Z0-9_.-]+", "_", args.method)
    gold_report = args.output_dir / f"{safe_method}.gold_validation.json"
    validate_gold(args.gold_dir, args.gold_validator, gold_report)

    gold = index_records(args.gold_dir)
    predictions = index_records(args.prediction_dir)
    if len(gold) != 30:
        raise ValueError(f"expected 30 validated gold records, found {len(gold)}")

    scalar_correct = Counter()
    scalar_total = Counter()
    set_totals = {name: [0, 0, 0] for name in SET_FIELDS}
    text_totals = {name: [0, 0, 0] for name in TEXT_FIELDS}
    per_record: list[dict[str, Any]] = []

    for file_id, (gold_path, gold_record) in sorted(gold.items()):
        prediction_item = predictions.get(file_id)
        prediction = prediction_item[1] if prediction_item else {}
        scalar_hits = 0
        for pointer in SCALAR_FIELDS:
            gold_value = normalize_scalar(pointer_get(gold_record, pointer, missing=None))
            pred_value = normalize_scalar(pointer_get(prediction, pointer, missing={"missing": True}))
            scalar_total[pointer] += 1
            if gold_value == pred_value:
                scalar_correct[pointer] += 1
                scalar_hits += 1

        set_f1_values = []
        for name in SET_FIELDS:
            tp, fp, fn = set_counts(
                extract_set(gold_record, name), extract_set(prediction, name)
            )
            set_totals[name][0] += tp
            set_totals[name][1] += fp
            set_totals[name][2] += fn
            set_f1_values.append(prf(tp, fp, fn)["f1"])

        text_f1_values = []
        for name in TEXT_FIELDS:
            tp, fp, fn, f1 = token_f1(
                joined_text(gold_record, name), joined_text(prediction, name)
            )
            text_totals[name][0] += tp
            text_totals[name][1] += fp
            text_totals[name][2] += fn
            text_f1_values.append(f1)

        per_record.append(
            {
                "ad_number": pointer_get(gold_record, "/ad_identity/ad_number"),
                "file_instance_id": file_id,
                "prediction_present": prediction_item is not None,
                "scalar_accuracy": scalar_hits / len(SCALAR_FIELDS),
                "mean_set_f1": sum(set_f1_values) / len(set_f1_values),
                "mean_text_token_f1": sum(text_f1_values) / len(text_f1_values),
            }
        )

    scalar_metrics = {
        pointer: {
            "correct": scalar_correct[pointer],
            "total": scalar_total[pointer],
            "accuracy": scalar_correct[pointer] / scalar_total[pointer],
        }
        for pointer in SCALAR_FIELDS
    }
    set_metrics = {
        name: {
            "tp": counts[0],
            "fp": counts[1],
            "fn": counts[2],
            **prf(*counts),
        }
        for name, counts in set_totals.items()
    }
    text_metrics = {
        name: {
            "token_tp": counts[0],
            "token_fp": counts[1],
            "token_fn": counts[2],
            **prf(*counts),
        }
        for name, counts in text_totals.items()
    }
    report = {
        "method": args.method,
        "gold_dir": str(args.gold_dir),
        "prediction_dir": str(args.prediction_dir),
        "gold_strict_validation": "pass",
        "gold_record_count": len(gold),
        "prediction_record_count": len(predictions),
        "matched_prediction_count": sum(
            1 for file_id in gold if file_id in predictions
        ),
        "unexpected_prediction_file_instance_ids": sorted(set(predictions) - set(gold)),
        "scalar_metrics": scalar_metrics,
        "set_metrics": set_metrics,
        "text_metrics": text_metrics,
        "macro_record_metrics": {
            "scalar_accuracy": sum(row["scalar_accuracy"] for row in per_record) / len(per_record),
            "mean_set_f1": sum(row["mean_set_f1"] for row in per_record) / len(per_record),
            "mean_text_token_f1": sum(row["mean_text_token_f1"] for row in per_record) / len(per_record),
        },
    }
    report_path = args.output_dir / f"{safe_method}.metrics.json"
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    csv_path = args.output_dir / f"{safe_method}.per_record.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_record[0]))
        writer.writeheader()
        writer.writerows(per_record)
    print(
        f"Scored {report['matched_prediction_count']}/30 predictions for {args.method}; "
        f"metrics={report_path}"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
