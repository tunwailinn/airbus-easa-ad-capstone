#!/usr/bin/env python3
"""Validate the frozen 30-record Step 3 gold pilot.

This is an additional gate, not a replacement for Step 2 validation.  Every
record is first checked with the frozen Draft 2020-12 schema and the existing
strict semantic validator.  Corpus-level Step 2 checks are then applied before
the Step 3 completeness, review-trail, and frozen-selection checks below.

The final adjudicated annotation is expected to contain one accepted or
corrected ``field_assertion`` whose ``field_path`` is exactly each substantive
section path in ``SUBSTANTIVE_SECTIONS``.  These section-completion assertions
make an empty section distinguishable from a section an annotator forgot to
review.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
STEP2_DIR = ROOT.parent / "step2_ad_schema"
DEFAULT_SELECTION = ROOT / "selection" / "pilot_selection.json"
DEFAULT_SCHEMA = STEP2_DIR / "easa_airbus_ad_annotation.schema.json"

if str(STEP2_DIR) not in sys.path:
    sys.path.insert(0, str(STEP2_DIR))

from validate_annotations import (  # noqa: E402
    batch_semantic_errors,
    load_json,
    load_schema,
    semantic_errors,
    structural_errors,
)


SUBSTANTIVE_SECTIONS = (
    "/ad_identity",
    "/publication",
    "/applicability_groups",
    "/definitions",
    "/unsafe_condition",
    "/requirements",
    "/exceptions",
    "/previous_action_credit",
    "/referenced_publications",
    "/relationships",
    "/amoc_and_contacts",
    "/classification",
)

FINAL_VERIFICATION_STATES = {"accepted", "corrected"}
HUMAN_SECTION_ORIGINS = {"human_annotated", "human_corrected", "adjudicated"}

# Objects at these paths are important enough that their own evidence_ids must
# be non-empty when the object is populated.  Step 2 already checks most of
# these; retaining the explicit Step 3 gate makes incomplete gold annotations
# visible even if the schema evolves later.
IMPORTANT_EVIDENCE_OBJECTS = (
    "/ad_identity",
    "/unsafe_condition",
    "/classification",
)
IMPORTANT_EVIDENCE_COLLECTIONS = (
    "/publication/ata_chapters",
    "/publication/manufacturers",
    "/applicability_groups",
    "/definitions",
    "/requirements",
    "/exceptions",
    "/previous_action_credit",
    "/referenced_publications",
    "/relationships",
    "/amoc_and_contacts",
)

# These populated arrays do not carry evidence_ids in the Step 2 schema, so a
# field assertion is the only direct evidence link for the normalized values.
IMPORTANT_ASSERTED_VALUES = (
    "/publication/type_model_designations",
    "/publication/tcds_numbers",
)


def _pointer_get(document: Any, pointer: str) -> Any:
    """Return a JSON Pointer value, or raise KeyError for a missing path."""

    if not pointer.startswith("/"):
        raise KeyError(pointer)
    current = document
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit():
            current = current[int(token)]
        else:
            raise KeyError(pointer)
    return current


def _populated(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, dict, str)):
        return bool(value)
    return True


def _selection_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _normal_optional(value: Any) -> Any:
    """Normalize blank selection cells to the schema's null convention."""

    return None if value in (None, "") else value


def _cohort_for_year(year: int) -> str | None:
    if 2019 <= year <= 2026:
        return "2019-2026"
    if 2006 <= year <= 2018:
        return "2006-2018"
    return None


def _annotator_entries(record: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = record.get("annotation_metadata") or {}
    entries = metadata.get("annotators") or []
    return [item for item in entries if isinstance(item, dict)]


def _event_entries(record: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = record.get("annotation_metadata") or {}
    entries = metadata.get("events") or []
    return [item for item in entries if isinstance(item, dict)]


def _require_complete_people(
    people: Iterable[dict[str, Any]], path: str, errors: list[str]
) -> None:
    for person in people:
        person_id = person.get("annotator_id") or "<missing>"
        if person.get("started_at") is None:
            errors.append(f"{path}: {person_id!r} is missing started_at")
        if person.get("submitted_at") is None:
            errors.append(f"{path}: {person_id!r} is missing submitted_at")


def _important_evidence_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for pointer in IMPORTANT_EVIDENCE_OBJECTS:
        try:
            value = _pointer_get(record, pointer)
        except (KeyError, IndexError):
            continue
        if _populated(value) and isinstance(value, dict) and not value.get("evidence_ids"):
            errors.append(f"{pointer}/evidence_ids: populated important object requires evidence")

    for pointer in IMPORTANT_EVIDENCE_COLLECTIONS:
        try:
            values = _pointer_get(record, pointer)
        except (KeyError, IndexError):
            continue
        if not isinstance(values, list):
            continue
        for index, value in enumerate(values):
            if isinstance(value, dict) and not value.get("evidence_ids"):
                errors.append(
                    f"{pointer}/{index}/evidence_ids: populated important item requires evidence"
                )

    # Compliance rules and limits are nested below requirements.
    for req_index, requirement in enumerate(record.get("requirements") or []):
        if not isinstance(requirement, dict):
            continue
        for rule_index, rule in enumerate(requirement.get("compliance_rules") or []):
            rule_path = f"/requirements/{req_index}/compliance_rules/{rule_index}"
            if isinstance(rule, dict) and not rule.get("evidence_ids"):
                errors.append(f"{rule_path}/evidence_ids: compliance rule requires evidence")
            if not isinstance(rule, dict):
                continue
            for bucket in ("initial_limits", "repetitive_intervals", "grace_periods"):
                for limit_index, limit_value in enumerate(rule.get(bucket) or []):
                    if isinstance(limit_value, dict) and not limit_value.get("evidence_ids"):
                        errors.append(
                            f"{rule_path}/{bucket}/{limit_index}/evidence_ids: "
                            "compliance limit requires evidence"
                        )

    return errors


def record_completion_errors(
    record: dict[str, Any], selection_row: dict[str, Any]
) -> list[str]:
    """Return Step 3 errors for one structurally valid final record."""

    errors: list[str] = []
    metadata = record.get("annotation_metadata") or {}
    benchmark = record.get("benchmark_metadata") or {}
    assertions = [
        item for item in (record.get("field_assertions") or []) if isinstance(item, dict)
    ]
    assertions_by_path: dict[str, list[dict[str, Any]]] = {}
    for assertion in assertions:
        assertions_by_path.setdefault(assertion.get("field_path"), []).append(assertion)

    if metadata.get("record_status") != "approved":
        errors.append("/annotation_metadata/record_status: final pilot record must be approved")
    if metadata.get("creation_method") != "manual":
        errors.append("/annotation_metadata/creation_method: gold pilot labels must be manual")
    if benchmark.get("gold_record") is not True:
        errors.append("/benchmark_metadata/gold_record: final pilot record must set gold_record=true")

    # Every assertion in a final record must have reached a final review state.
    for index, assertion in enumerate(assertions):
        path = f"/field_assertions/{index}"
        if assertion.get("verification_status") not in FINAL_VERIFICATION_STATES:
            errors.append(
                f"{path}/verification_status: final pilot assertions must be accepted or corrected"
            )
        origin = assertion.get("origin")
        if origin != "derived" and not assertion.get("annotator_id"):
            errors.append(f"{path}/annotator_id: reviewed non-derived assertion requires an annotator")
        if assertion.get("value_state") == "present" and origin != "derived" and not assertion.get("evidence_ids"):
            errors.append(f"{path}/evidence_ids: populated assertion requires evidence")
        if assertion.get("value_state") in {"unclear", "conflicting"}:
            if origin != "adjudicated":
                errors.append(f"{path}/origin: unclear/conflicting gold values require adjudication")
            if not assertion.get("notes"):
                errors.append(f"{path}/notes: unclear/conflicting gold values require a decision rationale")
            if not assertion.get("evidence_ids"):
                errors.append(f"{path}/evidence_ids: unclear/conflicting gold values require evidence")

    # Exact-root assertions are section-completion markers.  Requiring these
    # prevents an empty optional section from being confused with skipped work.
    for pointer in SUBSTANTIVE_SECTIONS:
        section_assertions = assertions_by_path.get(pointer, [])
        reviewed = [
            item
            for item in section_assertions
            if item.get("verification_status") in FINAL_VERIFICATION_STATES
            and item.get("origin") in HUMAN_SECTION_ORIGINS
        ]
        if not reviewed:
            errors.append(
                f"{pointer}: missing accepted/corrected human section-completion assertion"
            )
            continue
        try:
            section_value = _pointer_get(record, pointer)
        except (KeyError, IndexError):
            continue
        if _populated(section_value):
            if not any(item.get("value_state") == "present" for item in reviewed):
                errors.append(f"{pointer}: populated section must have value_state=present")
            if not any(item.get("evidence_ids") for item in reviewed):
                errors.append(f"{pointer}: populated section-completion assertion requires evidence")
        elif not any(
            item.get("value_state") in {"absent_in_source", "not_applicable"}
            for item in reviewed
        ):
            errors.append(
                f"{pointer}: empty section must be marked absent_in_source or not_applicable"
            )

    # Normalized publication lists without their own evidence_ids need a
    # direct field assertion whenever they are populated.
    for pointer in IMPORTANT_ASSERTED_VALUES:
        try:
            value = _pointer_get(record, pointer)
        except (KeyError, IndexError):
            continue
        if not _populated(value):
            continue
        candidates = [
            item
            for item in assertions_by_path.get(pointer, [])
            if item.get("verification_status") in FINAL_VERIFICATION_STATES
            and item.get("value_state") == "present"
            and item.get("evidence_ids")
        ]
        if not candidates:
            errors.append(f"{pointer}: populated important value requires a reviewed evidence assertion")

    errors.extend(_important_evidence_errors(record))

    # A/B and adjudication provenance is carried in the final record; the two
    # original independent submissions should still be retained separately.
    people = _annotator_entries(record)
    events = _event_entries(record)
    primary = [item for item in people if item.get("role") == "annotator"]
    reviewers = [
        item
        for item in people
        if item.get("role") in {"reviewer", "adjudicator", "domain_approver"}
    ]
    adjudicators = [item for item in people if item.get("role") == "adjudicator"]

    if not primary:
        errors.append("/annotation_metadata/annotators: annotator A is missing")
    if not reviewers:
        errors.append("/annotation_metadata/annotators: independent reviewer/approver is missing")
    _require_complete_people(primary + reviewers, "/annotation_metadata/annotators", errors)

    submitted_actor_ids = {
        item.get("actor_id") for item in events if item.get("event_type") == "submitted"
    }
    for person in primary:
        if person.get("annotator_id") not in submitted_actor_ids:
            errors.append(
                "/annotation_metadata/events: each annotator must have a submitted event"
            )

    if _selection_bool(selection_row.get("double_annotation")):
        if len(primary) < 2:
            errors.append(
                "/annotation_metadata/annotators: selected double annotation requires distinct annotators A and B"
            )
        if not adjudicators:
            errors.append(
                "/annotation_metadata/annotators: selected double annotation requires an adjudicator"
            )
        adjudicated_actor_ids = {
            item.get("actor_id")
            for item in events
            if item.get("event_type") == "adjudicated" and item.get("rationale")
        }
        if not any(
            item.get("annotator_id") in adjudicated_actor_ids for item in adjudicators
        ):
            errors.append(
                "/annotation_metadata/events: double annotation requires an adjudicated event with rationale"
            )

    return sorted(set(errors))


def selection_membership_errors(
    records: list[tuple[str, dict[str, Any]]],
    selection_rows: list[dict[str, Any]],
) -> list[str]:
    """Validate exact frozen membership, provenance, and the 15+15 design."""

    errors: list[str] = []
    if len(selection_rows) != 30:
        errors.append(f"selection must contain exactly 30 rows; found {len(selection_rows)}")

    selection_by_ad: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(selection_rows):
        ad_number = row.get("ad_number")
        if not ad_number:
            errors.append(f"selection[{index}]: missing ad_number")
            continue
        if ad_number in selection_by_ad:
            errors.append(f"selection: duplicate ad_number {ad_number!r}")
        selection_by_ad[ad_number] = row

    selection_cohorts = Counter(row.get("cohort") for row in selection_rows)
    expected_counts = {"2019-2026": 15, "2006-2018": 15}
    if dict(selection_cohorts) != expected_counts:
        errors.append(
            "selection cohort counts must be {'2019-2026': 15, '2006-2018': 15}; "
            f"found {dict(selection_cohorts)}"
        )
    if sum(_selection_bool(row.get("double_annotation")) for row in selection_rows) < 10:
        errors.append("selection must designate at least 10 records for double annotation")

    if len(records) != 30:
        errors.append(f"final pilot must contain exactly 30 records; found {len(records)}")

    records_by_ad: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    actual_cohorts: Counter[str | None] = Counter()
    for label, record in records:
        identity = record.get("ad_identity") or {}
        ad_number = identity.get("ad_number")
        records_by_ad.setdefault(ad_number, []).append((label, record))
        base = identity.get("base_ad_number") or ""
        try:
            year = int(base[:4])
        except (TypeError, ValueError):
            year = -1
        actual_cohorts[_cohort_for_year(year)] += 1

    for ad_number, members in records_by_ad.items():
        if len(members) > 1:
            errors.append(
                f"final pilot: duplicate ad_number {ad_number!r} in "
                + ", ".join(label for label, _ in members)
            )

    expected_ads = set(selection_by_ad)
    actual_ads = set(records_by_ad)
    missing = sorted(expected_ads - actual_ads)
    unexpected = sorted(actual_ads - expected_ads, key=lambda value: str(value))
    if missing:
        errors.append("final pilot is missing selected ADs: " + ", ".join(missing))
    if unexpected:
        errors.append(
            "final pilot contains unselected ADs: "
            + ", ".join(repr(value) for value in unexpected)
        )
    if dict(actual_cohorts) != expected_counts:
        errors.append(
            "record cohort counts must be {'2019-2026': 15, '2006-2018': 15}; "
            f"found {dict(actual_cohorts)}"
        )

    expected_fields = {
        "base_ad_number": ("ad_identity", "base_ad_number"),
        "logical_version_key": ("ad_identity", "logical_version_key"),
        "file_instance_id": ("source_document", "file_instance_id"),
        "file_instance_id:canonical": ("source_document", "canonical_file_instance_id"),
        "content_id": ("source_document", "content_id"),
        "file_name": ("source_document", "file_name"),
        "relative_path": ("source_document", "relative_path"),
        "file_sha256": ("source_document", "file_sha256"),
        "normalized_text_sha256": ("source_document", "normalized_text_sha256"),
        "page_count": ("source_document", "page_count"),
        "near_duplicate_cluster": ("source_document", "near_duplicate_cluster"),
    }
    for ad_number in sorted(expected_ads & actual_ads):
        label, record = records_by_ad[ad_number][0]
        row = selection_by_ad[ad_number]
        for selection_key, (section, record_key) in expected_fields.items():
            row_key = selection_key.split(":", 1)[0]
            expected = _normal_optional(row.get(row_key))
            actual = (record.get(section) or {}).get(record_key)
            if record_key == "page_count" and expected is not None:
                try:
                    expected = int(expected)
                except (TypeError, ValueError):
                    pass
            if actual != expected:
                errors.append(
                    f"{label}:{section}.{record_key}: does not match frozen selection "
                    f"({actual!r} != {expected!r})"
                )

    return sorted(set(errors))


def validate_final_pilot(
    records: list[tuple[str, dict[str, Any]]],
    selection_rows: list[dict[str, Any]],
    schema: dict[str, Any],
) -> list[str]:
    """Run Step 2 strict validation, then all Step 3 final-gold gates."""

    errors: list[str] = []
    structurally_valid: list[tuple[str, dict[str, Any]]] = []
    selection_by_ad = {
        row.get("ad_number"): row for row in selection_rows if row.get("ad_number")
    }

    for label, record in records:
        schema_findings = structural_errors(record, schema)
        if schema_findings:
            errors.extend(f"{label}:[step2-schema] {item}" for item in schema_findings)
            continue
        structurally_valid.append((label, record))
        strict_findings = semantic_errors(record, strict=True)
        errors.extend(f"{label}:[step2-strict] {item}" for item in strict_findings)

        ad_number = (record.get("ad_identity") or {}).get("ad_number")
        row = selection_by_ad.get(ad_number)
        if row is not None:
            errors.extend(
                f"{label}:[step3] {item}"
                for item in record_completion_errors(record, row)
            )

    errors.extend(
        f"[step2-batch] {item}"
        for item in batch_semantic_errors(structurally_valid)
    )
    errors.extend(
        f"[step3-selection] {item}"
        for item in selection_membership_errors(records, selection_rows)
    )
    return sorted(set(errors))


def _collect_annotation_paths(inputs: Iterable[Path]) -> list[Path]:
    paths: list[Path] = []
    for value in inputs:
        if value.is_dir():
            preferred = sorted(value.rglob("*.annotation.json"))
            paths.extend(preferred or sorted(value.rglob("*.json")))
        else:
            paths.append(value)
    return sorted(set(path.resolve() for path in paths))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="final annotation JSON file(s) or directories containing them",
    )
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument(
        "--report",
        type=Path,
        help="optional path for a machine-readable JSON validation report",
    )
    args = parser.parse_args(argv)

    paths = _collect_annotation_paths(args.inputs)
    if not paths:
        print("No annotation JSON files found.", file=sys.stderr)
        return 2

    try:
        selection_value = load_json(args.selection)
        if not isinstance(selection_value, list):
            raise ValueError("selection JSON must contain a list of rows")
        selection_rows = [row for row in selection_value if isinstance(row, dict)]
        if len(selection_rows) != len(selection_value):
            raise ValueError("every selection row must be a JSON object")
        schema = load_schema(args.schema)
    except (OSError, json.JSONDecodeError, RuntimeError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    records: list[tuple[str, dict[str, Any]]] = []
    load_errors: list[str] = []
    for path in paths:
        try:
            value = load_json(path)
            if not isinstance(value, dict):
                raise ValueError("annotation root must be a JSON object")
            records.append((str(path), value))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            load_errors.append(f"{path}: {exc}")

    errors = load_errors + validate_final_pilot(records, selection_rows, schema)
    passed = not errors
    print(
        f"{'PASS' if passed else 'FAIL'} Step 3 pilot: "
        f"{len(records)} loaded record(s), {len(errors)} error(s)"
    )
    for error in errors:
        print(f"  - {error}")

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(
                {
                    "passed": passed,
                    "record_count": len(records),
                    "selection_count": len(selection_rows),
                    "errors": errors,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
