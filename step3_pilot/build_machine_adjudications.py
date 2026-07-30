#!/usr/bin/env python3
"""Build machine-adjudicated Step 3 candidates without modifying A/B inputs."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "step3_pilot"
A_DIR = PILOT / "submitted" / "annotator_a"
B_DIR = PILOT / "submitted" / "annotator_b"
OUT_DIR = PILOT / "adjudication" / "machine_candidates"
DECISION_DIR = PILOT / "adjudication" / "decisions"
SELECTION_FILE = PILOT / "selection" / "pilot_selection.json"
SCOPE_SELECTION_FILE = PILOT / "adjudication" / "machine_scope_selection.json"

ADJUDICATOR_ID = "codex-a2"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def requirement(record: dict[str, Any], requirement_id: str) -> dict[str, Any]:
    return next(
        item for item in record["requirements"] if item["requirement_id"] == requirement_id
    )


def normalize_terminating_actions(record: dict[str, Any]) -> None:
    for item in record["requirements"]:
        terminating = item["terminating_action"]
        if terminating["state"] == "not_stated":
            terminating["present"] = False
            terminating["scope"] = "none"
            terminating["action_text"] = None
            terminating["terminates_requirement_ids"] = []
            terminating["evidence_ids"] = []


def action_union(record: dict[str, Any]) -> list[str]:
    ordered: list[str] = []
    for item in record["requirements"]:
        for action in item["action_types"]:
            if action not in ordered:
                ordered.append(action)
    return ordered


def machine_metadata(
    record: dict[str, Any],
    annotator_a: dict[str, Any],
    annotator_b: dict[str, Any],
    now: str,
    quality_flags: list[str],
    uncertainty_flags: list[str],
    notes: list[str],
) -> None:
    a_meta = annotator_a["annotation_metadata"]
    b_meta = annotator_b["annotation_metadata"]
    a_actor = copy.deepcopy(a_meta["annotators"][0])
    b_actor = copy.deepcopy(b_meta["annotators"][0])
    created_candidates = [
        value
        for value in (a_meta.get("created_at"), b_meta.get("created_at"))
        if value
    ]
    record["annotation_metadata"] = {
        "guideline_version": "1.0.0",
        "record_status": "adjudicated",
        "creation_method": "hybrid",
        "machine_provenance": {
            "system": "OpenAI Codex",
            "model": "GPT-5",
            "prompt_or_rules_version": "step3-machine-adjudication-1.0.0",
            "generated_at": now,
        },
        "annotators": [
            a_actor,
            b_actor,
            {
                "annotator_id": ADJUDICATOR_ID,
                "role": "adjudicator",
                "started_at": now,
                "submitted_at": now,
            },
        ],
        "events": [
            *copy.deepcopy(a_meta["events"]),
            *copy.deepcopy(b_meta["events"]),
            {
                "event_type": "adjudicated",
                "actor_id": ADJUDICATOR_ID,
                "timestamp": now,
                "rationale": (
                    "Machine-only reconciliation of independent A/B records against "
                    "the official PDF, frozen page text, reviewer-QC packet, schema, "
                    "guidelines, and comparison report; human confirmation remains required."
                ),
            },
        ],
        "quality_flags": quality_flags,
        "uncertainty_flags": uncertainty_flags,
        "notes": notes,
        "source_text_sha256": record["source_document"]["normalized_text_sha256"],
        "created_at": min(created_candidates) if created_candidates else now,
        "updated_at": now,
    }

    for assertion in record["field_assertions"]:
        assertion["origin"] = "auto_extracted"
        assertion["verification_status"] = "unreviewed"
        original_confidence = assertion.get("confidence")
        assertion["confidence"] = (
            min(float(original_confidence), 0.96)
            if isinstance(original_confidence, (int, float))
            else 0.9
        )
        assertion["annotator_id"] = ADJUDICATOR_ID
        assertion["derivation_rule"] = None
        assertion["input_field_paths"] = []
        assertion["notes"] = (
            "Machine-adjudicated synthesis; assertion remains unreviewed pending human review."
        )

    record["classification"]["human_confirmed"] = False
    record["benchmark_metadata"]["gold_record"] = False


def build_2010(now: str) -> tuple[dict[str, Any], dict[str, Any]]:
    stem = "2010-0164__60596be378420b04"
    a_path = A_DIR / f"{stem}.annotation.json"
    b_path = B_DIR / f"{stem}.annotation.json"
    a = load(a_path)
    b = load(b_path)
    record = copy.deepcopy(b)

    record["ad_identity"]["version_label"] = "Original"
    record["ad_identity"]["design_approval_holder"].update(
        {
            "value": "Airbus",
            "raw_text": "Type Approval Holder’s Name: AIRBUS",
        }
    )
    record["publication"]["type_model_designations"] = [
        "A318",
        "A319",
        "A320",
        "A321",
    ]
    record["classification"]["airbus_families"] = ["A320 family"]

    # Keep the global previously-accomplished exception, but reject Annotator B's
    # paragraph (10) restatement: it is the installation requirement itself.
    record["exceptions"] = [copy.deepcopy(b["exceptions"][0])]

    # Both directions are printed explicitly. Link them to the selected 2009 AD
    # record, while retaining candidate/unreviewed relationship status.
    for relationship in record["relationships"]:
        relationship["target_record_id"] = "adann-cb57166de0385f86"
        relationship["target_logical_version_key"] = "2009-0141|UNCORRECTED"
        relationship["verification_status"] = "candidate"
        relationship["manually_verified"] = False

    normalize_terminating_actions(record)
    record["classification"]["action_types"] = action_union(record)
    record["classification"]["terminating_action_present"] = True

    machine_metadata(
        record,
        a,
        b,
        now,
        quality_flags=[
            "complex_table",
            "cross_page_clause",
            "complex_applicability",
            "complex_compliance",
            "visual_transcription_used",
            "manual_review_required",
        ],
        uncertainty_flags=[
            "Machine-only adjudication requires human verification of the dense Appendix transcriptions and nested paragraph (8) timing logic."
        ],
        notes=[
            "Machine-adjudicated candidate only; not human-confirmed and not gold.",
            "Annotator B's 43 atomic requirements were retained because they preserve separately numbered initial, repetitive, follow-on, and terminating clauses.",
            "Appendix A-E P/N and S/N restrictions were visually checked against rendered pages; human table verification remains required.",
            "The source explicitly supersedes and retains requirements of AD 2009-0141; no successor or correction relationship was inferred.",
        ],
    )

    decision = {
        "ad_number": "2010-0164",
        "logical_version_key": "2010-0164|UNCORRECTED",
        "file_instance_id": "60596be378420b04",
        "annotator_a_file": str(a_path.relative_to(ROOT)),
        "annotator_b_file": str(b_path.relative_to(ROOT)),
        "adjudicator_id": ADJUDICATOR_ID,
        "comparison_sha256": "ba7d5d4c9a2077b80ab9104f525a9ca3cf5514da5eb155586f88f97e20b9ea29",
        "decision_status": "machine_adjudicated_pending_human_review",
        "resolved_record_file": str(
            (OUT_DIR / f"{stem}.annotation.json").relative_to(ROOT)
        ),
        "manual_review_required": True,
        "sections": [
            {
                "section": "ad_identity",
                "accepted_from": "synthesized",
                "source_pages": [1],
                "decision": "Use normalized Airbus holder, Original version label, and the explicit supersedes statement; lifecycle remains unknown.",
            },
            {
                "section": "publication",
                "accepted_from": "annotator_a",
                "source_pages": [1, 2],
                "decision": "Keep normalized subject, four broad type designations, issue/effective dates, ATA 55, TCDS and manufacturer provenance.",
            },
            {
                "section": "applicability_groups",
                "accepted_from": "annotator_b",
                "source_pages": list(range(1, 18)),
                "decision": "Retain seven Appendix/core-density populations and B's complete P/N/S/N mappings, including the 870-entry Appendix D list.",
            },
            {
                "section": "unsafe_condition",
                "accepted_from": "annotator_b",
                "source_pages": [1, 2],
                "decision": "Preserve skin-to-core debonding, rudder structural degradation, loss and controllability consequences without adding inferred causes.",
            },
            {
                "section": "requirements",
                "accepted_from": "annotator_b_with_normalization",
                "source_pages": list(range(2, 9)),
                "decision": "Use 43 atomic clauses; preserve nested timing, conditional findings, reports, partial terminations and the explicit paragraph (10) installation prohibition.",
            },
            {
                "section": "definitions",
                "accepted_from": "annotator_b",
                "source_pages": [3, 5, 6],
                "decision": "Keep the paragraph (2), (6), and (7) Reference Date definitions separately because their source scopes are distinct.",
            },
            {
                "section": "exceptions",
                "accepted_from": "synthesized",
                "source_pages": [2, 3, 5, 6, 7, 8],
                "decision": "Keep the explicit previously-accomplished exception; reject B EXC-002 because paragraph (10) is a requirement, not an exception.",
            },
            {
                "section": "previous_action_credit",
                "accepted_from": "annotator_b",
                "source_pages": [4, 7, 8],
                "decision": "Retain the four explicit credits with exact revision limitations and requirement links.",
            },
            {
                "section": "referenced_publications",
                "accepted_from": "annotator_b",
                "source_pages": list(range(2, 9)),
                "decision": "Retain 11 role- and revision-specific AOT/SB/TD entries; later-revision allowance does not broaden revision-specific previous-action credit.",
            },
            {
                "section": "relationships",
                "accepted_from": "annotator_b_with_target_resolution",
                "source_pages": [1],
                "decision": "Keep only explicit supersedes and retains-requirements-of edges to selected AD 2009-0141; both remain machine candidates, not manually verified.",
            },
            {
                "section": "amoc_and_contacts",
                "accepted_from": "annotator_b",
                "source_pages": [8],
                "decision": "Retain EASA AMOC/regulatory and Airbus technical contacts from the Remarks section.",
            },
            {
                "section": "classification",
                "accepted_from": "synthesized",
                "source_pages": list(range(1, 18)),
                "decision": "Normalize A320-family classification and action union; retain B evidence; mark machine-adjudicated, unreviewed, human_confirmed=false, gold_record=false, and manual_review_required.",
            },
        ],
        "overall_rationale": "Source-grounded machine reconciliation; a human reviewer must verify and approve before this record can enter the gold set.",
    }
    return record, decision


def build_2016(now: str) -> tuple[dict[str, Any], dict[str, Any]]:
    stem = "2016-0095__7f221fbcf3eea6a5"
    a_path = A_DIR / f"{stem}.annotation.json"
    b_path = B_DIR / f"{stem}.annotation.json"
    a = load(a_path)
    b = load(b_path)
    record = copy.deepcopy(b)

    record["ad_identity"]["version_label"] = "Original"
    record["ad_identity"]["design_approval_holder"].update(
        {"value": "Airbus", "raw_text": "AIRBUS"}
    )
    record["publication"]["subject"]["value"] = (
        "Wings – Flap Parts – Identification / Inspection [Wrong material]"
    )
    record["publication"]["type_model_designations"] = ["A380"]
    record["classification"]["airbus_families"] = ["A380"]
    record["classification"]["frequency"] = "mixed"

    req1 = requirement(record, "REQ-001")
    req1["action_types"] = ["test_or_check", "records_review"]
    req2 = requirement(record, "REQ-002")
    req2["applicability_group_ids"] = ["APP-002", "APP-003"]
    req3 = requirement(record, "REQ-003")
    req3["compliance_rules"][0]["logic"] = "conditional"
    req3["compliance_rules"][0]["conditions"] = [
        "A non-conforming-material part is detected during REQ-002"
    ]
    req5 = requirement(record, "REQ-005")
    req5["applicability_group_ids"] = ["APP-002", "APP-003"]
    req5_rule = req5["compliance_rules"][0]
    req5_rule["logic"] = "all"
    req5_rule["raw_text"] = (
        "From the effective date of this AD, prior to installation, determine "
        "that an Appendix-listed flap is serviceable"
    )
    req5_rule["initial_limits"].append(
        {
            "limit_id": "LIM-007",
            "relation": "from",
            "quantity": None,
            "unit": "calendar_date",
            "raw_value": "From the effective date of this AD",
            "reference_event": "effective date of this AD",
            "calendar_date": "2016-06-02",
            "evidence_ids": ["EV-004"],
        }
    )

    normalize_terminating_actions(record)
    record["classification"]["action_types"] = action_union(record)
    record["classification"]["terminating_action_present"] = False
    record["source_document"]["near_duplicate_cluster"] = (
        "near-2016-0095--2017-0013"
    )
    record["benchmark_metadata"]["duplicate_cluster_ids"] = [
        "near-2016-0095--2017-0013"
    ]

    machine_metadata(
        record,
        a,
        b,
        now,
        quality_flags=[
            "complex_table",
            "complex_applicability",
            "complex_compliance",
            "visual_transcription_used",
            "manual_review_required",
        ],
        uncertainty_flags=[
            "Machine-only adjudication requires human verification of every Appendix flap row and confirmation that no successor identity is encoded by the watermark."
        ],
        notes=[
            "Machine-adjudicated candidate only; not human-confirmed and not gold.",
            "All 118 middle-flap and 67 outboard-flap Appendix row mappings from Annotator B were retained after rendered-table inspection.",
            "The visible SUPERSEDED watermark supports lifecycle_status=superseded but does not identify a successor; relationships therefore remain empty.",
            "The frozen near-duplicate cluster with AD 2017-0013 is preserved exactly.",
        ],
    )

    decision = {
        "ad_number": "2016-0095",
        "logical_version_key": "2016-0095|UNCORRECTED",
        "file_instance_id": "7f221fbcf3eea6a5",
        "annotator_a_file": str(a_path.relative_to(ROOT)),
        "annotator_b_file": str(b_path.relative_to(ROOT)),
        "adjudicator_id": ADJUDICATOR_ID,
        "comparison_sha256": "d07d35b61baa74f72690535023d95f372390a9b8aba2ee6853ee5410ceaf4014",
        "decision_status": "machine_adjudicated_pending_human_review",
        "resolved_record_file": str(
            (OUT_DIR / f"{stem}.annotation.json").relative_to(ROOT)
        ),
        "manual_review_required": True,
        "sections": [
            {
                "section": "ad_identity",
                "accepted_from": "synthesized",
                "source_pages": [1],
                "decision": "Use normalized Airbus holder and Original label; preserve explicit Supersedure: None and lifecycle=superseded from the visible watermark.",
            },
            {
                "section": "publication",
                "accepted_from": "annotator_a",
                "source_pages": [1],
                "decision": "Use normalized subject/type values while preserving exact raw text, dates, ATA 57, EASA.A.110 and manufacturer.",
            },
            {
                "section": "applicability_groups",
                "accepted_from": "annotator_b",
                "source_pages": [1, 4, 5, 6],
                "decision": "Retain general aircraft plus distinct middle/outboard groups and every row-level LH/RH serial/date mapping.",
            },
            {
                "section": "unsafe_condition",
                "accepted_from": "annotator_b",
                "source_pages": [1],
                "decision": "Retain wrong-alloy defect, affected flap structures, reduced structural integrity and the stated mitigation chain.",
            },
            {
                "section": "requirements",
                "accepted_from": "synthesized",
                "source_pages": [2],
                "decision": "Use five atomic actions; identify by check/records review, apply SDI/contact/replacement/install clauses to both flap groups, preserve delegated replacement timing, and add both effective-date and pre-install limits.",
            },
            {
                "section": "definitions",
                "accepted_from": "annotator_b",
                "source_pages": [2, 4],
                "decision": "Keep N/A, starting-date, and serviceable-flap definitions; all are explicitly stated and affect table interpretation or installation eligibility.",
            },
            {
                "section": "exceptions",
                "accepted_from": "annotator_b",
                "source_pages": [2],
                "decision": "Retain the explicit unless-accomplished-previously exception for the initial identification and inspection actions.",
            },
            {
                "section": "previous_action_credit",
                "accepted_from": "both",
                "source_pages": [2],
                "decision": "No discrete previous-action credit is stated; keep an empty array distinct from the global exception.",
            },
            {
                "section": "referenced_publications",
                "accepted_from": "both",
                "source_pages": [2],
                "decision": "Retain Airbus SB A380-57-8111 original issue dated 2016-01-07 as required method with later approved revisions allowed.",
            },
            {
                "section": "relationships",
                "accepted_from": "source",
                "source_pages": [1],
                "decision": "Keep relationships empty: the watermark does not name a successor and the structured field explicitly says None; no correction edge is present.",
            },
            {
                "section": "amoc_and_contacts",
                "accepted_from": "annotator_b",
                "source_pages": [2, 3],
                "decision": "Retain EASA AMOC/regulatory and Airbus A380 technical contacts.",
            },
            {
                "section": "classification",
                "accepted_from": "synthesized",
                "source_pages": [1, 2, 4, 5, 6],
                "decision": "Use mixed frequency and exact action union; retain B evidence and frozen near-duplicate cluster; mark machine-adjudicated, unreviewed and manual_review_required.",
            },
        ],
        "overall_rationale": "Source-grounded machine reconciliation; a human reviewer must verify and approve before this record can enter the gold set.",
    }
    return record, decision


def build_2023(now: str) -> tuple[dict[str, Any], dict[str, Any]]:
    stem = "2023-0093R1__f8c89a351f146b17"
    a_path = A_DIR / f"{stem}.annotation.json"
    b_path = B_DIR / f"{stem}.annotation.json"
    a = load(a_path)
    b = load(b_path)
    record = copy.deepcopy(b)

    record["ad_identity"]["design_approval_holder"]["value"] = "Airbus"
    record["publication"]["ata_chapters"][0]["title"] = "Landing Gear"
    record["publication"]["ata_chapters"][1]["title"] = (
        "Electric and Electronic Common Installation"
    )

    # The source explicitly defines the three groups as a Definitions entry.
    record["definitions"].append(
        {
            "definition_id": "DEF-012",
            "term": "Groups",
            "definition_text": (
                "Group 1a aeroplanes have an affected BSCU and a type 1 relay "
                "installed; Group 1b aeroplanes have a non-affected BSCU and a "
                "type 1 relay installed; Group 2 aeroplanes are neither Group 1a "
                "nor Group 1b."
            ),
            "evidence_ids": ["EV-006"],
        }
    )

    # Preserve Appendix 1's provisional grouping rule as applicability logic,
    # not as a flat aircraft-model attribute.
    appendix_group = record["applicability_groups"][0]
    appendix_group["configuration_conditions"] = [
        "Until paragraph (1) inspection determines relay type, a listed-MSN aeroplane is provisionally considered Group 1a or Group 1b depending on the installed BSCU."
    ]
    appendix_group["boolean_logic"] = "mixed"
    if "EV-006" not in appendix_group["evidence_ids"]:
        appendix_group["evidence_ids"].append("EV-006")

    # The boilerplate is an exception, not previous-action credit. Paragraph
    # (7) remains a separately encoded conditional installation requirement.
    record["exceptions"] = [
        {
            "exception_id": "EXC-001",
            "text": "Required as indicated, unless accomplished previously.",
            "applies_to_requirement_ids": [
                f"REQ-{index:03d}" for index in range(1, 13)
            ],
            "evidence_ids": ["EV-009"],
        }
    ]
    record["previous_action_credit"] = []

    # Explicit prohibitions are classified as prohibitions. Paragraph (7) is
    # affirmative permission conditioned on serviceability, not a prohibition.
    for requirement_id in ("REQ-013", "REQ-014", "REQ-016"):
        requirement(record, requirement_id)["action_types"] = ["prohibition"]
    req15 = requirement(record, "REQ-015")
    req15["action_types"] = ["install"]
    req15["obligation"] = "conditional"

    # Keep all explicitly printed historical AD mentions, but only the current
    # document's revision edge is directional. None is a correction/successor
    # inference, and all remain machine candidates.
    for relationship in record["relationships"]:
        relationship["verification_status"] = "candidate"
        relationship["manually_verified"] = False

    normalize_terminating_actions(record)
    record["classification"]["airbus_families"] = ["A320neo family"]
    record["classification"]["frequency"] = "mixed"
    record["classification"]["compliance_complexity"] = "mixed"
    record["classification"]["action_types"] = action_union(record)
    record["classification"]["terminating_action_present"] = False

    # Repair assertion semantics after moving the boilerplate from credit to
    # exceptions, and add a detail assertion for the explicit Groups definition.
    assertion_by_path = {
        item["field_path"]: item for item in record["field_assertions"]
    }
    assertion_by_path["/exceptions"]["value_state"] = "present"
    assertion_by_path["/exceptions"]["evidence_ids"] = ["EV-009"]
    assertion_by_path["/previous_action_credit"]["value_state"] = (
        "absent_in_source"
    )
    assertion_by_path["/previous_action_credit"]["evidence_ids"] = []
    credit_detail = assertion_by_path["/previous_action_credit/0"]
    credit_detail["field_path"] = "/exceptions/0"
    credit_detail["value_state"] = "present"
    credit_detail["evidence_ids"] = ["EV-009"]
    record["field_assertions"].append(
        {
            "assertion_id": "AST-066",
            "field_path": "/definitions/11",
            "value_state": "present",
            "origin": "auto_extracted",
            "verification_status": "unreviewed",
            "confidence": 0.95,
            "evidence_ids": ["EV-006"],
            "annotator_id": ADJUDICATOR_ID,
            "derivation_rule": None,
            "input_field_paths": [],
            "notes": "Machine-adjudicated synthesis; human review pending.",
        }
    )

    machine_metadata(
        record,
        a,
        b,
        now,
        quality_flags=[
            "complex_table",
            "cross_page_clause",
            "complex_applicability",
            "complex_compliance",
            "visual_transcription_used",
            "manual_review_required",
        ],
        uncertainty_flags=[
            "Machine-only adjudication requires human verification of all 319 Appendix 1 MSNs, Appendix 2 MMEL effectivity rows, and historical-reference classification."
        ],
        notes=[
            "Machine-adjudicated candidate only; not human-confirmed and not gold.",
            "Annotator B's 16 atomic requirements were retained because they preserve both paragraph (1) table branches, four paragraph (4) actions, four paragraph (5) branches, and each installation rule separately.",
            "The 319 Appendix 1 MSNs and Appendix 2 MMEL rows were visually checked against rendered pages; human table verification remains required.",
            "The current AD revises AD 2023-0093. Mentions of AD 2022-0032R1, AD 2022-0032, and DGAC France AD F-1993-163-043 remain referenced_only; no direct supersedes, correction, or successor edge was inferred.",
        ],
    )

    decision = {
        "ad_number": "2023-0093R1",
        "logical_version_key": "2023-0093R1|UNCORRECTED",
        "file_instance_id": "f8c89a351f146b17",
        "annotator_a_file": str(a_path.relative_to(ROOT)),
        "annotator_b_file": str(b_path.relative_to(ROOT)),
        "adjudicator_id": ADJUDICATOR_ID,
        "comparison_sha256": "2911e5ed5d2d709320d1baee904032dbe5995c6ceee55277142968e551ae9d8c",
        "decision_status": "machine_adjudicated_pending_human_review",
        "resolved_record_file": str(
            (OUT_DIR / f"{stem}.annotation.json").relative_to(ROOT)
        ),
        "manual_review_required": True,
        "sections": [
            {
                "section": "ad_identity",
                "accepted_from": "synthesized",
                "source_pages": [1],
                "decision": "Preserve R1 identity and exact structured revision statement; normalize AIRBUS S.A.S. to Airbus; lifecycle remains unknown.",
            },
            {
                "section": "publication",
                "accepted_from": "synthesized",
                "source_pages": [1],
                "decision": "Retain the exact two-ATA subject, dates, EASA.A.064 and structured A319/A320/A321 types; normalize ATA titles to the printed chapter names.",
            },
            {
                "section": "applicability_groups",
                "accepted_from": "annotator_b_with_source_rule",
                "source_pages": [1, 2, 3, 4, 6],
                "decision": "Use all-aircraft, 319-MSN Appendix, Group 1a, Group 1b and Group 2 groups; add the explicit provisional grouping rule for listed MSNs before inspection.",
            },
            {
                "section": "unsafe_condition",
                "accepted_from": "annotator_b",
                "source_pages": [2, 3],
                "decision": "Retain the complete BSCU-failure, wrong-relay, freezing, braking-loss and runway-excursion chain plus the revision-specific inspection-report finding.",
            },
            {
                "section": "requirements",
                "accepted_from": "annotator_b_with_action_normalization",
                "source_pages": [3, 4, 5, 6, 7],
                "decision": "Use 16 atomic branches; preserve table-driven 12/24-month limits, conditional BSCU replacement, four MEL actions, four relay-replacement branches, three prohibitions, and paragraph (7) as conditional installation permission.",
            },
            {
                "section": "definitions",
                "accepted_from": "synthesized",
                "source_pages": [1, 2],
                "decision": "Retain B's 11 exact terms and add the explicitly printed Groups definition omitted from B.",
            },
            {
                "section": "exceptions",
                "accepted_from": "synthesized",
                "source_pages": [3],
                "decision": "Encode unless accomplished previously as one exception applying to REQ-001 through REQ-012; paragraph (7) is a requirement, not an exception.",
            },
            {
                "section": "previous_action_credit",
                "accepted_from": "annotator_a",
                "source_pages": [3],
                "decision": "Keep empty: the global previously-accomplished wording is not a publication-specific previous-action credit.",
            },
            {
                "section": "referenced_publications",
                "accepted_from": "annotator_b",
                "source_pages": [2, 4, 5, 7],
                "decision": "Retain eight version-specific AOT, MMEL, FOT and SB entries and their required-method or information roles, including later-approved-revision allowance.",
            },
            {
                "section": "relationships",
                "accepted_from": "annotator_b_with_direction_review",
                "source_pages": [1, 3],
                "decision": "Keep revises 2023-0093 plus three referenced_only historical mentions; explicitly reject the parser's direct supersedes-2022-0032R1 guess and add no correction/successor edge.",
            },
            {
                "section": "amoc_and_contacts",
                "accepted_from": "annotator_b",
                "source_pages": [5],
                "decision": "Retain the exact EASA AMOC and regulatory offices and Airbus 1IASA technical contact.",
            },
            {
                "section": "classification",
                "accepted_from": "synthesized",
                "source_pages": [1, 3, 4, 5, 6, 7],
                "decision": "Use A320neo family, ATA 32/92, mixed frequency/complexity and the exact requirement action union; retain B evidence and mark machine-adjudicated, unreviewed and manual_review_required.",
            },
        ],
        "overall_rationale": "Source-grounded machine reconciliation; a human reviewer must verify and approve before this record can enter the gold set.",
    }
    return record, decision


def main() -> None:
    now = utc_now()
    outputs = {
        "2010-0164__60596be378420b04": build_2010(now),
        "2016-0095__7f221fbcf3eea6a5": build_2016(now),
        "2023-0093R1__f8c89a351f146b17": build_2023(now),
    }
    for stem, (record, decision) in outputs.items():
        dump(OUT_DIR / f"{stem}.annotation.json", record)
        dump(DECISION_DIR / f"{stem}.adjudication.json", decision)

    selection = load(SELECTION_FILE)
    scoped_ids = {record["source_document"]["file_instance_id"] for record, _ in outputs.values()}
    for row in selection:
        row["double_annotation"] = row["file_instance_id"] in scoped_ids
    dump(SCOPE_SELECTION_FILE, selection)


if __name__ == "__main__":
    main()
