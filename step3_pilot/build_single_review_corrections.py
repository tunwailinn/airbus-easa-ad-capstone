#!/usr/bin/env python3
"""Build corrected single-review candidates without modifying frozen A/B files."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "step3_pilot" / "submitted" / "annotator_a"
OUTPUT_DIR = ROOT / "step3_pilot" / "adjudication" / "single_review_candidates"

STEMS = (
    "2019-0011R2__1949a5e809ac47e1",
    "2020-0028__734af537e02af649",
    "2021-0087__9e367bf311641409",
    "2021-0242__3d05d4995d986ef5",
    "2022-0026__2003cabcfcd8976a",
    "2022-0197__2f70e87899358165",
    "2024-0038__db594c767fc8f98e",
)

LIFECYCLE_ABSENCE_ADS = {
    "2019-0011R2",
    "2020-0028",
    "2021-0087",
    "2021-0242",
    "2022-0197",
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def serialize(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def write(path: Path, value: Any) -> str:
    payload = serialize(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def assertion(record: dict[str, Any], field_path: str) -> dict[str, Any]:
    matches = [
        item for item in record["field_assertions"] if item["field_path"] == field_path
    ]
    if len(matches) != 1:
        raise ValueError(f"{record['record_id']}: expected one assertion for {field_path}")
    return matches[0]


def requirement(record: dict[str, Any], requirement_id: str) -> dict[str, Any]:
    return next(
        item
        for item in record["requirements"]
        if item["requirement_id"] == requirement_id
    )


def optional_rule(
    compliance_id: str,
    raw_text: str,
    conditions: list[str],
) -> dict[str, Any]:
    return {
        "compliance_id": compliance_id,
        "state": "not_stated",
        "raw_text": raw_text,
        "logic": "conditional",
        "conditions": conditions,
        "initial_limits": [],
        "is_repetitive": False,
        "repetitive_intervals": [],
        "grace_periods": [],
        "evidence_ids": ["EV-008"],
    }


def correct_record(
    record: dict[str, Any], now: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result = copy.deepcopy(record)
    ad_number = result["ad_identity"]["ad_number"]
    changes: list[dict[str, Any]] = []

    correction_assertion = assertion(result, "/ad_identity/is_correction")
    if correction_assertion["assertion_id"] != "AST-008":
        raise ValueError(f"{ad_number}: correction assertion is not AST-008")
    correction_assertion["evidence_ids"] = ["EV-001"]
    correction_assertion["notes"] = (
        "Source header reviewed: the publication identity/revision is printed in "
        "EV-001 and no correction notice or correction date is printed; "
        "is_correction=false remains a machine assertion pending human review."
    )
    changes.append(
        {
            "field_path": "/ad_identity/is_correction",
            "change": "Attached source header evidence EV-001 to the populated false assertion.",
            "evidence_ids": ["EV-001"],
        }
    )

    if ad_number in LIFECYCLE_ABSENCE_ADS:
        lifecycle_assertion = assertion(result, "/ad_identity/lifecycle_status")
        if lifecycle_assertion["assertion_id"] != "AST-010":
            raise ValueError(f"{ad_number}: lifecycle assertion is not AST-010")
        if result["ad_identity"]["lifecycle_status"] != "unknown":
            raise ValueError(f"{ad_number}: lifecycle value is not neutral unknown")
        lifecycle_assertion.update(
            {
                "value_state": "absent_in_source",
                "origin": "auto_extracted",
                "verification_status": "unreviewed",
                "confidence": 0.96,
                "evidence_ids": [],
                "notes": (
                    "Rendered cover and frozen page text were reviewed. The source "
                    "contains no lifecycle disposition and no visible SUPERSEDED "
                    "watermark. absent_in_source records that source absence; the "
                    "neutral lifecycle_status=unknown is not a claim that the AD is "
                    "current or superseded. Human review remains pending."
                ),
            }
        )
        changes.append(
            {
                "field_path": "/ad_identity/lifecycle_status",
                "change": (
                    "Reclassified AST-010 from unclear to absent_in_source while "
                    "retaining neutral lifecycle_status=unknown; no current or "
                    "superseded status was inferred."
                ),
                "evidence_ids": [],
            }
        )

    if ad_number == "2024-0038":
        req6 = requirement(result, "REQ-006")
        req7 = requirement(result, "REQ-007")
        req8 = requirement(result, "REQ-008")
        if any(item["compliance_rules"] for item in (req6, req7, req8)):
            raise ValueError("2024-0038: expected REQ-006/007/008 empty rules")
        req6["compliance_rules"] = [
            optional_rule(
                "CMP-006",
                (
                    "Modification of an affected part on an aeroplane, accomplished "
                    "in accordance with the instructions of the modification SB, "
                    "constitutes terminating action for the initial and repetitive "
                    "inspections as required by paragraphs (1) and (5) of this AD, "
                    "as applicable, for that galley."
                ),
                ["If the operator elects to use paragraph (6) as terminating action"],
            )
        ]
        req7["compliance_rules"] = [
            optional_rule(
                "CMP-007",
                (
                    "Modification of all affected parts on an aeroplane, accomplished "
                    "in accordance with the instructions of the modification SB, "
                    "constitutes terminating action for the initial and repetitive "
                    "inspections as required by paragraphs (1) and (5) of this AD, "
                    "as applicable, for that aeroplane, provided that no affected "
                    "parts are re-installed on that aeroplane after that modification."
                ),
                [
                    "If the operator elects to use paragraph (7) as terminating action",
                    "No affected parts are re-installed on the aeroplane after modification",
                ],
            )
        ]
        req8["compliance_rules"] = [
            optional_rule(
                "CMP-008",
                (
                    "For Group 1 and Group 2 aeroplanes: Replacement of an affected "
                    "part with a part in post-modification SB configuration on an "
                    "aeroplane is an acceptable method to comply with the requirements "
                    "of paragraph (1) or (2) of this AD, as applicable, for that part."
                ),
                [
                    "If the operator elects the paragraph (8) acceptable replacement method",
                    "Apply to paragraph (1) or (2), as applicable, for that part",
                ],
            )
        ]
        changes.append(
            {
                "field_path": "/requirements/5-7/compliance_rules",
                "change": (
                    "Added CMP-006/007/008 as conditional elective rules with no "
                    "invented deadline: paragraphs (6)/(7) are optional terminating "
                    "actions and paragraph (8) is an acceptable compliance method."
                ),
                "evidence_ids": ["EV-008"],
            }
        )

    metadata = result["annotation_metadata"]
    metadata["record_status"] = "first_pass_complete"
    metadata["creation_method"] = "hybrid"
    metadata["machine_provenance"].update(
        {
            "system": "OpenAI Codex",
            "model": "GPT-5",
            "prompt_or_rules_version": "step3-single-review-correction-1.0.0",
            "generated_at": now,
        }
    )
    if "manual_review_required" not in metadata["quality_flags"]:
        metadata["quality_flags"].append("manual_review_required")
    metadata["events"].append(
        {
            "event_type": "reviewed",
            "actor_id": "codex-a1",
            "timestamp": now,
            "rationale": (
                "Machine preapproval-blocker review corrected evidence/state or "
                "compliance-rule completeness; no human acceptance or approval claimed."
            ),
        }
    )
    metadata["notes"].append(
        "Corrected single-review candidate; frozen Annotator-A submission remains unchanged and independent human review is still required."
    )
    metadata["updated_at"] = now
    result["classification"]["human_confirmed"] = False
    result["benchmark_metadata"]["gold_record"] = False
    return result, changes


def main() -> None:
    now = now_utc()
    log_rows: list[dict[str, Any]] = []
    for stem in STEMS:
        source_path = SOURCE_DIR / f"{stem}.annotation.json"
        output_path = OUTPUT_DIR / source_path.name
        source = load(source_path)
        corrected, changes = correct_record(source, now)
        corrected_hash = write(output_path, corrected)
        log_rows.append(
            {
                "ad_number": corrected["ad_identity"]["ad_number"],
                "file_instance_id": corrected["source_document"]["file_instance_id"],
                "frozen_source_file": str(source_path.relative_to(ROOT)),
                "frozen_source_sha256": sha256(source_path),
                "corrected_file": str(output_path.relative_to(ROOT)),
                "corrected_sha256": corrected_hash,
                "changes": changes,
            }
        )

    correction_log = {
        "log_version": "1.0.0",
        "generated_at": now,
        "scope": "Seven machine-corrected single-review candidates; no frozen A/B file modified.",
        "record_count": len(log_rows),
        "human_review_required": True,
        "records": log_rows,
    }
    write(OUTPUT_DIR / "correction_log.json", correction_log)


if __name__ == "__main__":
    main()
