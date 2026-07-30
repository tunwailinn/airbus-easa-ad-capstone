#!/usr/bin/env python3
"""Audit all ten transparent machine-adjudication candidates and logs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


SECTIONS = (
    "ad_identity",
    "publication",
    "applicability_groups",
    "definitions",
    "unsafe_condition",
    "requirements",
    "exceptions",
    "previous_action_credit",
    "referenced_publications",
    "relationships",
    "amoc_and_contacts",
    "classification",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--selection",
        type=Path,
        default=Path("step3_pilot/selection/pilot_selection.json"),
    )
    parser.add_argument(
        "--roster",
        type=Path,
        default=Path("step3_pilot/selection/annotation_assignment_roster.csv"),
    )
    parser.add_argument(
        "--candidate-dir",
        type=Path,
        default=Path("step3_pilot/adjudication/machine_candidates"),
    )
    parser.add_argument(
        "--decision-dir",
        type=Path,
        default=Path("step3_pilot/adjudication/decisions"),
    )
    parser.add_argument(
        "--comparison",
        type=Path,
        default=Path("step3_pilot/adjudication/double_annotation_comparison.json"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("step3_pilot/validation/machine_adjudication_audit.json"),
    )
    return parser.parse_args()


def load_index(directory: Path, pattern: str) -> dict[str, tuple[Path, dict[str, Any]]]:
    result = {}
    for path in sorted(directory.glob(pattern)):
        value = json.loads(path.read_text(encoding="utf-8"))
        file_id = value.get("file_instance_id") or (
            value.get("source_document") or {}
        ).get("file_instance_id")
        if not file_id or file_id in result:
            raise ValueError(f"{path}: missing or duplicate file_instance_id")
        result[file_id] = (path, value)
    return result


def audit_candidate(
    record: dict[str, Any], selected: dict[str, Any], assignment: dict[str, str]
) -> list[str]:
    errors = []
    identity = record.get("ad_identity") or {}
    source = record.get("source_document") or {}
    metadata = record.get("annotation_metadata") or {}
    classification = record.get("classification") or {}
    benchmark = record.get("benchmark_metadata") or {}
    if identity.get("ad_number") != selected["ad_number"]:
        errors.append("AD number does not match selection")
    if identity.get("logical_version_key") != selected["logical_version_key"]:
        errors.append("logical version does not match selection")
    if source.get("file_sha256") != selected["file_sha256"]:
        errors.append("source hash does not match selection")
    if (source.get("near_duplicate_cluster") or None) != (
        selected.get("near_duplicate_cluster") or None
    ):
        errors.append("near-duplicate cluster does not match selection")
    if metadata.get("record_status") != "adjudicated":
        errors.append("record_status must be adjudicated")
    if metadata.get("creation_method") != "hybrid":
        errors.append("creation_method must be hybrid")
    if classification.get("human_confirmed") is not False:
        errors.append("human_confirmed must remain false")
    if benchmark.get("gold_record") is not False:
        errors.append("gold_record must remain false")
    if "manual_review_required" not in metadata.get("quality_flags", []):
        errors.append("manual_review_required quality flag is missing")

    roles = {
        item.get("annotator_id"): item.get("role")
        for item in metadata.get("annotators", [])
    }
    expected_roles = {
        assignment["annotator_a"]: "annotator",
        assignment["annotator_b"]: "annotator",
        assignment["machine_adjudicator"]: "adjudicator",
    }
    if roles != expected_roles:
        errors.append(f"annotator/adjudicator roles mismatch: {roles!r}")
    events = metadata.get("events", [])
    if not any(
        event.get("event_type") == "adjudicated"
        and event.get("actor_id") == assignment["machine_adjudicator"]
        and event.get("rationale")
        for event in events
    ):
        errors.append("machine adjudication event/rationale is missing")

    paths = [item.get("field_path") for item in record.get("field_assertions", [])]
    for section in SECTIONS:
        pointer = f"/{section}"
        if paths.count(pointer) != 1:
            errors.append(f"expected one section assertion for {pointer}")
    for index, assertion in enumerate(record.get("field_assertions", [])):
        if assertion.get("origin") != "auto_extracted":
            errors.append(f"field_assertions[{index}] origin must remain auto_extracted")
        if assertion.get("verification_status") != "unreviewed":
            errors.append(f"field_assertions[{index}] must remain unreviewed")
        confidence = assertion.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            errors.append(f"field_assertions[{index}] requires numeric confidence")
        if assertion.get("value_state") == "present" and not assertion.get("evidence_ids"):
            errors.append(f"field_assertions[{index}] present value requires evidence")
    for index, requirement in enumerate(record.get("requirements", [])):
        if not requirement.get("compliance_rules"):
            errors.append(f"requirements[{index}] requires at least one compliance rule")
    return errors


def audit_decision(
    decision: dict[str, Any],
    selected: dict[str, Any],
    assignment: dict[str, str],
    comparison: dict[str, Any],
) -> list[str]:
    errors = []
    if decision.get("ad_number") != selected["ad_number"]:
        errors.append("decision AD number mismatch")
    if decision.get("logical_version_key") != selected["logical_version_key"]:
        errors.append("decision logical version mismatch")
    if decision.get("adjudicator_id") != assignment["machine_adjudicator"]:
        errors.append("decision adjudicator mismatch")
    if decision.get("decision_status") != "machine_adjudicated_pending_human_review":
        errors.append("decision status must remain pending human review")
    if decision.get("manual_review_required") is not True:
        errors.append("decision must require manual review")
    expected_comparison_hash = hashlib.sha256(
        json.dumps(comparison, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    if decision.get("comparison_sha256") != expected_comparison_hash:
        errors.append("decision comparison hash does not match the frozen comparison")
    if not decision.get("overall_rationale"):
        errors.append("overall decision rationale is missing")
    sections = decision.get("sections") or []
    names = [item.get("section") for item in sections if isinstance(item, dict)]
    if set(names) != set(SECTIONS) or len(names) != len(SECTIONS):
        errors.append("decision log must contain exactly the 12 substantive sections")
    for index, section in enumerate(sections):
        if not section.get("decision"):
            errors.append(f"decision sections[{index}] lacks a decision")
        if not isinstance(section.get("source_pages"), list):
            errors.append(f"decision sections[{index}] lacks source_pages list")
    return errors


def main() -> int:
    args = parse_args()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    selected = {
        row["file_instance_id"]: row
        for row in selection
        if bool(row.get("double_annotation"))
    }
    with args.roster.open("r", encoding="utf-8", newline="") as handle:
        roster = {row["ad_number"]: row for row in csv.DictReader(handle)}
    candidates = load_index(args.candidate_dir, "*.annotation.json")
    decisions = load_index(args.decision_dir, "*.adjudication.json")
    comparison_report = json.loads(args.comparison.read_text(encoding="utf-8"))
    comparisons = {
        row["file_instance_id"]: row
        for row in comparison_report.get("comparisons", [])
        if row.get("status") == "ready_for_adjudication"
    }
    reports = []
    missing_candidates = sorted(set(selected) - set(candidates))
    missing_decisions = sorted(set(selected) - set(decisions))
    unexpected_candidates = sorted(set(candidates) - set(selected))
    unexpected_decisions = sorted(set(decisions) - set(selected))
    for file_id in sorted(set(selected) & set(candidates) & set(decisions)):
        row = selected[file_id]
        errors = audit_candidate(candidates[file_id][1], row, roster[row["ad_number"]])
        if file_id not in comparisons:
            errors.append("frozen A/B comparison is missing")
        else:
            errors.extend(
                audit_decision(
                    decisions[file_id][1],
                    row,
                    roster[row["ad_number"]],
                    comparisons[file_id],
                )
            )
        reports.append(
            {
                "ad_number": row["ad_number"],
                "file_instance_id": file_id,
                "status": "pass" if not errors else "fail",
                "errors": errors,
            }
        )
    error_count = (
        len(missing_candidates)
        + len(missing_decisions)
        + len(unexpected_candidates)
        + len(unexpected_decisions)
        + sum(len(row["errors"]) for row in reports)
    )
    report = {
        "expected_count": 10,
        "candidate_count": len(candidates),
        "decision_count": len(decisions),
        "missing_candidate_ids": missing_candidates,
        "missing_decision_ids": missing_decisions,
        "unexpected_candidate_ids": unexpected_candidates,
        "unexpected_decision_ids": unexpected_decisions,
        "error_count": error_count,
        "records": reports,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"Audited {len(candidates)}/10 candidates and {len(decisions)}/10 logs; "
        f"errors={error_count}"
    )
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
