#!/usr/bin/env python3
"""Build Codex A3 machine-only adjudication candidates for four double annotations.

The frozen Annotator A and Annotator B submissions are read-only inputs.  Each
candidate remains unreviewed, human_confirmed=false, and gold_record=false.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
STEP3 = ROOT / "step3_pilot"
SUBMITTED_A = STEP3 / "submitted" / "annotator_a"
SUBMITTED_B = STEP3 / "submitted" / "annotator_b"
PAGE_TEXT = STEP3 / "page_text"
TEMPLATES = STEP3 / "adjudication" / "decision_templates"
OUT_RECORDS = STEP3 / "adjudication" / "machine_candidates"
OUT_DECISIONS = STEP3 / "adjudication" / "decisions"

ADJUDICATOR_ID = "codex-a3"
PROMPT_VERSION = "step3-machine-adjudication-1.0.0"

FILES = {
    "2019-0183": "2019-0183__5577514a19f6917c",
    "2020-0085R1": "2020-0085R1__5ced2074d6402f32",
    "2025-0068": "2025-0068__6e80e67e640ba6d1",
    "2026-0017": "2026-0017__1f3af1a66dad0ea4",
}

SECTION_PATHS = (
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

SECTION_NAMES = tuple(path[1:] for path in SECTION_PATHS)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def evidence_ids(value: Any) -> list[str]:
    """Collect evidence IDs recursively, retaining first-seen order."""

    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "evidence_ids" and isinstance(item, list):
                found.extend(x for x in item if isinstance(x, str))
            elif key not in {"field_assertions", "evidence_spans"}:
                found.extend(evidence_ids(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(evidence_ids(item))
    return unique(found)


def load_pages(stem: str) -> dict[int, dict[str, Any]]:
    pages: dict[int, dict[str, Any]] = {}
    path = PAGE_TEXT / f"{stem}.pages.jsonl"
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            page = json.loads(line)
            pages[page["page_number"]] = page
    return pages


def add_native_evidence(
    record: dict[str, Any],
    pages: dict[int, dict[str, Any]],
    *,
    page_number: int,
    section: str,
    clause_path: str,
    start_marker: str,
    end_marker: str | None = None,
) -> str:
    """Append one exact evidence span selected from frozen native page text."""

    page = pages[page_number]
    text = page["text"]
    start = text.index(start_marker)
    if end_marker is None:
        end = start + len(start_marker)
    else:
        end = text.index(end_marker, start) + len(end_marker)
    quote = text[start:end]
    next_number = len(record["evidence_spans"]) + 1
    new_id = f"EV-{next_number:03d}"
    record["evidence_spans"].append(
        {
            "evidence_id": new_id,
            "source_file_instance_id": record["source_document"]["file_instance_id"],
            "page_number": page_number,
            "printed_page_label": f"Page {page_number} of {record['source_document']['page_count']}",
            "section": section,
            "section_raw": None,
            "clause_path": clause_path,
            "exact_quote": quote,
            "start_char": start,
            "end_char": end,
            "page_text_sha256": page["page_text_sha256"],
            "bbox_normalized": None,
            "extraction_method": "native_text",
            "quality": "exact",
            "table_context": None,
            "annotation_note": None,
        }
    )
    return new_id


def no_termination() -> dict[str, Any]:
    return {
        "state": "not_stated",
        "present": False,
        "scope": "none",
        "action_text": None,
        "terminates_requirement_ids": [],
        "evidence_ids": [],
    }


def normalize_nonterminating_requirements(record: dict[str, Any]) -> None:
    for requirement in record["requirements"]:
        termination = requirement["terminating_action"]
        if termination["state"] == "not_stated":
            requirement["terminating_action"] = no_termination()


def renumber_requirements(record: dict[str, Any]) -> None:
    """Renumber requirement, compliance, and limit IDs after atomic splitting."""

    requirements = record["requirements"]
    old_to_new: dict[str, str] = {}
    for index, requirement in enumerate(requirements, start=1):
        old = requirement["requirement_id"]
        new = f"REQ-{index:03d}"
        if old not in old_to_new:
            old_to_new[old] = new
        requirement["requirement_id"] = new

    # The inserted paragraph (8) installation requirement deliberately starts
    # with the same cloned ID.  All later links are set explicitly below.
    for requirement in requirements:
        parent = requirement["parent_requirement_id"]
        if parent is not None:
            requirement["parent_requirement_id"] = old_to_new.get(parent, parent)
        requirement["follow_on_requirement_ids"] = [
            old_to_new.get(item, item) for item in requirement["follow_on_requirement_ids"]
        ]
        termination = requirement["terminating_action"]
        termination["terminates_requirement_ids"] = [
            old_to_new.get(item, item) for item in termination["terminates_requirement_ids"]
        ]

    cmp_index = 0
    limit_index = 0
    for requirement in requirements:
        for rule in requirement["compliance_rules"]:
            cmp_index += 1
            rule["compliance_id"] = f"CMP-{cmp_index:03d}"
            for bucket in ("initial_limits", "repetitive_intervals", "grace_periods"):
                for limit in rule[bucket]:
                    limit_index += 1
                    limit["limit_id"] = f"LIM-{limit_index:03d}"


def action_union(record: dict[str, Any]) -> list[str]:
    return unique(
        action
        for requirement in record["requirements"]
        for action in requirement["action_types"]
    )


def add_optional_no_deadline_rules(record: dict[str, Any]) -> None:
    """Ground optional paragraphs (6)-(8) without inventing a deadline.

    The source states what each elected terminating action or acceptable method
    accomplishes, but it gives no mandatory compliance time for electing it.
    A not_stated rule keeps that distinction explicit while satisfying the gold
    gate's requirement that every requirement carry a reviewed compliance-rule
    object.
    """

    existing_numbers = [
        int(rule["compliance_id"].split("-")[1])
        for requirement in record["requirements"]
        for rule in requirement["compliance_rules"]
    ]
    next_number = max(existing_numbers, default=0)
    rules = {
        "(6)": {
            "raw_text": (
                "Modification of an affected part on an aeroplane, accomplished in accordance "
                "with the instructions of the modification SB, constitutes terminating action "
                "for the initial and repetitive inspections as required by paragraphs (1) and "
                "(5) of this AD, as applicable, for that galley."
            ),
            "conditions": [
                "If the operator elects to use the paragraph (6) terminating action"
            ],
        },
        "(7)": {
            "raw_text": (
                "Modification of all affected parts on an aeroplane, accomplished in accordance "
                "with the instructions of the modification SB, constitutes terminating action "
                "for the initial and repetitive inspections as required by paragraphs (1) and "
                "(5) of this AD, as applicable, for that aeroplane, provided that no affected "
                "parts are re-installed on that aeroplane after that modification."
            ),
            "conditions": [
                "If the operator elects to use the paragraph (7) terminating action",
                "No affected parts are re-installed on that aeroplane after modification",
            ],
        },
        "(8)": {
            "raw_text": (
                "For Group 1 and Group 2 aeroplanes: Replacement of a forward-facing galley of "
                "an aeroplane with a galley which has been modified in accordance with approved "
                "instructions, which include the accomplishment of the post-modification SB "
                "instructions, constitutes terminating action for the initial and repetitive "
                "inspections as required by paragraphs (1), (2) and (5) of this AD, as applicable, "
                "for that galley of that aeroplane."
            ),
            "conditions": [
                "If the operator elects to use the paragraph (8) acceptable method",
                "Replacement galley was modified under approved instructions including the post-modification SB instructions",
            ],
        },
    }
    for requirement in record["requirements"]:
        paragraph = requirement["paragraph_reference"]
        if paragraph not in rules:
            continue
        if requirement["compliance_rules"]:
            raise ValueError(
                f"{record['ad_identity']['ad_number']} {paragraph} unexpectedly already has a compliance rule"
            )
        next_number += 1
        rule = rules[paragraph]
        requirement["compliance_rules"] = [
            {
                "compliance_id": f"CMP-{next_number:03d}",
                "state": "not_stated",
                "raw_text": rule["raw_text"],
                "logic": "conditional",
                "conditions": rule["conditions"],
                "initial_limits": [],
                "is_repetitive": False,
                "repetitive_intervals": [],
                "grace_periods": [],
                "evidence_ids": ["EV-008"],
            }
        ]


def combine_machine_metadata(
    record: dict[str, Any],
    annotator_a: dict[str, Any],
    annotator_b: dict[str, Any],
    adjudicated_at: str,
    notes: list[str],
    *,
    uncertainty_flags: list[str] | None = None,
) -> None:
    a_meta = annotator_a["annotation_metadata"]
    b_meta = annotator_b["annotation_metadata"]
    a_person = copy.deepcopy(a_meta["annotators"][0])
    b_person = copy.deepcopy(b_meta["annotators"][0])
    record["annotation_metadata"] = {
        "guideline_version": "1.0.0",
        "record_status": "adjudicated",
        "creation_method": "hybrid",
        "machine_provenance": {
            "system": "OpenAI Codex",
            "model": "GPT-5",
            "prompt_or_rules_version": PROMPT_VERSION,
            "generated_at": adjudicated_at,
        },
        "annotators": [
            a_person,
            b_person,
            {
                "annotator_id": ADJUDICATOR_ID,
                "role": "adjudicator",
                "started_at": adjudicated_at,
                "submitted_at": adjudicated_at,
            },
        ],
        "events": copy.deepcopy(a_meta["events"])
        + copy.deepcopy(b_meta["events"])
        + [
            {
                "event_type": "adjudicated",
                "actor_id": ADJUDICATOR_ID,
                "timestamp": adjudicated_at,
                "rationale": (
                    "Machine-only reconciliation of frozen independent A/B records against "
                    "the official PDF, frozen page text, reviewer-QC packet, schema, "
                    "guidelines, and comparison report; human confirmation remains required."
                ),
            }
        ],
        "quality_flags": unique(
            list(a_meta.get("quality_flags", []))
            + list(b_meta.get("quality_flags", []))
            + ["manual_review_required"]
        ),
        "uncertainty_flags": uncertainty_flags or [],
        "notes": [
            "Machine-adjudicated candidate only; not human-confirmed and not gold.",
            *notes,
        ],
        "source_text_sha256": record["source_document"]["normalized_text_sha256"],
        "created_at": min(
            value
            for value in (a_meta.get("created_at"), b_meta.get("created_at"), adjudicated_at)
            if value is not None
        ),
        "updated_at": adjudicated_at,
    }
    record["classification"]["human_confirmed"] = False
    record["benchmark_metadata"]["gold_record"] = False


def assertion(
    assertion_id: str,
    field_path: str,
    value_state: str,
    ids: list[str],
    *,
    confidence: float,
) -> dict[str, Any]:
    return {
        "assertion_id": assertion_id,
        "field_path": field_path,
        "value_state": value_state,
        "origin": "auto_extracted",
        "verification_status": "unreviewed",
        "confidence": confidence,
        "evidence_ids": unique(ids),
        "annotator_id": ADJUDICATOR_ID,
        "derivation_rule": None,
        "input_field_paths": [],
        "notes": "Machine-adjudicated synthesis; assertion remains unreviewed pending human review.",
    }


def rebuild_assertions(record: dict[str, Any]) -> None:
    pending: list[tuple[str, str, list[str], float]] = []

    for path in SECTION_PATHS:
        key = path[1:]
        value = record[key]
        state = "absent_in_source" if isinstance(value, list) and not value else "present"
        pending.append((path, state, evidence_ids(value), 0.96))

    # Critical scalar and item-level assertions supplement the exact-root
    # completion markers without claiming human acceptance.
    details: list[tuple[str, Any, list[str], float, str | None]] = [
        ("/ad_identity/ad_number", record["ad_identity"]["ad_number"], record["ad_identity"]["evidence_ids"], 0.99, None),
        ("/ad_identity/design_approval_holder", record["ad_identity"]["design_approval_holder"], record["ad_identity"]["design_approval_holder"]["evidence_ids"], 0.99, None),
        ("/ad_identity/supersedure_statement", record["ad_identity"]["supersedure_statement"], record["ad_identity"]["supersedure_statement"]["evidence_ids"], 0.99, None),
        ("/publication/subject", record["publication"]["subject"], record["publication"]["subject"]["evidence_ids"], 0.99, None),
        ("/publication/issue_date", record["publication"]["issue_date"], record["publication"]["issue_date"]["evidence_ids"], 0.99, None),
        ("/publication/effective_date", record["publication"]["effective_date"], record["publication"]["effective_date"]["evidence_ids"], 0.99, None),
        ("/publication/type_model_designations", record["publication"]["type_model_designations"], evidence_ids(record["ad_identity"]), 0.98, None),
        ("/publication/tcds_numbers", record["publication"]["tcds_numbers"], evidence_ids(record["publication"]), 0.98, None),
        ("/publication/foreign_ad", record["publication"]["foreign_ad"], record["publication"]["foreign_ad"]["evidence_ids"], 0.99, "not_applicable"),
        ("/classification/action_types", record["classification"]["action_types"], record["classification"]["evidence_ids"], 0.96, None),
        ("/classification/frequency", record["classification"]["frequency"], record["classification"]["evidence_ids"], 0.95, None),
        ("/classification/compliance_complexity", record["classification"]["compliance_complexity"], record["classification"]["evidence_ids"], 0.95, None),
    ]

    for collection_name in (
        "applicability_groups",
        "definitions",
        "requirements",
        "exceptions",
        "previous_action_credit",
        "referenced_publications",
        "relationships",
        "amoc_and_contacts",
    ):
        for index, item in enumerate(record[collection_name]):
            details.append(
                (
                    f"/{collection_name}/{index}",
                    item,
                    item.get("evidence_ids", []),
                    0.95 if collection_name == "applicability_groups" else 0.97,
                    None,
                )
            )

    for path, value, ids, confidence, explicit_state in details:
        if explicit_state is not None:
            state = explicit_state
        elif isinstance(value, list) and not value:
            state = "absent_in_source"
        else:
            state = "present"
        pending.append((path, state, ids, confidence))

    record["field_assertions"] = [
        assertion(f"AST-{index:03d}", path, state, ids, confidence=confidence)
        for index, (path, state, ids, confidence) in enumerate(pending, start=1)
    ]


def exact_contacts(record: dict[str, Any], *, modern: bool) -> None:
    if modern:
        regulatory_org = "EASA Safety Information Section, Certification Directorate"
        regulatory_text = (
            "Enquiries regarding this AD should be referred to the EASA Safety Information "
            "Section, Certification Directorate. E-mail: ADs@easa.europa.eu."
        )
        technical_org = "AIRBUS – Airworthiness Office – 1IASA"
        technical_text = (
            "For any question concerning the technical content of the requirements in this AD, "
            "please contact: AIRBUS – Airworthiness Office – 1IASA; E-mail: "
            "account.airworth-eas@airbus.com."
        )
        technical_condition = "Questions concerning the technical content of the requirements in this AD"
    else:
        regulatory_org = "EASA Programming and Continued Airworthiness Information Section, Certification Directorate"
        regulatory_text = (
            "Enquiries regarding this AD should be referred to the EASA Programming and Continued "
            "Airworthiness Information Section, Certification Directorate. E-mail: ADs@easa.europa.eu."
        )
        technical_org = "Airbus"
        technical_text = (
            "For any question concerning the technical content of the requirements in this AD, "
            "please contact: continued-airworthiness.a350@airbus.com."
        )
        technical_condition = "Questions concerning the technical content of the requirements in this AD"

    record["amoc_and_contacts"][0].update(
        {
            "authority_or_organization": "EASA",
            "contact_text": (
                "If requested and appropriately substantiated, EASA can approve Alternative "
                "Methods of Compliance for this AD."
            ),
            "conditions": ["Requested and appropriately substantiated"],
        }
    )
    record["amoc_and_contacts"][1].update(
        {
            "authority_or_organization": regulatory_org,
            "contact_text": regulatory_text,
            "conditions": ["Enquiries regarding this AD"],
        }
    )
    record["amoc_and_contacts"][2].update(
        {
            "authority_or_organization": technical_org,
            "contact_text": technical_text,
            "conditions": [technical_condition],
        }
    )


def build_2019(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    record = copy.deepcopy(b)
    pages = load_pages(FILES["2019-0183"])
    generic_exception_ev = add_native_evidence(
        record,
        pages,
        page_number=2,
        section="required_actions_and_compliance_times",
        clause_path="Required Action(s) and Compliance Time(s)",
        start_marker="Required as indicated, unless accomplished previously:",
    )

    record["ad_identity"]["design_approval_holder"].update(
        {"value": "AIRBUS", "raw_text": "AIRBUS"}
    )
    record["publication"]["type_model_designations"] = ["A350 aeroplanes"]
    record["unsafe_condition"]["causes"] = []
    record["exceptions"] = [
        {
            "exception_id": "EXC-001",
            "text": "Required as indicated, unless accomplished previously.",
            "applies_to_requirement_ids": ["REQ-001"],
            "evidence_ids": [generic_exception_ev],
        }
    ]
    record["previous_action_credit"] = []
    exact_contacts(record, modern=False)
    normalize_nonterminating_requirements(record)
    record["classification"]["action_types"] = action_union(record)
    record["classification"]["evidence_ids"] = unique(
        record["classification"]["evidence_ids"] + [generic_exception_ev]
    )
    return record


def build_2020(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    record = copy.deepcopy(b)
    pages = load_pages(FILES["2020-0085R1"])
    production_ev = add_native_evidence(
        record,
        pages,
        page_number=2,
        section="reason",
        clause_path="Reason / production quality deficiency",
        start_marker="After EASA AD 2015-0021 was issued, a production quality deficiency was identified by Airbus",
        end_marker="CFM56-5A/5B engines.",
    )
    generic_exception_ev = add_native_evidence(
        record,
        pages,
        page_number=3,
        section="required_actions_and_compliance_times",
        clause_path="Required Action(s) and Compliance Time(s)",
        start_marker="Required as indicated, unless accomplished previously:",
    )

    record["ad_identity"]["design_approval_holder"].update(
        {"value": "AIRBUS", "raw_text": "AIRBUS"}
    )
    record["publication"]["type_model_designations"] = [
        "A318, A319, A320 and A321 aeroplanes"
    ]

    group_ev = record["definitions"][3]["evidence_ids"]
    record["definitions"] = record["definitions"][:3] + [
        {
            "definition_id": "DEF-004",
            "term": "Group 1 aeroplanes",
            "definition_text": "Aeroplanes that have an affected part installed.",
            "evidence_ids": group_ev,
        },
        {
            "definition_id": "DEF-005",
            "term": "Group 2 aeroplanes",
            "definition_text": "Aeroplanes that do not have an affected part installed.",
            "evidence_ids": group_ev,
        },
        {
            **copy.deepcopy(record["definitions"][4]),
            "definition_id": "DEF-006",
        },
        {
            **copy.deepcopy(record["definitions"][5]),
            "definition_id": "DEF-007",
        },
    ]

    app2 = record["applicability_groups"][1]
    app2["configuration_conditions"] = [
        "No affected aft engine mount assembly is installed.",
        (
            "Alternatively established as Group 2 when Airbus modification 158435 was embodied "
            "in production and no affected part was installed after manufacture; reliable "
            "maintenance records may establish that condition."
        ),
    ]
    app2["boolean_logic"] = "mixed"
    app2["evidence_ids"] = unique(app2["evidence_ids"] + ["EV-021"])

    record["unsafe_condition"].update(
        {
            "raw_reason_text": (
                "Several aft engine mount inner retainers were found broken in service. The main "
                "crack-initiation cause was vibration dynamic effect, with dull-finish pitting as "
                "an aggravating factor. A production quality deficiency also affected delivery of "
                "inner retainer P/N 238-0252-505. If not detected and corrected, the condition could "
                "cause in-flight loss of an aft engine mount link and damage to the aeroplane."
            ),
            "causes": [
                "Vibration dynamic effect initiating cracks in the retainers.",
                "Dull-surface-finish pitting as an aggravating factor.",
                "Production quality deficiency affecting inner retainer P/N 238-0252-505.",
            ],
            "evidence_ids": unique(
                record["unsafe_condition"]["evidence_ids"] + [production_ev]
            ),
        }
    )

    original = record["requirements"]
    operate_dull = copy.deepcopy(original[4])
    operate_dull["action_types"] = ["prohibition"]
    operate_dull["action_text"] = (
        "Do not operate any aeroplane having a dull-finish aft engine mount inner retainer installed."
    )
    install_dull = copy.deepcopy(original[4])
    install_dull["action_types"] = ["prohibition", "install"]
    install_dull["action_text"] = (
        "Do not install a dull-finish aft engine mount inner retainer on any aeroplane."
    )
    record["requirements"] = original[:4] + [operate_dull, install_dull] + original[5:]
    for requirement in record["requirements"]:
        if requirement["paragraph_reference"] in {"(10), (10.1)–(10.3)", "(11.1)", "(11.2)"}:
            requirement["action_types"] = ["prohibition", "install"]
    renumber_requirements(record)
    # Correct links whose cloned IDs cannot be resolved by the generic mapping.
    record["requirements"][10]["follow_on_requirement_ids"] = ["REQ-012"]
    record["requirements"][11]["parent_requirement_id"] = "REQ-011"

    record["exceptions"] = [
        {
            "exception_id": "EXC-001",
            "text": "Required as indicated, unless accomplished previously.",
            "applies_to_requirement_ids": [
                requirement["requirement_id"] for requirement in record["requirements"]
            ],
            "evidence_ids": [generic_exception_ev],
        }
    ]
    specific_credit = copy.deepcopy(b["previous_action_credit"][0])
    specific_credit["credit_id"] = "CRD-001"
    record["previous_action_credit"] = [specific_credit]
    exact_contacts(record, modern=True)
    normalize_nonterminating_requirements(record)
    record["classification"]["action_types"] = action_union(record)
    record["classification"]["evidence_ids"] = unique(
        record["classification"]["evidence_ids"]
        + [production_ev, generic_exception_ev]
    )
    return record


def build_near_duplicate(
    ad_number: str,
    a: dict[str, Any],
    b: dict[str, Any],
) -> dict[str, Any]:
    record = copy.deepcopy(b)
    record["definitions"][0]["definition_text"] = (
        "Forward-facing galleys having a Part Number (P/N) as listed in Appendix 1 of this AD."
    )
    # B's visual transcription is authoritative for the current Appendix list:
    # 815 entries in 2025, plus 6019F2-000001 in 2026.  Do not import any
    # struck-through row into the active part-number collection.
    assert len(record["applicability_groups"][0]["part_numbers"]) == (
        815 if ad_number == "2025-0068" else 816
    )
    assert record["source_document"]["near_duplicate_cluster"] == (
        "near-2024-0038--2025-0068--2026-0017"
    )
    assert record["benchmark_metadata"]["duplicate_cluster_ids"] == [
        "near-2024-0038--2025-0068--2026-0017"
    ]
    exact_contacts(record, modern=True)
    normalize_nonterminating_requirements(record)
    add_optional_no_deadline_rules(record)
    record["classification"]["action_types"] = action_union(record)
    return record


DECISION_SUMMARIES: dict[str, dict[str, tuple[str, list[int], str]]] = {
    "2019-0183": {
        "ad_identity": ("synthesized", [1], "Keep the printed AIRBUS holder and explicit Supersedure: None; create no positive relationship edge."),
        "publication": ("synthesized", [1], "Use the exact A350 aeroplanes type/model wording, issue/effective dates, ATA 92, TCDS and manufacturer."),
        "applicability_groups": ("annotator_b", [1], "Keep A350-941, all MSNs, excluding production modification 111827."),
        "definitions": ("annotator_b", [1], "Retain separate definitions for the SB and Airbus date of manufacture."),
        "unsafe_condition": ("synthesized", [1, 2], "Remove the inferred drainage-capacity cause; retain the observed drainage limitation, overflow, contamination and flight-control consequences."),
        "requirements": ("annotator_b", [2], "Keep one atomic modification requirement with the 80-month limit and no unstated terminating action."),
        "exceptions": ("annotator_a_with_new_evidence", [2], "Keep the standard explicit unless-accomplished-previously exception and attach a dedicated source span."),
        "previous_action_credit": ("source_absent", [2], "No separately granted previous-action credit is stated."),
        "referenced_publications": ("annotator_b", [2], "Keep Airbus SB A350-92-P014 original issue and its later-approved-revision allowance."),
        "relationships": ("source_absent", [1], "Supersedure is explicitly None, so no positive relationship is created."),
        "amoc_and_contacts": ("synthesized", [2], "Preserve full EASA AMOC/regulatory and Airbus technical-contact wording."),
        "classification": ("synthesized", [1, 2], "Classify as simple one-time ATA 92 modification; keep human_confirmed=false and manual review required."),
    },
    "2020-0085R1": {
        "ad_identity": ("synthesized", [1], "Use Revision 1 identity, printed AIRBUS holder, and the full structured revises sentence."),
        "publication": ("synthesized", [1], "Preserve exact A318, A319, A320 and A321 aeroplanes wording plus both printed effective-date contexts."),
        "applicability_groups": ("annotator_b_with_source_correction", [1, 2, 3, 4, 7], "Keep Group 1, Group 2 and 4-lugs populations; encode paragraph (6) as a Group 2 classification route, not an exception."),
        "definitions": ("synthesized", [1, 2, 3, 7], "Split Group 1 and Group 2 definitions and retain affected/serviceable parts, SB, 4-lugs engine and manufacture date."),
        "unsafe_condition": ("synthesized", [2, 3], "Retain vibration, dull-finish pitting and the stated P/N 238-0252-505 production-quality deficiency without adding an unstated causal chain."),
        "requirements": ("annotator_b_with_atomic_split", [3, 4, 5], "Split paragraph (8) operation and installation prohibitions, yielding 12 atomic requirements with preserved timing and dependency links."),
        "exceptions": ("annotator_a_with_new_evidence", [3], "Keep the blanket unless-accomplished-previously exception; paragraph (6) is not an exception."),
        "previous_action_credit": ("annotator_b", [4], "Keep only the explicitly labelled paragraph (5) credit for A320-71-1071 original issue or revision 01."),
        "referenced_publications": ("annotator_b", [5, 6], "Retain all 18 revision-specific AOT and SB records with their source roles."),
        "relationships": ("annotator_b", [1], "Keep only the explicit revises edge to 2020-0085; the older 2017-0251 clause is historical."),
        "amoc_and_contacts": ("synthesized", [6], "Preserve full EASA AMOC/regulatory and Airbus technical-contact wording."),
        "classification": ("synthesized", [1, 3, 4, 5, 7], "Classify as mixed, table-driven/complex inspection, replacement, modification, prohibition, installation and contact action; human review remains required."),
    },
    "2025-0068": {
        "ad_identity": ("annotator_b", [1], "Use printed identity and supersedes edge to 2024-0038; the visible SUPERSEDED watermark supports lifecycle status only and names no successor."),
        "publication": ("annotator_b", [1], "Keep exact type/model wording, dates, ATA 25, TCDS and Airbus manufacturer normalization."),
        "applicability_groups": ("annotator_b_visual", list(range(1, 11)), "Retain three groups and the visually checked 815-current-P/N set; exclude all 11 struck Appendix rows and preserve near-duplicate provenance."),
        "definitions": ("synthesized", [1, 2, 6, 7, 8, 9, 10], "Use the source affected-part wording and retain inspection/modification SB, manufacture-date and group definitions."),
        "unsafe_condition": ("annotator_b", [2], "Retain work-deck/retainer-block damage, trolley-detachment risk and escape-path consequence without inferring a cause."),
        "requirements": ("annotator_b", [3, 4], "Keep eight paragraph-level requirements with all Table 1/Table 2 timing branches, repetition and explicit terminating actions."),
        "exceptions": ("annotator_b", [3], "Keep the standard previous-accomplishment exception and the Note 1 manufacture-date substitution."),
        "previous_action_credit": ("source_absent", [3, 4], "No separately labelled revision-specific previous-action credit is stated."),
        "referenced_publications": ("annotator_b", [4], "Retain 11 revision-specific inspection and modification SB records."),
        "relationships": ("annotator_b", [1, 2], "Keep only explicit supersedes and retains-requirements-of edges to 2024-0038; both remain machine candidates."),
        "amoc_and_contacts": ("synthesized", [5], "Preserve full EASA AMOC/regulatory and Airbus technical-contact wording."),
        "classification": ("synthesized", list(range(1, 11)), "Classify as mixed table-driven complex compliance with visual transcription; keep human_confirmed=false and manual review required."),
    },
    "2026-0017": {
        "ad_identity": ("annotator_b", [1], "Use printed identity and explicit supersedes statement to 2025-0068; do not infer current/latest lifecycle status."),
        "publication": ("annotator_b", [1], "Keep exact type/model wording, dates, ATA 25, TCDS and Airbus manufacturer normalization."),
        "applicability_groups": ("annotator_b_visual", list(range(1, 11)), "Retain three groups and the visually checked 816-current-P/N set, including bold non-struck 6019F2-000001; exclude all 11 struck rows."),
        "definitions": ("synthesized", [1, 2, 6, 7, 8, 9, 10], "Use source affected-part wording and retain inspection/modification SB, reference-date and group definitions."),
        "unsafe_condition": ("annotator_b", [2], "Retain work-deck/retainer-block damage, trolley-detachment risk and escape-path consequence without inferring a cause."),
        "requirements": ("annotator_b", [3, 4], "Keep eight paragraph-level requirements with the added 6019F2 timing branches, repetition and explicit terminating actions."),
        "exceptions": ("annotator_b", [3], "Keep the standard previous-accomplishment exception and the Note 1 reference-date substitution."),
        "previous_action_credit": ("source_absent", [3, 4], "No separately labelled revision-specific previous-action credit is stated."),
        "referenced_publications": ("annotator_b", [5], "Retain 13 revision-specific inspection and modification SB records."),
        "relationships": ("annotator_b", [1, 2, 3], "Keep only explicit supersedes and retains-requirements-of edges to 2025-0068; both remain machine candidates."),
        "amoc_and_contacts": ("synthesized", [5], "Preserve full EASA AMOC/regulatory and Airbus technical-contact wording."),
        "classification": ("synthesized", list(range(1, 11)), "Classify as mixed table-driven complex compliance with visual transcription; preserve near-duplicate provenance and require human review."),
    },
}


def decision_log(
    ad_number: str,
    stem: str,
    record: dict[str, Any],
) -> dict[str, Any]:
    template = read_json(TEMPLATES / f"{stem}.adjudication.json")
    summaries = DECISION_SUMMARIES[ad_number]
    assert tuple(summaries) == SECTION_NAMES
    return {
        "ad_number": ad_number,
        "logical_version_key": record["ad_identity"]["logical_version_key"],
        "file_instance_id": record["source_document"]["file_instance_id"],
        "annotator_a_file": f"step3_pilot/submitted/annotator_a/{stem}.annotation.json",
        "annotator_b_file": f"step3_pilot/submitted/annotator_b/{stem}.annotation.json",
        "adjudicator_id": ADJUDICATOR_ID,
        "comparison_sha256": template["comparison_sha256"],
        "decision_status": "machine_adjudicated_pending_human_review",
        "resolved_record_file": f"step3_pilot/adjudication/machine_candidates/{stem}.annotation.json",
        "manual_review_required": True,
        "sections": [
            {
                "section": section,
                "accepted_from": accepted_from,
                "source_pages": pages,
                "decision": decision,
            }
            for section, (accepted_from, pages, decision) in summaries.items()
        ],
        "overall_rationale": (
            "Source-grounded machine reconciliation; a human reviewer must verify and approve "
            "before this record can enter the gold set."
        ),
    }


def main() -> None:
    adjudicated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    OUT_RECORDS.mkdir(parents=True, exist_ok=True)
    OUT_DECISIONS.mkdir(parents=True, exist_ok=True)

    for ad_number, stem in FILES.items():
        a_path = SUBMITTED_A / f"{stem}.annotation.json"
        b_path = SUBMITTED_B / f"{stem}.annotation.json"
        annotator_a = read_json(a_path)
        annotator_b = read_json(b_path)

        if ad_number == "2019-0183":
            record = build_2019(annotator_a, annotator_b)
            notes = [
                "The standard previous-accomplishment clause is represented as an exception, matching pilot convention.",
                "Supersedure is explicitly None; no relationship was inferred.",
            ]
            uncertainty = []
        elif ad_number == "2020-0085R1":
            record = build_2020(annotator_a, annotator_b)
            notes = [
                "Paragraph (8) was split into atomic operation and installation prohibitions.",
                "Only the explicit revises edge to 2020-0085 is retained; 2017-0251 appears only in the older-AD history within the cover sentence.",
            ]
            uncertainty = [
                "Machine-only adjudication requires human verification of dense timing, prohibition, and table logic."
            ]
        else:
            record = build_near_duplicate(ad_number, annotator_a, annotator_b)
            pn_count = len(record["applicability_groups"][0]["part_numbers"])
            notes = [
                f"All 10 rendered pages were checked; {pn_count} current Appendix P/N entries are retained and 11 visibly struck rows are excluded.",
                "Near-duplicate component provenance is preserved exactly as near-2024-0038--2025-0068--2026-0017.",
                "Relationship candidates are limited to explicit source wording and remain manually_verified=false.",
            ]
            uncertainty = [
                "Machine-only adjudication requires human verification of the dense Appendix transcription and table-driven timing logic."
            ]

        combine_machine_metadata(
            record,
            annotator_a,
            annotator_b,
            adjudicated_at,
            notes,
            uncertainty_flags=uncertainty,
        )
        rebuild_assertions(record)

        record_path = OUT_RECORDS / f"{stem}.annotation.json"
        decision_path = OUT_DECISIONS / f"{stem}.adjudication.json"
        write_json(record_path, record)
        write_json(decision_path, decision_log(ad_number, stem, record))
        print(f"WROTE {record_path.relative_to(ROOT)}")
        print(f"WROTE {decision_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
