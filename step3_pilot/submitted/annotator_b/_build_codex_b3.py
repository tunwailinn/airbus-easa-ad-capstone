from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_DIR = ROOT / "step3_pilot" / "annotations" / "annotator_b"
PAGE_TEXT_DIR = ROOT / "step3_pilot" / "page_text"
OUT_DIR = Path(__file__).resolve().parent

GENERATED_AT = "2026-07-22T13:00:00Z"
STARTED_AT = "2026-07-22T12:45:00Z"
SUBMITTED_AT = "2026-07-22T14:30:00Z"

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


def load_template(filename: str) -> dict[str, Any]:
    return json.loads((TEMPLATE_DIR / filename).read_text(encoding="utf-8"))


def load_pages(filename: str) -> dict[int, dict[str, Any]]:
    pages: dict[int, dict[str, Any]] = {}
    with (PAGE_TEXT_DIR / filename).open(encoding="utf-8") as handle:
        for line in handle:
            page = json.loads(line)
            pages[page["page_number"]] = page
    return pages


class Evidence:
    def __init__(self, file_instance_id: str, pages: dict[int, dict[str, Any]], printed_total: int):
        self.file_instance_id = file_instance_id
        self.pages = pages
        self.printed_total = printed_total
        self.items: list[dict[str, Any]] = []

    def _next_id(self) -> str:
        return f"EV-{len(self.items) + 1:03d}"

    def native(
        self,
        page_number: int,
        section: str,
        start_marker: str,
        end_marker: str | None = None,
        *,
        section_raw: str | None = None,
        clause_path: str | None = None,
        table_context: dict[str, Any] | None = None,
        annotation_note: str | None = None,
    ) -> str:
        page = self.pages[page_number]
        text = page["text"]
        start = text.find(start_marker)
        if start < 0:
            raise ValueError(f"start marker not found on page {page_number}: {start_marker!r}")
        if end_marker is None:
            end = len(text)
        else:
            end = text.find(end_marker, start + len(start_marker))
            if end < 0:
                raise ValueError(f"end marker not found on page {page_number}: {end_marker!r}")
        quote = text[start:end].strip()
        quote_start = text.find(quote, start)
        evidence_id = self._next_id()
        self.items.append(
            {
                "evidence_id": evidence_id,
                "source_file_instance_id": self.file_instance_id,
                "page_number": page_number,
                "printed_page_label": f"{page_number}/{self.printed_total}",
                "section": section,
                "section_raw": section_raw,
                "clause_path": clause_path,
                "exact_quote": quote,
                "start_char": quote_start,
                "end_char": quote_start + len(quote),
                "page_text_sha256": page["page_text_sha256"],
                "bbox_normalized": None,
                "extraction_method": "native_text",
                "quality": "exact",
                "table_context": table_context,
                "annotation_note": annotation_note,
            }
        )
        return evidence_id

    def visual(
        self,
        page_number: int,
        section: str,
        exact_quote: str,
        *,
        section_raw: str | None = None,
        clause_path: str | None = None,
        annotation_note: str,
    ) -> str:
        page = self.pages[page_number]
        evidence_id = self._next_id()
        self.items.append(
            {
                "evidence_id": evidence_id,
                "source_file_instance_id": self.file_instance_id,
                "page_number": page_number,
                "printed_page_label": f"{page_number}/{self.printed_total}",
                "section": section,
                "section_raw": section_raw,
                "clause_path": clause_path,
                "exact_quote": exact_quote,
                "start_char": None,
                "end_char": None,
                "page_text_sha256": page["page_text_sha256"],
                "bbox_normalized": None,
                "extraction_method": "visual_transcription",
                "quality": "visual_transcription",
                "table_context": None,
                "annotation_note": annotation_note,
            }
        )
        return evidence_id


def grounded_text(state: str, value: str | None, raw_text: str | None, evidence_ids: list[str]) -> dict[str, Any]:
    return {"state": state, "value": value, "raw_text": raw_text, "evidence_ids": evidence_ids}


def grounded_date(state: str, value: str | None, raw_text: str | None, evidence_ids: list[str]) -> dict[str, Any]:
    return grounded_text(state, value, raw_text, evidence_ids)


def serial(
    restriction_id: str,
    kind: str,
    raw_expression: str,
    evidence_ids: list[str],
    *,
    lower_bound: str | None = None,
    upper_bound: str | None = None,
    explicit_values: list[str] | None = None,
    condition: str | None = None,
) -> dict[str, Any]:
    return {
        "restriction_id": restriction_id,
        "kind": kind,
        "raw_expression": raw_expression,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "explicit_values": explicit_values or [],
        "condition": condition,
        "evidence_ids": evidence_ids,
    }


def app(
    group_id: str,
    label: str,
    raw_text: str,
    families: list[str],
    models: list[str],
    evidence_ids: list[str],
    *,
    serial_restrictions: list[dict[str, Any]],
    part_numbers: list[str] | None = None,
    configuration_conditions: list[str] | None = None,
    exclusions: list[str] | None = None,
    boolean_logic: str = "all",
) -> dict[str, Any]:
    return {
        "group_id": group_id,
        "label": label,
        "state": "present",
        "raw_text": raw_text,
        "aircraft_families": families,
        "models": models,
        "serial_restrictions": serial_restrictions,
        "part_numbers": part_numbers or [],
        "configuration_conditions": configuration_conditions or [],
        "exclusions": exclusions or [],
        "boolean_logic": boolean_logic,
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
    evidence_ids: list[str],
    *,
    logic: str = "single",
    conditions: list[str] | None = None,
    initial_limits: list[dict[str, Any]] | None = None,
    is_repetitive: bool = False,
    repetitive_intervals: list[dict[str, Any]] | None = None,
    grace_periods: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "compliance_id": compliance_id,
        "state": "present",
        "raw_text": raw_text,
        "logic": logic,
        "conditions": conditions or [],
        "initial_limits": initial_limits or [],
        "is_repetitive": is_repetitive,
        "repetitive_intervals": repetitive_intervals or [],
        "grace_periods": grace_periods or [],
        "evidence_ids": evidence_ids,
    }


def no_termination() -> dict[str, Any]:
    return {
        "state": "not_stated",
        "present": False,
        "scope": "none",
        "action_text": None,
        "terminates_requirement_ids": [],
        "evidence_ids": [],
    }


def requirement(
    requirement_id: str,
    paragraph_reference: str,
    app_ids: list[str],
    action_types: list[str],
    obligation: str,
    action_text: str,
    evidence_ids: list[str],
    *,
    objects: list[str] | None = None,
    conditions: list[str] | None = None,
    publication_ids: list[str] | None = None,
    compliance_rules: list[dict[str, Any]] | None = None,
    parent_requirement_id: str | None = None,
    follow_on_requirement_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "paragraph_reference": paragraph_reference,
        "parent_requirement_id": parent_requirement_id,
        "applicability_group_ids": app_ids,
        "action_types": action_types,
        "obligation": obligation,
        "action_text": action_text,
        "objects_or_components": objects or [],
        "conditions": conditions or [],
        "method_publication_ids": publication_ids or [],
        "compliance_rules": compliance_rules or [],
        "follow_on_requirement_ids": follow_on_requirement_ids or [],
        "terminating_action": no_termination(),
        "evidence_ids": evidence_ids,
    }


def publication_ref(
    publication_id: str,
    publication_type: str,
    issuer: str | None,
    number: str,
    revision: str | None,
    publication_date: str | None,
    roles: list[str],
    evidence_ids: list[str],
    *,
    title: str | None = None,
    later: bool | None = None,
) -> dict[str, Any]:
    return {
        "publication_id": publication_id,
        "publication_type": publication_type,
        "issuer": issuer,
        "number": number,
        "revision": revision,
        "publication_date": publication_date,
        "title": title,
        "roles": roles,
        "later_approved_revisions_allowed": later,
        "evidence_ids": evidence_ids,
    }


def assertion(
    assertion_id: str,
    field_path: str,
    value_state: str,
    evidence_ids: list[str],
    notes: str,
    confidence: float = 0.99,
) -> dict[str, Any]:
    return {
        "assertion_id": assertion_id,
        "field_path": field_path,
        "value_state": value_state,
        "origin": "auto_extracted",
        "verification_status": "unreviewed",
        "confidence": confidence,
        "evidence_ids": evidence_ids,
        "annotator_id": "codex-b3",
        "derivation_rule": None,
        "input_field_paths": [],
        "notes": notes,
    }


def add_assertions(
    record: dict[str, Any],
    section_states: dict[str, tuple[str, list[str], str]],
) -> None:
    assertions: list[dict[str, Any]] = []
    for path in SECTION_PATHS:
        state, evidence_ids, note = section_states[path]
        assertions.append(assertion(f"AST-{len(assertions) + 1:03d}", path, state, evidence_ids, note))

    details: list[tuple[str, str, list[str], str]] = [
        ("/ad_identity/ad_number", "present", record["ad_identity"]["evidence_ids"], "Cover-page AD identity."),
        ("/publication/issue_date", "present", record["publication"]["issue_date"]["evidence_ids"], "Printed issue date."),
        ("/publication/effective_date", "present", record["publication"]["effective_date"]["evidence_ids"], "Printed effective date."),
        ("/publication/subject", "present", record["publication"]["subject"]["evidence_ids"], "Printed ATA subject."),
    ]
    if record["ad_identity"]["is_correction"]:
        details.append(("/ad_identity/correction_date", "present", record["ad_identity"]["correction_date"]["evidence_ids"], "Printed correction notice."))
    if record["ad_identity"]["supersedure_statement"]["state"] in {"present", "explicit_none"}:
        details.append(("/ad_identity/supersedure_statement", "present", record["ad_identity"]["supersedure_statement"]["evidence_ids"], "Structured supersedure field."))
    if record["ad_identity"]["lifecycle_status"] == "superseded":
        details.append(("/ad_identity/lifecycle_status", "present", record["ad_identity"]["evidence_ids"], "Visible lifecycle stamp."))

    for field_name in (
        "applicability_groups",
        "definitions",
        "requirements",
        "exceptions",
        "previous_action_credit",
        "referenced_publications",
        "relationships",
        "amoc_and_contacts",
    ):
        for index, item in enumerate(record[field_name]):
            details.append((f"/{field_name}/{index}", "present", item["evidence_ids"], f"Annotated {field_name} item."))

    for field_path, value_state, evidence_ids, note in details:
        assertions.append(
            assertion(
                f"AST-{len(assertions) + 1:03d}",
                field_path,
                value_state,
                evidence_ids,
                note,
            )
        )
    record["field_assertions"] = assertions


def finalize(
    record: dict[str, Any],
    evidence: Evidence,
    *,
    quality_flags: list[str],
    notes: list[str],
    section_states: dict[str, tuple[str, list[str], str]],
) -> dict[str, Any]:
    record["evidence_spans"] = evidence.items
    record["annotation_metadata"] = {
        "guideline_version": "1.0.0",
        "record_status": "first_pass_complete",
        "creation_method": "hybrid",
        "machine_provenance": {
            "system": "OpenAI Codex",
            "model": "GPT-5",
            "prompt_or_rules_version": "step2-guidelines-1.0.0-manual-pass-b3",
            "generated_at": GENERATED_AT,
        },
        "annotators": [
            {
                "annotator_id": "codex-b3",
                "role": "annotator",
                "started_at": STARTED_AT,
                "submitted_at": SUBMITTED_AT,
            }
        ],
        "events": [
            {
                "event_type": "created",
                "actor_id": "codex-b3",
                "timestamp": STARTED_AT,
                "rationale": "Independent blind first-pass annotation from the assigned PDF and page text.",
            },
            {
                "event_type": "submitted",
                "actor_id": "codex-b3",
                "timestamp": SUBMITTED_AT,
                "rationale": "First pass completed; no review, adjudication, or human approval claimed.",
            },
        ],
        "quality_flags": quality_flags,
        "uncertainty_flags": [],
        "notes": notes,
        "source_text_sha256": record["source_document"]["normalized_text_sha256"],
        "created_at": STARTED_AT,
        "updated_at": SUBMITTED_AT,
    }
    record["benchmark_metadata"]["gold_record"] = False
    record["classification"]["human_confirmed"] = False
    add_assertions(record, section_states)
    return record


def build_2023() -> tuple[str, dict[str, Any]]:
    filename = "2023-0093R1__f8c89a351f146b17.annotation.json"
    record = deepcopy(load_template(filename))
    pages = load_pages("2023-0093R1__f8c89a351f146b17.pages.jsonl")
    evidence = Evidence(record["source_document"]["file_instance_id"], pages, 7)

    ev_identity = evidence.native(1, "cover", "Airworthiness Directive", "Note:", section_raw="AD No. / Issued")
    ev_cover = evidence.native(1, "cover", "Design Approval Holder", "Manufacturer(s):", section_raw="Cover fields")
    ev_app = evidence.native(1, "applicability", "Manufacturer(s):", "Definitions", section_raw="Manufacturer(s) / Applicability")
    ev_defs_1 = evidence.native(1, "definitions", "Definitions", "TE.CAP", section_raw="Definitions")
    ev_defs_2 = evidence.native(2, "definitions", "Serviceable BSCU:", "Groups:", section_raw="Definitions")
    ev_groups = evidence.native(2, "applicability", "Groups:", "Reason:", section_raw="Groups")
    ev_reason_1 = evidence.native(2, "reason", "Reason:", "TE.CAP", section_raw="Reason")
    ev_reason_2 = evidence.native(3, "reason", "To address this potential unsafe condition", "Required Action(s) and Compliance Time(s):", section_raw="Reason")
    ev_req_1 = evidence.native(3, "required_actions_and_compliance_times", "Inspection:", "Table 1 – Relay Inspection", section_raw="Required Action(s) and Compliance Time(s)", clause_path="(1)")
    ev_table_1 = evidence.native(3, "table", "Table 1 – Relay Inspection", "TE.CAP", section_raw="Table 1 – Relay Inspection", clause_path="(1)", table_context={"table_label": "Table 1 – Relay Inspection", "row_headers": ["Affected BSCU", "Non-affected BSCU"], "column_headers": ["BSCU Installed", "Compliance Time (after the effective date of this AD)"], "footnotes": []})
    ev_note_2 = evidence.native(4, "applicability", "Note 2:", "BSCU Replacement:", section_raw="Note 2")
    ev_req_2 = evidence.native(4, "required_actions_and_compliance_times", "BSCU Replacement:", "(3)", section_raw="Required Action(s) and Compliance Time(s)", clause_path="(2)")
    ev_req_3 = evidence.native(4, "required_actions_and_compliance_times", "(3)", "MMEL Amendment:", section_raw="Required Action(s) and Compliance Time(s)", clause_path="(3)")
    ev_req_4 = evidence.native(4, "required_actions_and_compliance_times", "MMEL Amendment:", "Modification:", section_raw="Required Action(s) and Compliance Time(s)", clause_path="(4)")
    ev_req_5 = evidence.native(4, "required_actions_and_compliance_times", "Modification:", "Table 2 – Relay Replacement", section_raw="Required Action(s) and Compliance Time(s)", clause_path="(5)")
    ev_table_2 = evidence.native(4, "table", "Table 2 – Relay Replacement", "Note 3:", section_raw="Table 2 – Relay Replacement", clause_path="(5)", table_context={"table_label": "Table 2 – Relay Replacement", "row_headers": ["1a", "1b"], "column_headers": ["Group", "Compliance Time (after the effective date of this AD)"], "footnotes": []})
    ev_note_3 = evidence.native(4, "required_actions_and_compliance_times", "Note 3:", "Part(s) Installation:", section_raw="Note 3", clause_path="Note 3")
    ev_req_6 = evidence.native(4, "required_actions_and_compliance_times", "Part(s) Installation:", "TE.CAP", section_raw="Required Action(s) and Compliance Time(s)", clause_path="(6)")
    ev_req_7 = evidence.native(5, "required_actions_and_compliance_times", "(7)", "(8)", section_raw="Required Action(s) and Compliance Time(s)", clause_path="(7)")
    ev_req_8 = evidence.native(5, "required_actions_and_compliance_times", "(8)", "Ref. Publications:", section_raw="Required Action(s) and Compliance Time(s)", clause_path="(8)")
    ev_refs = evidence.native(5, "reference_publications", "Ref. Publications:", "Remarks:", section_raw="Ref. Publications")
    ev_amoc = evidence.native(5, "remarks", "If requested and appropriately substantiated", "The original issue of this AD", section_raw="Remarks", clause_path="1")
    ev_reg_contact = evidence.native(5, "remarks", "Enquiries regarding this AD", "Information about any failures", section_raw="Remarks", clause_path="3")
    ev_tech_contact = evidence.native(5, "remarks", "For any question concerning the technical content", "TE.CAP", section_raw="Remarks", clause_path="5")
    ev_appendix_1 = evidence.native(6, "table", "Appendix 1", "TE.CAP", section_raw="Appendix 1 / Table 1 – Affected MSN", table_context={"table_label": "Appendix 1, Table 1 – Affected MSN", "row_headers": [], "column_headers": ["MSN"], "footnotes": []})
    ev_appendix_2 = evidence.native(7, "table", "Appendix 2", "TE.CAP", section_raw="Appendix 2 / Table 2 – Affected MMEL Items", table_context={"table_label": "Appendix 2, Table 2 – Affected MMEL Items", "row_headers": ["32-31-01", "32-32-02", "32-32-03", "32-42-03", "32-42-04", "32-44-01", "32-44-03", "78-09-01", "78-30-01"], "column_headers": ["ITEM", "Title", "Ident MI", "Date", "Effectivity"], "footnotes": []})

    record["ad_identity"].update(
        {
            "design_approval_holder": grounded_text("present", "AIRBUS S.A.S.", "AIRBUS S.A.S.", [ev_cover]),
            "correction_date": grounded_date("not_stated", None, None, []),
            "lifecycle_status": "unknown",
            "supersedure_statement": grounded_text("present", "This AD revises EASA AD 2023-0093 dated 05 May 2023, which superseded EASA AD 2022-0032R1 dated 29 July 2022.", "This AD revises EASA AD 2023-0093 dated 05 May 2023, which superseded EASA AD 2022-0032R1 dated 29 July 2022.", [ev_cover]),
            "evidence_ids": [ev_identity, ev_cover],
        }
    )
    subject = "ATA 32 – Landing Gear – Braking and Steering Control Unit – Replacement / Master Minimum Equipment List – Amendment; ATA 92 – Electric and Electronic Common Installation – Relays – Replacement"
    record["publication"] = {
        "subject": grounded_text("present", subject, subject, [ev_cover]),
        "issue_date": grounded_date("present", "2023-05-15", "Issued: 15 May 2023", [ev_identity]),
        "effective_date": grounded_date("present", "2023-05-19", "Revision 1: 19 May 2023; Original Issue: 19 May 2023", [ev_cover]),
        "ata_chapters": [
            {"code": "32", "title": "Landing Gear – Braking and Steering Control Unit – Replacement / Master Minimum Equipment List – Amendment", "evidence_ids": [ev_cover]},
            {"code": "92", "title": "Electric and Electronic Common Installation – Relays – Replacement", "evidence_ids": [ev_cover]},
        ],
        "manufacturers": [{"raw_name": "Airbus S.A.S.", "normalized_name": "Airbus", "role": "manufacturer", "evidence_ids": [ev_app]}],
        "type_model_designations": ["A319", "A320", "A321"],
        "tcds_numbers": ["EASA.A.064"],
        "foreign_ad": grounded_text("explicit_none", None, "Not applicable", [ev_cover]),
    }

    models = [
        "A319-151N", "A319-153N", "A319-171N", "A320-251N", "A320-252N", "A320-253N",
        "A320-271N", "A320-272N", "A320-273N", "A321-251N", "A321-251NX", "A321-252N",
        "A321-252NX", "A321-253N", "A321-253NX", "A321-271N", "A321-271NX", "A321-272N", "A321-272NX",
    ]
    msn_segment = pages[6]["text"].split("MSN\n", 1)[1].split("TE.CAP", 1)[0]
    affected_msns = re.findall(r"\b[0-9]{4,5}\b", msn_segment)
    if len(affected_msns) != 319 or len(set(affected_msns)) != 319:
        raise ValueError(f"unexpected affected MSN count: {len(affected_msns)} total, {len(set(affected_msns))} unique")

    record["applicability_groups"] = [
        app("APP-001", "Appendix 1 affected MSN population", "Applicable model variants having an MSN listed in Table 1 of Appendix 1 of this AD.", ["A320neo family"], models, [ev_app, ev_appendix_1], serial_restrictions=[serial("MSN-001", "include_list", "MSN listed in Table 1 of Appendix 1", [ev_appendix_1], explicit_values=affected_msns)]),
        app("APP-002", "Group 1a aeroplanes", "Group 1a aeroplanes are those that have an affected BSCU and a type 1 relay installed.", ["A320neo family"], models, [ev_app, ev_groups], serial_restrictions=[serial("MSN-002", "all", "all manufacturer serial numbers (MSN)", [ev_app])], part_numbers=["E21327307", "E0244-28A0"], configuration_conditions=["Affected BSCU P/N E21327307 installed", "Type 1 relay P/N E0244-28A0 installed at FIN 24GG and 25GG"]),
        app("APP-003", "Group 1b aeroplanes", "Group 1b aeroplanes are those that have a non-affected BSCU and a type 1 relay installed.", ["A320neo family"], models, [ev_app, ev_groups], serial_restrictions=[serial("MSN-003", "all", "all manufacturer serial numbers (MSN)", [ev_app])], part_numbers=["E0244-28A0"], configuration_conditions=["BSCU P/N other than E21327307 installed", "Type 1 relay P/N E0244-28A0 installed at FIN 24GG and 25GG"]),
        app("APP-004", "Group 2 aeroplanes", "Group 2 aeroplanes are those that are not Group 1a nor 1b; an aeroplane with mod 171984 embodied in production and an MSN not listed in Appendix 1 is Group 2 while it remains in that configuration.", ["A320neo family"], models, [ev_app, ev_groups], serial_restrictions=[serial("MSN-004", "all", "all manufacturer serial numbers (MSN)", [ev_app])], configuration_conditions=["Not Group 1a or Group 1b", "Includes mod 171984/type 2 relay P/N E0669D28A0 production configuration for MSN not listed in Appendix 1 while configuration is retained"], boolean_logic="mixed"),
        app("APP-005", "All applicable aeroplanes", "The listed Airbus A319neo, A320neo and A321neo variants, all manufacturer serial numbers.", ["A320neo family"], models, [ev_app], serial_restrictions=[serial("MSN-005", "all", "all manufacturer serial numbers (MSN)", [ev_app])]),
    ]

    definitions = [
        ("Affected BSCU", "Braking and Steering Control Units (BSCU) having Part Number (P/N) E21327307.", [ev_defs_1]),
        ("Non-affected BSCU", "Any BSCU having a P/N other than E21327307.", [ev_defs_1]),
        ("Serviceable BSCU", "Any BSCU, eligible for installation, which is a non-affected BSCU; or an affected BSCU that has never triggered any fault signature on an aeroplane as defined in Appendix 1 of the AOT 1.", [ev_defs_2]),
        ("Type 1 relay", "Relays having P/N E0244-28A0, installed at Functional Item Number (FIN) positions 24GG and 25GG.", [ev_defs_2]),
        ("Type 2 relay", "A relay having P/N E0669D28A0.", [ev_defs_2]),
        ("The AOT 1", "Airbus Alert Operators Transmission (AOT) A32N025-22.", [ev_defs_2]),
        ("The AOT 2", "Airbus AOT A32N030-23.", [ev_defs_2]),
        ("The SB", "Airbus Service Bulletin (SB) A320-92-1149.", [ev_defs_2]),
        ("The MMEL update", "Airbus A318/A319/A320/A321 Master Minimum Equipment List (MMEL) items listed in the Appendix 2 of this AD or in the MMEL Revision dated 05 April 2023.", [ev_defs_2, ev_appendix_2]),
        ("The FOT", "Airbus Flight Operations Transmission (FOT) 999.0010/22.", [ev_defs_2]),
        ("Aeroplane date of manufacture", "The date of transfer of title (ownership) which is referenced in Airbus documentation at the time of first delivery to an operator.", [ev_defs_2]),
    ]
    record["definitions"] = [
        {"definition_id": f"DEF-{i:03d}", "term": term, "definition_text": text, "evidence_ids": evs}
        for i, (term, text, evs) in enumerate(definitions, 1)
    ]
    record["unsafe_condition"] = {
        "state": "present",
        "raw_reason_text": evidence.items[6]["exact_quote"] + "\n" + evidence.items[7]["exact_quote"],
        "observed_events_or_defects": ["Several BSCU channel failures were detected.", "A type 1 relay was installed where a type 2 relay should have been installed.", "Relays at FIN 24GG/25GG on certain post-production aeroplanes did not conform to the Aeroplane Inspection Report."],
        "causes": ["The affected BSCU standard P/N E21327307 introduced by modification 165148", "Combination of a type 1 relay with an affected BSCU can induce BSCU freezing"],
        "unsafe_conditions": ["Dual BSCU channel failures can cause loss of anti-skid, reversion to alternate braking, and loss of nose wheel steering.", "BSCU freezing caused by the affected BSCU/type 1 relay combination."],
        "potential_consequences": ["Loss of braking performance with a significant increase in stopping distance, possibly resulting in runway excursion."],
        "affected_components": ["Braking and Steering Control Unit P/N E21327307", "Type 1 relays at FIN 24GG and 25GG"],
        "intended_risk_mitigation": ["Relay identification inspection", "Replacement of affected BSCUs after fault signatures", "MMEL/MEL amendment and flight-crew notification", "Replacement and installation prohibition for type 1 relays"],
        "evidence_ids": [ev_reason_1, ev_reason_2],
    }

    record["referenced_publications"] = [
        publication_ref("PUB-001", "all_operators_telex", "Airbus", "A32N025-22", "original issue", "2022-02-24", ["required_method", "referenced_information"], [ev_refs], title="Alert Operators Transmission", later=True),
        publication_ref("PUB-002", "all_operators_telex", "Airbus", "A32N025-22", "Revision 01", "2023-05-10", ["required_method", "referenced_information"], [ev_refs], title="Alert Operators Transmission", later=True),
        publication_ref("PUB-003", "all_operators_telex", "Airbus", "A32N030-23", "original issue", "2023-02-27", ["required_method", "referenced_information"], [ev_refs], title="Alert Operators Transmission", later=True),
        publication_ref("PUB-004", "other", "Airbus", "A318/A319/A320/A321 MMEL", "Revision", "2023-04-05", ["required_method", "referenced_information"], [ev_refs, ev_appendix_2], title="Master Minimum Equipment List", later=True),
        publication_ref("PUB-005", "other", "Airbus", "999.0010/22", "original issue", "2022-02-22", ["referenced_information"], [ev_refs], title="Flight Operations Transmission", later=True),
        publication_ref("PUB-006", "other", "Airbus", "999.0010/22", "Revision 01", "2022-02-25", ["referenced_information"], [ev_refs], title="Flight Operations Transmission", later=True),
        publication_ref("PUB-007", "service_bulletin", "Airbus", "A320-92-1149", "original issue", "2022-10-11", ["required_method", "referenced_information"], [ev_refs], later=True),
        publication_ref("PUB-008", "service_bulletin", "Airbus", "A320-92-1149", "Revision 01", "2023-01-20", ["required_method", "referenced_information"], [ev_refs], later=True),
    ]

    def months_cmp(cid: str, lid: str, months: int, evs: list[str], condition: str | None = None) -> dict[str, Any]:
        return compliance(cid, f"Within {months} months after the effective date of this AD", evs, conditions=[condition] if condition else [], initial_limits=[limit(lid, "within", months, "calendar_month", f"Within {months} months after the effective date of this AD", "effective_date", evs)])

    def before_next(cid: str, lid: str, raw: str, evs: list[str], condition: str) -> dict[str, Any]:
        return compliance(cid, raw, evs, conditions=[condition], initial_limits=[limit(lid, "before", None, "before_next_flight", "before next flight", "BSCU fault signature trigger", evs)])

    def from_effective(cid: str, lid: str, raw: str, evs: list[str]) -> dict[str, Any]:
        return compliance(cid, raw, evs, initial_limits=[limit(lid, "from", None, "other", raw, "effective_date", evs)])

    mmel_items = ["32-31-01", "32-32-02", "32-32-03", "32-42-03", "32-42-04", "32-44-01", "32-44-03", "78-09-01", "78-30-01"]
    record["requirements"] = [
        requirement("REQ-001", "(1)", ["APP-001"], ["inspection"], "mandatory", "Visually inspect FIN 24GG and 25GG to determine whether a type 1 relay is installed, for an aeroplane with an affected BSCU.", [ev_req_1, ev_table_1, ev_appendix_1], objects=["Relays at FIN 24GG and 25GG"], conditions=["MSN listed in Appendix 1", "Affected BSCU installed"], compliance_rules=[months_cmp("CMP-001", "LIM-001", 12, [ev_table_1], "Affected BSCU installed")]),
        requirement("REQ-002", "(1)", ["APP-001"], ["inspection"], "mandatory", "Visually inspect FIN 24GG and 25GG to determine whether a type 1 relay is installed, for an aeroplane with a non-affected BSCU.", [ev_req_1, ev_table_1, ev_appendix_1], objects=["Relays at FIN 24GG and 25GG"], conditions=["MSN listed in Appendix 1", "Non-affected BSCU installed"], compliance_rules=[months_cmp("CMP-002", "LIM-002", 24, [ev_table_1], "Non-affected BSCU installed")]),
        requirement("REQ-003", "(2)", ["APP-002"], ["replacement"], "conditional", "Replace the affected BSCU with a serviceable BSCU in accordance with AOT 1 if a defined BSCU fault signature is triggered.", [ev_req_2], objects=["Affected BSCU"], conditions=["Group 1a aeroplane", "MSN not listed in Appendix 1", "Fault signature triggered during any flight after 10 March 2022"], publication_ids=["PUB-001", "PUB-002"], compliance_rules=[before_next("CMP-003", "LIM-003", "If a BSCU fault signature is triggered during any flight after 10 March 2022, before next flight", [ev_req_2], "Fault signature triggered after 10 March 2022")]),
        requirement("REQ-004", "(3)", ["APP-002", "APP-001"], ["replacement"], "conditional", "Replace the affected BSCU with a serviceable BSCU in accordance with AOT 1 if a defined BSCU fault signature is triggered.", [ev_req_3], objects=["Affected BSCU"], conditions=["Group 1a aeroplane", "MSN listed in Appendix 1", "Fault signature triggered during any flight after the effective date"], publication_ids=["PUB-001", "PUB-002"], compliance_rules=[before_next("CMP-004", "LIM-004", "If a BSCU fault signature is triggered during any flight after the effective date of this AD, before next flight", [ev_req_3], "Fault signature triggered after the effective date")]),
        requirement("REQ-005", "(4)", ["APP-005"], ["document_amendment"], "mandatory", "Implement the instructions of the MMEL update.", [ev_req_4, ev_appendix_2], objects=["MMEL items " + ", ".join(mmel_items)], conditions=["Apply the Appendix 2 item effectivity or the MMEL Revision dated 05 April 2023"], publication_ids=["PUB-004"], compliance_rules=[compliance("CMP-005", "Before next flight after the effective date of this AD", [ev_req_4], initial_limits=[limit("LIM-005", "before", None, "before_next_flight", "Before next flight after the effective date of this AD", "effective_date", [ev_req_4])])]),
        requirement("REQ-006", "(4)", ["APP-005"], ["document_amendment"], "mandatory", "Amend the operator’s MEL on the basis of the MMEL update.", [ev_req_4, ev_appendix_2], objects=["Operator Minimum Equipment List"], publication_ids=["PUB-004"], compliance_rules=[compliance("CMP-006", "Before next flight after the effective date of this AD", [ev_req_4], initial_limits=[limit("LIM-006", "before", None, "before_next_flight", "Before next flight after the effective date of this AD", "effective_date", [ev_req_4])])]),
        requirement("REQ-007", "(4)", ["APP-005"], ["operational_procedure"], "mandatory", "Inform all flight crews of the MMEL/MEL update.", [ev_req_4], objects=["All flight crews"], publication_ids=["PUB-004"], compliance_rules=[compliance("CMP-007", "Before next flight after the effective date of this AD", [ev_req_4], initial_limits=[limit("LIM-007", "before", None, "before_next_flight", "Before next flight after the effective date of this AD", "effective_date", [ev_req_4])])]),
        requirement("REQ-008", "(4)", ["APP-005"], ["operational_procedure", "limitation"], "mandatory", "Thereafter, operate the aeroplane in accordance with the amended MEL.", [ev_req_4], objects=["Aeroplane operation under amended MEL"], publication_ids=["PUB-004"], compliance_rules=[compliance("CMP-008", "thereafter, operate the aeroplane accordingly", [ev_req_4], initial_limits=[limit("LIM-008", "after", None, "other", "thereafter", "implementation of the MMEL update and MEL amendment", [ev_req_4])])]),
        requirement("REQ-009", "(5)", ["APP-002"], ["replacement"], "mandatory", "For a Group 1a aeroplane with an MSN not listed in Appendix 1, replace each type 1 relay with a type 2 relay in accordance with the SB.", [ev_req_5, ev_table_2], objects=["Type 1 relay P/N E0244-28A0"], conditions=["Group 1a", "MSN not listed in Appendix 1"], publication_ids=["PUB-007", "PUB-008"], compliance_rules=[months_cmp("CMP-009", "LIM-009", 12, [ev_table_2], "Group 1a")]),
        requirement("REQ-010", "(5)", ["APP-002", "APP-001"], ["replacement"], "mandatory", "For a Group 1a aeroplane with an MSN listed in Appendix 1, replace each type 1 relay with a type 2 relay in accordance with AOT 2.", [ev_req_5, ev_table_2], objects=["Type 1 relay P/N E0244-28A0"], conditions=["Group 1a", "MSN listed in Appendix 1"], publication_ids=["PUB-003"], compliance_rules=[months_cmp("CMP-010", "LIM-010", 12, [ev_table_2], "Group 1a")]),
        requirement("REQ-011", "(5)", ["APP-003"], ["replacement"], "mandatory", "For a Group 1b aeroplane with an MSN not listed in Appendix 1, replace each type 1 relay with a type 2 relay in accordance with the SB.", [ev_req_5, ev_table_2], objects=["Type 1 relay P/N E0244-28A0"], conditions=["Group 1b", "MSN not listed in Appendix 1"], publication_ids=["PUB-007", "PUB-008"], compliance_rules=[months_cmp("CMP-011", "LIM-011", 24, [ev_table_2], "Group 1b")]),
        requirement("REQ-012", "(5)", ["APP-003", "APP-001"], ["replacement"], "mandatory", "For a Group 1b aeroplane with an MSN listed in Appendix 1, replace each type 1 relay with a type 2 relay in accordance with AOT 2.", [ev_req_5, ev_table_2], objects=["Type 1 relay P/N E0244-28A0"], conditions=["Group 1b", "MSN listed in Appendix 1"], publication_ids=["PUB-003"], compliance_rules=[months_cmp("CMP-012", "LIM-012", 24, [ev_table_2], "Group 1b")]),
        requirement("REQ-013", "(6.1)", ["APP-002", "APP-003"], ["prohibition", "install"], "prohibited", "Do not install relay P/N E0244-28A0 at FIN 24GG and 25GG after completing paragraph (5).", [ev_req_6], objects=["Relay P/N E0244-28A0 at FIN 24GG and 25GG"], conditions=["Group 1a or Group 1b", "Paragraph (5) modification completed"], compliance_rules=[compliance("CMP-013", "After modification of the aeroplane as required by paragraph (5) of this AD", [ev_req_6], initial_limits=[limit("LIM-013", "after", None, "other", "After modification required by paragraph (5)", "paragraph (5) modification", [ev_req_6])])]),
        requirement("REQ-014", "(6.2)", ["APP-004"], ["prohibition", "install"], "prohibited", "Do not install relay P/N E0244-28A0 at FIN 24GG and 25GG on a Group 2 aeroplane.", [ev_req_6], objects=["Relay P/N E0244-28A0 at FIN 24GG and 25GG"], conditions=["Group 2"], compliance_rules=[from_effective("CMP-014", "LIM-014", "From the effective date of this AD", [ev_req_6])]),
        requirement("REQ-015", "(7)", ["APP-002"], ["prohibition", "install"], "prohibited", "Install a BSCU on a Group 1a aeroplane only if it is a serviceable BSCU.", [ev_req_7], objects=["BSCU"], conditions=["Group 1a", "Installation permitted only for a serviceable BSCU"], compliance_rules=[from_effective("CMP-015", "LIM-015", "From the effective date of this AD", [ev_req_7])]),
        requirement("REQ-016", "(8)", ["APP-003"], ["prohibition", "install"], "prohibited", "Do not install an affected BSCU on a Group 1b aeroplane.", [ev_req_8], objects=["Affected BSCU P/N E21327307"], conditions=["Group 1b"], compliance_rules=[from_effective("CMP-016", "LIM-016", "From the effective date of this AD", [ev_req_8])]),
    ]
    record["exceptions"] = []
    record["previous_action_credit"] = [
        {"credit_id": "CRD-001", "text": "Required as indicated, unless accomplished previously.", "applies_to_requirement_ids": [f"REQ-{i:03d}" for i in range(1, 13)], "credited_publication_ids": [], "conditions": ["Applicable action already accomplished"], "evidence_ids": [ev_req_1]}
    ]
    record["relationships"] = [
        {"relationship_id": "REL-001", "relationship_type": "revises", "target_ad_number": "2023-0093", "target_record_id": None, "target_logical_version_key": None, "source": "structured_supersedure_field", "verification_status": "candidate", "manually_verified": False, "raw_text": "This AD revises EASA AD 2023-0093 dated 05 May 2023.", "evidence_ids": [ev_cover]},
        {"relationship_id": "REL-002", "relationship_type": "referenced_only", "target_ad_number": "2022-0032R1", "target_record_id": None, "target_logical_version_key": None, "source": "historical_reference", "verification_status": "candidate", "manually_verified": False, "raw_text": "EASA AD 2023-0093 dated 05 May 2023, which superseded EASA AD 2022-0032R1 dated 29 July 2022.", "evidence_ids": [ev_cover, ev_reason_2]},
        {"relationship_id": "REL-003", "relationship_type": "referenced_only", "target_ad_number": "2022-0032", "target_record_id": None, "target_logical_version_key": None, "source": "historical_reference", "verification_status": "candidate", "manually_verified": False, "raw_text": "Consequently, EASA issued AD 2022-0032 (later revised).", "evidence_ids": [ev_reason_2]},
        {"relationship_id": "REL-004", "relationship_type": "referenced_only", "target_ad_number": "F-1993-163-043", "target_record_id": None, "target_logical_version_key": None, "source": "historical_reference", "verification_status": "candidate", "manually_verified": False, "raw_text": "required through DGAC France AD F-1993-163-043 (grandfathered by EASA)", "evidence_ids": [ev_reason_2]},
    ]
    record["amoc_and_contacts"] = [
        {"entry_id": "AMC-001", "entry_type": "amoc_authority", "authority_or_organization": "EASA", "contact_text": "If requested and appropriately substantiated, EASA can approve Alternative Methods of Compliance for this AD.", "conditions": ["Requested and appropriately substantiated"], "evidence_ids": [ev_amoc]},
        {"entry_id": "AMC-002", "entry_type": "regulatory_contact", "authority_or_organization": "EASA Safety Information Section, Certification Directorate", "contact_text": "E-mail: ADs@easa.europa.eu.", "conditions": [], "evidence_ids": [ev_reg_contact]},
        {"entry_id": "AMC-003", "entry_type": "technical_contact", "authority_or_organization": "AIRBUS – Airworthiness Office – 1IASA", "contact_text": "E-mail: account.airworth-eas@airbus.com.", "conditions": [], "evidence_ids": [ev_tech_contact]},
    ]
    record["classification"] = {
        "airbus_families": ["A320neo family"],
        "ata_chapters": ["32", "92"],
        "action_types": ["inspection", "replacement", "document_amendment", "operational_procedure", "limitation", "prohibition", "install"],
        "frequency": "mixed",
        "emergency_status": "standard",
        "terminating_action_present": False,
        "table_or_appendix_present": True,
        "compliance_complexity": "mixed",
        "human_confirmed": False,
        "evidence_ids": [ev_cover, ev_app, ev_groups, ev_req_1, ev_table_1, ev_req_2, ev_req_3, ev_req_4, ev_req_5, ev_table_2, ev_req_6, ev_req_7, ev_req_8, ev_appendix_1, ev_appendix_2],
    }

    section_states = {
        "/ad_identity": ("present", record["ad_identity"]["evidence_ids"], "Section completion: AD identity reviewed."),
        "/publication": ("present", [ev_identity, ev_cover, ev_app], "Section completion: publication reviewed."),
        "/applicability_groups": ("present", [ev_app, ev_groups, ev_appendix_1], "Section completion: model, MSN and configuration applicability reviewed."),
        "/definitions": ("present", [ev_defs_1, ev_defs_2, ev_appendix_2], "Section completion: all explicit definitions reviewed."),
        "/unsafe_condition": ("present", [ev_reason_1, ev_reason_2], "Section completion: unsafe condition reviewed."),
        "/requirements": ("present", [ev_req_1, ev_table_1, ev_req_2, ev_req_3, ev_req_4, ev_req_5, ev_table_2, ev_req_6, ev_req_7, ev_req_8], "Section completion: requirements and table-driven branches reviewed."),
        "/exceptions": ("absent_in_source", [], "Section completion: no separate requirement exceptions."),
        "/previous_action_credit": ("present", [ev_req_1], "Section completion: generic accomplished-previously credit reviewed."),
        "/referenced_publications": ("present", [ev_refs, ev_appendix_2], "Section completion: referenced publications reviewed."),
        "/relationships": ("present", [ev_cover, ev_reason_2], "Section completion: revision and historical AD references reviewed; historical references are not supersedure edges."),
        "/amoc_and_contacts": ("present", [ev_amoc, ev_reg_contact, ev_tech_contact], "Section completion: AMOC and contacts reviewed."),
        "/classification": ("present", record["classification"]["evidence_ids"], "Section completion: classification reviewed."),
    }
    return filename, finalize(
        record,
        evidence,
        quality_flags=["complex_table", "complex_applicability", "complex_compliance"],
        notes=[
            "All seven PDF pages were visually rendered and checked independently, including both appendix tables.",
            "Appendix 1 contains 319 unique affected MSN values, preserved in the applicability restriction.",
            "Historical AD references are labeled referenced_only and are not treated as current-document supersedure edges.",
            "Note 3 changes the post-modification group classification but does not explicitly declare a terminating action.",
        ],
        section_states=section_states,
    )


def build_2007() -> tuple[str, dict[str, Any]]:
    filename = "2007-0278__0b6a17dbe6f95907.annotation.json"
    record = deepcopy(load_template(filename))
    pages = load_pages("2007-0278__0b6a17dbe6f95907.pages.jsonl")
    evidence = Evidence(record["source_document"]["file_instance_id"], pages, 4)

    ev_identity = evidence.native(1, "cover", "AD No.:", "No person may operate", section_raw="AD No. / Date")
    ev_cover = evidence.native(1, "cover", "Type Approval Holder", "Reason:", section_raw="Cover fields")
    ev_reason_1 = evidence.native(1, "reason", "Reason:", "1/4", section_raw="Reason")
    ev_reason_2 = evidence.native(2, "reason", "modification of electrical bonding of equipment installed in fuel", "This new AD supersedes", section_raw="Reason")
    ev_change_notice = evidence.native(2, "reason", "This new AD supersedes", "Effective Date:", section_raw="Reason / correction notice")
    ev_effective = evidence.native(2, "cover", "Effective Date:", "Compliance:", section_raw="Effective Date")
    ev_compliance_intro = evidence.native(2, "compliance", "Compliance:", "Action n°1 applicable to:", section_raw="Compliance")
    ev_action_1 = evidence.native(2, "compliance", "Action n°1 applicable to:", "Action n°2 applicable to:", section_raw="Compliance", clause_path="Action 1")
    ev_action_2a = evidence.native(2, "compliance", "Action n°2 applicable to:", "2/4", section_raw="Compliance", clause_path="Action 2")
    ev_action_2b = evidence.native(3, "compliance", "production or modified in-service", "For aircraft that have already been modified", section_raw="Compliance", clause_path="Action 2")
    ev_action_2_extra = evidence.native(3, "compliance", "For aircraft that have already been modified", "Accomplishment of AIRBUS SB A330-28-3101", section_raw="Compliance", clause_path="Action 2 additional work")
    ev_action_2_credit = evidence.native(3, "credit", "Accomplishment of AIRBUS SB A330-28-3101", "Action n°3 applicable to:", section_raw="Compliance", clause_path="Action 2 credit")
    ev_action_3 = evidence.native(3, "compliance", "Action n°3 applicable to:", "Reminder:", section_raw="Compliance", clause_path="Action 3")
    ev_reminder = evidence.native(3, "compliance", "Reminder:", "Action n°4 applicable to:", section_raw="Compliance", clause_path="Action 3 reminder")
    ev_action_4 = evidence.native(3, "compliance", "Action n°4 applicable to:", "For all aircraft where", section_raw="Compliance", clause_path="Action 4")
    ev_action_4_defer_a = evidence.native(3, "compliance", "For all aircraft where", "3/4", section_raw="Compliance", clause_path="Action 4 extension")
    ev_action_4_defer_b = evidence.native(4, "compliance", "1996 (\"solution A\")", "Action n°5 applicable to:", section_raw="Compliance", clause_path="Action 4 extension")
    ev_action_5 = evidence.native(4, "compliance", "Action n°5 applicable to:", "Accomplishment of AIRBUS SB A340-28-4073", section_raw="Compliance", clause_path="Action 5")
    ev_action_5_credit = evidence.native(4, "credit", "Accomplishment of AIRBUS SB A340-28-4073", "Ref. Publications:", section_raw="Compliance", clause_path="Action 5 credit")
    ev_refs = evidence.native(4, "reference_publications", "Ref. Publications:", "Remarks :", section_raw="Ref. Publications")
    ev_amoc = evidence.native(4, "remarks", "If requested and appropriately substantiated", "This AD was posted", section_raw="Remarks", clause_path="1")
    ev_reg_contact = evidence.native(4, "remarks", "Enquiries regarding this Airworthiness Directive", "For any question concerning", section_raw="Remarks", clause_path="3")
    ev_tech_contact = evidence.native(4, "remarks", "For any question concerning", "4/4", section_raw="Remarks", clause_path="4")
    ev_stamp = evidence.visual(1, "other", "SUPERSEDED", section_raw="Lifecycle stamp", annotation_note="Large diagonal SUPERSEDED stamp visible on the rendered PDF but absent from native page text.")

    record["ad_identity"].update(
        {
            "design_approval_holder": grounded_text("present", "AIRBUS", "AIRBUS", [ev_cover]),
            "correction_date": grounded_date("present", "2007-11-08", "[Corrected: 08 November 2007]", [ev_identity, ev_change_notice]),
            "lifecycle_status": "superseded",
            "supersedure_statement": grounded_text("present", "EASA AD 2006-0322 dated 18 October 2006", "EASA AD 2006-0322 dated 18 October 2006.", [ev_cover]),
            "evidence_ids": [ev_identity, ev_cover, ev_change_notice, ev_stamp],
        }
    )
    record["publication"] = {
        "subject": grounded_text("present", "Fuel - Fuel tanks – Prevention against Fuel Explosion Risks – Modification / Installation", "ATA 28 Fuel - Fuel tanks – Prevention against Fuel Explosion Risks – Modification / Installation", [ev_cover]),
        "issue_date": grounded_date("present", "2007-11-05", "Date: 05 November 2007", [ev_identity]),
        "effective_date": grounded_date("present", "2007-11-19", "Effective Date: 19 November 2007", [ev_effective]),
        "ata_chapters": [{"code": "28", "title": "Fuel - Fuel tanks – Prevention against Fuel Explosion Risks – Modification / Installation", "evidence_ids": [ev_cover]}],
        "manufacturers": [{"raw_name": "AIRBUS (formerly AIRBUS INDUSTRIE)", "normalized_name": "Airbus", "role": "manufacturer", "evidence_ids": [ev_cover]}],
        "type_model_designations": ["A330", "A340-200", "A340-300"],
        "tcds_numbers": ["EASA A.004", "EASA A.015"],
        "foreign_ad": grounded_text("explicit_none", None, "Not applicable", [ev_cover]),
    }

    all_msn = lambda rid, ev: [serial(rid, "all", "all serial numbers", [ev])]
    record["applicability_groups"] = [
        app("APP-001", "Action 1 aircraft", "AIRBUS A330, A340-200 and A340-300 aircraft, all certified models, all serial numbers except aircraft with modification 47634 embodied in production.", ["A330 family", "A340 family"], ["A330", "A340-200", "A340-300"], [ev_action_1], serial_restrictions=all_msn("MSN-001", ev_action_1), exclusions=["AIRBUS modification No. 47634 embodied in production"]),
        app("APP-002", "Action 2 aircraft", "AIRBUS A330, A340-200 and A340-300 aircraft, all certified models, all serial numbers except aircraft with modifications 49135, 49630, 51825 and 55118 embodied in production, or modified in-service by both applicable SB pairs.", ["A330 family", "A340 family"], ["A330", "A340-200", "A340-300"], [ev_action_2a, ev_action_2b], serial_restrictions=all_msn("MSN-002", ev_action_2a), exclusions=["All four AIRBUS modifications 49135, 49630, 51825 and 55118 embodied in production", "A330 aircraft modified in-service by both SB A330-28-3082 Revision 04 and SB A330-28-3101 Revision 01", "A340 aircraft modified in-service by both SB A340-28-4097 Revision 03 and SB A340-28-4118 Revision 02"], boolean_logic="mixed"),
        app("APP-003", "Action 2 additional-work aircraft", "Aircraft already modified by SB A330-28-3082 at original issue or SB A340-28-4097 at an issue before Revision 03.", ["A330 family", "A340 family"], ["A330", "A340-200", "A340-300"], [ev_action_2_extra], serial_restrictions=all_msn("MSN-003", ev_action_2_extra), configuration_conditions=["Already modified by SB A330-28-3082 at original issue OR SB A340-28-4097 at any issue before Revision 03"], boolean_logic="mixed"),
        app("APP-004", "Action 3 ACT aircraft", "AIRBUS A340-200 and A340-300 aircraft with modification 42612/SB A340-28-4047, 44002/SB A340-28-4066, or 44005/SB A340-28-4067 embodied, except aircraft modified by SB A340-28-4078 Revision 01 in service.", ["A340 family"], ["A340-200", "A340-300"], [ev_action_3], serial_restrictions=all_msn("MSN-004", ev_action_3), configuration_conditions=["One of modification 42612/SB A340-28-4047, 44002/SB A340-28-4066, or 44005/SB A340-28-4067 embodied in production or in service (installation of ACT)"], exclusions=["Modified by SB A340-28-4078 Revision 01 in service"], boolean_logic="mixed"),
        app("APP-005", "Action 4 A330-300 aircraft", "AIRBUS A330-300 -301, -321, -322, -341 and -342 models, all serial numbers, except modification 44252 embodied in production or SB A330-55-3016 embodied in service.", ["A330 family"], ["A330-301", "A330-321", "A330-322", "A330-341", "A330-342"], [ev_action_4], serial_restrictions=all_msn("MSN-005", ev_action_4), exclusions=["AIRBUS modification No. 44252 embodied in production", "Modified in-service in accordance with AIRBUS SB A330-55-3016"]),
        app("APP-006", "Action 4 A340 aircraft", "AIRBUS A340-200 and A340-300 aircraft, all certified models, all serial numbers, except modification 44252 embodied in production or SB A340-55-4017 embodied in service.", ["A340 family"], ["A340-200", "A340-300"], [ev_action_4], serial_restrictions=all_msn("MSN-006", ev_action_4), exclusions=["AIRBUS modification No. 44252 embodied in production", "Modified in-service in accordance with AIRBUS SB A340-55-4017"]),
        app("APP-007", "Action 4 solution A extension aircraft", "Aircraft on which the THS lightning strike protection improvement was already performed in accordance with AOT 55-03 dated 22 August 1996 (solution A), mandated by the listed DGAC ADs.", ["A330 family", "A340 family"], ["A330-300", "A340-200", "A340-300"], [ev_action_4_defer_a, ev_action_4_defer_b], serial_restrictions=all_msn("MSN-007", ev_action_4_defer_b), configuration_conditions=["THS lightning strike protection improvement already performed under AOT 55-03 dated 22 August 1996 (solution A)", "Mandated by DGAC AD F-1996-178-049(B) R1 or DGAC AD F-1996-177-038(B) with 15 November 1996 compliance"], boolean_logic="mixed"),
        app("APP-008", "Action 5 aircraft", "AIRBUS A340-200 and A340-300 aircraft, all certified models, all serial numbers, except modification 46142 embodied in production or SB A340-28-4073 Revision 02 embodied in service.", ["A340 family"], ["A340-200", "A340-300"], [ev_action_5], serial_restrictions=all_msn("MSN-008", ev_action_5), exclusions=["Modification 46142 embodied in production", "Modified in-service in accordance with AIRBUS SB A340-28-4073 Revision 02"]),
    ]
    record["definitions"] = []
    record["unsafe_condition"] = {
        "state": "present",
        "raw_reason_text": evidence.items[2]["exact_quote"] + "\n" + evidence.items[3]["exact_quote"],
        "observed_events_or_defects": ["The TWA800 Boeing 747-131 accident prompted an explosion-hazard design review."],
        "causes": ["Fuel quantity indicator and fuel level sensor harness chafing against metallic P-clips", "Inadequate or omitted electrical bonding in fuel tanks and the ACT", "Insufficient distance between metallic parts on the THS Trim Tank", "Missing bonding lead on the jettison valve actuator and drive assembly"],
        "unsafe_conditions": ["Fuel tank explosion risks"],
        "potential_consequences": ["Fuel explosion hazard"],
        "affected_components": ["Fuel tank P-clips and FQI/FLSS harnesses", "Fuel-tank equipment bonding", "Additional Center Tank", "THS Trim Tank", "Jettison valve actuator and drive assembly"],
        "intended_risk_mitigation": ["Inspect P-clips and perform corrective actions", "Modify electrical bonding", "Increase THS Trim Tank metallic-part distance", "Install a jettison-valve bonding lead"],
        "evidence_ids": [ev_reason_1, ev_reason_2, ev_change_notice],
    }

    refs = [
        publication_ref("PUB-001", "service_bulletin", "Airbus", "A330-28-3092", "Revision 01", None, ["required_method", "referenced_information"], [ev_action_1, ev_refs], later=True),
        publication_ref("PUB-002", "service_bulletin", "Airbus", "A340-28-4107", "Revision 01", None, ["required_method", "referenced_information"], [ev_action_1, ev_refs], later=True),
        publication_ref("PUB-003", "service_bulletin", "Airbus", "A330-28-3082", "Revision 04", None, ["required_method", "referenced_information"], [ev_action_2b, ev_refs], later=True),
        publication_ref("PUB-004", "service_bulletin", "Airbus", "A330-28-3101", "Revision 01", None, ["required_method", "referenced_information"], [ev_action_2b, ev_refs], later=True),
        publication_ref("PUB-005", "service_bulletin", "Airbus", "A340-28-4097", "Revision 03", None, ["required_method", "referenced_information"], [ev_action_2b, ev_refs], later=True),
        publication_ref("PUB-006", "service_bulletin", "Airbus", "A340-28-4118", "Revision 02", None, ["required_method", "referenced_information"], [ev_action_2b, ev_refs], later=True),
        publication_ref("PUB-007", "service_bulletin", "Airbus", "A340-28-4078", "Revision 01", None, ["required_method", "referenced_information"], [ev_action_3, ev_refs], later=True),
        publication_ref("PUB-008", "service_bulletin", "Airbus", "A330-55-3016", None, None, ["required_method", "referenced_information"], [ev_action_4, ev_refs], later=True),
        publication_ref("PUB-009", "service_bulletin", "Airbus", "A340-55-4017", None, None, ["required_method", "referenced_information"], [ev_action_4, ev_refs], later=True),
        publication_ref("PUB-010", "service_bulletin", "Airbus", "A340-28-4073", "Revision 02", None, ["required_method", "referenced_information"], [ev_action_5, ev_refs], later=True),
        publication_ref("PUB-011", "service_bulletin", "Airbus", "A330-28-3101", "original issue", None, ["previous_action_credit"], [ev_action_2_credit]),
        publication_ref("PUB-012", "service_bulletin", "Airbus", "A340-28-4118", "original issue", None, ["previous_action_credit"], [ev_action_2_credit]),
        publication_ref("PUB-013", "service_bulletin", "Airbus", "A340-28-4118", "Revision 01", None, ["previous_action_credit"], [ev_action_2_credit]),
        publication_ref("PUB-014", "service_bulletin", "Airbus", "A330-28-3082", "Revision 01", None, ["previous_action_credit"], [ev_action_2_credit]),
        publication_ref("PUB-015", "service_bulletin", "Airbus", "A330-28-3082", "Revision 02", None, ["previous_action_credit"], [ev_action_2_credit]),
        publication_ref("PUB-016", "service_bulletin", "Airbus", "A330-28-3082", "Revision 03", None, ["previous_action_credit"], [ev_action_2_credit]),
        publication_ref("PUB-017", "service_bulletin", "Airbus", "A340-28-4078", "original issue", None, ["previous_action_credit"], [ev_action_3]),
        publication_ref("PUB-018", "service_bulletin", "Airbus", "A340-28-4073", "original issue", None, ["previous_action_credit"], [ev_action_5_credit]),
        publication_ref("PUB-019", "service_bulletin", "Airbus", "A340-28-4073", "Revision 01", None, ["previous_action_credit"], [ev_action_5_credit]),
        publication_ref("PUB-020", "service_bulletin", "Airbus", "A340-28-4047", None, None, ["referenced_information"], [ev_action_3]),
        publication_ref("PUB-021", "service_bulletin", "Airbus", "A340-28-4066", None, None, ["referenced_information"], [ev_action_3]),
        publication_ref("PUB-022", "service_bulletin", "Airbus", "A340-28-4067", None, None, ["referenced_information"], [ev_action_3]),
        publication_ref("PUB-023", "all_operators_telex", "Airbus", "55-03", None, "1996-08-22", ["referenced_information"], [ev_action_4_defer_a, ev_action_4_defer_b]),
        publication_ref("PUB-024", "other", "DGAC France", "F-1996-178-049(B) R1", None, None, ["referenced_information"], [ev_action_4_defer_a, ev_action_4_defer_b], title="Airworthiness Directive"),
        publication_ref("PUB-025", "other", "DGAC France", "F-1996-177-038(B)", None, None, ["referenced_information"], [ev_action_4_defer_a, ev_action_4_defer_b], title="Airworthiness Directive"),
    ]
    record["referenced_publications"] = refs

    def date_cmp(cid: str, lid: str, date_value: str, raw: str, evs: list[str]) -> dict[str, Any]:
        return compliance(cid, raw, evs, initial_limits=[limit(lid, "not_later_than", None, "calendar_date", raw, None, evs, calendar_date=date_value)])

    record["requirements"] = [
        requirement("REQ-001", "Action 1", ["APP-001"], ["inspection"], "mandatory", "Perform a detailed visual inspection of the P-clips in the wings and center fuel tanks.", [ev_action_1], objects=["P-clips in wings and center fuel tanks"], publication_ids=["PUB-001", "PUB-002"], compliance_rules=[date_cmp("CMP-001", "LIM-001", "2009-12-31", "Not later than December 31st, 2009", [ev_action_1])], follow_on_requirement_ids=["REQ-002"]),
        requirement("REQ-002", "Action 1", ["APP-001"], ["other"], "conditional", "If necessary, apply the corrective actions specified by the applicable Service Bulletin.", [ev_action_1], objects=["P-clips and associated fuel-system harnesses"], conditions=["Corrective action is necessary based on inspection"], publication_ids=["PUB-001", "PUB-002"], compliance_rules=[date_cmp("CMP-002", "LIM-002", "2009-12-31", "Not later than December 31st, 2009", [ev_action_1])], parent_requirement_id="REQ-001"),
        requirement("REQ-003", "Action 2", ["APP-002"], ["modification"], "mandatory", "Modify the electrical bonding of equipment installed in fuel tanks.", [ev_action_2a, ev_action_2b], objects=["Electrical bonding of equipment installed in fuel tanks"], publication_ids=["PUB-003", "PUB-004", "PUB-005", "PUB-006"], compliance_rules=[date_cmp("CMP-003", "LIM-003", "2009-12-31", "Not later than December 31st, 2009", [ev_action_2b])]),
        requirement("REQ-004", "Action 2 additional work", ["APP-003"], ["modification"], "mandatory", "Perform the additional bonding work introduced by the specified later Service Bulletin revision.", [ev_action_2_extra], objects=["Previously omitted fuel-tank bonding points"], publication_ids=["PUB-003", "PUB-005"], compliance_rules=[date_cmp("CMP-004", "LIM-004", "2011-12-31", "Not later than December 31st, 2011", [ev_action_2_extra])]),
        requirement("REQ-005", "Action 3", ["APP-004"], ["modification"], "mandatory", "Modify the electrical bonding in the Additional Center Tank.", [ev_action_3], objects=["Additional Center Tank electrical bonding"], publication_ids=["PUB-007"], compliance_rules=[date_cmp("CMP-005", "LIM-005", "2009-12-31", "Not later than December 31st, 2009", [ev_action_3])]),
        requirement("REQ-006", "Action 3 reminder", ["APP-004"], ["records_review", "limitation"], "mandatory", "Ensure that any spare ACT that could be installed does not jeopardize aircraft compliance with this AD.", [ev_reminder], objects=["Spare Additional Center Tank"], conditions=["A spare ACT could be installed on the aircraft"], compliance_rules=[compliance("CMP-006", "Ensure any spare ACT that could be installed does not jeopardize compliance", [ev_reminder], conditions=["Spare ACT installation"], initial_limits=[limit("LIM-006", "upon", None, "other", "when a spare ACT could be installed", "spare ACT installation", [ev_reminder])])]),
        requirement("REQ-007", "Action 4", ["APP-005", "APP-006"], ["modification"], "mandatory", "Increase the distance between metallic parts on the THS Trim Tank.", [ev_action_4], objects=["Metallic parts on the THS Trim Tank"], conditions=["Aircraft does not qualify for the solution A compliance-time extension in Action 4"], publication_ids=["PUB-008", "PUB-009"], compliance_rules=[date_cmp("CMP-007", "LIM-007", "2009-12-31", "Not later than December 31st, 2009", [ev_action_4])]),
        requirement("REQ-008", "Action 4 solution A extension", ["APP-007"], ["modification"], "mandatory", "Increase the distance between metallic parts on the THS Trim Tank at the first specified maintenance opportunity after 31 December 2009.", [ev_action_4_defer_a, ev_action_4_defer_b], objects=["Metallic parts on the THS Trim Tank"], publication_ids=["PUB-008", "PUB-009"], compliance_rules=[compliance("CMP-008", "After 31st December 2009, whenever the THS is first removed and placed on the support tool for any reason, or at the first maintenance task requiring THS lifting and resting point fittings", [ev_action_4_defer_a, ev_action_4_defer_b], logic="whichever_occurs_first", conditions=["Solution A improvement already performed"], initial_limits=[limit("LIM-008", "upon", None, "other", "first THS removal from aircraft and placement on Support Tool after 31 December 2009", "first qualifying THS removal after 2009-12-31", [ev_action_4_defer_b]), limit("LIM-009", "upon", None, "next_scheduled_check", "first aircraft maintenance task requiring THS Lifting and Resting points Fittings after 31 December 2009", "first qualifying maintenance task after 2009-12-31", [ev_action_4_defer_b])])]),
        requirement("REQ-009", "Action 5", ["APP-008"], ["install"], "mandatory", "Install a bonding lead between the bonding tags on the jettison valve actuator and drive assembly.", [ev_action_5], objects=["Jettison valve actuator and drive assembly bonding lead"], publication_ids=["PUB-010"], compliance_rules=[date_cmp("CMP-009", "LIM-010", "2009-12-31", "Not later than December 31st, 2009", [ev_action_5])]),
    ]
    record["exceptions"] = []
    record["previous_action_credit"] = [
        {"credit_id": "CRD-001", "text": "Unless already accomplished, the listed measures are mandatory from 02 November 2006.", "applies_to_requirement_ids": ["REQ-001", "REQ-002", "REQ-003", "REQ-004", "REQ-005", "REQ-007", "REQ-008", "REQ-009"], "credited_publication_ids": [], "conditions": ["Action already accomplished"], "evidence_ids": [ev_compliance_intro]},
        {"credit_id": "CRD-002", "text": "The specified earlier issues of A330-28-3101, A340-28-4118 and A330-28-3082 are acceptable for Action 2 compliance.", "applies_to_requirement_ids": ["REQ-003"], "credited_publication_ids": ["PUB-011", "PUB-012", "PUB-013", "PUB-014", "PUB-015", "PUB-016"], "conditions": [], "evidence_ids": [ev_action_2_credit]},
        {"credit_id": "CRD-003", "text": "Accomplishment of AIRBUS SB A340-28-4078 at original issue is acceptable for Action 3 compliance.", "applies_to_requirement_ids": ["REQ-005"], "credited_publication_ids": ["PUB-017"], "conditions": [], "evidence_ids": [ev_action_3]},
        {"credit_id": "CRD-004", "text": "Accomplishment of AIRBUS SB A340-28-4073 at original issue or Revision 01 is acceptable for Action 5 compliance.", "applies_to_requirement_ids": ["REQ-009"], "credited_publication_ids": ["PUB-018", "PUB-019"], "conditions": [], "evidence_ids": [ev_action_5_credit]},
    ]
    record["relationships"] = [
        {"relationship_id": "REL-001", "relationship_type": "supersedes", "target_ad_number": "2006-0322", "target_record_id": None, "target_logical_version_key": None, "source": "structured_supersedure_field", "verification_status": "candidate", "manually_verified": False, "raw_text": "Supersedure: EASA AD 2006-0322 dated 18 October 2006.", "evidence_ids": [ev_cover, ev_change_notice]}
    ]
    record["amoc_and_contacts"] = [
        {"entry_id": "AMC-001", "entry_type": "amoc_authority", "authority_or_organization": "EASA", "contact_text": "If requested and appropriately substantiated, EASA can accept Alternative Methods of Compliance for this AD.", "conditions": ["Requested and appropriately substantiated"], "evidence_ids": [ev_amoc]},
        {"entry_id": "AMC-002", "entry_type": "regulatory_contact", "authority_or_organization": "EASA", "contact_text": "Airworthiness Directive Focal Point - Certification Directorate, EASA. E-mail: ADs@easa.europa.eu.", "conditions": [], "evidence_ids": [ev_reg_contact]},
        {"entry_id": "AMC-003", "entry_type": "technical_contact", "authority_or_organization": "AIRBUS SAS – Airworthiness Office - EAL", "contact_text": "E-mail: airworthiness.A330-A340@airbus.com.", "conditions": [], "evidence_ids": [ev_tech_contact]},
    ]
    record["classification"] = {
        "airbus_families": ["A330 family", "A340 family"],
        "ata_chapters": ["28"],
        "action_types": ["inspection", "other", "modification", "records_review", "limitation", "install"],
        "frequency": "mixed",
        "emergency_status": "standard",
        "terminating_action_present": False,
        "table_or_appendix_present": False,
        "compliance_complexity": "mixed",
        "human_confirmed": False,
        "evidence_ids": [ev_cover, ev_action_1, ev_action_2a, ev_action_2b, ev_action_2_extra, ev_action_3, ev_action_4, ev_action_4_defer_a, ev_action_4_defer_b, ev_action_5],
    }

    section_states = {
        "/ad_identity": ("present", record["ad_identity"]["evidence_ids"], "Section completion: AD identity and visible lifecycle stamp reviewed."),
        "/publication": ("present", [ev_identity, ev_cover, ev_effective], "Section completion: publication reviewed."),
        "/applicability_groups": ("present", [ev_action_1, ev_action_2a, ev_action_2b, ev_action_3, ev_action_4, ev_action_5], "Section completion: action-specific applicability reviewed."),
        "/definitions": ("absent_in_source", [], "Section completion: no explicit definitions section or defined terms."),
        "/unsafe_condition": ("present", [ev_reason_1, ev_reason_2], "Section completion: unsafe condition reviewed."),
        "/requirements": ("present", [ev_action_1, ev_action_2a, ev_action_2b, ev_action_2_extra, ev_action_3, ev_reminder, ev_action_4, ev_action_4_defer_b, ev_action_5], "Section completion: requirements reviewed."),
        "/exceptions": ("absent_in_source", [], "Section completion: applicability exclusions are encoded inside applicability groups; no separate requirement exception."),
        "/previous_action_credit": ("present", [ev_compliance_intro, ev_action_2_credit, ev_action_3, ev_action_5_credit], "Section completion: previous-action credit reviewed."),
        "/referenced_publications": ("present", [ev_refs, ev_action_2_credit, ev_action_3, ev_action_4_defer_b, ev_action_5_credit], "Section completion: referenced publications reviewed."),
        "/relationships": ("present", [ev_cover, ev_change_notice], "Section completion: explicit supersedure reviewed; no correction edge fabricated without a distinct target."),
        "/amoc_and_contacts": ("present", [ev_amoc, ev_reg_contact, ev_tech_contact], "Section completion: AMOC and contacts reviewed."),
        "/classification": ("present", record["classification"]["evidence_ids"], "Section completion: classification reviewed."),
    }
    return filename, finalize(
        record,
        evidence,
        quality_flags=["visual_transcription_used", "complex_applicability", "complex_compliance", "cross_page_clause"],
        notes=[
            "All four PDF pages were visually rendered and checked independently.",
            "The lifecycle status is based on the diagonal SUPERSEDED stamp visible on every rendered page; the native text omits that stamp.",
            "The correction notice is recorded without a correction relationship because no distinct uncorrected target publication is present in the assigned pilot.",
            "Action 1 corrective actions are unspecified in the AD and therefore use the controlled label other.",
        ],
        section_states=section_states,
    )


def build_2009() -> tuple[str, dict[str, Any]]:
    filename = "2009-0025__46511578be7115fd.annotation.json"
    record = deepcopy(load_template(filename))
    pages = load_pages("2009-0025__46511578be7115fd.pages.jsonl")
    evidence = Evidence(record["source_document"]["file_instance_id"], pages, 3)

    ev_identity = evidence.native(1, "cover", "AD No.: 2009-0025", "Note:", section_raw="AD No. / Date")
    ev_cover = evidence.native(1, "cover", "Type Approval Holder", "Reason:", section_raw="Cover fields")
    ev_reason = evidence.native(1, "reason", "Reason:", "EASA Form 110", section_raw="Reason")
    ev_correction = evidence.native(2, "other", "This Correction is issued", "Effective Date:", section_raw="Correction notice")
    ev_effective = evidence.native(2, "cover", "Effective Date:", "Required Action(s)", section_raw="Effective Date")
    ev_1a = evidence.native(2, "required_actions_and_compliance_times", "Within 600 flight hours", "If the bearing of a pendulum assembly is found to have migrated", section_raw="Required Action(s) and Compliance Time(s)", clause_path="1.a")
    ev_1b = evidence.native(2, "required_actions_and_compliance_times", "If the bearing of a pendulum assembly is found to have migrated", "If the bearing of a pendulum assembly is found incorrectly swaged", section_raw="Required Action(s) and Compliance Time(s)", clause_path="1.b")
    ev_1c = evidence.native(2, "required_actions_and_compliance_times", "If the bearing of a pendulum assembly is found incorrectly swaged", "The required actions as per paragraph 1.", section_raw="Required Action(s) and Compliance Time(s)", clause_path="1.c")
    ev_exceptions = evidence.native(2, "required_actions_and_compliance_times", "The required actions as per paragraph 1.", "After the effective date of this AD", section_raw="Required Action(s) and Compliance Time(s)", clause_path="2")
    ev_prohibition = evidence.native(2, "required_actions_and_compliance_times", "After the effective date of this AD", "Ref. Publications:", section_raw="Required Action(s) and Compliance Time(s)", clause_path="3")
    ev_refs = evidence.native(2, "reference_publications", "Ref. Publications:", "EASA Form 110", section_raw="Ref. Publications")
    ev_amoc = evidence.native(3, "remarks", "If requested and appropriately substantiated", "This AD was published", section_raw="Remarks", clause_path="1")
    ev_reg_contact = evidence.native(3, "remarks", "Enquiries regarding this AD", "For any question concerning", section_raw="Remarks", clause_path="3")
    ev_tech_contact = evidence.native(3, "remarks", "For any question concerning", "EASA Form 110", section_raw="Remarks", clause_path="4")

    record["ad_identity"].update(
        {
            "design_approval_holder": grounded_text("present", "AIRBUS", "AIRBUS", [ev_cover]),
            "correction_date": grounded_date("present", "2009-02-11", "[Corrected: 11 February 2009]", [ev_identity, ev_correction]),
            "lifecycle_status": "unknown",
            "supersedure_statement": grounded_text("explicit_none", None, "None", [ev_cover]),
            "evidence_ids": [ev_identity, ev_cover, ev_correction],
        }
    )
    record["publication"] = {
        "subject": grounded_text("present", "Wings – Flap Track No.1 Pendulum Assembly – Inspection / Replacement", "ATA 57 Wings – Flap Track No.1 Pendulum Assembly – Inspection / Replacement", [ev_cover]),
        "issue_date": grounded_date("present", "2009-02-10", "Date: 10 February 2009", [ev_identity]),
        "effective_date": grounded_date("present", "2009-02-24", "Effective Date: 24 February 2009", [ev_effective]),
        "ata_chapters": [{"code": "57", "title": "Wings – Flap Track No.1 Pendulum Assembly – Inspection / Replacement", "evidence_ids": [ev_cover]}],
        "manufacturers": [{"raw_name": "AIRBUS (formerly AIRBUS INDUSTRIE)", "normalized_name": "Airbus", "role": "manufacturer", "evidence_ids": [ev_cover]}],
        "type_model_designations": ["A318", "A319", "A320", "A321"],
        "tcds_numbers": ["EASA.A.064"],
        "foreign_ad": grounded_text("explicit_none", None, "Not applicable", [ev_cover]),
    }

    a318_320_models = [
        "A318-111", "A318-112", "A318-121", "A318-122", "A319-111", "A319-112", "A319-113",
        "A319-114", "A319-115", "A319-131", "A319-132", "A319-133", "A320-111", "A320-211",
        "A320-212", "A320-214", "A320-215", "A320-216", "A320-231", "A320-232", "A320-233",
    ]
    a321_models = ["A321-111", "A321-112", "A321-131", "A321-211", "A321-212", "A321-213", "A321-231", "A321-232"]
    record["applicability_groups"] = [
        app("APP-001", "A318/A319/A320 aircraft", "AIRBUS A318, A319 and A320 listed models, all manufacturer serial numbers.", ["A320 family"], a318_320_models, [ev_cover], serial_restrictions=[serial("MSN-001", "all", "all manufacturer serial numbers", [ev_cover])]),
        app("APP-002", "A321 aircraft", "AIRBUS A321 listed models, all manufacturer serial numbers.", ["A320 family"], a321_models, [ev_cover], serial_restrictions=[serial("MSN-002", "all", "all manufacturer serial numbers", [ev_cover])]),
    ]
    record["definitions"] = []
    record["unsafe_condition"] = {
        "state": "present",
        "raw_reason_text": evidence.items[2]["exact_quote"],
        "observed_events_or_defects": ["A flap track No.1 pendulum assembly bearing migrated out of position during a routine inspection."],
        "causes": ["In-service bearing replacement was performed without the necessary special tools, fixtures and equipment."],
        "unsafe_conditions": ["Separation of the bearing/flap track assembly and detachment of the affected flap surface from the wing."],
        "potential_consequences": ["Loss of control of the aircraft."],
        "affected_components": ["Flap track No.1 pendulum assembly bearing", "Affected flap surface"],
        "intended_risk_mitigation": ["One-time bearing migration inspection", "Replacement of an affected flap track pendulum assembly", "Corrective action for an incorrectly swaged bearing"],
        "evidence_ids": [ev_reason],
    }

    refs = [
        publication_ref("PUB-001", "service_bulletin", "Airbus", "A320-57-1144", "original issue", "2007-02-06", ["required_method", "referenced_information"], [ev_refs], later=True),
        publication_ref("PUB-002", "service_bulletin", "Airbus", "A320-57-1144", "Revision 1", "2007-06-18", ["required_method", "referenced_information"], [ev_refs], later=True),
        publication_ref("PUB-003", "alert_service_bulletin", "Airbus", "A320-57A1146", "original issue", "2007-09-21", ["required_method", "referenced_information"], [ev_refs], later=True),
    ]
    record["referenced_publications"] = refs

    cmp_600 = lambda cid, lid, ev: compliance(cid, "Within 600 flight hours after the effective date of this AD", [ev], initial_limits=[limit(lid, "within", 600, "flight_hour", "Within 600 flight hours after the effective date of this AD", "effective_date", [ev])])
    cmp_before = lambda cid, lid, raw, ev: compliance(cid, raw, [ev], conditions=[raw.split(", before")[0] if ", before" in raw else raw], initial_limits=[limit(lid, "before", None, "before_next_flight", "before next/further flight", "specified finding", [ev])])
    cmp_from = lambda cid, lid, ev: compliance(cid, "After the effective date of this AD", [ev], initial_limits=[limit(lid, "after", None, "other", "After the effective date of this AD", "effective_date", [ev])])

    record["requirements"] = [
        requirement("REQ-001", "1.a", ["APP-001"], ["inspection"], "mandatory", "Inspect the flap track No.1 pendulum assembly in accordance with Airbus SB A320-57A1146.", [ev_1a], objects=["Flap track No.1 pendulum assembly"], publication_ids=["PUB-003"], compliance_rules=[cmp_600("CMP-001", "LIM-001", ev_1a)], follow_on_requirement_ids=["REQ-003", "REQ-004"]),
        requirement("REQ-002", "1.a", ["APP-002"], ["inspection"], "mandatory", "Inspect the flap track No.1 pendulum assembly in accordance with Airbus SB A320-57-1144.", [ev_1a], objects=["Flap track No.1 pendulum assembly"], publication_ids=["PUB-001", "PUB-002"], compliance_rules=[cmp_600("CMP-002", "LIM-002", ev_1a)], follow_on_requirement_ids=["REQ-003", "REQ-004"]),
        requirement("REQ-003", "1.b", ["APP-001", "APP-002"], ["replacement"], "conditional", "If the bearing of a pendulum assembly is found to have migrated, replace the affected flap track pendulum assembly.", [ev_1b], objects=["Affected flap track pendulum assembly"], conditions=["Bearing migration is found"], compliance_rules=[cmp_before("CMP-003", "LIM-003", "If bearing migration is found, before further flight", ev_1b)]),
        requirement("REQ-004", "1.c", ["APP-001", "APP-002"], ["contact_manufacturer"], "conditional", "If a bearing is found incorrectly swaged, contact Airbus for further instructions.", [ev_1c], objects=["Incorrectly swaged pendulum assembly bearing"], conditions=["Bearing is found incorrectly swaged"], compliance_rules=[cmp_before("CMP-004", "LIM-004", "If a bearing is found incorrectly swaged, before next flight", ev_1c)], follow_on_requirement_ids=["REQ-005", "REQ-006"]),
        requirement("REQ-005", "1.c", ["APP-001"], ["other"], "conditional", "Accomplish the relevant corrective actions in accordance with Airbus SB A320-57A1146.", [ev_1c], objects=["Incorrectly swaged pendulum assembly bearing"], conditions=["Bearing is found incorrectly swaged"], publication_ids=["PUB-003"], compliance_rules=[cmp_before("CMP-005", "LIM-005", "If a bearing is found incorrectly swaged, before next flight", ev_1c)], parent_requirement_id="REQ-004"),
        requirement("REQ-006", "1.c", ["APP-002"], ["other"], "conditional", "Accomplish the relevant corrective actions in accordance with Airbus SB A320-57-1144.", [ev_1c], objects=["Incorrectly swaged pendulum assembly bearing"], conditions=["Bearing is found incorrectly swaged"], publication_ids=["PUB-001", "PUB-002"], compliance_rules=[cmp_before("CMP-006", "LIM-006", "If a bearing is found incorrectly swaged, before next flight", ev_1c)], parent_requirement_id="REQ-004"),
        requirement("REQ-007", "3", ["APP-001", "APP-002"], ["prohibition", "replacement"], "prohibited", "Do not replace the bearing in the flap track pendulum assembly unless the pendulum assembly is of new manufacture or records demonstrate that the bearing has not been replaced or re-swaged since new manufacture.", [ev_prohibition], objects=["Bearing in the flap track pendulum assembly"], conditions=["Permitted only if the pendulum assembly is of new manufacture OR records demonstrate the bearing has not been replaced or re-swaged since new manufacture"], compliance_rules=[cmp_from("CMP-007", "LIM-007", ev_prohibition)]),
        requirement("REQ-008", "3", ["APP-001", "APP-002"], ["prohibition", "install"], "prohibited", "Do not install a pendulum assembly unless it is of new manufacture or records demonstrate that its bearing has not been replaced or re-swaged since new manufacture.", [ev_prohibition], objects=["Flap track pendulum assembly"], conditions=["Permitted only if the pendulum assembly is of new manufacture OR records demonstrate the bearing has not been replaced or re-swaged since new manufacture"], compliance_rules=[cmp_from("CMP-008", "LIM-008", ev_prohibition)]),
    ]

    all_para1 = [f"REQ-{i:03d}" for i in range(1, 7)]
    exception_texts = [
        "Aircraft originally delivered after the effective date of this AD.",
        "Aircraft for which records demonstrate that no pendulum assembly bearing has been replaced or re-swaged since original delivery.",
        "Aircraft inspected before the effective date under the applicable SB, with records demonstrating no later installation of a pendulum assembly whose bearing was replaced or re-swaged since new manufacture.",
        "Aircraft inspected before the effective date under the applicable SB, with records demonstrating no later pendulum bearing replacement or re-swaging.",
    ]
    record["exceptions"] = [
        {"exception_id": f"EXC-{i:03d}", "text": text, "applies_to_requirement_ids": all_para1, "evidence_ids": [ev_exceptions]}
        for i, text in enumerate(exception_texts, 1)
    ]
    record["previous_action_credit"] = []
    record["relationships"] = []
    record["amoc_and_contacts"] = [
        {"entry_id": "AMC-001", "entry_type": "amoc_authority", "authority_or_organization": "EASA", "contact_text": "If requested and appropriately substantiated, EASA can approve Alternative Methods of Compliance for this AD.", "conditions": ["Requested and appropriately substantiated"], "evidence_ids": [ev_amoc]},
        {"entry_id": "AMC-002", "entry_type": "regulatory_contact", "authority_or_organization": "EASA", "contact_text": "Airworthiness Directives, Safety Management & Research Section, Certification Directorate, EASA. E-mail: ADs@easa.europa.eu.", "conditions": [], "evidence_ids": [ev_reg_contact]},
        {"entry_id": "AMC-003", "entry_type": "technical_contact", "authority_or_organization": "AIRBUS – Airworthiness Office – EAS", "contact_text": "Fax: +33 5 61 93 44 51, E-mail: account.airworth-eas@airbus.com.", "conditions": [], "evidence_ids": [ev_tech_contact]},
    ]
    record["classification"] = {
        "airbus_families": ["A320 family"],
        "ata_chapters": ["57"],
        "action_types": ["inspection", "replacement", "contact_manufacturer", "other", "prohibition", "install"],
        "frequency": "mixed",
        "emergency_status": "standard",
        "terminating_action_present": False,
        "table_or_appendix_present": False,
        "compliance_complexity": "conditional_branches",
        "human_confirmed": False,
        "evidence_ids": [ev_cover, ev_1a, ev_1b, ev_1c, ev_exceptions, ev_prohibition],
    }

    section_states = {
        "/ad_identity": ("present", record["ad_identity"]["evidence_ids"], "Section completion: AD identity reviewed."),
        "/publication": ("present", [ev_identity, ev_cover, ev_effective], "Section completion: publication reviewed."),
        "/applicability_groups": ("present", [ev_cover], "Section completion: applicability reviewed."),
        "/definitions": ("absent_in_source", [], "Section completion: no explicit definitions in the source."),
        "/unsafe_condition": ("present", [ev_reason], "Section completion: unsafe condition reviewed."),
        "/requirements": ("present", [ev_1a, ev_1b, ev_1c, ev_prohibition], "Section completion: requirements reviewed."),
        "/exceptions": ("present", [ev_exceptions], "Section completion: requirement exceptions reviewed."),
        "/previous_action_credit": ("absent_in_source", [], "Section completion: no separate previous-action credit; paragraph 2 is encoded as exceptions."),
        "/referenced_publications": ("present", [ev_refs], "Section completion: referenced publications reviewed."),
        "/relationships": ("not_applicable", [ev_identity, ev_correction], "Section completion: correction is explicit, but no distinct uncorrected target publication exists in the assigned pilot; no correction edge fabricated."),
        "/amoc_and_contacts": ("present", [ev_amoc, ev_reg_contact, ev_tech_contact], "Section completion: AMOC and contacts reviewed."),
        "/classification": ("present", record["classification"]["evidence_ids"], "Section completion: classification reviewed."),
    }
    return filename, finalize(
        record,
        evidence,
        quality_flags=[],
        notes=[
            "All three PDF pages were visually rendered and checked independently.",
            "The correction notice is recorded without a correction relationship because no distinct uncorrected target publication is present in the assigned pilot.",
            "The source does not specify the nature of the relevant corrective actions in paragraph 1.c; those actions use the controlled label other.",
        ],
        section_states=section_states,
    )


BUILDERS = [build_2023, build_2007, build_2009]


def main() -> None:
    for build in BUILDERS:
        filename, record = build()
        path = OUT_DIR / filename
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
