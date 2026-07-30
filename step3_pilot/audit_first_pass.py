#!/usr/bin/env python3
"""Audit a machine-assisted Step 3 first-pass annotation stream.

This is stricter than ordinary Step 2 validation about pilot membership and
section-completion assertions, but it is not the human gold gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SECTION_ASSERTIONS = (
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("annotation_dir", type=Path)
    parser.add_argument(
        "--selection",
        type=Path,
        default=Path("step3_pilot/selection/pilot_selection.json"),
    )
    parser.add_argument(
        "--expected",
        choices=("all", "double"),
        required=True,
        help="all=the 30 Annotator-A records; double=the 10 Annotator-B records",
    )
    parser.add_argument(
        "--status",
        choices=("first_pass_complete", "double_annotated", "adjudicated"),
        default="first_pass_complete",
        help="required annotation_metadata.record_status",
    )
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def collect_evidence_references(value: Any, path: str = "") -> list[tuple[str, str]]:
    references: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}/{key}"
            if key == "evidence_ids" and isinstance(item, list):
                references.extend((child, evidence_id) for evidence_id in item)
            else:
                references.extend(collect_evidence_references(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            references.extend(collect_evidence_references(item, f"{path}/{index}"))
    return references


def audit_record(
    record: dict[str, Any], selected: dict[str, Any], expected_status: str
) -> list[str]:
    errors: list[str] = []
    identity = record.get("ad_identity") or {}
    source = record.get("source_document") or {}
    metadata = record.get("annotation_metadata") or {}
    benchmark = record.get("benchmark_metadata") or {}
    classification = record.get("classification") or {}
    publication = record.get("publication") or {}

    expected_values = {
        "ad_identity.ad_number": (identity.get("ad_number"), selected.get("ad_number")),
        "ad_identity.base_ad_number": (
            identity.get("base_ad_number"),
            selected.get("base_ad_number"),
        ),
        "ad_identity.logical_version_key": (
            identity.get("logical_version_key"),
            selected.get("logical_version_key"),
        ),
        "source_document.file_instance_id": (
            source.get("file_instance_id"),
            selected.get("file_instance_id"),
        ),
        "source_document.content_id": (
            source.get("content_id"),
            selected.get("content_id"),
        ),
        "source_document.file_sha256": (
            source.get("file_sha256"),
            selected.get("file_sha256"),
        ),
        "source_document.normalized_text_sha256": (
            source.get("normalized_text_sha256"),
            selected.get("normalized_text_sha256"),
        ),
        "source_document.page_count": (
            source.get("page_count"),
            selected.get("page_count"),
        ),
        "source_document.near_duplicate_cluster": (
            source.get("near_duplicate_cluster"),
            selected.get("near_duplicate_cluster"),
        ),
    }
    for path, (actual, expected) in expected_values.items():
        if path == "source_document.near_duplicate_cluster":
            actual = actual or None
            expected = expected or None
        if str(actual) != str(expected):
            errors.append(f"{path}: {actual!r} != frozen selection {expected!r}")

    if metadata.get("record_status") != expected_status:
        errors.append(
            f"annotation_metadata.record_status must be {expected_status}"
        )
    if metadata.get("creation_method") != "hybrid":
        errors.append("annotation_metadata.creation_method must be hybrid")
    if classification.get("human_confirmed") is not False:
        errors.append("classification.human_confirmed must remain false before human review")
    if benchmark.get("gold_record") is not False:
        errors.append("benchmark_metadata.gold_record must remain false before human review")

    evidence_ids = [item.get("evidence_id") for item in record.get("evidence_spans", [])]
    evidence_set = set(evidence_ids)
    if None in evidence_set:
        errors.append("evidence_spans contains an item without evidence_id")
    if len(evidence_ids) != len(evidence_set):
        errors.append("evidence_spans contains duplicate evidence_id values")
    for path, evidence_id in collect_evidence_references(record):
        if evidence_id not in evidence_set:
            errors.append(f"{path}: unresolved evidence ID {evidence_id!r}")

    assertion_paths = [
        item.get("field_path") for item in record.get("field_assertions", [])
    ]
    for required in SECTION_ASSERTIONS:
        count = assertion_paths.count(required)
        if count != 1:
            errors.append(f"field_assertions: expected one {required!r}, found {count}")

    ata_publication = {
        item.get("code") for item in publication.get("ata_chapters", [])
    }
    ata_classification = set(classification.get("ata_chapters", []))
    if ata_publication != ata_classification:
        errors.append("classification.ata_chapters does not match publication ATA union")
    action_union = {
        action
        for requirement in record.get("requirements", [])
        for action in requirement.get("action_types", [])
    }
    if action_union != set(classification.get("action_types", [])):
        errors.append("classification.action_types does not match requirement action union")
    terminating_present = any(
        (item.get("terminating_action") or {}).get("present") is True
        for item in record.get("requirements", [])
    )
    if classification.get("terminating_action_present") != terminating_present:
        errors.append("classification.terminating_action_present is inconsistent")

    for index, manufacturer in enumerate(publication.get("manufacturers", [])):
        raw = (manufacturer.get("raw_name") or "").lower()
        if "airbus" in raw and manufacturer.get("normalized_name") != "Airbus":
            errors.append(
                f"publication.manufacturers[{index}]: Airbus name must normalize to 'Airbus'"
            )
    return errors


def main() -> int:
    args = parse_args()
    selection = load_json(args.selection)
    if not isinstance(selection, list) or len(selection) != 30:
        raise ValueError("frozen selection must contain exactly 30 rows")
    expected_rows = (
        selection
        if args.expected == "all"
        else [row for row in selection if bool(row.get("double_annotation"))]
    )
    expected_by_file = {row["file_instance_id"]: row for row in expected_rows}
    paths = sorted(args.annotation_dir.glob("*.annotation.json"))
    found: dict[str, tuple[Path, dict[str, Any]]] = {}
    load_errors: list[str] = []
    for path in paths:
        try:
            record = load_json(path)
            file_id = (record.get("source_document") or {}).get("file_instance_id")
            if not file_id:
                load_errors.append(f"{path}: missing source_document.file_instance_id")
            elif file_id in found:
                load_errors.append(f"{path}: duplicate file_instance_id {file_id}")
            else:
                found[file_id] = (path, record)
        except (OSError, json.JSONDecodeError) as exc:
            load_errors.append(f"{path}: {exc}")

    missing = sorted(set(expected_by_file) - set(found))
    unexpected = sorted(set(found) - set(expected_by_file))
    record_reports = []
    for file_id in sorted(set(found) & set(expected_by_file)):
        path, record = found[file_id]
        errors = audit_record(record, expected_by_file[file_id], args.status)
        record_reports.append(
            {
                "ad_number": expected_by_file[file_id]["ad_number"],
                "file": str(path),
                "status": "pass" if not errors else "fail",
                "errors": errors,
            }
        )

    error_count = (
        len(load_errors)
        + len(missing)
        + len(unexpected)
        + sum(len(item["errors"]) for item in record_reports)
    )
    report = {
        "annotation_dir": str(args.annotation_dir),
        "expected_stream": args.expected,
        "expected_status": args.status,
        "expected_count": len(expected_rows),
        "found_count": len(found),
        "missing_file_instance_ids": missing,
        "unexpected_file_instance_ids": unexpected,
        "load_errors": load_errors,
        "error_count": error_count,
        "records": record_reports,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    print(
        f"Audited {len(found)}/{len(expected_rows)} expected records; "
        f"errors={error_count}"
    )
    for item in load_errors:
        print(f"ERROR {item}")
    for file_id in missing:
        print(f"ERROR missing {file_id}")
    for file_id in unexpected:
        print(f"ERROR unexpected {file_id}")
    for item in record_reports:
        for error in item["errors"]:
            print(f"ERROR {item['ad_number']}: {error}")
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
