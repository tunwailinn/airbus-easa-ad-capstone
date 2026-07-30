#!/usr/bin/env python3
"""Build three independent blind Annotator-B Step 3 working records.

This script is intentionally limited to the assigned Annotator-B templates and
their frozen blind page-text packets.  It does not read another annotation.
"""

from __future__ import annotations

import argparse
import copy
import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "step3_pilot"
TEMPLATE_DIR = PILOT / "annotations" / "annotator_b"
PACKET_DIR = PILOT / "packets" / "blind"
OUTPUT_DIR = PILOT / "submitted" / "annotator_b"
ANNOTATOR_ID = "codex-b2"
SECTION_PATHS = [
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
]

ASSIGNMENTS = {
    "2019-0183": {
        "template": "2019-0183__5577514a19f6917c.annotation.json",
        "packet": "2019-0183__5577514a19f6917c.blind-packet.json",
    },
    "2020-0085R1": {
        "template": "2020-0085R1__5ced2074d6402f32.annotation.json",
        "packet": "2020-0085R1__5ced2074d6402f32.blind-packet.json",
    },
    "2017-0013": {
        "template": "2017-0013__67c94127f7b8e53d.annotation.json",
        "packet": "2017-0013__67c94127f7b8e53d.blind-packet.json",
    },
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalized(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).replace("\u00ad", "")
    return " ".join(value.split())


def normalized_with_raw_map(value: str) -> tuple[str, list[int], list[int]]:
    """Return whitespace-normalized text plus raw start/end per output char."""

    chars: list[str] = []
    starts: list[int] = []
    ends: list[int] = []
    for raw_index, raw_char in enumerate(value):
        for char in unicodedata.normalize("NFKC", raw_char):
            if char == "\u00ad":
                continue
            if char.isspace():
                if not chars:
                    continue
                if chars[-1] == " ":
                    ends[-1] = raw_index + 1
                else:
                    chars.append(" ")
                    starts.append(raw_index)
                    ends.append(raw_index + 1)
            else:
                chars.append(char)
                starts.append(raw_index)
                ends.append(raw_index + 1)
    if chars and chars[-1] == " ":
        chars.pop()
        starts.pop()
        ends.pop()
    return "".join(chars), starts, ends


class EvidenceBuilder:
    def __init__(self, packet: dict[str, Any], source_id: str):
        self.pages = {int(page["page_number"]): page for page in packet["pages"]}
        self.source_id = source_id
        self.items: list[dict[str, Any]] = []

    def _locate(self, page_number: int, phrase: str, occurrence: int = 0) -> tuple[int, int]:
        page_text = self.pages[page_number]["text"]
        norm_text, starts, ends = normalized_with_raw_map(page_text)
        needle = normalized(phrase)
        search_at = 0
        found = -1
        for _ in range(occurrence + 1):
            found = norm_text.find(needle, search_at)
            if found < 0:
                raise ValueError(
                    f"Page {page_number}: evidence phrase not found: {needle!r}"
                )
            search_at = found + 1
        return starts[found], ends[found + len(needle) - 1]

    def add(
        self,
        page_number: int,
        phrase: str,
        section: str,
        *,
        section_raw: str | None = None,
        clause_path: str | None = None,
        table_context: dict[str, Any] | None = None,
        annotation_note: str | None = None,
        occurrence: int = 0,
    ) -> str:
        start, end = self._locate(page_number, phrase, occurrence)
        return self._append(
            page_number,
            start,
            end,
            section,
            section_raw=section_raw,
            clause_path=clause_path,
            table_context=table_context,
            annotation_note=annotation_note,
        )

    def add_between(
        self,
        page_number: int,
        start_phrase: str,
        end_phrase: str,
        section: str,
        *,
        section_raw: str | None = None,
        clause_path: str | None = None,
        table_context: dict[str, Any] | None = None,
        annotation_note: str | None = None,
    ) -> str:
        start, _ = self._locate(page_number, start_phrase)
        end_start, end = self._locate(page_number, end_phrase)
        if end_start < start:
            raise ValueError(
                f"Page {page_number}: end marker precedes start marker: {end_phrase!r}"
            )
        return self._append(
            page_number,
            start,
            end,
            section,
            section_raw=section_raw,
            clause_path=clause_path,
            table_context=table_context,
            annotation_note=annotation_note,
        )

    def _append(
        self,
        page_number: int,
        start: int,
        end: int,
        section: str,
        *,
        section_raw: str | None,
        clause_path: str | None,
        table_context: dict[str, Any] | None,
        annotation_note: str | None,
    ) -> str:
        page = self.pages[page_number]
        evidence_id = f"EV-{len(self.items) + 1:03d}"
        self.items.append(
            {
                "evidence_id": evidence_id,
                "source_file_instance_id": self.source_id,
                "page_number": page_number,
                "printed_page_label": f"Page {page_number} of {page['page_count']}",
                "section": section,
                "section_raw": section_raw,
                "clause_path": clause_path,
                "exact_quote": page["text"][start:end],
                "start_char": start,
                "end_char": end,
                "page_text_sha256": page["page_text_sha256"],
                "bbox_normalized": None,
                "extraction_method": "native_text",
                "quality": "normalized_whitespace",
                "table_context": table_context,
                "annotation_note": annotation_note,
            }
        )
        return evidence_id


def grounded_text(value: str, raw_text: str, evidence_ids: list[str]) -> dict[str, Any]:
    return {
        "state": "present",
        "value": value,
        "raw_text": raw_text,
        "evidence_ids": evidence_ids,
    }


def grounded_date(value: str, raw_text: str, evidence_ids: list[str]) -> dict[str, Any]:
    return grounded_text(value, raw_text, evidence_ids)


def not_stated() -> dict[str, Any]:
    return {"state": "not_stated", "value": None, "raw_text": None, "evidence_ids": []}


def explicit_none(raw_text: str, evidence_ids: list[str]) -> dict[str, Any]:
    return {
        "state": "explicit_none",
        "value": None,
        "raw_text": raw_text,
        "evidence_ids": evidence_ids,
    }


def non_terminating() -> dict[str, Any]:
    return {
        "state": "not_stated",
        "present": False,
        "scope": "none",
        "action_text": None,
        "terminates_requirement_ids": [],
        "evidence_ids": [],
    }


def terminating(text: str, targets: list[str], evidence_ids: list[str]) -> dict[str, Any]:
    return {
        "state": "present",
        "present": True,
        "scope": "full",
        "action_text": text,
        "terminates_requirement_ids": targets,
        "evidence_ids": evidence_ids,
    }


def limit(
    limit_id: str,
    relation: str,
    quantity: float | None,
    unit: str,
    raw_value: str,
    reference_event: str | None,
    evidence_ids: list[str],
    *,
    calendar_date: str | None = None,
) -> dict[str, Any]:
    return {
        "limit_id": limit_id,
        "relation": relation,
        "quantity": quantity,
        "unit": unit,
        "raw_value": raw_value,
        "reference_event": reference_event,
        "calendar_date": calendar_date,
        "evidence_ids": evidence_ids,
    }


def compliance(
    compliance_id: str,
    raw_text: str,
    logic: str,
    conditions: list[str],
    initial_limits: list[dict[str, Any]],
    evidence_ids: list[str],
    *,
    repetitive_intervals: list[dict[str, Any]] | None = None,
    grace_periods: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    intervals = repetitive_intervals or []
    return {
        "compliance_id": compliance_id,
        "state": "present",
        "raw_text": raw_text,
        "logic": logic,
        "conditions": conditions,
        "initial_limits": initial_limits,
        "is_repetitive": bool(intervals),
        "repetitive_intervals": intervals,
        "grace_periods": grace_periods or [],
        "evidence_ids": evidence_ids,
    }


def requirement(
    requirement_id: str,
    paragraph_reference: str,
    applicability_group_ids: list[str],
    action_types: list[str],
    obligation: str,
    action_text: str,
    objects_or_components: list[str],
    conditions: list[str],
    method_publication_ids: list[str],
    compliance_rules: list[dict[str, Any]],
    evidence_ids: list[str],
    *,
    parent_requirement_id: str | None = None,
    follow_on_requirement_ids: list[str] | None = None,
    terminating_action: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "paragraph_reference": paragraph_reference,
        "parent_requirement_id": parent_requirement_id,
        "applicability_group_ids": applicability_group_ids,
        "action_types": action_types,
        "obligation": obligation,
        "action_text": action_text,
        "objects_or_components": objects_or_components,
        "conditions": conditions,
        "method_publication_ids": method_publication_ids,
        "compliance_rules": compliance_rules,
        "follow_on_requirement_ids": follow_on_requirement_ids or [],
        "terminating_action": terminating_action or non_terminating(),
        "evidence_ids": evidence_ids,
    }


def publication_reference(
    publication_id: str,
    publication_type: str,
    issuer: str,
    number: str,
    revision: str,
    publication_date: str,
    roles: list[str],
    evidence_ids: list[str],
) -> dict[str, Any]:
    return {
        "publication_id": publication_id,
        "publication_type": publication_type,
        "issuer": issuer,
        "number": number,
        "revision": revision,
        "publication_date": publication_date,
        "title": None,
        "roles": roles,
        "later_approved_revisions_allowed": True,
        "evidence_ids": evidence_ids,
    }


def pointer_value(document: Any, pointer: str) -> Any:
    current = document
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(token)]
        else:
            current = current[token]
    return current


def collect_evidence_ids(value: Any) -> list[str]:
    found: list[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if key == "evidence_ids" and isinstance(child, list):
                    for evidence_id in child:
                        if evidence_id not in found:
                            found.append(evidence_id)
                else:
                    visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return found


def build_assertions(
    record: dict[str, Any],
    detail_specs: list[dict[str, Any]],
    section_states: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    section_states = section_states or {}
    specs: list[dict[str, Any]] = []
    for path in SECTION_PATHS:
        value = pointer_value(record, path)
        populated = value is not None and value != []
        specs.append(
            {
                "path": path,
                "state": section_states.get(
                    path, "present" if populated else "absent_in_source"
                ),
                "evidence_ids": collect_evidence_ids(value),
                "confidence": 0.98 if populated else 0.96,
                "notes": "Step 3 section-completion marker.",
            }
        )
    specs.extend(detail_specs)
    assertions: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for spec in specs:
        path = spec["path"]
        if path in seen_paths:
            continue
        seen_paths.add(path)
        value = pointer_value(record, path)
        evidence_ids = spec.get("evidence_ids")
        if evidence_ids is None:
            evidence_ids = collect_evidence_ids(value)
        assertions.append(
            {
                "assertion_id": f"AST-{len(assertions) + 1:03d}",
                "field_path": path,
                "value_state": spec.get("state", "present"),
                "origin": "auto_extracted",
                "verification_status": "unreviewed",
                "confidence": spec.get("confidence", 0.95),
                "evidence_ids": evidence_ids,
                "annotator_id": ANNOTATOR_ID,
                "derivation_rule": None,
                "input_field_paths": [],
                "notes": spec.get("notes"),
            }
        )
    return assertions


def detail(
    path: str,
    evidence_ids: list[str] | None = None,
    *,
    state: str = "present",
    confidence: float = 0.95,
    notes: str | None = None,
) -> dict[str, Any]:
    return {
        "path": path,
        "evidence_ids": evidence_ids,
        "state": state,
        "confidence": confidence,
        "notes": notes,
    }


def finalize(
    record: dict[str, Any],
    evidence: EvidenceBuilder,
    detail_specs: list[dict[str, Any]],
    quality_flags: list[str],
    *,
    section_states: dict[str, str] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
    record["evidence_spans"] = evidence.items
    record["field_assertions"] = build_assertions(
        record, detail_specs, section_states=section_states
    )
    record["annotation_metadata"] = {
        "guideline_version": "1.0.0",
        "record_status": "first_pass_complete",
        "creation_method": "hybrid",
        "machine_provenance": {
            "system": "OpenAI Codex",
            "model": "GPT-5",
            "prompt_or_rules_version": "step2-guidelines-1.0.0-manual-pass-b2",
            "generated_at": timestamp,
        },
        "annotators": [
            {
                "annotator_id": ANNOTATOR_ID,
                "role": "annotator",
                "started_at": timestamp,
                "submitted_at": timestamp,
            }
        ],
        "events": [
            {
                "event_type": "created",
                "actor_id": ANNOTATOR_ID,
                "timestamp": timestamp,
                "rationale": "Independent blind Annotator-B source review begun.",
            },
            {
                "event_type": "submitted",
                "actor_id": ANNOTATOR_ID,
                "timestamp": timestamp,
                "rationale": "First-pass source annotation completed for independent review.",
            },
        ],
        "quality_flags": quality_flags,
        "uncertainty_flags": [],
        "notes": [
            "Independent Annotator-B pass based only on the assigned blank template, original PDF, frozen blind page text, and Step 2 guidance.",
            "All field assertions remain automatic-origin and unreviewed until independent human review or adjudication.",
            *(notes or []),
        ],
        "source_text_sha256": record["source_document"]["normalized_text_sha256"],
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    record["classification"]["human_confirmed"] = False
    record["benchmark_metadata"]["gold_record"] = False
    return record


def load_assignment(ad_number: str) -> tuple[dict[str, Any], dict[str, Any]]:
    assignment = ASSIGNMENTS[ad_number]
    template = copy.deepcopy(load_json(TEMPLATE_DIR / assignment["template"]))
    packet = load_json(PACKET_DIR / assignment["packet"])
    if packet["record_id"] != template["record_id"]:
        raise ValueError(f"Packet/template record mismatch for {ad_number}")
    return template, packet


def build_2019() -> dict[str, Any]:
    record, packet = load_assignment("2019-0183")
    ev = EvidenceBuilder(packet, record["source_document"]["file_instance_id"])

    e_header = ev.add(
        1,
        "AD No.: 2019-0183 Issued: 26 July 2019",
        "cover",
        clause_path="AD No.; Issued",
    )
    e_holder_type = ev.add(
        1,
        "Design Approval Holder’s Name:: Type/Model designation(s): AIRBUS A350 aeroplanes",
        "cover",
        clause_path="Design Approval Holder; Type/Model designation(s)",
    )
    e_cover_fields = ev.add(
        1,
        "Effective Date: 09 August 2019 TCDS Number(s): EASA.A.151 Foreign AD: Not applicable Supersedure: None",
        "cover",
        clause_path="Effective Date; TCDS; Foreign AD; Supersedure",
    )
    e_subject = ev.add(
        1,
        "ATA 92 – Electric and Electronic Common Installation – Cargo Lining Gutter Assemblies – Modification",
        "cover",
        clause_path="ATA / Subject",
    )
    e_manufacturer = ev.add(
        1,
        "Manufacturer(s): Airbus",
        "applicability",
        clause_path="Manufacturer(s)",
    )
    e_applicability = ev.add(
        1,
        "Applicability: Airbus A350-941 aeroplanes, all manufacturer serial numbers, except those on which Airbus modification (mod) 111827 has been embodied in production.",
        "applicability",
        clause_path="Applicability",
    )
    e_def_sb = ev.add(
        1,
        "The SB: Airbus Service Bulletin (SB) A350-92-P014.",
        "definitions",
        clause_path="Definitions / The SB",
    )
    e_def_date = ev.add(
        1,
        "Airbus date of manufacture: The date of transfer of title (ownership) of the aeroplane upon delivery by Airbus to the first operator.",
        "definitions",
        clause_path="Definitions / Airbus date of manufacture",
    )
    e_reason_start = ev.add_between(
        1,
        "Reason: The function of the cargo lining gutter assembly",
        "that this assembly would not be able to correctly drain a certain quantity of water in case of potable",
        "reason",
        clause_path="Reason",
    )
    e_reason_consequence = ev.add_between(
        2,
        "water distribution pipe leakage, or rupture of the pipe close to the electronics bay entrance.",
        "reduced control of the aeroplane.",
        "reason",
        clause_path="Reason (continued)",
    )
    e_reason_mitigation = ev.add_between(
        2,
        "To address this potential unsafe condition, affecting components located on the rear side",
        "gutter design with improved outlets on both sides for a better water drainage.",
        "reason",
        clause_path="Reason / affected components and mitigation",
    )
    e_requirement = ev.add(
        2,
        "Before exceeding 80 months since Airbus date of manufacture, modify the cargo lining gutter assemblies in accordance with the instructions of the SB.",
        "required_actions_and_compliance_times",
        section_raw="Modification",
        clause_path="Modification",
    )
    e_publication = ev.add_between(
        2,
        "Ref. Publications: Airbus SB A350-92-P014 original issue dated 29 October 2018.",
        "with the requirements of this AD.",
        "reference_publications",
        clause_path="Ref. Publications",
    )
    e_amoc = ev.add(
        2,
        "If requested and appropriately substantiated, EASA can approve Alternative Methods of Compliance for this AD.",
        "remarks",
        clause_path="Remarks / 1",
    )
    e_reg_contact = ev.add(
        2,
        "Enquiries regarding this AD should be referred to the EASA Programming and Continued Airworthiness Information Section, Certification Directorate. E-mail: ADs@easa.europa.eu.",
        "remarks",
        clause_path="Remarks / 3",
    )
    e_tech_contact = ev.add(
        2,
        "For any question concerning the technical content of the requirements in this AD, please contact: continued-airworthiness.a350@airbus.com.",
        "remarks",
        clause_path="Remarks / 5",
    )

    record["ad_identity"].update(
        {
            "correction_date": not_stated(),
            "version_label": "2019-0183",
            "logical_version_key": "2019-0183|UNCORRECTED",
            "is_latest_version": None,
            "lifecycle_status": "unknown",
            "design_approval_holder": grounded_text("Airbus", "AIRBUS", [e_holder_type]),
            "supersedure_statement": explicit_none("None", [e_cover_fields]),
            "evidence_ids": [e_header, e_holder_type, e_cover_fields],
        }
    )
    subject = "ATA 92 – Electric and Electronic Common Installation – Cargo Lining Gutter Assemblies – Modification"
    record["publication"] = {
        "subject": grounded_text(subject, subject, [e_subject]),
        "issue_date": grounded_date("2019-07-26", "26 July 2019", [e_header]),
        "effective_date": grounded_date("2019-08-09", "09 August 2019", [e_cover_fields]),
        "ata_chapters": [
            {"code": "92", "title": "Electric and Electronic Common Installation", "evidence_ids": [e_subject]}
        ],
        "manufacturers": [
            {
                "raw_name": "Airbus",
                "normalized_name": "Airbus",
                "role": "manufacturer",
                "evidence_ids": [e_manufacturer],
            }
        ],
        "type_model_designations": ["A350"],
        "tcds_numbers": ["EASA.A.151"],
        "foreign_ad": explicit_none("Not applicable", [e_cover_fields]),
    }
    record["applicability_groups"] = [
        {
            "group_id": "APP-001",
            "label": "A350-941 all MSNs excluding production modification 111827",
            "state": "present",
            "raw_text": "Airbus A350-941 aeroplanes, all manufacturer serial numbers, except those on which Airbus modification (mod) 111827 has been embodied in production.",
            "aircraft_families": ["A350"],
            "models": ["A350-941"],
            "serial_restrictions": [
                {
                    "restriction_id": "MSN-001",
                    "kind": "all",
                    "raw_expression": "all manufacturer serial numbers",
                    "lower_bound": None,
                    "upper_bound": None,
                    "explicit_values": [],
                    "condition": None,
                    "evidence_ids": [e_applicability],
                }
            ],
            "part_numbers": [],
            "configuration_conditions": [],
            "exclusions": ["Airbus modification 111827 embodied in production"],
            "boolean_logic": "mixed",
            "evidence_ids": [e_applicability],
        }
    ]
    record["definitions"] = [
        {
            "definition_id": "DEF-001",
            "term": "The SB",
            "definition_text": "Airbus Service Bulletin (SB) A350-92-P014.",
            "evidence_ids": [e_def_sb],
        },
        {
            "definition_id": "DEF-002",
            "term": "Airbus date of manufacture",
            "definition_text": "The date of transfer of title (ownership) of the aeroplane upon delivery by Airbus to the first operator.",
            "evidence_ids": [e_def_date],
        },
    ]
    record["unsafe_condition"] = {
        "state": "present",
        "raw_reason_text": "The cargo lining gutter assembly may be unable to drain water from a potable water distribution pipe leakage or rupture near the electronics bay entrance, creating overflow and water spillage. Fluid contamination of electrical equipment and connectors could cause loss of several flight-control functions and reduced control of the aeroplane.",
        "observed_events_or_defects": [
            "The cargo lining gutter assembly would not be able to correctly drain a certain quantity of water following a potable-water pipe leakage or rupture near the electronics bay entrance."
        ],
        "causes": [
            "Insufficient cargo lining gutter drainage capacity for the stated potable-water leakage or rupture case."
        ],
        "unsafe_conditions": ["Overflow and risk of water spillage during flight."],
        "potential_consequences": [
            "Fluid contamination of electrical equipment and connectors.",
            "Loss of several flight-control functions with consequent reduced control of the aeroplane.",
        ],
        "affected_components": [
            "Cargo lining gutter assemblies",
            "Components behind avionics racks 1100 VU and 1200 VU",
            "PRIM, SEC1 and SEC2 related functions",
            "Four pairs of spoilers and the left elevator",
        ],
        "intended_risk_mitigation": [
            "Introduce a new drain gutter design with improved outlets on both sides."
        ],
        "evidence_ids": [e_reason_start, e_reason_consequence, e_reason_mitigation],
    }
    record["requirements"] = [
        requirement(
            "REQ-001",
            "Modification",
            ["APP-001"],
            ["modification"],
            "mandatory",
            "Modify the cargo lining gutter assemblies in accordance with the instructions of the SB.",
            ["cargo lining gutter assemblies"],
            [],
            ["PUB-001"],
            [
                compliance(
                    "CMP-001",
                    "Before exceeding 80 months since Airbus date of manufacture.",
                    "single",
                    [],
                    [
                        limit(
                            "LIM-001",
                            "before",
                            80,
                            "calendar_month",
                            "Before exceeding 80 months",
                            "Airbus date of manufacture",
                            [e_requirement],
                        )
                    ],
                    [e_requirement],
                )
            ],
            [e_requirement],
        )
    ]
    record["exceptions"] = []
    record["previous_action_credit"] = []
    record["referenced_publications"] = [
        publication_reference(
            "PUB-001",
            "service_bulletin",
            "Airbus",
            "A350-92-P014",
            "Original issue",
            "2018-10-29",
            ["required_method"],
            [e_publication],
        )
    ]
    record["relationships"] = []
    record["amoc_and_contacts"] = [
        {
            "entry_id": "AMC-001",
            "entry_type": "amoc_authority",
            "authority_or_organization": "EASA",
            "contact_text": "EASA can approve Alternative Methods of Compliance for this AD.",
            "conditions": ["Requested and appropriately substantiated"],
            "evidence_ids": [e_amoc],
        },
        {
            "entry_id": "AMC-002",
            "entry_type": "regulatory_contact",
            "authority_or_organization": "EASA Programming and Continued Airworthiness Information Section, Certification Directorate",
            "contact_text": "ADs@easa.europa.eu",
            "conditions": ["Enquiries regarding this AD"],
            "evidence_ids": [e_reg_contact],
        },
        {
            "entry_id": "AMC-003",
            "entry_type": "technical_contact",
            "authority_or_organization": "Airbus",
            "contact_text": "continued-airworthiness.a350@airbus.com",
            "conditions": ["Questions concerning the technical content of the requirements"],
            "evidence_ids": [e_tech_contact],
        },
    ]
    record["classification"] = {
        "airbus_families": ["A350"],
        "ata_chapters": ["92"],
        "action_types": ["modification"],
        "frequency": "one_time",
        "emergency_status": "standard",
        "terminating_action_present": False,
        "table_or_appendix_present": False,
        "compliance_complexity": "simple",
        "human_confirmed": False,
        "evidence_ids": [e_subject, e_applicability, e_requirement],
    }
    details = [
        detail("/ad_identity/ad_number", [e_header], confidence=0.99),
        detail("/ad_identity/design_approval_holder", [e_holder_type], confidence=0.99),
        detail("/ad_identity/supersedure_statement", [e_cover_fields], confidence=0.99),
        detail("/publication/subject", [e_subject], confidence=0.99),
        detail("/publication/issue_date", [e_header], confidence=0.99),
        detail("/publication/effective_date", [e_cover_fields], confidence=0.99),
        detail("/publication/ata_chapters", [e_subject], confidence=0.99),
        detail("/publication/manufacturers", [e_manufacturer], confidence=0.99),
        detail("/publication/type_model_designations", [e_holder_type], confidence=0.98),
        detail("/publication/tcds_numbers", [e_cover_fields], confidence=0.99),
        detail("/publication/foreign_ad", [e_cover_fields], state="not_applicable", confidence=0.99),
        detail("/applicability_groups/0", [e_applicability], confidence=0.98),
        detail("/definitions/0", [e_def_sb], confidence=0.99),
        detail("/definitions/1", [e_def_date], confidence=0.99),
        detail("/requirements/0", [e_requirement], confidence=0.98),
        detail("/referenced_publications/0", [e_publication], confidence=0.98),
        detail("/amoc_and_contacts/0", [e_amoc], confidence=0.98),
        detail("/amoc_and_contacts/1", [e_reg_contact], confidence=0.99),
        detail("/amoc_and_contacts/2", [e_tech_contact], confidence=0.99),
        detail("/classification/action_types", [e_requirement], confidence=0.97),
        detail("/classification/frequency", [e_requirement], confidence=0.96),
        detail("/classification/compliance_complexity", [e_requirement], confidence=0.96),
    ]
    return finalize(
        record,
        ev,
        details,
        ["cross_page_clause"],
        section_states={
            "/exceptions": "absent_in_source",
            "/previous_action_credit": "absent_in_source",
            "/relationships": "absent_in_source",
        },
        notes=[
            "Supersedure is explicitly stated as None; no positive relationship edge was created."
        ],
    )


def build_2020() -> dict[str, Any]:
    record, packet = load_assignment("2020-0085R1")
    ev = EvidenceBuilder(packet, record["source_document"]["file_instance_id"])

    e_header = ev.add(
        1,
        "AD No.: 2020-0085R1 Issued: 06 August 2021",
        "cover",
        clause_path="AD No.; Issued",
    )
    e_holder_type = ev.add(
        1,
        "Design Approval Holder’s Name: Type/Model designation(s): AIRBUS A318, A319, A320 and A321 aeroplanes",
        "cover",
        clause_path="Design Approval Holder; Type/Model designation(s)",
    )
    e_cover_fields = ev.add_between(
        1,
        "Effective Date: Revision 1: 13 August 2021",
        "AD 2017-0251 dated 15 December 2017.",
        "cover",
        clause_path="Effective Date; TCDS; Foreign AD; Supersedure",
    )
    e_subject = ev.add(
        1,
        "ATA 71 – Powerplant – Aft Engine Mount Retainers – Replacement",
        "cover",
        clause_path="ATA / Subject",
    )
    e_manufacturer = ev.add(
        1,
        "Manufacturer(s): Airbus, formerly Airbus Industrie",
        "applicability",
        clause_path="Manufacturer(s)",
    )
    e_applicability = ev.add_between(
        1,
        "Applicability: Airbus A318-111",
        "A321-213 aeroplanes, all manufacturer serial numbers.",
        "applicability",
        clause_path="Applicability",
    )
    e_def_affected = ev.add(
        1,
        "Affected part: Aft engine mount assemblies, having a Part Number (P/N) identified as “Old” in Table 1 of this AD.",
        "definitions",
        clause_path="Definitions / affected part",
    )
    e_def_serviceable = ev.add(
        1,
        "Serviceable part: Aft engine mount assemblies, having a P/N identified as “New” in Table 1 of this AD.",
        "definitions",
        clause_path="Definitions / serviceable part",
    )
    e_def_sb = ev.add(
        1,
        "The SB: Airbus Service Bulletin (SB) A320-71-1071 revision (rev.) 02.",
        "definitions",
        clause_path="Definitions / The SB",
    )
    e_def_groups = ev.add(
        2,
        "Groups: Group 1 aeroplanes are those that have an affected part installed. Group 2 aeroplanes are those that do not have an affected part installed.",
        "definitions",
        clause_path="Definitions / Groups",
    )
    e_def_4lug = ev.add(
        2,
        "4-lugs engine: CFM56-5A1, CFM56-5A3, CFM56-5A4, CFM56-5A4/F, CFM56-5A5 or CFM56-5A5/F engines, fitted with a turbine rear frame (TRF) having a P/N as identified in Appendix 1 of this AD.",
        "definitions",
        clause_path="Definitions / 4-lugs engine",
    )
    e_def_date = ev.add(
        2,
        "Aeroplane date of manufacture: The date of transfer of title (ownership) at the time of first delivery to an operator, which is referenced in Airbus documentation.",
        "definitions",
        clause_path="Definitions / Aeroplane date of manufacture",
    )
    e_reason = ev.add_between(
        2,
        "Reason: During in-service inspections",
        "possibly resulting in damage to the aeroplane.",
        "reason",
        clause_path="Reason / defect, cause and consequence",
    )
    e_revision_reason = ev.add_between(
        3,
        "Since that AD was issued, Airbus provided additional data",
        "this AD is revised accordingly.",
        "reason",
        clause_path="Reason / Revision 1 rationale",
    )
    e_req1 = ev.add_between(
        3,
        "(1) For Group 1 aeroplanes: Within 12 months after the last DET inspection",
        "Goodrich Aerostructures SB RA32071 -160.",
        "required_actions_and_compliance_times",
        section_raw="Repetitive Inspections",
        clause_path="(1)",
    )
    table1_context = {
        "table_label": "Table 1 – Aft Engine Mount P/N (Affected and Serviceable Parts)",
        "row_headers": ["Old P/N"],
        "column_headers": ["Old P/N", "New P/N – 3 lugs configuration", "New P/N – 4 lugs configuration"],
        "footnotes": [],
    }
    e_table1 = ev.add_between(
        3,
        "Table 1 – Aft Engine Mount P/N (Affected and Serviceable Parts)",
        "642-2300-15",
        "table",
        clause_path="Table 1",
        table_context=table1_context,
    )
    e_req2 = ev.add_between(
        4,
        "(2) If, during any DET as required by paragraph (1)",
        "instructions of Airbus SB A320 -71-1060.",
        "required_actions_and_compliance_times",
        section_raw="Corrective Action(s)",
        clause_path="(2)",
    )
    e_req3 = ev.add_between(
        4,
        "(3) For Group 1 aeroplanes: Within 60 months after 16 August 2017",
        "SB RA32071-174, as applicable.",
        "required_actions_and_compliance_times",
        section_raw="Modification",
        clause_path="(3)",
    )
    e_req4 = ev.add_between(
        4,
        "(4) Replacement on an aeroplane of each affected part",
        "paragraph (3) of this AD for that aeroplane.",
        "required_actions_and_compliance_times",
        section_raw="Alternative Method",
        clause_path="(4)",
    )
    e_credit = ev.add_between(
        4,
        "(5) Modification of an aeroplane (except those equipped with 4-lugs engines)",
        "at original issue or at rev. 01",
        "credit",
        clause_path="(5)",
    )
    e_group2 = ev.add_between(
        4,
        "(6) An aeroplane on which Airbus modification 158435",
        "provided those records can be relied upon for that purpose.",
        "required_actions_and_compliance_times",
        clause_path="(6)",
    )
    e_termination = ev.add_between(
        4,
        "(7) Modification of an aeroplane as required by paragraph (3)",
        "paragraph (1) of this AD for that aeroplane.",
        "required_actions_and_compliance_times",
        section_raw="Terminating Action",
        clause_path="(7)",
    )
    e_req8 = ev.add_between(
        4,
        "(8) For Group 1 and Group 2 aeroplanes: From 04 May 2020",
        "can be used to verify the correct finish of the part.",
        "required_actions_and_compliance_times",
        section_raw="Parts Installation",
        clause_path="(8)",
    )
    e_req9a = ev.add_between(
        4,
        "(9) For Group 1 aeroplanes: From 04 May 2020",
        "Part listed in Table 1 of Airbus AOT A71N011-15 rev. 01.",
        "required_actions_and_compliance_times",
        section_raw="Parts Installation",
        clause_path="(9), (9.1)",
    )
    e_req9b = ev.add_between(
        5,
        "(9.2) Part installed since the aeroplane date of manufacture",
        "which cannot be identified by a PO.",
        "required_actions_and_compliance_times",
        section_raw="Parts Installation",
        clause_path="(9.2), (9.3)",
    )
    e_req10 = ev.add_between(
        5,
        "(10) From 27 January 2016",
        "Part listed in Table 1 of AOT A71N011-15 rev. 01.",
        "required_actions_and_compliance_times",
        section_raw="Parts Installation",
        clause_path="(10), (10.1)–(10.3)",
    )
    e_req11 = ev.add_between(
        5,
        "(11) Do not install an affected part on any aeroplane",
        "0138].",
        "required_actions_and_compliance_times",
        section_raw="Parts Installation",
        clause_path="(11), (11.1), (11.2)",
    )
    e_req12 = ev.add_between(
        5,
        "(12) For an aeroplane equipped with 4-lugs engine",
        "accomplish those instructions accordingly.",
        "required_actions_and_compliance_times",
        section_raw="Parts Installation",
        clause_path="(12)",
    )
    e_pub_aot1 = ev.add(
        5,
        "Airbus AOT A71N001-12 rev. 01 dated 09 August 2012, or rev. 02 dated 27 February 2013.",
        "reference_publications",
        clause_path="Ref. Publications / A71N001-12",
    )
    e_pub_aot2 = ev.add(
        5,
        "Airbus AOT A71N011-15 original issue dated 16 September 2015, or rev. 01 dated 01 February 2016.",
        "reference_publications",
        clause_path="Ref. Publications / A71N011-15",
    )
    e_pub_sb1060 = ev.add_between(
        5,
        "Airbus SB A320-71-1060 original issue dated 09 October 2014",
        "18 December 2015.",
        "reference_publications",
        clause_path="Ref. Publications / A320-71-1060",
    )
    e_pub_sb1071 = ev.add_between(
        5,
        "Airbus SB A320-71-1071 original issue dated 08 November 2016",
        "rev. 02 dated 22 October 2019.",
        "reference_publications",
        clause_path="Ref. Publications / A320-71-1071",
    )
    e_pub_146 = ev.add(
        6,
        "Goodrich Aerostructures SB RA32071-146 rev. 02 dated 26 July 2012.",
        "reference_publications",
        clause_path="Ref. Publications / RA32071-146",
    )
    e_pub_160 = ev.add(
        6,
        "Goodrich Aerostructures SB RA32071-160 original issue dated 18 September 2014, or rev.01 dated 23 September 2016.",
        "reference_publications",
        clause_path="Ref. Publications / RA32071-160",
    )
    e_pub_164 = ev.add(
        6,
        "Goodrich Aerostructures SB RA32071-164 original issue dated 06 October 2016, or rev. 01 dated 19 July 2017, or rev. 02 dated 04 April 2018, or rev. 03 dated 14 September 2018.",
        "reference_publications",
        clause_path="Ref. Publications / RA32071-164",
    )
    e_pub_174 = ev.add(
        6,
        "Goodrich Aerostructures SB RA32071-174 original issue dated 17 September 2019.",
        "reference_publications",
        clause_path="Ref. Publications / RA32071-174",
    )
    e_later_revs = ev.add(
        6,
        "The use of later approved revisions of the above-mentioned documents is acceptable for compliance with the requirements of this AD.",
        "reference_publications",
        clause_path="Ref. Publications / later revisions",
    )
    e_amoc = ev.add(
        6,
        "If requested and appropriately substantiated, EASA can approve Alternative Methods of Compliance for this AD.",
        "remarks",
        clause_path="Remarks / 1",
    )
    e_reg_contact = ev.add(
        6,
        "Enquiries regarding this AD should be referred to the EASA Safety Information Section, Certification Directorate. E-mail: ADs@easa.europa.eu.",
        "remarks",
        clause_path="Remarks / 3",
    )
    e_tech_contact = ev.add(
        6,
        "For any question concerning the technical content of the requirements in this AD, please contact: AIRBUS – Airworthiness Office – IIASA; E-mail: account.airworth-eas@airbus.com.",
        "remarks",
        clause_path="Remarks / 5",
    )
    appendix_context = {
        "table_label": "Appendix 1 – TRF with 4 lugs configuration",
        "row_headers": [],
        "column_headers": ["P/N"],
        "footnotes": [],
    }
    e_appendix = ev.add_between(
        7,
        "Appendix 1 – TRF with 4 lugs configuration",
        "336-031-642-0",
        "appendix",
        clause_path="Appendix 1",
        table_context=appendix_context,
    )

    record["ad_identity"].update(
        {
            "correction_date": not_stated(),
            "version_label": "Revision 1",
            "logical_version_key": "2020-0085R1|UNCORRECTED",
            "is_latest_version": None,
            "lifecycle_status": "unknown",
            "design_approval_holder": grounded_text("Airbus", "AIRBUS", [e_holder_type]),
            "supersedure_statement": grounded_text(
                "This AD revises EASA AD 2020-0085 dated 06 April 2020, which superseded EASA AD 2017-0251 dated 15 December 2017.",
                "This AD revises EASA AD 2020-0085 dated 06 April 2020, which superseded EASA AD 2017-0251 dated 15 December 2017.",
                [e_cover_fields],
            ),
            "evidence_ids": [e_header, e_holder_type, e_cover_fields],
        }
    )
    subject = "ATA 71 – Powerplant – Aft Engine Mount Retainers – Replacement"
    models = [
        "A318-111", "A318-112", "A319-111", "A319-112", "A319-113", "A319-114", "A319-115",
        "A320-211", "A320-212", "A320-214", "A320-215", "A320-216", "A321-111", "A321-112",
        "A321-211", "A321-212", "A321-213",
    ]
    old_parts = ["238-0230-11", "238-0230-15", "238-0230-5", "642-2300-3"]
    appendix_parts = [
        "336-031-615-0", "336-031-617-0", "336-031-618-0", "336-031-621-0",
        "336-031-650-0", "336-031-651-0", "336-031-652-0", "336-031-653-0",
        "336-031-660-0", "336-031-661-0", "336-031-662-0", "336-031-663-0",
        "336-031-670-0", "336-031-671-0", "336-031-672-0", "336-031-673-0",
        "336-031-640-0", "336-031-642-0",
    ]
    record["publication"] = {
        "subject": grounded_text(subject, subject, [e_subject]),
        "issue_date": grounded_date("2021-08-06", "06 August 2021", [e_header]),
        "effective_date": grounded_date("2021-08-13", "Revision 1: 13 August 2021", [e_cover_fields]),
        "ata_chapters": [{"code": "71", "title": "Powerplant", "evidence_ids": [e_subject]}],
        "manufacturers": [
            {
                "raw_name": "Airbus, formerly Airbus Industrie",
                "normalized_name": "Airbus",
                "role": "manufacturer",
                "evidence_ids": [e_manufacturer],
            }
        ],
        "type_model_designations": ["A318", "A319", "A320", "A321"],
        "tcds_numbers": ["EASA.A.064"],
        "foreign_ad": explicit_none("Not applicable", [e_cover_fields]),
    }
    raw_scope = "Airbus A318-111, A318-112, A319-111, A319-112, A319-113, A319-114, A319-115, A320-211, A320-212, A320-214, A320-215, A320-216, A321-111, A321-112, A321-211, A321-212 and A321-213 aeroplanes, all manufacturer serial numbers."
    serial_all = lambda restriction_id: {
        "restriction_id": restriction_id,
        "kind": "all",
        "raw_expression": "all manufacturer serial numbers",
        "lower_bound": None,
        "upper_bound": None,
        "explicit_values": [],
        "condition": None,
        "evidence_ids": [e_applicability],
    }
    record["applicability_groups"] = [
        {
            "group_id": "APP-001",
            "label": "Group 1 – affected part installed",
            "state": "present",
            "raw_text": raw_scope + " Group 1 aeroplanes are those that have an affected part installed.",
            "aircraft_families": ["A320 family"],
            "models": models,
            "serial_restrictions": [serial_all("MSN-001")],
            "part_numbers": old_parts,
            "configuration_conditions": ["At least one affected aft engine mount assembly is installed."],
            "exclusions": [],
            "boolean_logic": "all",
            "evidence_ids": [e_applicability, e_def_groups, e_table1],
        },
        {
            "group_id": "APP-002",
            "label": "Group 2 – no affected part installed",
            "state": "present",
            "raw_text": raw_scope + " Group 2 aeroplanes are those that do not have an affected part installed.",
            "aircraft_families": ["A320 family"],
            "models": models,
            "serial_restrictions": [serial_all("MSN-002")],
            "part_numbers": [],
            "configuration_conditions": ["No affected aft engine mount assembly is installed."],
            "exclusions": [],
            "boolean_logic": "all",
            "evidence_ids": [e_applicability, e_def_groups],
        },
        {
            "group_id": "APP-003",
            "label": "Aeroplanes equipped with a defined 4-lugs engine",
            "state": "present",
            "raw_text": raw_scope + " A 4-lugs engine is a listed CFM56-5A engine fitted with a TRF having a P/N identified in Appendix 1.",
            "aircraft_families": ["A320 family"],
            "models": models,
            "serial_restrictions": [serial_all("MSN-003")],
            "part_numbers": appendix_parts,
            "configuration_conditions": [
                "CFM56-5A1, CFM56-5A3, CFM56-5A4, CFM56-5A4/F, CFM56-5A5 or CFM56-5A5/F engine",
                "Turbine rear frame has a 4-lug configuration and a P/N listed in Appendix 1",
            ],
            "exclusions": [],
            "boolean_logic": "mixed",
            "evidence_ids": [e_applicability, e_def_4lug, e_appendix],
        },
    ]
    record["definitions"] = [
        {"definition_id": "DEF-001", "term": "Affected part", "definition_text": "Aft engine mount assemblies having a P/N identified as Old in Table 1 of this AD.", "evidence_ids": [e_def_affected, e_table1]},
        {"definition_id": "DEF-002", "term": "Serviceable part", "definition_text": "Aft engine mount assemblies having a P/N identified as New in Table 1 of this AD.", "evidence_ids": [e_def_serviceable, e_table1]},
        {"definition_id": "DEF-003", "term": "The SB", "definition_text": "Airbus Service Bulletin A320-71-1071 revision 02.", "evidence_ids": [e_def_sb]},
        {"definition_id": "DEF-004", "term": "Groups", "definition_text": "Group 1 aeroplanes have an affected part installed; Group 2 aeroplanes do not have an affected part installed.", "evidence_ids": [e_def_groups]},
        {"definition_id": "DEF-005", "term": "4-lugs engine", "definition_text": "A listed CFM56-5A engine fitted with a turbine rear frame having a P/N identified in Appendix 1.", "evidence_ids": [e_def_4lug, e_appendix]},
        {"definition_id": "DEF-006", "term": "Aeroplane date of manufacture", "definition_text": "The date of transfer of title (ownership) at first delivery to an operator, as referenced in Airbus documentation.", "evidence_ids": [e_def_date]},
    ]
    record["unsafe_condition"] = {
        "state": "present",
        "raw_reason_text": "Several aft engine mount inner retainers on aeroplanes with CFM56-5A/5B engines were found broken. Vibration dynamic effects initiated cracks, with dull-surface-finish pitting as an aggravating factor. The condition could lead to in-flight loss of an aft engine mount link and damage to the aeroplane.",
        "observed_events_or_defects": ["Several aft engine mount inner retainers were found broken during in-service inspections."],
        "causes": ["Vibration dynamic effect initiating cracks in the retainers.", "Dull-surface-finish pitting as an aggravating factor."],
        "unsafe_conditions": ["Broken or missing aft engine mount inner retainers."],
        "potential_consequences": ["In-flight loss of an aft engine mount link.", "Damage to the aeroplane."],
        "affected_components": ["Aft engine mount inner retainers", "Aft engine mount link"],
        "intended_risk_mitigation": ["Repetitive detailed inspections and corrective replacement.", "Modification or replacement of affected aft engine mount assemblies.", "Operation and installation prohibitions for specified retainers and parts."],
        "evidence_ids": [e_reason, e_revision_reason],
    }

    pubs_1060 = ["PUB-005", "PUB-006", "PUB-007"]
    pubs_160 = ["PUB-012", "PUB-013"]
    pubs_164 = ["PUB-014", "PUB-015", "PUB-016", "PUB-017"]
    record["requirements"] = [
        requirement(
            "REQ-001", "(1)", ["APP-001"], ["inspection"], "mandatory",
            "Accomplish a detailed inspection of the aft engine mount inner retainers in accordance with Airbus SB A320-71-1060 or Goodrich Aerostructures SB RA32071-160.",
            ["aft engine mount inner retainers"], [], pubs_1060 + pubs_160,
            [compliance(
                "CMP-001",
                "Within 12 months after the last DET inspection previously required by paragraph (2) of EASA AD 2017-0251 and thereafter at intervals not to exceed 12 months.",
                "single", [],
                [limit("LIM-001", "within", 12, "calendar_month", "Within 12 months", "last DET inspection accomplished under paragraph (2) of EASA AD 2017-0251", [e_req1])],
                [e_req1],
                repetitive_intervals=[limit("LIM-002", "not_to_exceed", 12, "calendar_month", "intervals not to exceed 12 months", "previous DET", [e_req1])],
            )],
            [e_req1], follow_on_requirement_ids=["REQ-002"],
        ),
        requirement(
            "REQ-002", "(2)", ["APP-001"], ["replacement"], "conditional",
            "Before next flight, replace each affected aft engine mount inner retainer found damaged, cracked, broken or missing.",
            ["aft engine mount inner retainers"],
            ["A retainer is found damaged, cracked or broken, or detected as missing during the DET required by paragraph (1)."],
            pubs_1060,
            [compliance("CMP-002", "Before next flight.", "conditional", ["Specified DET finding"], [limit("LIM-003", "before", None, "before_next_flight", "before next flight", "detection of the specified finding", [e_req2])], [e_req2])],
            [e_req2], parent_requirement_id="REQ-001",
        ),
        requirement(
            "REQ-003", "(3)", ["APP-001"], ["modification"], "mandatory",
            "Modify each affected part and re-identify it as a serviceable part as applicable to the TRF lug configuration.",
            ["affected aft engine mount assemblies"], ["Use the instructions applicable to the TRF lug configuration."],
            ["PUB-010", *pubs_164, "PUB-018"],
            [compliance("CMP-003", "Within 60 months after 16 August 2017.", "single", [], [limit("LIM-004", "within", 60, "calendar_month", "Within 60 months", "16 August 2017, the effective date of EASA AD 2017-0138", [e_req3])], [e_req3])],
            [e_req3, e_termination],
            terminating_action=terminating("Modification under paragraph (3) constitutes terminating action for the repetitive DET in paragraph (1).", ["REQ-001"], [e_termination]),
        ),
        requirement(
            "REQ-004", "(4)", ["APP-001"], ["replacement"], "optional_terminating",
            "Replace each affected part with the corresponding serviceable part applicable to the TRF lug configuration as an alternative to paragraph (3).",
            ["affected aft engine mount assemblies"], ["Alternative method for compliance with paragraph (3)."], [],
            [compliance("CMP-004", "Comply within the paragraph (3) modification period: within 60 months after 16 August 2017.", "single", [], [limit("LIM-005", "within", 60, "calendar_month", "Within 60 months", "16 August 2017, inherited from paragraph (3)", [e_req3, e_req4])], [e_req3, e_req4])],
            [e_req4, e_termination],
            terminating_action=terminating("Replacement under paragraph (4) constitutes terminating action for the repetitive DET in paragraph (1).", ["REQ-001"], [e_termination]),
        ),
        requirement(
            "REQ-005", "(8)", ["APP-001", "APP-002"], ["prohibition"], "prohibited",
            "Do not operate an aeroplane with, and do not install on an aeroplane, a dull-finish aft engine mount inner retainer.",
            ["dull-finish aft engine mount inner retainer"], [], ["PUB-001", "PUB-002", "PUB-011"],
            [compliance("CMP-005", "From 04 May 2020.", "single", [], [limit("LIM-006", "from", None, "calendar_date", "From 04 May 2020", "effective date of the original issue of this AD", [e_req8], calendar_date="2020-05-04")], [e_req8])],
            [e_req8],
        ),
        requirement(
            "REQ-006", "(9), (9.1)–(9.3)", ["APP-001"], ["prohibition"], "prohibited",
            "Do not operate an aeroplane with an installed engine mount inner retainer meeting any criterion in paragraphs (9.1), (9.2) or (9.3).",
            ["engine mount inner retainer"],
            ["Part listed in Table 1 of Airbus AOT A71N011-15 rev. 01.", "Part installed since manufacture or 01 March 2015, whichever is later, identifiable by a Purchase Order in Table 2 of the AOT.", "Part installed since manufacture or 01 March 2015, whichever is later, and before 27 January 2016, which cannot be identified by a Purchase Order."],
            ["PUB-004"],
            [compliance("CMP-006", "From 04 May 2020.", "conditional", ["Any paragraph (9.1), (9.2) or (9.3) criterion is met."], [limit("LIM-007", "from", None, "calendar_date", "From 04 May 2020", "effective date of the original issue of this AD", [e_req9a], calendar_date="2020-05-04")], [e_req9a, e_req9b])],
            [e_req9a, e_req9b],
        ),
        requirement(
            "REQ-007", "(10), (10.1)–(10.3)", ["APP-001", "APP-002"], ["prohibition"], "prohibited",
            "Do not install an engine mount inner retainer meeting any criterion in paragraphs (10.1), (10.2) or (10.3).",
            ["engine mount inner retainer"],
            ["Part delivered through a Purchase Order listed in Table 2 of AOT A71N011-15 rev. 01.", "Part delivered through an unidentified Purchase Order.", "Part listed in Table 1 of AOT A71N011-15 rev. 01."],
            ["PUB-004"],
            [compliance("CMP-007", "From 27 January 2016.", "conditional", ["Any paragraph (10.1), (10.2) or (10.3) criterion is met."], [limit("LIM-008", "from", None, "calendar_date", "From 27 January 2016", "effective date of the original issue of EASA AD 2016-0010", [e_req10], calendar_date="2016-01-27")], [e_req10])],
            [e_req10],
        ),
        requirement(
            "REQ-008", "(11.1)", ["APP-001"], ["prohibition"], "prohibited",
            "Do not install an affected part after the aeroplane is modified under paragraph (3), or as specified in paragraph (4) or (5).",
            ["affected aft engine mount assembly"], ["Group 1 aeroplane after the stated modification, replacement or credited modification."], [],
            [compliance("CMP-008", "After modification under paragraph (3), (4) or (5).", "conditional", ["Group 1 aeroplane"], [limit("LIM-009", "after", None, "other", "After modification of the aeroplane", "paragraph (3), (4) or (5) action", [e_req11])], [e_req11])],
            [e_req11],
        ),
        requirement(
            "REQ-009", "(11.2)", ["APP-002"], ["prohibition"], "prohibited",
            "Do not install an affected part on a Group 2 aeroplane.",
            ["affected aft engine mount assembly"], ["Group 2 aeroplane"], [],
            [compliance("CMP-009", "From 16 August 2017.", "single", [], [limit("LIM-010", "from", None, "calendar_date", "From 16 August 2017", "effective date of EASA AD 2017-0138", [e_req11], calendar_date="2017-08-16")], [e_req11])],
            [e_req11],
        ),
        requirement(
            "REQ-010", "(12)", ["APP-003"], ["contact_manufacturer"], "conditional",
            "Contact Airbus for approved instructions for the specified 4-lugs-engine/3-lugs-assembly configuration.",
            ["aft engine mount assembly on an aeroplane equipped with a 4-lugs engine"],
            ["Before 15 December 2017, a New P/N for 3-lugs configuration was installed on the affected pylon, or an affected part was modified and re-identified to that corresponding P/N."], [],
            [compliance("CMP-010", "Before next flight after 15 December 2017.", "conditional", ["Specified paragraph (12) configuration"], [limit("LIM-011", "before", None, "before_next_flight", "before next flight after 15 December 2017", "15 December 2017", [e_req12])], [e_req12])],
            [e_req12], follow_on_requirement_ids=["REQ-011"],
        ),
        requirement(
            "REQ-011", "(12)", ["APP-003"], ["other"], "conditional",
            "Accomplish the approved Airbus instructions accordingly.",
            ["specified aft engine mount assembly configuration"], ["Approved instructions have been obtained from Airbus under paragraph (12)."], [],
            [compliance("CMP-011", "Accomplish those instructions accordingly.", "conditional", ["Timing and actions are delegated to the approved Airbus instructions."], [limit("LIM-012", "within", None, "other", "as specified in the approved Airbus instructions", "receipt of approved Airbus instructions", [e_req12])], [e_req12])],
            [e_req12], parent_requirement_id="REQ-010",
        ),
    ]
    record["exceptions"] = [
        {
            "exception_id": "EXC-001",
            "text": "An aeroplane with Airbus modification 158435 embodied in production is Group 2, provided no affected part was installed after manufacture; reliable maintenance records may establish that condition.",
            "applies_to_requirement_ids": ["REQ-001", "REQ-002", "REQ-003", "REQ-004", "REQ-006", "REQ-008"],
            "evidence_ids": [e_group2],
        }
    ]
    record["previous_action_credit"] = [
        {
            "credit_id": "CRD-001",
            "text": "For aeroplanes not equipped with 4-lugs engines, pre-effective-date modification under Airbus SB A320-71-1071 original issue or revision 01 is acceptable for paragraph (3).",
            "applies_to_requirement_ids": ["REQ-003"],
            "credited_publication_ids": ["PUB-008", "PUB-009"],
            "conditions": ["Modification accomplished before this revision's effective date.", "Aeroplane is not equipped with 4-lugs engines."],
            "evidence_ids": [e_credit],
        }
    ]
    record["referenced_publications"] = [
        publication_reference("PUB-001", "all_operators_telex", "Airbus", "A71N001-12", "rev. 01", "2012-08-09", ["optional_method"], [e_pub_aot1, e_later_revs]),
        publication_reference("PUB-002", "all_operators_telex", "Airbus", "A71N001-12", "rev. 02", "2013-02-27", ["optional_method"], [e_pub_aot1, e_later_revs]),
        publication_reference("PUB-003", "all_operators_telex", "Airbus", "A71N011-15", "Original issue", "2015-09-16", ["referenced_information"], [e_pub_aot2, e_later_revs]),
        publication_reference("PUB-004", "all_operators_telex", "Airbus", "A71N011-15", "rev. 01", "2016-02-01", ["required_method"], [e_pub_aot2, e_later_revs]),
        publication_reference("PUB-005", "service_bulletin", "Airbus", "A320-71-1060", "Original issue", "2014-10-09", ["required_method"], [e_pub_sb1060, e_later_revs]),
        publication_reference("PUB-006", "service_bulletin", "Airbus", "A320-71-1060", "rev. 01", "2015-04-07", ["required_method"], [e_pub_sb1060, e_later_revs]),
        publication_reference("PUB-007", "service_bulletin", "Airbus", "A320-71-1060", "rev. 02", "2015-12-18", ["required_method"], [e_pub_sb1060, e_later_revs]),
        publication_reference("PUB-008", "service_bulletin", "Airbus", "A320-71-1071", "Original issue", "2016-11-08", ["previous_action_credit"], [e_pub_sb1071, e_credit, e_later_revs]),
        publication_reference("PUB-009", "service_bulletin", "Airbus", "A320-71-1071", "rev. 01", "2017-10-17", ["previous_action_credit"], [e_pub_sb1071, e_credit, e_later_revs]),
        publication_reference("PUB-010", "service_bulletin", "Airbus", "A320-71-1071", "rev. 02", "2019-10-22", ["required_method"], [e_pub_sb1071, e_def_sb, e_later_revs]),
        publication_reference("PUB-011", "service_bulletin", "Goodrich Aerostructures", "RA32071-146", "rev. 02", "2012-07-26", ["optional_method"], [e_pub_146, e_later_revs]),
        publication_reference("PUB-012", "service_bulletin", "Goodrich Aerostructures", "RA32071-160", "Original issue", "2014-09-18", ["required_method"], [e_pub_160, e_later_revs]),
        publication_reference("PUB-013", "service_bulletin", "Goodrich Aerostructures", "RA32071-160", "rev. 01", "2016-09-23", ["required_method"], [e_pub_160, e_later_revs]),
        publication_reference("PUB-014", "service_bulletin", "Goodrich Aerostructures", "RA32071-164", "Original issue", "2016-10-06", ["required_method"], [e_pub_164, e_later_revs]),
        publication_reference("PUB-015", "service_bulletin", "Goodrich Aerostructures", "RA32071-164", "rev. 01", "2017-07-19", ["required_method"], [e_pub_164, e_later_revs]),
        publication_reference("PUB-016", "service_bulletin", "Goodrich Aerostructures", "RA32071-164", "rev. 02", "2018-04-04", ["required_method"], [e_pub_164, e_later_revs]),
        publication_reference("PUB-017", "service_bulletin", "Goodrich Aerostructures", "RA32071-164", "rev. 03", "2018-09-14", ["required_method"], [e_pub_164, e_later_revs]),
        publication_reference("PUB-018", "service_bulletin", "Goodrich Aerostructures", "RA32071-174", "Original issue", "2019-09-17", ["required_method"], [e_pub_174, e_later_revs]),
    ]
    record["relationships"] = [
        {
            "relationship_id": "REL-001",
            "relationship_type": "revises",
            "target_ad_number": "2020-0085",
            "target_record_id": None,
            "target_logical_version_key": None,
            "source": "structured_supersedure_field",
            "verification_status": "candidate",
            "manually_verified": False,
            "raw_text": "This AD revises EASA AD 2020-0085 dated 06 April 2020.",
            "evidence_ids": [e_cover_fields],
        }
    ]
    record["amoc_and_contacts"] = [
        {"entry_id": "AMC-001", "entry_type": "amoc_authority", "authority_or_organization": "EASA", "contact_text": "EASA can approve Alternative Methods of Compliance for this AD.", "conditions": ["Requested and appropriately substantiated"], "evidence_ids": [e_amoc]},
        {"entry_id": "AMC-002", "entry_type": "regulatory_contact", "authority_or_organization": "EASA Safety Information Section, Certification Directorate", "contact_text": "ADs@easa.europa.eu", "conditions": ["Enquiries regarding this AD"], "evidence_ids": [e_reg_contact]},
        {"entry_id": "AMC-003", "entry_type": "technical_contact", "authority_or_organization": "AIRBUS – Airworthiness Office – IIASA", "contact_text": "account.airworth-eas@airbus.com", "conditions": ["Questions concerning the technical content of the requirements"], "evidence_ids": [e_tech_contact]},
    ]
    action_union = ["inspection", "replacement", "modification", "prohibition", "contact_manufacturer", "other"]
    record["classification"] = {
        "airbus_families": ["A320 family"],
        "ata_chapters": ["71"],
        "action_types": action_union,
        "frequency": "mixed",
        "emergency_status": "standard",
        "terminating_action_present": True,
        "table_or_appendix_present": True,
        "compliance_complexity": "mixed",
        "human_confirmed": False,
        "evidence_ids": [e_subject, e_applicability, e_def_groups, e_req1, e_req2, e_req3, e_req8, e_req9a, e_req9b, e_req10, e_req11, e_req12, e_table1, e_appendix],
    }
    details = [
        detail("/ad_identity/ad_number", [e_header], confidence=0.99),
        detail("/ad_identity/revision_number", [e_header, e_cover_fields], confidence=0.99),
        detail("/ad_identity/design_approval_holder", [e_holder_type], confidence=0.99),
        detail("/ad_identity/supersedure_statement", [e_cover_fields], confidence=0.99),
        detail("/publication/subject", [e_subject], confidence=0.99),
        detail("/publication/issue_date", [e_header], confidence=0.99),
        detail("/publication/effective_date", [e_cover_fields], confidence=0.99),
        detail("/publication/ata_chapters", [e_subject], confidence=0.99),
        detail("/publication/manufacturers", [e_manufacturer], confidence=0.99),
        detail("/publication/type_model_designations", [e_holder_type], confidence=0.99),
        detail("/publication/tcds_numbers", [e_cover_fields], confidence=0.99),
        detail("/publication/foreign_ad", [e_cover_fields], state="not_applicable", confidence=0.99),
        *[detail(f"/applicability_groups/{index}", collect_evidence_ids(group), confidence=0.94) for index, group in enumerate(record["applicability_groups"])],
        *[detail(f"/definitions/{index}", collect_evidence_ids(item), confidence=0.97) for index, item in enumerate(record["definitions"])],
        *[detail(f"/requirements/{index}", collect_evidence_ids(item), confidence=0.93) for index, item in enumerate(record["requirements"])],
        detail("/exceptions/0", [e_group2], confidence=0.91),
        detail("/previous_action_credit/0", [e_credit], confidence=0.98),
        *[detail(f"/referenced_publications/{index}", collect_evidence_ids(item), confidence=0.97) for index, item in enumerate(record["referenced_publications"])],
        detail("/relationships/0", [e_cover_fields], confidence=0.99),
        *[detail(f"/amoc_and_contacts/{index}", collect_evidence_ids(item), confidence=0.98) for index, item in enumerate(record["amoc_and_contacts"])],
        detail("/classification/action_types", [e_req1, e_req2, e_req3, e_req8, e_req12], confidence=0.93),
        detail("/classification/frequency", [e_req1, e_req2, e_req3, e_req8], confidence=0.92),
        detail("/classification/compliance_complexity", [e_req1, e_req9a, e_req9b, e_req10, e_req11, e_req12], confidence=0.94),
    ]
    return finalize(
        record,
        ev,
        details,
        ["complex_table", "cross_page_clause", "complex_applicability", "complex_compliance"],
        notes=[
            "The structured cover sentence supports only the current revision's revises edge to 2020-0085; its historical statement about 2017-0251 was not converted into a current supersedure edge.",
            "Paragraph (12)'s unspecified approved instructions are represented with action type other; no unstated repair or modification content was inferred.",
        ],
    )


def build_2017() -> dict[str, Any]:
    record, packet = load_assignment("2017-0013")
    ev = EvidenceBuilder(packet, record["source_document"]["file_instance_id"])

    e_header = ev.add(
        1,
        "AD No.: 2017-0013 Issued: 27 January 2017",
        "cover",
        clause_path="AD No.; Issued",
    )
    e_holder_type = ev.add(
        1,
        "Design Approval Holder’s Name: Type/Model designation(s): AIRBUS A380 aeroplanes",
        "cover",
        clause_path="Design Approval Holder; Type/Model designation(s)",
    )
    e_cover_fields = ev.add(
        1,
        "Effective Date: 10 February 2017 TCDS Number(s): EASA.A.110 Foreign AD: Not applicable Supersedure: This AD supersedes EASA AD 2016-0095 dated 19 May 2016.",
        "cover",
        clause_path="Effective Date; TCDS; Foreign AD; Supersedure",
    )
    e_subject = ev.add(
        1,
        "ATA 57 – Wings – Flap Parts – Identification / Inspection [Wrong material]",
        "cover",
        clause_path="ATA / Subject",
    )
    e_manufacturer = ev.add(
        1,
        "Manufacturer(s): Airbus",
        "applicability",
        clause_path="Manufacturer(s)",
    )
    e_applicability = ev.add(
        1,
        "Applicability: Airbus A380-841, A380-842 and A380-861 aeroplanes, all manufacturer serial numbers (MSN).",
        "applicability",
        clause_path="Applicability",
    )
    e_reason = ev.add_between(
        1,
        "Reason: Following an Airbus quality control review",
        "could reduce the structural integrity of the aeroplane.",
        "reason",
        clause_path="Reason / defect and consequence",
    )
    e_reason_history = ev.add_between(
        1,
        "To address this potential unsafe condition, Airbus issued Service Bulletin",
        "installed on the right",
        "reason",
        clause_path="Reason / prior action and revision discovery",
    )
    e_revision = ev.add_between(
        2,
        "hand (RH) position a reduced starting date",
        "Table 1, of this AD.",
        "reason",
        clause_path="Reason / changes and retained requirements",
    )
    e_note1 = ev.add(
        2,
        "Note 1: Appendix 1 of this AD lists the s/n of the potentially affected middle flaps (Table 1) and outboard flaps (Table 2).",
        "required_actions_and_compliance_times",
        clause_path="Note 1",
    )
    e_req1 = ev.add_between(
        2,
        "(1) Within 3 months after 02 June 2016",
        "affected parts can be positively identified from that review.",
        "required_actions_and_compliance_times",
        clause_path="(1)",
    )
    e_note2 = ev.add_between(
        2,
        "Note 2: Airbus SB A380-57-8111 lists the batch",
        "re-installed on another aeroplane.",
        "required_actions_and_compliance_times",
        clause_path="Note 2",
    )
    e_req2 = ev.add_between(
        2,
        "(2) For each middle and outboard flap",
        "Airbus SB A380-57-8111.",
        "required_actions_and_compliance_times",
        clause_path="(2)",
    )
    e_req3 = ev.add_between(
        2,
        "(3) If, during the SDI as required by paragraph (2)",
        "accomplish the replacement accordingly.",
        "required_actions_and_compliance_times",
        clause_path="(3)",
    )
    e_req4 = ev.add_between(
        2,
        "(4) From 02 June 2016",
        "Note 3 of this AD.",
        "required_actions_and_compliance_times",
        clause_path="(4)",
    )
    e_def_serviceable = ev.add_between(
        2,
        "Note 3: For the purpose of this AD, a serviceable middle or outboard flap",
        "but has passed an SDI",
        "definitions",
        clause_path="Note 3",
    )
    e_publication = ev.add_between(
        3,
        "Ref. Publications: Airbus SB A380-57-8111 original issue dated 07 January 2016",
        "requirements of this AD.",
        "reference_publications",
        clause_path="Ref. Publications",
    )
    e_amoc = ev.add(
        3,
        "If requested and appropriately substantiated, EASA can approve Alternative Methods of Compliance for this AD.",
        "remarks",
        clause_path="Remarks / 1",
    )
    e_reg_contact = ev.add(
        3,
        "Enquiries regarding this AD should be referred to the EASA Safety Information Section, Certification Directorate. E-mail: ADs@easa.europa.eu.",
        "remarks",
        clause_path="Remarks / 3",
    )
    e_tech_contact = ev.add_between(
        3,
        "For any question concerning the technical content of the requirements in this AD",
        "account.airworth-A380@airbus.com.",
        "remarks",
        clause_path="Remarks / 4",
    )
    e_table_intro = ev.add_between(
        4,
        "Appendix 1 – Middle and Outboard Flaps to be inspected",
        "at the time of aeroplane first delivery to an operator.",
        "appendix",
        clause_path="Appendix 1 / Note 4",
    )
    table1_context = {
        "table_label": "Table 1 – Middle Flaps",
        "row_headers": [],
        "column_headers": ["s/n LH", "s/n RH", "Starting date for service life calculation"],
        "footnotes": ["N/A means not applicable", "Dates are shown dd/mm/yyyy"],
    }
    e_table1a = ev.add_between(
        4,
        "Table 1 – Middle Flaps",
        "TB2054 TB2053 28/11/2012",
        "table",
        clause_path="Appendix 1 / Table 1 (page 4)",
        table_context=table1_context,
    )
    e_table1b = ev.add_between(
        5,
        "Table 1 – Middle Flaps",
        "TB2074 TB2073 19/09/2013",
        "table",
        clause_path="Appendix 1 / Table 1 (page 5)",
        table_context=table1_context,
    )
    table2_context = {
        "table_label": "Table 2 – Outboard Flaps",
        "row_headers": [],
        "column_headers": ["s/n LH", "s/n RH", "Starting date for service life calculation"],
        "footnotes": ["N/A means not applicable", "Dates are shown dd/mm/yyyy"],
    }
    e_table2 = ev.add_between(
        6,
        "Table 2 – Outboard Flaps",
        "TB2042 TB2042 12/10/2012",
        "table",
        clause_path="Appendix 1 / Table 2",
        table_context=table2_context,
    )

    record["ad_identity"].update(
        {
            "correction_date": not_stated(),
            "version_label": "2017-0013",
            "logical_version_key": "2017-0013|UNCORRECTED",
            "is_latest_version": None,
            "lifecycle_status": "unknown",
            "design_approval_holder": grounded_text("Airbus", "AIRBUS", [e_holder_type]),
            "supersedure_statement": grounded_text(
                "This AD supersedes EASA AD 2016-0095 dated 19 May 2016.",
                "This AD supersedes EASA AD 2016-0095 dated 19 May 2016.",
                [e_cover_fields],
            ),
            "evidence_ids": [e_header, e_holder_type, e_cover_fields],
        }
    )
    subject = "ATA 57 – Wings – Flap Parts – Identification / Inspection [Wrong material]"
    models = ["A380-841", "A380-842", "A380-861"]
    record["publication"] = {
        "subject": grounded_text(subject, subject, [e_subject]),
        "issue_date": grounded_date("2017-01-27", "27 January 2017", [e_header]),
        "effective_date": grounded_date("2017-02-10", "10 February 2017", [e_cover_fields]),
        "ata_chapters": [{"code": "57", "title": "Wings", "evidence_ids": [e_subject]}],
        "manufacturers": [{"raw_name": "Airbus", "normalized_name": "Airbus", "role": "manufacturer", "evidence_ids": [e_manufacturer]}],
        "type_model_designations": ["A380"],
        "tcds_numbers": ["EASA.A.110"],
        "foreign_ad": explicit_none("Not applicable", [e_cover_fields]),
    }
    all_msn = lambda restriction_id: {
        "restriction_id": restriction_id,
        "kind": "all",
        "raw_expression": "all manufacturer serial numbers (MSN)",
        "lower_bound": None,
        "upper_bound": None,
        "explicit_values": [],
        "condition": None,
        "evidence_ids": [e_applicability],
    }
    record["applicability_groups"] = [
        {
            "group_id": "APP-001",
            "label": "All listed A380 models and MSNs",
            "state": "present",
            "raw_text": "Airbus A380-841, A380-842 and A380-861 aeroplanes, all manufacturer serial numbers (MSN).",
            "aircraft_families": ["A380"],
            "models": models,
            "serial_restrictions": [all_msn("MSN-001")],
            "part_numbers": [],
            "configuration_conditions": [],
            "exclusions": [],
            "boolean_logic": "all",
            "evidence_ids": [e_applicability],
        },
        {
            "group_id": "APP-002",
            "label": "Aeroplanes with an Appendix 1 middle or outboard flap serial number installed",
            "state": "present",
            "raw_text": "Potentially affected middle and outboard flaps are those with serial numbers listed in Appendix 1, Tables 1 and 2; middle flap s/n TB2101 is removed from Table 1.",
            "aircraft_families": ["A380"],
            "models": models,
            "serial_restrictions": [all_msn("MSN-002")],
            "part_numbers": [],
            "configuration_conditions": ["An installed middle or outboard flap has an s/n listed in Appendix 1 Table 1 or Table 2."],
            "exclusions": ["Middle flap s/n TB2101"],
            "boolean_logic": "mixed",
            "evidence_ids": [e_note1, e_revision, e_table1a, e_table1b, e_table2],
        },
    ]
    record["definitions"] = [
        {
            "definition_id": "DEF-001",
            "term": "Serviceable middle or outboard flap",
            "definition_text": "A part not listed by s/n in Appendix 1, or a listed part that has passed an SDI under Airbus SB A380-57-8111.",
            "evidence_ids": [e_def_serviceable],
        },
        {
            "definition_id": "DEF-002",
            "term": "Starting date for service life calculation",
            "definition_text": "The transfer-of-title date of the aeroplane where the flap s/n was recorded in Airbus documentation at first delivery to an operator.",
            "evidence_ids": [e_table_intro],
        },
    ]
    record["unsafe_condition"] = {
        "state": "present",
        "raw_reason_text": "Non-conforming aluminium alloy was used to manufacture structural parts on middle and outboard flaps. If not detected and corrected, the condition could reduce the structural integrity of the aeroplane.",
        "observed_events_or_defects": ["Non-conforming aluminium alloy was discovered in several middle- and outboard-flap structural parts."],
        "causes": ["Use of non-conforming aluminium alloy during manufacture."],
        "unsafe_conditions": ["Potentially affected flap structural parts made from non-conforming material."],
        "potential_consequences": ["Reduced structural integrity of the aeroplane."],
        "affected_components": ["Middle flap structural parts", "Outboard flap structural parts"],
        "intended_risk_mitigation": ["Identify installed flap serial numbers.", "Perform a one-time special detailed inspection of listed flap parts.", "Replace non-conforming parts with serviceable parts."],
        "evidence_ids": [e_reason, e_reason_history, e_revision],
    }
    record["requirements"] = [
        requirement(
            "REQ-001", "(1)", ["APP-001"], ["test_or_check", "records_review"], "mandatory",
            "Identify the serial numbers of the installed left- and right-hand middle and outboard flaps; reliable delivery or maintenance records are an acceptable identification method.",
            ["installed LH and RH middle and outboard flaps"], [], [],
            [compliance("CMP-001", "Within 3 months after 02 June 2016.", "single", [], [limit("LIM-001", "within", 3, "calendar_month", "Within 3 months", "02 June 2016, the effective date of EASA AD 2016-0095", [e_req1])], [e_req1])],
            [e_req1], follow_on_requirement_ids=["REQ-002"],
        ),
        requirement(
            "REQ-002", "(2)", ["APP-002"], ["inspection"], "conditional",
            "Accomplish a special detailed inspection of each affected flap part identified under paragraph (1) and having an s/n listed in Appendix 1, in accordance with Airbus SB A380-57-8111.",
            ["middle and outboard flap parts with Appendix 1 serial numbers"],
            ["The installed flap s/n is listed in Appendix 1.", "The applicable starting date depends on the affected flap s/n in Appendix 1."],
            ["PUB-001", "PUB-002"],
            [compliance(
                "CMP-002", "Within 7 years or 4 300 flight cycles, whichever occurs first, accumulated by the affected flap from the applicable Appendix 1 date.",
                "whichever_occurs_first", ["Starting date is selected from Appendix 1 by flap s/n."],
                [
                    limit("LIM-002", "within", 7, "calendar_year", "within 7 years", "applicable starting date in Appendix 1", [e_req2, e_table1a, e_table1b, e_table2]),
                    limit("LIM-003", "within", 4300, "flight_cycle", "4 300 flight cycles", "applicable starting date in Appendix 1", [e_req2, e_table1a, e_table1b, e_table2]),
                ],
                [e_req2, e_table_intro, e_table1a, e_table1b, e_table2],
            )],
            [e_req2, e_table_intro, e_table1a, e_table1b, e_table2], parent_requirement_id="REQ-001", follow_on_requirement_ids=["REQ-003"],
        ),
        requirement(
            "REQ-003", "(3)", ["APP-002"], ["contact_manufacturer"], "conditional",
            "Contact Airbus for replacement instructions when the SDI detects a part manufactured from non-conforming material.",
            ["non-conforming middle or outboard flap part"], ["The SDI required by paragraph (2) detects non-conforming material."], [],
            [compliance("CMP-003", "Within 30 days after the SDI required by paragraph (2).", "conditional", ["Non-conforming material detected"], [limit("LIM-004", "within", 30, "calendar_day", "within 30 days", "SDI required by paragraph (2)", [e_req3])], [e_req3])],
            [e_req3], parent_requirement_id="REQ-002", follow_on_requirement_ids=["REQ-004"],
        ),
        requirement(
            "REQ-004", "(3)", ["APP-002"], ["replacement"], "conditional",
            "Accomplish the replacement in accordance with Airbus's replacement instructions.",
            ["non-conforming middle or outboard flap part"], ["Airbus replacement instructions have been obtained under paragraph (3)."], [],
            [compliance("CMP-004", "Within the compliance time indicated in the Airbus instructions.", "conditional", ["Timing is delegated to the approved Airbus instructions."], [limit("LIM-005", "within", None, "other", "within the compliance time indicated in those instructions", "Airbus replacement instructions", [e_req3])], [e_req3])],
            [e_req3], parent_requirement_id="REQ-003",
        ),
        requirement(
            "REQ-005", "(4)", ["APP-002"], ["install"], "conditional",
            "Install an Appendix 1 middle or outboard flap only if it has been determined to be serviceable before installation.",
            ["middle or outboard flap with an Appendix 1 serial number"], ["The flap is a serviceable part under Note 3 before installation."], [],
            [compliance("CMP-005", "From 02 June 2016; serviceability must be determined before installation.", "conditional", ["Installation is limited to a serviceable part."], [limit("LIM-006", "from", None, "calendar_date", "From 02 June 2016", "effective date of EASA AD 2016-0095", [e_req4], calendar_date="2016-06-02")], [e_req4, e_def_serviceable])],
            [e_req4, e_def_serviceable],
        ),
    ]
    record["exceptions"] = []
    record["previous_action_credit"] = []
    record["referenced_publications"] = [
        publication_reference("PUB-001", "service_bulletin", "Airbus", "A380-57-8111", "Original issue", "2016-01-07", ["required_method"], [e_publication]),
        publication_reference("PUB-002", "service_bulletin", "Airbus", "A380-57-8111", "Revision 1", "2016-11-25", ["required_method"], [e_publication]),
    ]
    record["relationships"] = [
        {
            "relationship_id": "REL-001",
            "relationship_type": "supersedes",
            "target_ad_number": "2016-0095",
            "target_record_id": None,
            "target_logical_version_key": None,
            "source": "structured_supersedure_field",
            "verification_status": "candidate",
            "manually_verified": False,
            "raw_text": "This AD supersedes EASA AD 2016-0095 dated 19 May 2016.",
            "evidence_ids": [e_cover_fields],
        },
        {
            "relationship_id": "REL-002",
            "relationship_type": "retains_requirements_of",
            "target_ad_number": "2016-0095",
            "target_record_id": None,
            "target_logical_version_key": None,
            "source": "explicit_directional_sentence",
            "verification_status": "candidate",
            "manually_verified": False,
            "raw_text": "This AD retains the requirements of EASA AD 2016-0095, which is superseded.",
            "evidence_ids": [e_revision],
        },
    ]
    record["amoc_and_contacts"] = [
        {"entry_id": "AMC-001", "entry_type": "amoc_authority", "authority_or_organization": "EASA", "contact_text": "EASA can approve Alternative Methods of Compliance for this AD.", "conditions": ["Requested and appropriately substantiated"], "evidence_ids": [e_amoc]},
        {"entry_id": "AMC-002", "entry_type": "regulatory_contact", "authority_or_organization": "EASA Safety Information Section, Certification Directorate", "contact_text": "ADs@easa.europa.eu", "conditions": ["Enquiries regarding this AD"], "evidence_ids": [e_reg_contact]},
        {"entry_id": "AMC-003", "entry_type": "technical_contact", "authority_or_organization": "AIRBUS - EIANA (Airworthiness Office)", "contact_text": "Telephone: +33 562 110 253; Fax: +33 562 110 307; E-mail: account.airworth-A380@airbus.com", "conditions": ["Questions concerning the technical content of the requirements"], "evidence_ids": [e_tech_contact]},
    ]
    action_union = ["test_or_check", "records_review", "inspection", "contact_manufacturer", "replacement", "install"]
    record["classification"] = {
        "airbus_families": ["A380"],
        "ata_chapters": ["57"],
        "action_types": action_union,
        "frequency": "mixed",
        "emergency_status": "standard",
        "terminating_action_present": False,
        "table_or_appendix_present": True,
        "compliance_complexity": "mixed",
        "human_confirmed": False,
        "evidence_ids": [e_subject, e_applicability, e_req1, e_req2, e_req3, e_req4, e_table_intro, e_table1a, e_table1b, e_table2],
    }
    details = [
        detail("/ad_identity/ad_number", [e_header], confidence=0.99),
        detail("/ad_identity/design_approval_holder", [e_holder_type], confidence=0.99),
        detail("/ad_identity/supersedure_statement", [e_cover_fields], confidence=0.99),
        detail("/publication/subject", [e_subject], confidence=0.99),
        detail("/publication/issue_date", [e_header], confidence=0.99),
        detail("/publication/effective_date", [e_cover_fields], confidence=0.99),
        detail("/publication/ata_chapters", [e_subject], confidence=0.99),
        detail("/publication/manufacturers", [e_manufacturer], confidence=0.99),
        detail("/publication/type_model_designations", [e_holder_type], confidence=0.99),
        detail("/publication/tcds_numbers", [e_cover_fields], confidence=0.99),
        detail("/publication/foreign_ad", [e_cover_fields], state="not_applicable", confidence=0.99),
        *[detail(f"/applicability_groups/{index}", collect_evidence_ids(group), confidence=0.94) for index, group in enumerate(record["applicability_groups"])],
        *[detail(f"/definitions/{index}", collect_evidence_ids(item), confidence=0.97) for index, item in enumerate(record["definitions"])],
        *[detail(f"/requirements/{index}", collect_evidence_ids(item), confidence=0.94) for index, item in enumerate(record["requirements"])],
        *[detail(f"/referenced_publications/{index}", collect_evidence_ids(item), confidence=0.98) for index, item in enumerate(record["referenced_publications"])],
        *[detail(f"/relationships/{index}", collect_evidence_ids(item), confidence=0.99) for index, item in enumerate(record["relationships"])],
        *[detail(f"/amoc_and_contacts/{index}", collect_evidence_ids(item), confidence=0.98) for index, item in enumerate(record["amoc_and_contacts"])],
        detail("/classification/action_types", [e_req1, e_req2, e_req3, e_req4], confidence=0.94),
        detail("/classification/frequency", [e_req1, e_req2, e_req3, e_req4], confidence=0.93),
        detail("/classification/compliance_complexity", [e_req2, e_table_intro, e_table1a, e_table1b, e_table2], confidence=0.96),
    ]
    return finalize(
        record,
        ev,
        details,
        ["complex_table", "cross_page_clause", "complex_applicability", "complex_compliance"],
        section_states={"/exceptions": "absent_in_source", "/previous_action_credit": "absent_in_source"},
        notes=[
            "Appendix flap values are component serial numbers, so they are preserved as table evidence and configuration conditions rather than misclassified as aircraft MSNs or part numbers.",
            "Only the explicit supersedes and retains-requirements statements were converted into relationship candidates."
        ],
    )


BUILDERS = {
    "2019-0183": build_2019,
    "2020-0085R1": build_2020,
    "2017-0013": build_2017,
}


def write_record(ad_number: str) -> Path:
    record = BUILDERS[ad_number]()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_name = ASSIGNMENTS[ad_number]["template"]
    path = OUTPUT_DIR / output_name
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ad", choices=sorted(BUILDERS), action="append")
    args = parser.parse_args()
    selected: Iterable[str] = args.ad or BUILDERS.keys()
    for ad_number in selected:
        path = write_record(ad_number)
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
