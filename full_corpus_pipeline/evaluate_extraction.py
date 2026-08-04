#!/usr/bin/env python3
"""Evaluate deterministic extraction against the v3.1 content benchmark.

Primary metrics intentionally separate:
- stable structured metadata;
- reference/lifecycle identifiers; and
- raw-section preservation.

The gold projection stores reviewed semantic units for difficult sections, while
the live parser preserves complete PDF sections. Therefore raw section text is
not scored by exact semantic/string overlap with the projection.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from full_corpus_pipeline.content_projection import validate_record
from full_corpus_pipeline.local_extractor import _clean_layout_text


ROOT = Path(__file__).resolve().parents[1]
GOLD_DIR = ROOT / "evaluation_sets/easa_airbus_ad_content_gold_50_v2"
DEFAULT_SOURCE_TEXT = ROOT / "step3_pilot/source_metadata/corpus_extracted_text.parquet"
SCHEMA = json.loads(
    (Path(__file__).with_name("content_record.schema.json")).read_text(encoding="utf-8")
)

RAW_SECTION_NAMES = (
    "definitions",
    "reason",
    "required_actions",
    "referenced_publications_text",
    "remarks",
)

CONTAMINATION_PATTERNS: dict[str, re.Pattern[str]] = {
    "page_number": re.compile(r"\bPage\s+\d+\s+of\s+\d+\b", re.IGNORECASE),
    "te_cap_footer": re.compile(r"\bTE\.CAP\.\d+(?:-\d+)?\b", re.IGNORECASE),
    "repeated_ad_header": re.compile(
        r"\bEASA\s+AD\s+No\.?\s*:\s*(?:19|20)\d{2}-\d{4}(?:R\d+)?\b",
        re.IGNORECASE,
    ),
    "easa_copyright": re.compile(
        r"European\s+Union\s+Aviation\s+Safety\s+Agency", re.IGNORECASE
    ),
    "proprietary_footer": re.compile(
        r"Proprietary\s+document\.\s*Copies\s+are\s+not\s+controlled",
        re.IGNORECASE,
    ),
    "agency_footer": re.compile(
        r"An\s+agency\s+of\s+the\s+European\s+Union", re.IGNORECASE
    ),
    "status_watermark": re.compile(r"\b(?:SUPERSEDED|CANCELLED|CANCELED)\b"),
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def normalize_entity(value: Any) -> str:
    text = normalize_text(value)
    return re.sub(r"[.\s]+", " ", text).strip()


def normalize_identifier(value: Any) -> str:
    text = str(value or "").upper().replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", "", text).strip()


def normalize_date(value: Any) -> str:
    return str(value or "").strip()


Normalizer = Callable[[Any], str]


def get_path(record: dict[str, Any], *parts: str) -> Any:
    value: Any = record
    for part in parts:
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def scalar_values(
    record: dict[str, Any],
    path: tuple[str, ...],
    normalizer: Normalizer = normalize_text,
) -> set[str]:
    value = get_path(record, *path)
    normalized = normalizer(value)
    return {normalized} if normalized else set()


def list_values(
    record: dict[str, Any],
    path: tuple[str, ...],
    normalizer: Normalizer = normalize_text,
) -> set[str]:
    raw = get_path(record, *path)
    if not isinstance(raw, list):
        return set()
    return {normalized for item in raw if (normalized := normalizer(item))}


def nested_list_values(
    record: dict[str, Any],
    path: tuple[str, ...],
    key: str,
    normalizer: Normalizer = normalize_text,
) -> set[str]:
    raw = get_path(record, *path)
    if not isinstance(raw, list):
        return set()
    values = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        normalized = normalizer(item.get(key))
        if normalized:
            values.add(normalized)
    return values


def applicability_values(record: dict[str, Any], key: str) -> set[str]:
    values = set()
    for item in record.get("applicability", []) or []:
        if not isinstance(item, dict):
            continue
        for value in item.get(key, []) or []:
            normalized = (
                normalize_identifier(value) if key == "models" else normalize_text(value)
            )
            if normalized:
                values.add(normalized)
    return values


def ata_codes(record: dict[str, Any]) -> set[str]:
    return nested_list_values(
        record, ("publication", "ata_chapters"), "code", normalize_identifier
    )


def reference_numbers(record: dict[str, Any]) -> set[str]:
    return nested_list_values(
        record, ("referenced_publications",), "number", normalize_identifier
    )


def superseded_numbers(record: dict[str, Any]) -> set[str]:
    return list_values(
        record, ("supersedure", "superseded_ad_numbers"), normalize_identifier
    )


FieldExtractor = Callable[[dict[str, Any]], set[str]]


COMPARABLE_FIELDS: dict[str, FieldExtractor] = {
    "ad_number": lambda record: scalar_values(
        record, ("ad_identity", "ad_number"), normalize_identifier
    ),
    "authority": lambda record: scalar_values(record, ("ad_identity", "authority")),
    "document_type": lambda record: scalar_values(
        record, ("ad_identity", "document_type")
    ),
    "revision": lambda record: scalar_values(
        record, ("ad_identity", "revision"), normalize_identifier
    ),
    "emergency": lambda record: (
        {"true"} if get_path(record, "ad_identity", "emergency") is True else set()
    ),
    "correction_date": lambda record: scalar_values(
        record, ("ad_identity", "correction_date"), normalize_date
    ),
    "design_approval_holder": lambda record: scalar_values(
        record, ("ad_identity", "design_approval_holder"), normalize_entity
    ),
    "subject": lambda record: scalar_values(record, ("publication", "subject")),
    "issue_date": lambda record: scalar_values(
        record, ("publication", "issue_date"), normalize_date
    ),
    "effective_date": lambda record: scalar_values(
        record, ("publication", "effective_date"), normalize_date
    ),
    "ata_codes": ata_codes,
    "manufacturers": lambda record: list_values(
        record, ("publication", "manufacturers"), normalize_entity
    ),
    "type_model_designations": lambda record: list_values(
        record, ("publication", "type_model_designations"), normalize_identifier
    ),
    "tcds_numbers": lambda record: list_values(
        record, ("publication", "tcds_numbers"), normalize_identifier
    ),
    "foreign_ad": lambda record: scalar_values(record, ("publication", "foreign_ad")),
    "applicability_models": lambda record: applicability_values(record, "models"),
    "applicability_families": lambda record: applicability_values(
        record, "aircraft_families"
    ),
    "reference_numbers": reference_numbers,
    "superseded_ad_numbers": superseded_numbers,
}

STABLE_METADATA_FIELDS = (
    "ad_number",
    "authority",
    "document_type",
    "revision",
    "emergency",
    "correction_date",
    "design_approval_holder",
    "subject",
    "issue_date",
    "effective_date",
    "ata_codes",
    "manufacturers",
    "type_model_designations",
    "tcds_numbers",
    "foreign_ad",
    "applicability_models",
    "applicability_families",
)

REFERENCE_LIFECYCLE_FIELDS = (
    "reference_numbers",
    "superseded_ad_numbers",
)


def prf(predicted: set[Any], gold: set[Any]) -> dict[str, float | int]:
    true_positive = len(predicted & gold)
    precision = true_positive / len(predicted) if predicted else float(not gold)
    recall = true_positive / len(gold) if gold else float(not predicted)
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positive": true_positive,
        "predicted_count": len(predicted),
        "gold_count": len(gold),
    }


def macro_f1(field_metrics: dict[str, dict[str, Any]], names: tuple[str, ...]) -> float:
    values = [field_metrics[name]["f1"] for name in names if name in field_metrics]
    return sum(values) / len(values) if values else 0.0


def raw_section_texts(record: dict[str, Any], section: str) -> list[str]:
    if section == "required_actions":
        return [
            str(item["action"])
            for item in record.get("required_actions", []) or []
            if isinstance(item, dict) and item.get("action")
        ]
    value = record.get(section)
    if isinstance(value, dict) and value.get("text"):
        return [str(value["text"])]
    return []


def contamination(texts: list[str]) -> list[str]:
    joined = " ".join(texts)
    return sorted(
        name for name, pattern in CONTAMINATION_PATTERNS.items() if pattern.search(joined)
    )


def source_contains(raw_texts: list[str], source_text: str) -> bool | None:
    if not raw_texts:
        return None
    cleaned_source = normalize_text(_clean_layout_text(source_text))
    if not cleaned_source:
        return None
    return all(normalize_text(value) in cleaned_source for value in raw_texts)


def load_source_text(path: Path | None, selected_ids: set[str]) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    frame = pd.read_parquet(path, columns=["file_instance_id", "text"])
    frame["file_instance_id"] = frame["file_instance_id"].astype(str)
    frame = frame[frame["file_instance_id"].isin(selected_ids)]
    return {
        str(row["file_instance_id"]): str(row["text"])
        for row in frame.to_dict(orient="records")
    }


def legacy_projection_overlap(
    prediction: dict[str, Any], gold: dict[str, Any]
) -> dict[str, float]:
    """Retain the old set-overlap metric only as a secondary diagnostic."""
    structured_sections = {
        "ad_identity",
        "publication",
        "applicability",
        "referenced_publications",
        "supersedure",
    }

    def flatten(value: Any, path: str = "") -> set[tuple[str, str]]:
        if isinstance(value, dict):
            return {
                item
                for key, child in value.items()
                for item in flatten(child, f"{path}/{key}")
            }
        if isinstance(value, list):
            return {
                item
                for child in value
                for item in flatten(child, f"{path}[]")
            }
        return {(path, normalize_text(value))}

    predicted = {
        key: value for key, value in prediction.items() if key in structured_sections
    }
    expected = {
        key: value for key, value in gold.items() if key in structured_sections
    }
    score = prf(flatten(predicted), flatten(expected))
    return {
        "precision": float(score["precision"]),
        "recall": float(score["recall"]),
        "f1": float(score["f1"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "predictions", type=Path, help="Directory of individual content JSON records"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=("development", "test"), default="test")
    parser.add_argument(
        "--source-text-parquet",
        type=Path,
        default=DEFAULT_SOURCE_TEXT,
        help=(
            "Optional document-text cache used only for raw-section source-containment "
            "and contamination checks."
        ),
    )
    args = parser.parse_args()

    split = json.loads(
        (GOLD_DIR / "split_manifest.json").read_text(encoding="utf-8")
    )
    selected = [row for row in split if row["split"] == args.split]
    record_count = len(selected)
    selected_ids = {str(row["file_instance_id"]) for row in selected}
    source_text_by_id = load_source_text(args.source_text_parquet, selected_ids)

    schema_valid = 0
    predicted_record_count = 0
    field_predicted_facts: dict[str, set[tuple[str, str]]] = defaultdict(set)
    field_gold_facts: dict[str, set[tuple[str, str]]] = defaultdict(set)
    field_record_matches: dict[str, int] = defaultdict(int)
    field_record_totals: dict[str, int] = defaultdict(int)

    raw_reference_expected: dict[str, set[str]] = defaultdict(set)
    raw_prediction_present: dict[str, set[str]] = defaultdict(set)
    raw_contamination_counts: dict[str, int] = defaultdict(int)
    raw_source_checks = 0
    raw_source_passes = 0

    legacy_rows: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

    for item in selected:
        ad_number = str(item["ad_number"])
        file_id = str(item["file_instance_id"])
        gold_path = GOLD_DIR / "records" / item["derived_filename"]
        prediction_path = args.predictions / item["derived_filename"]
        gold = json.loads(gold_path.read_text(encoding="utf-8"))

        for section in RAW_SECTION_NAMES:
            if raw_section_texts(gold, section):
                raw_reference_expected[section].add(ad_number)

        if not prediction_path.exists():
            rows.append(
                {
                    "ad_number": ad_number,
                    "file_instance_id": file_id,
                    "missing": True,
                    "schema_valid": False,
                    "field_mismatches": [
                        {"field": name, "gold": sorted(extractor(gold)), "predicted": []}
                        for name, extractor in COMPARABLE_FIELDS.items()
                        if extractor(gold)
                    ],
                }
            )
            for name, extractor in COMPARABLE_FIELDS.items():
                gold_values = extractor(gold)
                field_record_totals[name] += 1
                for value in gold_values:
                    field_gold_facts[name].add((ad_number, value))
            continue

        predicted_record_count += 1
        prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
        valid = not validate_record(prediction, SCHEMA)
        schema_valid += int(valid)

        mismatches = []
        for name, extractor in COMPARABLE_FIELDS.items():
            predicted_values = extractor(prediction)
            gold_values = extractor(gold)
            field_record_totals[name] += 1
            if predicted_values == gold_values:
                field_record_matches[name] += 1
            else:
                mismatches.append(
                    {
                        "field": name,
                        "gold": sorted(gold_values),
                        "predicted": sorted(predicted_values),
                    }
                )
            for value in predicted_values:
                field_predicted_facts[name].add((ad_number, value))
            for value in gold_values:
                field_gold_facts[name].add((ad_number, value))

        source_text = source_text_by_id.get(file_id)
        raw_details = {}
        for section in RAW_SECTION_NAMES:
            predicted_texts = raw_section_texts(prediction, section)
            expected_texts = raw_section_texts(gold, section)
            if predicted_texts:
                raw_prediction_present[section].add(ad_number)
            noise = contamination(predicted_texts)
            raw_contamination_counts[section] += int(bool(noise))
            contained: bool | None = None
            if source_text is not None and predicted_texts:
                contained = source_contains(predicted_texts, source_text)
                raw_source_checks += 1
                raw_source_passes += int(contained is True)
            raw_details[section] = {
                "reference_expected": bool(expected_texts),
                "prediction_present": bool(predicted_texts),
                "source_contained": contained,
                "contamination": noise,
            }

        legacy = legacy_projection_overlap(prediction, gold)
        legacy_rows.append({"ad_number": ad_number, **legacy})
        rows.append(
            {
                "ad_number": ad_number,
                "file_instance_id": file_id,
                "missing": False,
                "schema_valid": valid,
                "field_mismatches": mismatches,
                "raw_sections": raw_details,
                "legacy_projection_overlap": legacy,
            }
        )

    field_metrics = {}
    for name in COMPARABLE_FIELDS:
        score = prf(field_predicted_facts[name], field_gold_facts[name])
        field_metrics[name] = {
            **score,
            "record_exact_accuracy": (
                field_record_matches[name] / field_record_totals[name]
                if field_record_totals[name]
                else 0.0
            ),
        }

    raw_presence = {}
    for section in RAW_SECTION_NAMES:
        predicted = raw_prediction_present[section]
        expected = raw_reference_expected[section]
        raw_presence[section] = {
            **prf(
                {(ad, section) for ad in predicted},
                {(ad, section) for ad in expected},
            ),
            "missing_expected_records": sorted(expected - predicted),
            "extra_prediction_records": sorted(predicted - expected),
            "contaminated_record_count": raw_contamination_counts[section],
        }

    legacy_mean = {
        metric: (
            sum(row[metric] for row in legacy_rows) / record_count
            if record_count
            else 0.0
        )
        for metric in ("precision", "recall", "f1")
    }

    report = {
        "evaluation_version": "content-eval-v3.1.1",
        "split": args.split,
        "record_count": record_count,
        "prediction_coverage": (
            predicted_record_count / record_count if record_count else 0.0
        ),
        "schema_valid_percentage": (
            schema_valid / record_count if record_count else 0.0
        ),
        "stable_metadata_macro_f1": macro_f1(
            field_metrics, STABLE_METADATA_FIELDS
        ),
        "reference_lifecycle_macro_f1": macro_f1(
            field_metrics, REFERENCE_LIFECYCLE_FIELDS
        ),
        "reference_number_f1": field_metrics["reference_numbers"]["f1"],
        "superseded_ad_number_f1": field_metrics["superseded_ad_numbers"]["f1"],
        "field_metrics": field_metrics,
        "raw_section_reference_presence": raw_presence,
        "raw_section_source_containment": {
            "available": bool(source_text_by_id),
            "checked_section_count": raw_source_checks,
            "contained_section_count": raw_source_passes,
            "accuracy": (
                raw_source_passes / raw_source_checks if raw_source_checks else None
            ),
            "source_text_parquet": (
                str(args.source_text_parquet) if args.source_text_parquet else None
            ),
        },
        "raw_section_policy": (
            "Difficult sections are evaluated for expected presence, source-text "
            "containment, and page-furniture contamination. Exact string/semantic "
            "overlap with the reviewed gold projection is not a primary metric because "
            "the gold projection stores semantic units while the live parser preserves "
            "complete source sections."
        ),
        "legacy_projection_overlap": {
            **legacy_mean,
            "primary_metric": False,
            "note": (
                "Retained only for continuity with content-eval v1. It penalizes "
                "intentional representation differences and must not be reported as "
                "the primary v3.1 extraction accuracy."
            ),
        },
        "records": rows,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    console = {
        key: value
        for key, value in report.items()
        if key not in {"records", "field_metrics", "raw_section_reference_presence"}
    }
    console["field_metrics"] = {
        name: {
            "precision": round(float(values["precision"]), 4),
            "recall": round(float(values["recall"]), 4),
            "f1": round(float(values["f1"]), 4),
            "record_exact_accuracy": round(float(values["record_exact_accuracy"]), 4),
        }
        for name, values in field_metrics.items()
    }
    console["raw_section_reference_presence"] = raw_presence
    print(json.dumps(console, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
