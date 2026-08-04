#!/usr/bin/env python3
"""Evaluate deterministic extraction against the v3.1 content benchmark.

Primary scoring separates stable structured metadata, secondary catalogue
normalization, reference/lifecycle identifiers, and source-driven raw-section
preservation. Complete raw PDF sections are not exact-string scored against the
semantic gold projection.
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
SCHEMA = json.loads((Path(__file__).with_name("content_record.schema.json")).read_text(encoding="utf-8"))

KNOWN_CONTAMINATED_TEST_ADS = {
    "2024-0038": (
        "This source PDF was explicitly used to diagnose and tune the local parser; "
        "it is excluded from clean locked-test reporting."
    )
}

AIRBUS_SCOPE_HOLDER_ALIASES = {
    "airbus",
    "airbus sas",
    "airbus s a s",
    "airbus industrie",
    "airbus formerly airbus industrie",
    "airbus sas formerly airbus industrie",
    "airbus s a s formerly airbus industrie",
}

RAW_SECTION_NAMES = (
    "definitions",
    "reason",
    "required_actions",
    "referenced_publications_text",
    "remarks",
)

RAW_SOURCE_HEADINGS = {
    "definitions": re.compile(r"(?:^|\n)\s*Definitions?\s*:?[ \t]*(?:\n|\S)", re.IGNORECASE),
    "reason": re.compile(r"(?:^|\n)\s*Reas\w*n\s*:?[ \t]*(?:\n|\S)", re.IGNORECASE),
    "required_actions": re.compile(
        r"(?:^|\n)\s*(?:Required\s+Action(?:s|\(s\))?"
        r"(?:\s+and\s+Compliance\s+Time(?:s|\(s\))?)?|Compliance)\s*:?[ \t]*(?:\n|\S)",
        re.IGNORECASE,
    ),
    "referenced_publications_text": re.compile(
        r"(?:^|\n)\s*(?:Ref\.?\s+Publications?|Referenced\s+Publications?)\s*:?[ \t]*(?:\n|\S)",
        re.IGNORECASE,
    ),
    "remarks": re.compile(r"(?:^|\n)\s*Remarks?\s*:?[ \t]*(?:\n|\S)", re.IGNORECASE),
}

CONTAMINATION_PATTERNS: dict[str, re.Pattern[str]] = {
    "page_number": re.compile(
        r"(?:\bEASA\s+Form\s+\d+\s+Page\s+\d+\s*/\s*\d+\b|"
        r"\bPage\s+\d+\s*(?:of|/)\s*\d+\b)",
        re.IGNORECASE,
    ),
    "te_cap_footer": re.compile(r"\bTE\.CAP\.\d+(?:-\d+)?\b", re.IGNORECASE),
    "repeated_ad_header": re.compile(
        r"\bEASA\s+AD\s+No\.?\s*:?[ \t]*(?:19|20)\d{2}-\d{4}(?:R\d+)?\b",
        re.IGNORECASE,
    ),
    "easa_copyright": re.compile(r"European\s+Union\s+Aviation\s+Safety\s+Agency", re.IGNORECASE),
    "proprietary_footer": re.compile(r"Proprietary\s+document\.\s*Copies\s+are\s+not\s+controlled", re.IGNORECASE),
    "agency_footer": re.compile(r"An\s+agency\s+of\s+the\s+European\s+Union", re.IGNORECASE),
    "status_watermark": re.compile(r"\b(?:SUPERSEDED|CANCELLED|CANCELED)\b"),
}

MODEL_TOKEN_RE = re.compile(
    r"\b(?:A300(?:\s*[BCF]\d)?(?:\s*-\s*\d{2,4}[A-Z]*)?|"
    r"A310(?:\s*-\s*\d{2,4}[A-Z]*)?|"
    r"A(?:318|319|320|321|330|340|350|380)(?:\s*-\s*\d{2,4}[A-Z]*)?)\b",
    re.IGNORECASE,
)
EASA_TCDS_RE = re.compile(r"\bEASA\s*\.?\s*A\s*\.\s*\d{3}\b", re.IGNORECASE)
FRANCE_TCDS_RE = re.compile(r"\bFrance\s*(?:N[°ºo]\.?|No\.?)\s*\d+\b", re.IGNORECASE)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def normalize_entity(value: Any) -> str:
    text = normalize_text(value)
    text = re.sub(r"^manufacturer(?:\(s\))?\s*:\s*", "", text)
    return re.sub(r"[.\s]+", " ", text).strip()


def normalize_holder_scope(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", normalize_text(value)).strip()


def _holder_looks_malformed(holder: str) -> bool:
    if not holder:
        return True
    if len(holder) > 180:
        return True
    markers = (
        "type model",
        "type designation",
        "model designation",
        "applicability",
        "aeroplanes tcds",
        "aircraft tcds",
        " reason ",
    )
    padded = f" {holder} "
    return any(marker in padded for marker in markers)


def benchmark_scope_status(record: dict[str, Any]) -> tuple[str, str]:
    """Return (eligible|excluded|unknown, normalized holder) for project scope.

    Only reviewed Airbus aliases are automatically eligible. Known external
    organizations are excluded. Missing, malformed, or unfamiliar holder names
    remain unknown so parser/governance uncertainty cannot silently shrink the
    Airbus S.A.S. corpus.
    """
    raw = get_path(record, "ad_identity", "design_approval_holder")
    holder = normalize_holder_scope(raw)
    if not holder:
        return "unknown", ""
    if holder in AIRBUS_SCOPE_HOLDER_ALIASES:
        return "eligible", holder

    known_external = (
        "lufthansa technik",
        "airbus defence",
        "elbe flugzeugwerke",
        "fokker services",
        "short brothers",
        "jet aviation",
        "societe air france",
    )
    if any(marker in holder for marker in known_external):
        return "excluded", holder
    if _holder_looks_malformed(holder):
        return "unknown", holder
    return "unknown", holder


def normalize_document_type(value: Any) -> str:
    text = normalize_text(value).replace("_", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if "cancellation" in text and "notice" in text:
        return "cancellation notice"
    if text in {"airworthiness directive", "ad"}:
        return "airworthiness directive"
    return text


def normalize_subject(value: Any) -> str:
    text = normalize_text(value)
    text = re.sub(r"^ata\s+\d{2}(?:\s*[,/&]\s*\d{2})*\s*[-–—:]?\s*", "", text, flags=re.IGNORECASE)
    return text


def normalize_foreign_ad(value: Any) -> str:
    text = normalize_text(value)
    text = re.sub(r"^foreign\s+ad\s*:\s*", "", text)
    return "not applicable" if text in {"none", "n/a", "not applicable"} else text


def normalize_identifier(value: Any) -> str:
    text = str(value or "").upper().replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", "", text).strip()


def normalize_date(value: Any) -> str:
    return str(value or "").strip()

Normalizer = Callable[[Any], str]
FieldExtractor = Callable[[dict[str, Any]], set[str]]


def get_path(record: dict[str, Any], *parts: str) -> Any:
    value: Any = record
    for part in parts:
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def scalar_values(record: dict[str, Any], path: tuple[str, ...], normalizer: Normalizer = normalize_text) -> set[str]:
    value = normalizer(get_path(record, *path))
    return {value} if value else set()


def list_values(record: dict[str, Any], path: tuple[str, ...], normalizer: Normalizer = normalize_text) -> set[str]:
    raw = get_path(record, *path)
    if not isinstance(raw, list):
        return set()
    return {value for item in raw if (value := normalizer(item))}


def nested_list_values(record: dict[str, Any], path: tuple[str, ...], key: str, normalizer: Normalizer = normalize_text) -> set[str]:
    raw = get_path(record, *path)
    if not isinstance(raw, list):
        return set()
    values = set()
    for item in raw:
        if isinstance(item, dict) and (value := normalizer(item.get(key))):
            values.add(value)
    return values


def model_tokens(values: list[Any]) -> set[str]:
    result = set()
    for raw in values:
        text = str(raw or "")
        matches = list(MODEL_TOKEN_RE.finditer(text))
        for match in matches:
            following = text[match.end() : match.end() + 8]
            if re.match(r"\s*-[A-Z0-9]", following, re.IGNORECASE):
                continue
            result.add(normalize_identifier(match.group(0)))
        if not matches and (value := normalize_identifier(text)):
            result.add(value)
    return result


def publication_models(record: dict[str, Any]) -> set[str]:
    raw = get_path(record, "publication", "type_model_designations")
    return model_tokens(raw if isinstance(raw, list) else [])


def tcds_identifiers(record: dict[str, Any]) -> set[str]:
    raw = get_path(record, "publication", "tcds_numbers")
    if not isinstance(raw, list):
        return set()
    values = set()
    for item in raw:
        text = str(item)
        matches = list(EASA_TCDS_RE.finditer(text)) + list(FRANCE_TCDS_RE.finditer(text))
        if matches:
            values.update(normalize_identifier(match.group(0)) for match in matches)
        elif (value := normalize_identifier(item)):
            values.add(value)
    return values


def applicability_values(record: dict[str, Any], key: str) -> set[str]:
    values = []
    for item in record.get("applicability", []) or []:
        if isinstance(item, dict):
            values.extend(item.get(key, []) or [])
    if key == "models":
        return model_tokens(values)
    return {value for item in values if (value := normalize_text(item))}


def ata_codes(record: dict[str, Any]) -> set[str]:
    return nested_list_values(record, ("publication", "ata_chapters"), "code", normalize_identifier)


def reference_numbers(record: dict[str, Any]) -> set[str]:
    return nested_list_values(record, ("referenced_publications",), "number", normalize_identifier)


def superseded_numbers(record: dict[str, Any]) -> set[str]:
    return list_values(record, ("supersedure", "superseded_ad_numbers"), normalize_identifier)

COMPARABLE_FIELDS: dict[str, FieldExtractor] = {
    "ad_number": lambda r: scalar_values(r, ("ad_identity", "ad_number"), normalize_identifier),
    "authority": lambda r: scalar_values(r, ("ad_identity", "authority")),
    "document_type": lambda r: scalar_values(r, ("ad_identity", "document_type"), normalize_document_type),
    "revision": lambda r: scalar_values(r, ("ad_identity", "revision"), normalize_identifier),
    "emergency": lambda r: ({"true"} if get_path(r, "ad_identity", "emergency") is True else set()),
    "correction_date": lambda r: scalar_values(r, ("ad_identity", "correction_date"), normalize_date),
    "design_approval_holder": lambda r: scalar_values(r, ("ad_identity", "design_approval_holder"), normalize_entity),
    "subject": lambda r: scalar_values(r, ("publication", "subject"), normalize_subject),
    "issue_date": lambda r: scalar_values(r, ("publication", "issue_date"), normalize_date),
    "effective_date": lambda r: scalar_values(r, ("publication", "effective_date"), normalize_date),
    "ata_codes": ata_codes,
    "manufacturers": lambda r: list_values(r, ("publication", "manufacturers"), normalize_entity),
    "publication_model_identifiers": publication_models,
    "easa_tcds_identifiers": tcds_identifiers,
    "foreign_ad": lambda r: scalar_values(r, ("publication", "foreign_ad"), normalize_foreign_ad),
    "applicability_models": lambda r: applicability_values(r, "models"),
    "applicability_families": lambda r: applicability_values(r, "aircraft_families"),
    "reference_numbers": reference_numbers,
    "superseded_ad_numbers": superseded_numbers,
}

STABLE_METADATA_FIELDS = (
    "ad_number", "authority", "document_type", "revision", "emergency", "correction_date",
    "design_approval_holder", "subject", "issue_date", "effective_date", "ata_codes",
    "manufacturers", "easa_tcds_identifiers", "foreign_ad", "applicability_models",
)
SECONDARY_TAXONOMY_FIELDS = ("publication_model_identifiers", "applicability_families")
REFERENCE_LIFECYCLE_FIELDS = ("reference_numbers", "superseded_ad_numbers")


def prf(predicted: set[Any], gold: set[Any]) -> dict[str, float | int]:
    tp = len(predicted & gold)
    precision = tp / len(predicted) if predicted else float(not gold)
    recall = tp / len(gold) if gold else float(not predicted)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "true_positive": tp, "predicted_count": len(predicted), "gold_count": len(gold)}


def macro_f1(metrics: dict[str, dict[str, Any]], names: tuple[str, ...]) -> float:
    values = [float(metrics[name]["f1"]) for name in names]
    return sum(values) / len(values) if values else 0.0


def raw_section_texts(record: dict[str, Any], section: str) -> list[str]:
    if section == "required_actions":
        return [str(item["action"]) for item in record.get("required_actions", []) or [] if isinstance(item, dict) and item.get("action")]
    value = record.get(section)
    return [str(value["text"])] if isinstance(value, dict) and value.get("text") else []


def contamination(texts: list[str]) -> list[str]:
    joined = " ".join(texts)
    return sorted(name for name, pattern in CONTAMINATION_PATTERNS.items() if pattern.search(joined))


def source_contains(raw_texts: list[str], source_text: str) -> bool | None:
    if not raw_texts:
        return None
    cleaned = normalize_text(_clean_layout_text(source_text))
    if not cleaned:
        return None
    return all(normalize_text(value) in cleaned for value in raw_texts)


def source_has_section(source_text: str, section: str) -> bool:
    if section not in RAW_SOURCE_HEADINGS:
        raise KeyError(section)
    normalized = source_text.replace("\r\n", "\n").replace("\r", "\n")
    return bool(RAW_SOURCE_HEADINGS[section].search(normalized))


def load_source_text(path: Path | None, ids: set[str]) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    frame = pd.read_parquet(path, columns=["file_instance_id", "text"])
    frame["file_instance_id"] = frame["file_instance_id"].astype(str)
    frame = frame[frame["file_instance_id"].isin(ids)]
    return {str(row["file_instance_id"]): str(row["text"]) for row in frame.to_dict(orient="records")}


def legacy_projection_overlap(prediction: dict[str, Any], gold: dict[str, Any]) -> dict[str, float]:
    structured = {"ad_identity", "publication", "applicability", "referenced_publications", "supersedure"}
    def flatten(value: Any, path: str = "") -> set[tuple[str, str]]:
        if isinstance(value, dict):
            return {item for key, child in value.items() for item in flatten(child, f"{path}/{key}")}
        if isinstance(value, list):
            return {item for child in value for item in flatten(child, f"{path}[]")}
        return {(path, normalize_text(value))}
    score = prf(flatten({k: v for k, v in prediction.items() if k in structured}), flatten({k: v for k, v in gold.items() if k in structured}))
    return {name: float(score[name]) for name in ("precision", "recall", "f1")}


def load_gold(item: dict[str, Any]) -> dict[str, Any]:
    return json.loads((GOLD_DIR / "records" / item["derived_filename"]).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions", type=Path, help="Directory of individual content JSON records")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=("development", "test"), default="test")
    parser.add_argument("--include-scope-excluded", action="store_true", help="Diagnostic only: include excluded/unknown scope cases.")
    parser.add_argument("--include-contaminated", action="store_true")
    parser.add_argument("--source-text-parquet", type=Path, default=DEFAULT_SOURCE_TEXT)
    args = parser.parse_args()

    split = json.loads((GOLD_DIR / "split_manifest.json").read_text(encoding="utf-8"))
    nominal = [row for row in split if row["split"] == args.split]

    scope_exclusions, scope_unknown, selected = [], [], []
    for row in nominal:
        gold = load_gold(row)
        status, holder = benchmark_scope_status(gold)
        if status == "excluded":
            scope_exclusions.append({"ad_number": str(row["ad_number"]), "design_approval_holder": holder, "reason": "Design Approval Holder is outside the project's Airbus S.A.S. scope; immutable gold is retained but excluded from primary scoring."})
            if not args.include_scope_excluded:
                continue
        elif status == "unknown":
            scope_unknown.append({"ad_number": str(row["ad_number"]), "design_approval_holder": holder or None, "reason": "Reviewed holder is missing, malformed, or not yet classified as an accepted Airbus S.A.S. alias; excluded from primary scoring pending scope review."})
            if not args.include_scope_excluded:
                continue
        selected.append(row)

    contamination_exclusions = []
    if args.split == "test" and not args.include_contaminated:
        contamination_exclusions = [{"ad_number": str(row["ad_number"]), "reason": KNOWN_CONTAMINATED_TEST_ADS[str(row["ad_number"])]} for row in selected if str(row["ad_number"]) in KNOWN_CONTAMINATED_TEST_ADS]
        selected = [row for row in selected if str(row["ad_number"]) not in KNOWN_CONTAMINATED_TEST_ADS]

    count = len(selected)
    ids = {str(row["file_instance_id"]) for row in selected}
    source_by_id = load_source_text(args.source_text_parquet, ids)

    schema_valid = predicted_count = 0
    predicted_facts: dict[str, set[tuple[str, str]]] = defaultdict(set)
    gold_facts: dict[str, set[tuple[str, str]]] = defaultdict(set)
    record_matches: dict[str, int] = defaultdict(int)
    record_totals: dict[str, int] = defaultdict(int)
    raw_expected: dict[str, set[str]] = defaultdict(set)
    raw_present: dict[str, set[str]] = defaultdict(set)
    raw_contamination: dict[str, int] = defaultdict(int)
    raw_expectation_basis: dict[str, str] = {}
    source_checks = source_passes = 0
    rows, legacy_rows = [], []

    for item in selected:
        ad = str(item["ad_number"])
        file_id = str(item["file_instance_id"])
        gold = load_gold(item)
        source = source_by_id.get(file_id)
        path = args.predictions / item["derived_filename"]

        expected_by_section: dict[str, bool | None] = {}
        for section in RAW_SECTION_NAMES:
            if source is not None:
                expected_by_section[section] = source_has_section(source, section)
                raw_expectation_basis[section] = "source_text_heading"
            elif section == "referenced_publications_text":
                expected_by_section[section] = None
                raw_expectation_basis[section] = "unscorable_without_source_text"
            else:
                expected_by_section[section] = bool(raw_section_texts(gold, section))
                raw_expectation_basis[section] = "gold_projection_fallback"
            if expected_by_section[section] is True:
                raw_expected[section].add(ad)

        if not path.exists():
            for name, extractor in COMPARABLE_FIELDS.items():
                record_totals[name] += 1
                gold_facts[name].update((ad, value) for value in extractor(gold))
            rows.append({"ad_number": ad, "file_instance_id": file_id, "missing": True, "schema_valid": False})
            continue

        predicted_count += 1
        prediction = json.loads(path.read_text(encoding="utf-8"))
        valid = not validate_record(prediction, SCHEMA)
        schema_valid += int(valid)
        mismatches = []
        for name, extractor in COMPARABLE_FIELDS.items():
            pv, gv = extractor(prediction), extractor(gold)
            record_totals[name] += 1
            record_matches[name] += int(pv == gv)
            if pv != gv:
                mismatches.append({"field": name, "gold": sorted(gv), "predicted": sorted(pv)})
            predicted_facts[name].update((ad, value) for value in pv)
            gold_facts[name].update((ad, value) for value in gv)

        raw_detail = {}
        for section in RAW_SECTION_NAMES:
            texts = raw_section_texts(prediction, section)
            expected = expected_by_section[section]
            if texts and expected is not None:
                raw_present[section].add(ad)
            noise = contamination(texts)
            raw_contamination[section] += int(bool(noise))
            contained = None
            if source is not None and texts:
                contained = source_contains(texts, source)
                source_checks += 1
                source_passes += int(contained is True)
            raw_detail[section] = {
                "reference_expected": expected,
                "expectation_basis": raw_expectation_basis[section],
                "prediction_present": bool(texts),
                "source_contained": contained,
                "contamination": noise,
            }

        legacy = legacy_projection_overlap(prediction, gold)
        legacy_rows.append(legacy)
        rows.append({"ad_number": ad, "file_instance_id": file_id, "missing": False, "schema_valid": valid, "field_mismatches": mismatches, "raw_sections": raw_detail, "legacy_projection_overlap": legacy})

    field_metrics = {}
    for name in COMPARABLE_FIELDS:
        score = prf(predicted_facts[name], gold_facts[name])
        field_metrics[name] = {**score, "record_exact_accuracy": record_matches[name] / record_totals[name] if record_totals[name] else 0.0}

    raw_presence = {}
    for section in RAW_SECTION_NAMES:
        if raw_expectation_basis.get(section) == "unscorable_without_source_text":
            raw_presence[section] = {"scorable": False, "reason": "No equivalent raw gold field and source-text cache unavailable.", "contaminated_record_count": raw_contamination[section]}
            continue
        predicted, expected = raw_present[section], raw_expected[section]
        raw_presence[section] = {
            "scorable": True,
            "expectation_basis": raw_expectation_basis.get(section),
            **prf({(ad, section) for ad in predicted}, {(ad, section) for ad in expected}),
            "missing_expected_records": sorted(expected - predicted),
            "extra_prediction_records": sorted(predicted - expected),
            "contaminated_record_count": raw_contamination[section],
        }

    legacy_mean = {name: (sum(row[name] for row in legacy_rows) / count if count else 0.0) for name in ("precision", "recall", "f1")}
    report = {
        "evaluation_version": "content-eval-v3.1.5",
        "split": args.split,
        "nominal_split_count": len(nominal),
        "record_count": count,
        "scope_exclusions": scope_exclusions,
        "scope_unknown": scope_unknown,
        "contamination_exclusions": contamination_exclusions,
        "prediction_coverage": predicted_count / count if count else 0.0,
        "schema_valid_percentage": schema_valid / count if count else 0.0,
        "stable_metadata_macro_f1": macro_f1(field_metrics, STABLE_METADATA_FIELDS),
        "secondary_taxonomy_macro_f1": macro_f1(field_metrics, SECONDARY_TAXONOMY_FIELDS),
        "reference_lifecycle_macro_f1": macro_f1(field_metrics, REFERENCE_LIFECYCLE_FIELDS),
        "reference_number_f1": field_metrics["reference_numbers"]["f1"],
        "superseded_ad_number_f1": field_metrics["superseded_ad_numbers"]["f1"],
        "field_metrics": field_metrics,
        "raw_section_reference_presence": raw_presence,
        "raw_section_source_containment": {"available": bool(source_by_id), "checked_section_count": source_checks, "contained_section_count": source_passes, "accuracy": source_passes / source_checks if source_checks else None, "source_text_parquet": str(args.source_text_parquet)},
        "raw_section_policy": "Raw-section presence is source-heading-driven when document text is available; difficult sections are checked for source containment and page-furniture contamination, not semantic exact-string equality with the gold projection.",
        "legacy_projection_overlap": {**legacy_mean, "primary_metric": False, "note": "Retained only for continuity; do not report it as v3.1 extraction accuracy."},
        "records": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"records"}}, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
