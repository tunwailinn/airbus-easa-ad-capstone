#!/usr/bin/env python3
"""Build the blind first-pass Codex A3 annotations for the assigned ten ADs.

This script reads only the named blind packets.  It deliberately does not read
reviewer packets, selection rationale, or another annotator's records.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
PACKET_DIR = ROOT / "step3_pilot" / "packets" / "blind"
OUT_DIR = ROOT / "step3_pilot" / "submitted" / "annotator_a"

PACKETS = {
    "2009-0141": "2009-0141__cb57166de0385f86.blind-packet.json",
    "2010-0164": "2010-0164__60596be378420b04.blind-packet.json",
    "2011-0112": "2011-0112__7a321140308c146d.blind-packet.json",
    "2012-0175R2": "2012-0175R2__08a8fc0e2bbbc711.blind-packet.json",
    "2013-0234R2": "2013-0234R2__9a197fbc37092cfe.blind-packet.json",
    "2014-0062": "2014-0062__58916308a3527d59.blind-packet.json",
    "2015-0135R3": "2015-0135R3__ffb267d0dfbcbbd9.blind-packet.json",
    "2016-0095": "2016-0095__7f221fbcf3eea6a5.blind-packet.json",
    "2017-0013": "2017-0013__67c94127f7b8e53d.blind-packet.json",
    "2018-0108": "2018-0108__75144c1f05797c10.blind-packet.json",
}

CREATED_AT = "2026-07-22T11:45:00Z"
SUBMITTED_AT = "2026-07-22T12:45:00Z"
MACHINE_AT = "2026-07-22T11:53:23Z"
ANNOTATOR_ID = "codex-a3"


A320_MODELS_WITH_111 = [
    "A318-111", "A318-112", "A318-121", "A318-122",
    "A319-111", "A319-112", "A319-113", "A319-114", "A319-115",
    "A319-131", "A319-132", "A319-133",
    "A320-111", "A320-211", "A320-212", "A320-214", "A320-215",
    "A320-216", "A320-231", "A320-232", "A320-233",
    "A321-111", "A321-112", "A321-131", "A321-211", "A321-212",
    "A321-213", "A321-231", "A321-232",
]
A320_MODELS = [m for m in A320_MODELS_WITH_111 if m != "A320-111"]


def norm(text: str) -> str:
    """Normalize whitespace while preserving source wording."""
    return " ".join(text.split())


def source_excerpt(builder: "Builder", page: int, start: str, end: str | None = None) -> str:
    """Return an exact native-text excerpt bounded by stable source markers."""
    text = builder.page_text(page)
    start_index = text.index(start)
    end_index = text.index(end, start_index + len(start)) if end is not None else len(text)
    return text[start_index:end_index]


def paragraph_excerpt(builder: "Builder", page: int, number: str, next_number: str | None = None) -> str:
    """Extract one numbered AD paragraph without normalizing its wording."""
    text = builder.page_text(page)
    start_match = re.search(rf"(?m)^\s*\({re.escape(number)}\)\s+", text)
    if start_match is None:
        raise ValueError(f"paragraph ({number}) not found on page {page} of {builder.ad_number}")
    if next_number is None:
        end_index = len(text)
    else:
        end_match = re.search(rf"(?m)^\s*\({re.escape(next_number)}\)\s+", text[start_match.end():])
        if end_match is None:
            raise ValueError(f"paragraph ({next_number}) not found after ({number}) on page {page} of {builder.ad_number}")
        end_index = start_match.end() + end_match.start()
    return text[start_match.start():end_index]


def unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def parse_rudder_rows(text: str) -> list[tuple[str, str, bool]]:
    """Parse appendix rows as normalized P/N, S/N, and 24-kg/m3 marker."""
    rows: list[tuple[str, str, bool]] = []
    for raw_line in text.splitlines():
        line = norm(raw_line)
        if "D554" not in line or "TS-" not in line:
            continue
        serial_match = re.search(r"TS-[0-9]+", line)
        if serial_match is None:
            continue
        pn_digits = "".join(re.findall(r"[0-9]", line[: serial_match.start()]))
        if not pn_digits.startswith("554"):
            continue
        rows.append(("D" + pn_digits, serial_match.group(0), bool(re.search(r"\sX\s*$", line))))
    return rows


class Builder:
    def __init__(self, ad_number: str):
        self.ad_number = ad_number
        self.packet_path = PACKET_DIR / PACKETS[ad_number]
        self.packet = json.loads(self.packet_path.read_text(encoding="utf-8"))
        self.pages = {p["page_number"]: p for p in self.packet["pages"]}
        self.evidence: list[dict[str, Any]] = []
        self._cmp = 0
        self._lim = 0

    @property
    def identity(self) -> dict[str, Any]:
        return self.packet["document_identity"]

    @property
    def provenance(self) -> dict[str, Any]:
        return self.packet["pdf_provenance"]

    def page_text(self, page: int) -> str:
        return self.pages[page]["text"]

    def page_quote(self, page: int) -> str:
        return norm(self.page_text(page))

    def ev(
        self,
        page: int,
        section: str,
        quote: str,
        *,
        section_raw: str | None = None,
        clause: str | None = None,
        table: dict[str, Any] | None = None,
        method: str = "native_text",
        quality: str = "normalized_whitespace",
        note: str | None = None,
    ) -> str:
        evidence_id = f"EV-{len(self.evidence) + 1:03d}"
        count = self.provenance["page_count"]
        year = int(self.ad_number[:4])
        printed = f"{page}/{count}" if year <= 2014 else f"Page {page} of {count}"
        self.evidence.append(
            {
                "evidence_id": evidence_id,
                "source_file_instance_id": self.provenance["file_instance_id"],
                "page_number": page,
                "printed_page_label": printed,
                "section": section,
                "section_raw": section_raw,
                "clause_path": clause,
                "exact_quote": norm(quote),
                "start_char": None,
                "end_char": None,
                "page_text_sha256": self.pages[page]["page_text_sha256"],
                "bbox_normalized": None,
                "extraction_method": method,
                "quality": quality,
                "table_context": table,
                "annotation_note": note,
            }
        )
        return evidence_id

    def table_ev(
        self,
        page: int,
        label: str,
        columns: list[str],
        *,
        rows: list[str] | None = None,
        footnotes: list[str] | None = None,
        note: str | None = None,
    ) -> str:
        return self.ev(
            page,
            "table",
            self.page_quote(page),
            section_raw=label,
            table={
                "table_label": label,
                "row_headers": rows or [],
                "column_headers": columns,
                "footnotes": footnotes or [],
            },
            note=note,
        )

    def limit(
        self,
        relation: str,
        quantity: float | None,
        unit: str,
        raw: str,
        evidence_ids: list[str],
        *,
        reference_event: str | None = None,
        calendar_date: str | None = None,
    ) -> dict[str, Any]:
        self._lim += 1
        return {
            "limit_id": f"LIM-{self._lim:03d}",
            "relation": relation,
            "quantity": quantity,
            "unit": unit,
            "raw_value": raw,
            "reference_event": reference_event,
            "calendar_date": calendar_date,
            "evidence_ids": evidence_ids,
        }

    def cmp(
        self,
        raw: str,
        evidence_ids: list[str],
        *,
        logic: str = "single",
        conditions: list[str] | None = None,
        initial: list[dict[str, Any]] | None = None,
        repetitive: list[dict[str, Any]] | None = None,
        grace: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        self._cmp += 1
        repetitive = repetitive or []
        return {
            "compliance_id": f"CMP-{self._cmp:03d}",
            "state": "present",
            "raw_text": raw,
            "logic": logic,
            "conditions": conditions or [],
            "initial_limits": initial or [],
            "is_repetitive": bool(repetitive),
            "repetitive_intervals": repetitive,
            "grace_periods": grace or [],
            "evidence_ids": evidence_ids,
        }

    def source_document(self, *, hybrid: bool = False) -> dict[str, Any]:
        p = self.provenance
        near_duplicate_cluster = (
            "near-2016-0095--2017-0013"
            if self.identity["ad_number"] in {"2016-0095", "2017-0013"}
            else None
        )
        return {
            "file_instance_id": p["file_instance_id"],
            "content_id": p["content_id"],
            "canonical_file_instance_id": p["file_instance_id"],
            "file_aliases": [],
            "file_name": p["file_name"],
            "relative_path": p["relative_path"],
            "file_sha256": p["file_sha256"],
            "normalized_text_sha256": p["manifest_normalized_text_sha256"],
            "page_count": p["page_count"],
            "extraction_status": "hybrid" if hybrid else "native_text",
            "needs_ocr": False,
            "manifest_review_flags": [],
            "source_url": p["official_pdf_url"],
            "text_extraction_method": "hybrid" if hybrid else "native_text",
            "exact_duplicate_group": None,
            "near_duplicate_cluster": near_duplicate_cluster,
        }

    def finish(
        self,
        *,
        cover_ev: str,
        identity_evs: list[str],
        version_label: str,
        lifecycle: str,
        holder_raw: str,
        holder_value: str,
        supersedure: dict[str, Any],
        publication: dict[str, Any],
        applicability: list[dict[str, Any]],
        definitions: list[dict[str, Any]],
        unsafe_condition: dict[str, Any],
        requirements: list[dict[str, Any]],
        exceptions: list[dict[str, Any]],
        credits: list[dict[str, Any]],
        publications: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
        contacts: list[dict[str, Any]],
        classification: dict[str, Any],
        quality_flags: list[str] | None = None,
        uncertainty_flags: list[str] | None = None,
        notes: list[str] | None = None,
        hybrid_source: bool = False,
    ) -> dict[str, Any]:
        ident = self.identity
        record: dict[str, Any] = {
            "schema_version": "1.0.0",
            "record_id": self.packet["record_id"],
            "source_document": self.source_document(hybrid=hybrid_source),
            "ad_identity": {
                "authority": "EASA",
                "document_type": "airworthiness_directive",
                "ad_number": ident["ad_number"],
                "base_ad_number": ident["base_ad_number"],
                "revision_number": ident["revision_number"],
                "publication_kind": "emergency_ad" if ident["is_emergency"] else "standard_ad",
                "is_emergency": ident["is_emergency"],
                "is_correction": ident["is_correction"],
                "correction_date": {
                    "state": "not_stated",
                    "value": None,
                    "raw_text": None,
                    "evidence_ids": [cover_ev],
                },
                "version_label": version_label,
                "logical_version_key": ident["logical_version_key"],
                "is_latest_version": None,
                "lifecycle_status": lifecycle,
                "design_approval_holder": grounded_text(holder_value, holder_raw, [cover_ev]),
                "supersedure_statement": supersedure,
                "evidence_ids": unique(identity_evs),
            },
            "publication": publication,
            "applicability_groups": applicability,
            "definitions": definitions,
            "unsafe_condition": unsafe_condition,
            "requirements": requirements,
            "exceptions": exceptions,
            "previous_action_credit": credits,
            "referenced_publications": publications,
            "relationships": relationships,
            "amoc_and_contacts": contacts,
            "classification": classification,
            "evidence_spans": self.evidence,
            "field_assertions": [],
            "annotation_metadata": {
                "guideline_version": "1.0.0",
                "record_status": "first_pass_complete",
                "creation_method": "hybrid",
                "machine_provenance": {
                    "system": "OpenAI Codex",
                    "model": "GPT-5",
                    "prompt_or_rules_version": "step2-guidelines-1.0.0-manual-pass-a3",
                    "generated_at": MACHINE_AT,
                },
                "annotators": [
                    {
                        "annotator_id": ANNOTATOR_ID,
                        "role": "annotator",
                        "started_at": CREATED_AT,
                        "submitted_at": SUBMITTED_AT,
                    }
                ],
                "events": [
                    {
                        "event_type": "created",
                        "actor_id": ANNOTATOR_ID,
                        "timestamp": CREATED_AT,
                        "rationale": "Blind first-pass annotation from the source PDF and blind packet.",
                    },
                    {
                        "event_type": "submitted",
                        "actor_id": ANNOTATOR_ID,
                        "timestamp": SUBMITTED_AT,
                        "rationale": "First pass completed; no human review or approval claimed.",
                    },
                ],
                "quality_flags": unique(quality_flags or []),
                "uncertainty_flags": unique(uncertainty_flags or []),
                "notes": notes or [
                    "All source pages were visually rendered and checked; populated assertions remain unreviewed."
                ],
                "source_text_sha256": self.provenance["manifest_normalized_text_sha256"],
                "created_at": CREATED_AT,
                "updated_at": SUBMITTED_AT,
            },
            "benchmark_metadata": {
                "split": "unassigned",
                "split_group": ident["base_ad_number"],
                "selection_strata": [],
                "duplicate_cluster_ids": [],
                "gold_record": False,
            },
        }
        record["field_assertions"] = build_assertions(record)
        return record


def grounded_text(value: str, raw: str, evs: list[str]) -> dict[str, Any]:
    return {"state": "present", "value": value, "raw_text": raw, "evidence_ids": evs}


def grounded_date(value: str, raw: str, evs: list[str]) -> dict[str, Any]:
    return {"state": "present", "value": value, "raw_text": raw, "evidence_ids": evs}


def explicit_none(raw: str, evs: list[str]) -> dict[str, Any]:
    return {"state": "explicit_none", "value": None, "raw_text": raw, "evidence_ids": evs}


def term_none(evs: list[str] | None = None, *, explicit: bool = False) -> dict[str, Any]:
    return {
        "state": "present" if explicit else "not_stated",
        "present": False,
        "scope": "none",
        "action_text": None,
        "terminates_requirement_ids": [],
        "evidence_ids": evs or [],
    }


def term_yes(text: str, targets: list[str], evs: list[str], *, scope: str = "full") -> dict[str, Any]:
    return {
        "state": "present",
        "present": True,
        "scope": scope,
        "action_text": text,
        "terminates_requirement_ids": targets,
        "evidence_ids": evs,
    }


def req(
    rid: str,
    paragraph: str,
    apps: list[str],
    actions: list[str],
    obligation: str,
    text: str,
    evs: list[str],
    *,
    objects: list[str] | None = None,
    conditions: list[str] | None = None,
    pubs: list[str] | None = None,
    cmps: list[dict[str, Any]] | None = None,
    parent: str | None = None,
    follows: list[str] | None = None,
    terminating: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "requirement_id": rid,
        "paragraph_reference": paragraph,
        "parent_requirement_id": parent,
        "applicability_group_ids": apps,
        "action_types": actions,
        "obligation": obligation,
        "action_text": text,
        "objects_or_components": objects or [],
        "conditions": conditions or [],
        "method_publication_ids": pubs or [],
        "compliance_rules": cmps or [],
        "follow_on_requirement_ids": follows or [],
        "terminating_action": terminating or term_none(),
        "evidence_ids": evs,
    }


def all_serials(restriction_id: str, raw: str, evs: list[str]) -> dict[str, Any]:
    return {
        "restriction_id": restriction_id,
        "kind": "all",
        "raw_expression": raw,
        "lower_bound": None,
        "upper_bound": None,
        "explicit_values": [],
        "condition": None,
        "evidence_ids": evs,
    }


def listed_serials(
    restriction_id: str,
    raw: str,
    values: list[str],
    evs: list[str],
    *,
    condition: str | None = None,
) -> dict[str, Any]:
    return {
        "restriction_id": restriction_id,
        "kind": "include_list" if values else "conditional",
        "raw_expression": raw,
        "lower_bound": None,
        "upper_bound": None,
        "explicit_values": values,
        "condition": condition,
        "evidence_ids": evs,
    }


def app(
    aid: str,
    label: str,
    raw: str,
    families: list[str],
    models: list[str],
    serials: list[dict[str, Any]],
    evs: list[str],
    *,
    part_numbers: list[str] | None = None,
    conditions: list[str] | None = None,
    exclusions: list[str] | None = None,
    logic: str = "all",
) -> dict[str, Any]:
    return {
        "group_id": aid,
        "label": label,
        "state": "present",
        "raw_text": raw,
        "aircraft_families": families,
        "models": models,
        "serial_restrictions": serials,
        "part_numbers": part_numbers or [],
        "configuration_conditions": conditions or [],
        "exclusions": exclusions or [],
        "boolean_logic": logic,
        "evidence_ids": evs,
    }


def pub(
    pid: str,
    publication_type: str,
    issuer: str | None,
    number: str,
    revision: str | None,
    date: str | None,
    roles: list[str],
    evs: list[str],
    *,
    title: str | None = None,
    later: bool | None = None,
) -> dict[str, Any]:
    return {
        "publication_id": pid,
        "publication_type": publication_type,
        "issuer": issuer,
        "number": number,
        "revision": revision,
        "publication_date": date,
        "title": title,
        "roles": roles,
        "later_approved_revisions_allowed": later,
        "evidence_ids": evs,
    }


def rel(
    rid: str,
    kind: str,
    target: str,
    source: str,
    raw: str,
    evs: list[str],
) -> dict[str, Any]:
    return {
        "relationship_id": rid,
        "relationship_type": kind,
        "target_ad_number": target,
        "target_record_id": None,
        "target_logical_version_key": None,
        "source": source,
        "verification_status": "candidate",
        "manually_verified": False,
        "raw_text": raw,
        "evidence_ids": evs,
    }


def contacts(amoc_ev: str, contact_ev: str, technical_text: str, organization: str = "Airbus") -> list[dict[str, Any]]:
    return [
        {
            "entry_id": "AMC-001",
            "entry_type": "amoc_authority",
            "authority_or_organization": "EASA",
            "contact_text": "If requested and appropriately substantiated, EASA can approve Alternative Methods of Compliance for this AD.",
            "conditions": ["Requested and appropriately substantiated"],
            "evidence_ids": [amoc_ev],
        },
        {
            "entry_id": "AMC-002",
            "entry_type": "regulatory_contact",
            "authority_or_organization": "EASA",
            "contact_text": "Enquiries regarding this AD should be referred to EASA at ADs@easa.europa.eu.",
            "conditions": [],
            "evidence_ids": [contact_ev],
        },
        {
            "entry_id": "AMC-003",
            "entry_type": "technical_contact",
            "authority_or_organization": organization,
            "contact_text": technical_text,
            "conditions": [],
            "evidence_ids": [contact_ev],
        },
    ]


def build_assertions(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Attach automatic, unreviewed provenance to each substantive object."""
    items: list[tuple[str, str, list[str], float, str]] = []

    def aggregate_evidence(objects: Iterable[dict[str, Any]]) -> list[str]:
        return unique(ev for obj in objects for ev in (obj.get("evidence_ids") or []))

    publication_evs = unique(
        ev
        for key in ("subject", "issue_date", "effective_date", "foreign_ad")
        for ev in ((record["publication"].get(key) or {}).get("evidence_ids") or [])
    )
    section_specs = [
        ("/ad_identity", "present", record["ad_identity"]["evidence_ids"], 0.995, "Section completion: AD identity"),
        ("/publication", "present", publication_evs, 0.99, "Section completion: publication"),
    ]
    for key in (
        "applicability_groups",
        "definitions",
        "requirements",
        "exceptions",
        "previous_action_credit",
        "referenced_publications",
        "relationships",
        "amoc_and_contacts",
    ):
        objects = record[key]
        evs = aggregate_evidence(objects)
        if key == "relationships" and not evs:
            evs = record["ad_identity"]["supersedure_statement"]["evidence_ids"]
        section_specs.append(
            (
                f"/{key}",
                "present" if objects else "absent_in_source",
                evs,
                0.95 if objects else 0.90,
                f"Section completion: {key}",
            )
        )
    items.extend(section_specs)
    items.extend(
        [
            ("/ad_identity/ad_number", "present", record["ad_identity"]["evidence_ids"], 0.995, "Cover identity"),
            ("/ad_identity/supersedure_statement", "present", record["ad_identity"]["supersedure_statement"]["evidence_ids"], 0.99, "Printed status field"),
            ("/publication/issue_date", "present", record["publication"]["issue_date"]["evidence_ids"], 0.995, "Printed issue date"),
            ("/publication/effective_date", "present", record["publication"]["effective_date"]["evidence_ids"], 0.995, "Printed effective date"),
            ("/publication/subject", "present", record["publication"]["subject"]["evidence_ids"], 0.99, "Printed ATA subject"),
        ]
    )
    for key in ("applicability_groups", "definitions", "requirements", "exceptions", "previous_action_credit", "referenced_publications", "relationships", "amoc_and_contacts"):
        for idx, obj in enumerate(record[key]):
            items.append((f"/{key}/{idx}", "present", obj.get("evidence_ids", []), 0.94 if key == "requirements" else 0.96, key))
    unsafe = record.get("unsafe_condition")
    if unsafe:
        items.append(("/unsafe_condition", "present", unsafe.get("evidence_ids", []), 0.96, "Reason and unsafe condition"))
    items.append(("/classification", "present", record["classification"].get("evidence_ids", []), 0.90, "Schema classification"))

    assertions = []
    for idx, (path, value_state, evs, confidence, note) in enumerate(items, start=1):
        assertions.append(
            {
                "assertion_id": f"AST-{idx:03d}",
                "field_path": path,
                "value_state": value_state,
                "origin": "auto_extracted",
                "verification_status": "unreviewed",
                "confidence": confidence,
                "evidence_ids": unique(evs),
                "annotator_id": ANNOTATOR_ID,
                "derivation_rule": None,
                "input_field_paths": [],
                "notes": note,
            }
        )
    return assertions


def common_publication(
    *,
    subject: str,
    subject_raw: str,
    subject_ev: str,
    issue_date: str,
    issue_raw: str,
    issue_ev: str,
    effective_date: str,
    effective_raw: str,
    effective_ev: str,
    ata: str,
    ata_title: str,
    manufacturer_raw: str,
    manufacturer_ev: str,
    type_designations: list[str],
    tcds: list[str],
    foreign_ev: str,
) -> dict[str, Any]:
    return {
        "subject": grounded_text(subject, subject_raw, [subject_ev]),
        "issue_date": grounded_date(issue_date, issue_raw, [issue_ev]),
        "effective_date": grounded_date(effective_date, effective_raw, [effective_ev]),
        "ata_chapters": [{"code": ata, "title": ata_title, "evidence_ids": [subject_ev]}],
        "manufacturers": [
            {
                "raw_name": manufacturer_raw,
                "normalized_name": "Airbus",
                "role": "manufacturer",
                "evidence_ids": [manufacturer_ev],
            }
        ],
        "type_model_designations": type_designations,
        "tcds_numbers": tcds,
        "foreign_ad": explicit_none("Foreign AD: Not applicable", [foreign_ev]),
    }


def write_record(record: dict[str, Any]) -> Path:
    source = record["source_document"]
    path = OUT_DIR / f"{record['ad_identity']['ad_number']}__{source['file_instance_id']}.annotation.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def build_2011() -> dict[str, Any]:
    b = Builder("2011-0112")
    ev_cover = b.ev(1, "cover", "AD No.: 2011-0112. Date: 15 June 2011. Type Approval Holder’s Name: AIRBUS. Type/Model designation(s): A300 aeroplanes. TCDS Number: France N° 145. Foreign AD: Not applicable. Supersedure: None.", section_raw="Cover identity", method="visual_transcription", quality="visual_transcription", note="Visually transcribed from the rendered two-column cover because native extraction interleaves labels and values.")
    ev_subject = b.ev(1, "cover", "ATA 27 Flight Controls – Trimmable Horizontal Stabilizer Actuator (THSA) Upper Attachment - Modification. Manufacturer(s): Airbus (formerly Airbus Industrie).", section_raw="ATA / Manufacturer(s)")
    ev_app = b.ev(1, "applicability", "Airbus A300 aeroplanes, all certified models, all manufacturer serial numbers.", section_raw="Applicability")
    ev_reason = b.ev(1, "reason", "A specific failure case of the THSA upper primary attachment, which may result in a loading of the upper secondary attachment, has been identified by analysis. Primary load path failure can be caused by bearing migration from the upper attachment gimbal by failure or loss of a retention bolt. In case of failure of the THSA upper primary attachment, the THSA upper secondary attachment would engage. Because the upper attachment secondary load path can only withstand the loads for a limited period of time, the condition where it would be engaged could lead, if not detected and corrected, to the failure of the secondary load path, which would likely result in loss of control of the aeroplane. For the reasons explained above, this AD requires installation of three secondary retention plates for the gimbal bearings on the THSA upper primary attachment.", section_raw="Reason")
    ev_effective = b.ev(1, "cover", "Effective Date: 29 June 2011", section_raw="Effective Date")
    ev_req = b.ev(2, "required_actions_and_compliance_times", "Required as indicated, unless accomplished previously: Within 30 months after the effective date of this AD, install three retention plates on THSA upper primary attachment in accordance with the Accomplishment Instructions of AIRBUS Service Bulletin A300-27-0204 original issue.", section_raw="Required Action(s) and Compliance Time(s)")
    ev_pub = b.ev(2, "reference_publications", "Airbus Service Bulletin A300-27-0204 at original issue. The use of later approved revisions of this document is acceptable for compliance with requirements of this AD.", section_raw="Ref. Publications")
    ev_remarks = b.ev(2, "remarks", "If requested and appropriately substantiated, EASA can approve Alternative Methods of Compliance for this AD. Enquiries regarding this AD should be referred to the Airworthiness Directives, Safety Management & Research Section, Certification Directorate, EASA. E-mail ADs@easa.europa.eu. For any question concerning the technical content of the requirements in this AD, please contact: AIRBUS SAS – EAW (Airworthiness Office, Telephone: + 33 5 61 18 41 39, Fax: + 33 5 61 93 44 51).", section_raw="Remarks 1, 3 and 4")
    cmp1 = b.cmp(
        "Within 30 months after the effective date of this AD",
        [ev_req],
        initial=[b.limit("within", 30, "calendar_month", "within 30 months", [ev_req], reference_event="effective date of this AD")],
    )
    requirements = [
        req("REQ-001", "Required Action(s) and Compliance Time(s)", ["APP-001"], ["install", "modification"], "mandatory", "Install three retention plates on the THSA upper primary attachment.", [ev_req], objects=["THSA upper primary attachment", "Three secondary retention plates"], conditions=["Unless accomplished previously"], pubs=["PUB-001"], cmps=[cmp1])
    ]
    applicability = [
        app("APP-001", "All certified A300 models and all manufacturer serial numbers", "Airbus A300 aeroplanes, all certified models, all manufacturer serial numbers.", ["A300 family"], ["A300"], [all_serials("MSN-001", "all manufacturer serial numbers", [ev_app])], [ev_app])
    ]
    publication = common_publication(
        subject="Flight Controls – Trimmable Horizontal Stabilizer Actuator (THSA) Upper Attachment – Modification",
        subject_raw="ATA 27 Flight Controls – Trimmable Horizontal Stabilizer Actuator (THSA) Upper Attachment - Modification",
        subject_ev=ev_subject,
        issue_date="2011-06-15", issue_raw="Date: 15 June 2011", issue_ev=ev_cover,
        effective_date="2011-06-29", effective_raw="Effective Date: 29 June 2011", effective_ev=ev_effective,
        ata="27", ata_title="Flight Controls", manufacturer_raw="Airbus (formerly Airbus Industrie)", manufacturer_ev=ev_subject,
        type_designations=["A300"], tcds=["France N° 145"], foreign_ev=ev_cover,
    )
    unsafe = {
        "state": "present",
        "raw_reason_text": norm("A specific failure case of the THSA upper primary attachment, which may result in a loading of the upper secondary attachment, has been identified by analysis. Primary load path failure can be caused by bearing migration from the upper attachment gimbal by failure or loss of a retention bolt. In case of failure of the THSA upper primary attachment, the THSA upper secondary attachment would engage. Because the upper attachment secondary load path can only withstand the loads for a limited period of time, the condition where it would be engaged could lead, if not detected and corrected, to the failure of the secondary load path, which would likely result in loss of control of the aeroplane."),
        "observed_events_or_defects": ["Potential failure of the THSA upper primary attachment"],
        "causes": ["Bearing migration from the upper attachment gimbal following failure or loss of a retention bolt"],
        "unsafe_conditions": ["Engagement and possible failure of the limited-duration upper secondary load path"],
        "potential_consequences": ["Loss of control of the aeroplane"],
        "affected_components": ["THSA upper primary attachment", "THSA upper secondary attachment", "Gimbal bearings"],
        "intended_risk_mitigation": ["Install three secondary retention plates for the gimbal bearings"],
        "evidence_ids": [ev_reason],
    }
    return b.finish(
        cover_ev=ev_cover, identity_evs=[ev_cover], version_label="Original", lifecycle="unknown",
        holder_raw="Type Approval Holder’s Name: AIRBUS", holder_value="Airbus",
        supersedure=explicit_none("Supersedure: None", [ev_cover]), publication=publication,
        applicability=applicability, definitions=[], unsafe_condition=unsafe, requirements=requirements,
        exceptions=[], credits=[], publications=[pub("PUB-001", "service_bulletin", "Airbus", "A300-27-0204", "Original issue", None, ["required_method"], [ev_req, ev_pub], later=True)], relationships=[],
        contacts=contacts(ev_remarks, ev_remarks, "For technical questions, contact AIRBUS SAS – EAW (Airworthiness Office), telephone +33 5 61 18 41 39, fax +33 5 61 93 44 51."),
        classification={"airbus_families": ["A300 family"], "ata_chapters": ["27"], "action_types": ["install", "modification"], "frequency": "one_time", "emergency_status": "standard", "terminating_action_present": False, "table_or_appendix_present": False, "compliance_complexity": "simple", "human_confirmed": False, "evidence_ids": [ev_subject, ev_app, ev_req]}, quality_flags=["visual_transcription_used"], hybrid_source=True,
    )


def build_2014() -> dict[str, Any]:
    b = Builder("2014-0062")
    ev_cover = b.ev(1, "cover", "AD No.: 2014-0062. Date: 11 March 2014. Design Approval Holder’s Name: AIRBUS. Type/Model designation(s): A330 aeroplanes. TCDS Number: EASA.A.004. Foreign AD: Not applicable. Supersedure: None.", section_raw="Cover identity", method="visual_transcription", quality="visual_transcription", note="Visually transcribed from the rendered two-column cover because native extraction interleaves labels and values.")
    ev_subject = b.ev(1, "cover", "ATA 78 Exhaust – Thrust Reverser Cowl Door Hinge Sleeves – Identification / Replacement. Manufacturer(s): Airbus (formerly Airbus Industrie).", section_raw="ATA / Manufacturer(s)")
    ev_app = b.ev(1, "applicability", "Airbus A330-243, A330-243F, A330-341, A330-342, and A330-343 aeroplanes, all manufacturer serial numbers.", section_raw="Applicability")
    ev_reason = b.ev(1, "reason", "A manufacturing discrepancy (lack of heat treatment) on a batch of the N°3 and N°4 hinge sleeves installed on Thrust Reverser Unit (TRU) was identified. Those parts are only installed on A330 aeroplanes equipped with Rolls-Royce (RR) Trent 700 engines. This condition, if not corrected, in case of a Fan Blade Off event due to high vibration level, could cause in-flight loss of some heavy components of the TRU, possibly resulting in injury to persons on the ground. As current hinge sleeves are not serialized, it is not possible to identify the TRU hinge sleeves which did not receive the heat treatment. For the reason described above, this AD requires identification and replacement of the affected TRU hinge sleeves.", section_raw="Reason")
    ev_effective = b.ev(1, "cover", "Effective Date: 25 March 2014", section_raw="Effective Date")
    ev_r1 = b.ev(2, "required_actions_and_compliance_times", "(1) Within 12 months after the effective date of this AD, identify and, if found to be affected, replace the hinge sleeves N°3 and N°4 of the TRU cowl door in accordance with the instructions of Airbus Service Bulletin (SB) A330-78-3021 Revision 01.", section_raw="Required Action(s) and Compliance Time(s)", clause="(1)")
    ev_credit = b.ev(2, "credit", "(2) Aeroplanes on which Airbus Modification 202463 has been embodied in production or aeroplanes modified in accordance with the instructions of Airbus SB A330-78-3021 at original issue, are compliant with the requirement of paragraph (1) of this AD.", section_raw="Required Action(s) and Compliance Time(s)", clause="(2)")
    ev_r3 = b.ev(2, "required_actions_and_compliance_times", "(3) From the effective date of this AD, installation of a TRU is allowed, provided that, prior to installation, it is determined, in accordance with the instructions of Airbus SB A330-78-3021, that the cowl door hinge sleeves installed on the TRU are not affected by the requirements of this AD.", section_raw="Required Action(s) and Compliance Time(s)", clause="(3)")
    ev_pub = b.ev(2, "reference_publications", "Airbus SB A330-78-3021 at original issue dated 17 October 2012, or Revision 01 dated 30 July 2013. The use of later approved revisions of this document is acceptable for compliance with the requirements of this AD.", section_raw="Ref. Publications")
    ev_remarks = b.ev(2, "remarks", "If requested and appropriately substantiated, EASA can approve Alternative Methods of Compliance for this AD. Enquiries regarding this AD should be referred to the Safety Information Section, Executive Directorate, EASA. E-mail: ADs@easa.europa.eu. For any question concerning the technical content of the requirements in this AD, please contact: AIRBUS – Airworthiness Office – EIAL; E-mail: airworthiness.A330-A340@airbus.com.", section_raw="Remarks 1, 3 and 4")
    initial_12 = b.limit("within", 12, "calendar_month", "Within 12 months", [ev_r1], reference_event="effective date of this AD")
    cmp_identify = b.cmp("Within 12 months after the effective date of this AD", [ev_r1], initial=[copy.deepcopy(initial_12)])
    # Limit IDs must be unique, so create the replacement limit separately.
    cmp_replace = b.cmp("Within 12 months after the effective date of this AD, if found to be affected", [ev_r1], logic="conditional", conditions=["Hinge sleeves are found to be affected"], initial=[b.limit("within", 12, "calendar_month", "Within 12 months", [ev_r1], reference_event="effective date of this AD")])
    cmp_install = b.cmp("From the effective date of this AD, installation is allowed only after determining that the installed cowl door hinge sleeves are not affected", [ev_r3], logic="conditional", conditions=["Before installing a TRU", "Hinge sleeves determined not affected"], initial=[b.limit("from", None, "calendar_date", "From the effective date of this AD", [ev_r3], reference_event="effective date of this AD", calendar_date="2014-03-25")])
    requirements = [
        req("REQ-001", "(1)", ["APP-001"], ["test_or_check"], "mandatory", "Identify the N°3 and N°4 hinge sleeves of the TRU cowl door.", [ev_r1], objects=["TRU cowl door hinge sleeves N°3 and N°4"], conditions=["Unless accomplished previously"], pubs=["PUB-002"], cmps=[cmp_identify], follows=["REQ-002"]),
        req("REQ-002", "(1)", ["APP-001"], ["replacement"], "conditional", "Replace the N°3 and N°4 TRU cowl door hinge sleeves if they are found to be affected.", [ev_r1], objects=["Affected TRU cowl door hinge sleeves N°3 and N°4"], conditions=["Hinge sleeves found affected"], pubs=["PUB-002"], cmps=[cmp_replace], parent="REQ-001"),
        req("REQ-003", "(3)", ["APP-001"], ["install", "test_or_check", "prohibition"], "conditional", "Install a TRU only after determining that its cowl door hinge sleeves are not affected by this AD.", [ev_r3], objects=["Thrust Reverser Unit", "TRU cowl door hinge sleeves"], conditions=["Prior to installation", "Hinge sleeves determined not affected"], pubs=["PUB-001", "PUB-002"], cmps=[cmp_install]),
    ]
    apps = [app("APP-001", "Affected Rolls-Royce Trent 700 powered A330 models", "Airbus A330-243, A330-243F, A330-341, A330-342, and A330-343 aeroplanes, all manufacturer serial numbers.", ["A330 family"], ["A330-243", "A330-243F", "A330-341", "A330-342", "A330-343"], [all_serials("MSN-001", "all manufacturer serial numbers", [ev_app])], [ev_app], conditions=["Equipped with Rolls-Royce Trent 700 engines"]) ]
    publication = common_publication(subject="Exhaust – Thrust Reverser Cowl Door Hinge Sleeves – Identification / Replacement", subject_raw="ATA 78 Exhaust – Thrust Reverser Cowl Door Hinge Sleeves – Identification / Replacement", subject_ev=ev_subject, issue_date="2014-03-11", issue_raw="Date: 11 March 2014", issue_ev=ev_cover, effective_date="2014-03-25", effective_raw="Effective Date: 25 March 2014", effective_ev=ev_effective, ata="78", ata_title="Exhaust", manufacturer_raw="Airbus (formerly Airbus Industrie)", manufacturer_ev=ev_subject, type_designations=["A330"], tcds=["EASA.A.004"], foreign_ev=ev_cover)
    unsafe = {"state": "present", "raw_reason_text": norm("A manufacturing discrepancy (lack of heat treatment) on a batch of the N°3 and N°4 hinge sleeves installed on Thrust Reverser Unit (TRU) was identified. This condition, if not corrected, in case of a Fan Blade Off event due to high vibration level, could cause in-flight loss of some heavy components of the TRU, possibly resulting in injury to persons on the ground."), "observed_events_or_defects": ["Lack of heat treatment on a batch of N°3 and N°4 TRU hinge sleeves"], "causes": ["Manufacturing discrepancy"], "unsafe_conditions": ["Affected hinge sleeves may not withstand a high-vibration fan-blade-off event"], "potential_consequences": ["In-flight loss of heavy TRU components", "Injury to persons on the ground"], "affected_components": ["TRU cowl door hinge sleeves N°3 and N°4"], "intended_risk_mitigation": ["Identify and replace affected hinge sleeves"], "evidence_ids": [ev_reason]}
    credits = [{"credit_id": "CRD-001", "text": "Aeroplanes with Airbus Modification 202463 embodied in production or modified under Airbus SB A330-78-3021 original issue comply with paragraph (1).", "applies_to_requirement_ids": ["REQ-001", "REQ-002"], "credited_publication_ids": ["PUB-001"], "conditions": ["Modification 202463 embodied in production, or SB original issue accomplished"], "evidence_ids": [ev_credit]}]
    pubs = [pub("PUB-001", "service_bulletin", "Airbus", "A330-78-3021", "Original issue", "2012-10-17", ["previous_action_credit", "required_method"], [ev_credit, ev_pub], later=True), pub("PUB-002", "service_bulletin", "Airbus", "A330-78-3021", "Revision 01", "2013-07-30", ["required_method"], [ev_r1, ev_pub], later=True)]
    return b.finish(cover_ev=ev_cover, identity_evs=[ev_cover], version_label="Original", lifecycle="unknown", holder_raw="Design Approval Holder’s Name: AIRBUS", holder_value="Airbus", supersedure=explicit_none("Supersedure: None", [ev_cover]), publication=publication, applicability=apps, definitions=[], unsafe_condition=unsafe, requirements=requirements, exceptions=[], credits=credits, publications=pubs, relationships=[], contacts=contacts(ev_remarks, ev_remarks, "For technical questions, contact AIRBUS – Airworthiness Office – EIAL at airworthiness.A330-A340@airbus.com."), classification={"airbus_families": ["A330 family"], "ata_chapters": ["78"], "action_types": ["test_or_check", "replacement", "install", "prohibition"], "frequency": "mixed", "emergency_status": "standard", "terminating_action_present": False, "table_or_appendix_present": False, "compliance_complexity": "conditional_branches", "human_confirmed": False, "evidence_ids": [ev_subject, ev_app, ev_r1, ev_r3]}, quality_flags=["complex_compliance", "visual_transcription_used"], hybrid_source=True)


def build_2018() -> dict[str, Any]:
    b = Builder("2018-0108")
    ev_cover = b.ev(1, "cover", "AD No.: 2018-0108. Issued: 15 May 2018. Design Approval Holder’s Name: AIRBUS. Type/Model designation(s): A350 aeroplanes. Effective Date: 29 May 2018. TCDS Number(s): EASA.A.151. Foreign AD: Not applicable. Supersedure: None.", section_raw="Cover identity", method="visual_transcription", quality="visual_transcription", note="Visually transcribed from the rendered two-column cover because native extraction interleaves labels and values.")
    ev_subject = b.ev(1, "cover", "ATA 52 – Door – Passenger Doors Frameside Fittings – Modification. Manufacturer(s): Airbus.", section_raw="ATA / Manufacturer(s)")
    ev_app = b.ev(1, "applicability", "Airbus A350-941 aeroplanes, manufacturer serial numbers as listed in Airbus Service Bulletin (SB) A350-52-P012.", section_raw="Applicability")
    ev_defs = b.ev(1, "definitions", "Aeroplane date of manufacture: The date of transfer of title (ownership) at the time of first delivery to an operator, which is referenced in Airbus documentation. The SB: Airbus Service Bulletin (SB) A350-52-P012.", section_raw="Definitions")
    ev_reason1 = b.ev(1, "reason", "Due to the misinterpretation of the prevailing requirements for multimaterial (hybrid) joints of the passenger door frame fittings, the interfay sealant, which prevents water ingress, was only applied on the surface in direct contact with the aluminium parts and not between all surfaces of the joint parts.", section_raw="Reason")
    ev_reason2 = b.ev(2, "reason", "This condition, if not corrected, could lead to failure of the door to perform its intended function, possibly resulting in reduced evacuation capacity from the aeroplane during an emergency and consequent injury to occupants. To address this unsafe condition, Airbus developed production mod 110790 and mod 109554 to improve protection against corrosion, and issued the SB to provide modification instructions for in-service pre-mod aeroplanes. For the reasons described above, this AD requires a modification by adding sealant and protective treatment on the affected passenger doors.", section_raw="Reason continued")
    ev_req = b.ev(2, "required_actions_and_compliance_times", "Modification: Before exceeding 48 months since the aeroplane date of manufacture, apply additional corrosion protection to the hybrid joints of the doors 1, 2, 3 and 4, left-hand and right-hand sides, in accordance with the instructions of the SB.", section_raw="Required Action(s) and Compliance Time(s)")
    ev_pub = b.ev(2, "reference_publications", "Airbus SB A350-52-P012 original issue, dated 07 September 2017. The use of later approved revisions of the above-mentioned document is acceptable for compliance with the requirements of this AD.", section_raw="Ref. Publications")
    ev_remarks = b.ev(2, "remarks", "If requested and appropriately substantiated, EASA can approve Alternative Methods of Compliance for this AD. Enquiries regarding this AD should be referred to the EASA Safety Information Section, Certification Directorate. E-mail: ADs@easa.europa.eu. For any question concerning the technical content of the requirements in this AD, please contact: Airbus XWB, E-mail: continued-airworthiness.a350@airbus.com.", section_raw="Remarks 1, 3 and 4")
    apps = [app("APP-001", "A350-941 aeroplanes with MSN listed in SB A350-52-P012", "Airbus A350-941 aeroplanes, manufacturer serial numbers as listed in Airbus Service Bulletin (SB) A350-52-P012.", ["A350 family"], ["A350-941"], [listed_serials("MSN-001", "manufacturer serial numbers as listed in Airbus SB A350-52-P012", [], [ev_app], condition="MSN listed in Airbus SB A350-52-P012")], [ev_app])]
    cmp1 = b.cmp("Before exceeding 48 months since the aeroplane date of manufacture", [ev_req], initial=[b.limit("before", 48, "calendar_month", "Before exceeding 48 months", [ev_req], reference_event="aeroplane date of manufacture")])
    requirements = [req("REQ-001", "Modification", ["APP-001"], ["modification", "install"], "mandatory", "Apply additional corrosion protection to the hybrid joints of passenger doors 1, 2, 3 and 4 on the left-hand and right-hand sides.", [ev_req], objects=["Passenger doors 1, 2, 3 and 4, left-hand and right-hand", "Hybrid door-frame-fitting joints"], conditions=["Unless accomplished previously"], pubs=["PUB-001"], cmps=[cmp1])]
    publication = common_publication(subject="Door – Passenger Doors Frameside Fittings – Modification", subject_raw="ATA 52 – Door – Passenger Doors Frameside Fittings – Modification", subject_ev=ev_subject, issue_date="2018-05-15", issue_raw="Issued: 15 May 2018", issue_ev=ev_cover, effective_date="2018-05-29", effective_raw="Effective Date: 29 May 2018", effective_ev=ev_cover, ata="52", ata_title="Doors", manufacturer_raw="Airbus", manufacturer_ev=ev_subject, type_designations=["A350"], tcds=["EASA.A.151"], foreign_ev=ev_cover)
    unsafe = {"state": "present", "raw_reason_text": norm("Due to the misinterpretation of the prevailing requirements for multimaterial (hybrid) joints of the passenger door frame fittings, the interfay sealant, which prevents water ingress, was only applied on the surface in direct contact with the aluminium parts and not between all surfaces of the joint parts. This condition, if not corrected, could lead to failure of the door to perform its intended function, possibly resulting in reduced evacuation capacity from the aeroplane during an emergency and consequent injury to occupants."), "observed_events_or_defects": ["Interfay sealant omitted between some surfaces of hybrid passenger-door frame-fitting joints"], "causes": ["Misinterpretation of sealing requirements for multimaterial joints"], "unsafe_conditions": ["Water ingress and potential galvanic corrosion at aluminium holes", "Passenger door may fail to perform its intended function"], "potential_consequences": ["Reduced emergency evacuation capacity", "Injury to occupants"], "affected_components": ["Passenger door frame fittings", "Hybrid joints of doors 1 through 4"], "intended_risk_mitigation": ["Add sealant and protective treatment to affected passenger doors"], "evidence_ids": [ev_reason1, ev_reason2]}
    definitions = [{"definition_id": "DEF-001", "term": "Aeroplane date of manufacture", "definition_text": "The date of transfer of title (ownership) at the time of first delivery to an operator, which is referenced in Airbus documentation.", "evidence_ids": [ev_defs]}, {"definition_id": "DEF-002", "term": "The SB", "definition_text": "Airbus Service Bulletin (SB) A350-52-P012.", "evidence_ids": [ev_defs]}]
    return b.finish(cover_ev=ev_cover, identity_evs=[ev_cover], version_label="Original", lifecycle="unknown", holder_raw="Design Approval Holder’s Name: AIRBUS", holder_value="Airbus", supersedure=explicit_none("Supersedure: None", [ev_cover]), publication=publication, applicability=apps, definitions=definitions, unsafe_condition=unsafe, requirements=requirements, exceptions=[], credits=[], publications=[pub("PUB-001", "service_bulletin", "Airbus", "A350-52-P012", "Original issue", "2017-09-07", ["required_method"], [ev_defs, ev_req, ev_pub], later=True)], relationships=[], contacts=contacts(ev_remarks, ev_remarks, "For technical questions, contact Airbus XWB at continued-airworthiness.a350@airbus.com.", organization="Airbus XWB"), classification={"airbus_families": ["A350 family"], "ata_chapters": ["52"], "action_types": ["modification", "install"], "frequency": "one_time", "emergency_status": "standard", "terminating_action_present": False, "table_or_appendix_present": False, "compliance_complexity": "simple", "human_confirmed": False, "evidence_ids": [ev_subject, ev_app, ev_req]}, quality_flags=["visual_transcription_used"], hybrid_source=True)


def build_2012() -> dict[str, Any]:
    b = Builder("2012-0175R2")
    ev_cover = b.ev(1, "cover", "AD No.: 2012-0175R2. Issued: 02 February 2016. Design Approval Holder’s Name: AIRBUS. Type/Model designation(s): A318, A319, A320 and A321 aeroplanes. Effective Date: Revision 2: 04 February 2016; Revision 1: 21 January 2014; Original issue: 21 September 2012. TCDS Number(s): EASA.A.064. Foreign AD: Not applicable. Revision: This AD revises EASA AD 2012-0175R1 dated 07 January 2014.", section_raw="Cover identity", method="visual_transcription", quality="visual_transcription", note="Visually transcribed from the rendered two-column cover because native extraction interleaves some labels and values.")
    ev_subject = b.ev(1, "cover", "ATA 27 – Flight Controls – Trimmable Horizontal Stabilizer Actuator Ballscrew Lower Splines – Inspection / Replacement. Manufacturer(s): Airbus (formerly Airbus Industrie).", section_raw="ATA / Manufacturer(s)")
    app_raw = "Airbus A318-111, A318-112, A318-121, A318-122, A319-111, A319-112, A319-113, A319-114, A319-115, A319-131, A319-132, A319-133, A320-211, A320-212, A320-214, A320-215, A320-216, A320-231, A320-232, A320-233, A321-111, A321-112, A321-131, A321-211, A321-212, A321-213, A321-231 and A321-232 aeroplanes, all manufacturer serial numbers."
    ev_app = b.ev(1, "applicability", app_raw, section_raw="Applicability")
    ev_reason1 = b.ev(1, "reason", "Some Trimmable Horizontal Stabilizer Actuators (THSA), Part Number (P/N) 47147-500 fitted on A330/A340 aeroplanes were found with corrosion, affecting the ballscrew lower splines between the tie bar and the screw-jack. The affected ballscrew is made of steel and anti-corrosion protection is ensured, except on both extremities (upper and lower splines) where Molykote is applied. The results of the technical investigations identified that the corrosion was caused by a combination of contact/friction between the tie bar and the inner surface of the ballscrew leading to the removal", section_raw="Reason", method="visual_transcription", quality="visual_transcription", note="Visually transcribed through the diagonal SUPERSEDED stamp, which interrupts the native token THSA; the clause stops at the page boundary and continues on page 2.")
    ev_reason2 = b.ev(2, "reason", "of Molykote (corrosion protection) at the level of the tie bar splines, humidity ingress initiating surface oxidation starting from areas where Molykote is removed, and water retention in THSA lower part leading to corrosion spread out and to the creation of a brown deposit (iron oxide). The results of the technical investigations also concluded that the ballscrews of THSA P/N 47145-XXX (where XXX stands for a specific numerical value), installed on A320 family aeroplanes, might be affected by this corrosion issue. This condition, if not detected and corrected, may lead, in case of ballscrew rupture, to loss of transmission of THSA torque loads from the ballscrew to the tie-bar, prompting THSA blowback, possibly resulting in loss of control of the aeroplane.", section_raw="Reason continued", note="Exact continuation from the top of page 2; whitespace normalized.")
    ev_req1 = b.ev(2, "required_actions_and_compliance_times", "(1) Initially, within the compliance time indicated in Table 1 of this AD, and thereafter at intervals not to exceed 24 months, accomplish a detailed inspection of the ballscrew of each THSA having a P/N listed in Appendix 1 of this AD, in accordance with the instructions of Airbus Service Bulletin (SB) A320-27-1214. Table 1 – Initial THSA inspection. Compliance Time (whichever occurs later, A or B): A Before accumulating 22 years (see Note 1 of this AD); B Within 3 months after 21 September 2012 [the effective date of the original issue of this AD].", section_raw="Required Action(s) and Compliance Time(s)", clause="(1) and Table 1")
    ev_def = b.ev(2, "definitions", "For the purpose of this AD, the definition of THSA first flight is the THSA ‘entry into service date’ as listed in Goodrich SB 47145-27-16. If the THSA P/N is not listed in Goodrich SB 47145-27-16, the THSA first flight is the manufacturing date engraved on the THSA identification plate.", section_raw="Note 1")
    ev_req2 = b.ev(3, "required_actions_and_compliance_times", "(2) If, during any inspection as required by paragraph (1) of this AD, corrosion is found, within the applicable compliance time as defined in Paragraph 1.E.(2) of Airbus SB A320-27-1214, accomplish the applicable corrective actions (additional inspections of the affected THSA ballscrew, followed by replacement of the affected THSA) in accordance with the instructions of Airbus SB A320-27-1214. Within 90 days after an inspection where corrosion is found, report the results to Airbus.", section_raw="Required Action(s) and Compliance Time(s)", clause="(2)")
    ev_nonterm = b.ev(3, "required_actions_and_compliance_times", "(3) Replacement of a THSA as required by paragraph (2) of this AD does not constitute terminating action for the repetitive inspections as required by paragraph (1) of this AD, except as specified in paragraph (5) of this AD.", section_raw="Required Action(s) and Compliance Time(s)", clause="(3)")
    ev_req4 = b.ev(3, "required_actions_and_compliance_times", "(4) From 21 September 2012 [the effective date of the original issue of this AD], do not install on any aeroplane a THSA having a P/N listed in Appendix 1 of this AD, unless the part has not yet accumulated 22 years since its first flight, or unless it has been determined that the THSA is classified as Type 1 (no corrosion) at the time of installation, in accordance with criteria defined in Airbus SB A320-27-1214, and on the condition that, following installation, the THSA is inspected and, depending on findings, corrected as required by this AD.", section_raw="Required Action(s) and Compliance Time(s)", clause="(4)")
    ev_req5 = b.ev(3, "required_actions_and_compliance_times", "(5) Installation on an aeroplane of a THSA having a P/N not listed in Appendix 1 of this AD constitutes terminating action for the repetitive inspections as required by paragraph (1) of this AD for that aeroplane, provided the installation is accomplished in accordance with approved aircraft modification instructions. Using the instructions of Airbus SB A320-27-1222 to replace an affected THSA is an acceptable method to modify an aeroplane.", section_raw="Required Action(s) and Compliance Time(s)", clause="(5)")
    ev_exc = b.ev(3, "required_actions_and_compliance_times", "(6) An aeroplane on which Airbus modification 154170 (installation of THSA P/N 47145-168 with improved ballscrew design) and/or modification 156952 (installation of THSA P/N 47145-268 fitted with improved ballscrew design and Electrical Load Sensing Device -ELSD) has been embodied in production is not affected by the requirements of paragraphs (1) of this AD, provided that it is determined that no THSA with a P/N as listed in Appendix 1 of this AD is installed on that aeroplane.", section_raw="Required Action(s) and Compliance Time(s)", clause="(6)")
    ev_pubs = b.ev(3, "reference_publications", "Airbus SB A320-27-1214 original issue dated 23 February 2012. Airbus SB A320-27-1222 original issue dated 17 July 2015. Goodrich SB 47145-27-16 original issue dated 07 November 2011. UTAS SB 47145-27-18 original issue dated 31 March 2015. UTAS SB 47145-27-20 original issue dated 16 July 2015. The use of later approved revisions of these documents is acceptable for compliance with the requirements of this AD.", section_raw="Ref. Publications")
    ev_remarks = b.ev(4, "remarks", "If requested and appropriately substantiated, EASA can approve Alternative Methods of Compliance for this AD. Enquiries regarding this AD should be referred to the EASA Safety Information Section, Certification Directorate. E-mail: ADs@easa.europa.eu. For any question concerning the technical content of the requirements in this AD, please contact: AIRBUS – Airworthiness Office – EIAS, Fax +33 5 61 93 44 51, E-mail: account.airworth-eas@airbus.com.", section_raw="Remarks 1, 3 and 4")
    ev_status = b.ev(4, "other", "SUPERSEDED", section_raw="Document status stamp", quality="exact", note="Visible diagonal status stamp checked on the rendered PDF; the native extraction also contains this text.")
    ev_tab5 = b.table_ev(5, "Appendix 1 – Affected P/N 47145-XXX THSA", ["P/N – no ELSD", "P/N with ELSD (post-UTAS SB 47145-27-20)"], note="Full native-text transcription retained for row-level review.")
    ev_tab6 = b.table_ev(6, "Appendix 1 – Affected P/N 47145-XXX THSA (continued)", ["P/N – no ELSD", "P/N with ELSD (post-UTAS SB 47145-27-20)"], note="Full native-text transcription retained for row-level review.")
    parts = sorted(set(re.findall(r"\b47145-[0-9]{3}\b", b.page_text(5) + "\n" + b.page_text(6))))
    apps = [app("APP-001", "A320-family aeroplanes with an affected Appendix 1 THSA P/N", app_raw + " Affected THSA are those having a P/N listed in Appendix 1.", ["A320 family"], A320_MODELS, [all_serials("MSN-001", "all manufacturer serial numbers", [ev_app])], [ev_app, ev_tab5, ev_tab6], part_numbers=parts, conditions=["A THSA with a P/N listed in Appendix 1 is installed"])]
    cmp1 = b.cmp("Initially, whichever occurs later: before accumulating 22 years since THSA first flight, or within 3 months after 21 September 2012; thereafter at intervals not to exceed 24 months.", [ev_req1, ev_def], logic="whichever_occurs_later", initial=[b.limit("before", 22, "calendar_year", "Before accumulating 22 years", [ev_req1, ev_def], reference_event="THSA first flight"), b.limit("within", 3, "calendar_month", "Within 3 months after 21 September 2012", [ev_req1], reference_event="21 September 2012")], repetitive=[b.limit("not_to_exceed", 24, "calendar_month", "intervals not to exceed 24 months", [ev_req1], reference_event="last detailed inspection")])
    cmp2 = b.cmp("If corrosion is found, within the applicable compliance time defined in Paragraph 1.E.(2) of Airbus SB A320-27-1214", [ev_req2], logic="conditional", conditions=["Corrosion found during a paragraph (1) inspection"], initial=[])
    cmp3 = b.cmp("Within 90 days after an inspection where corrosion is found", [ev_req2], logic="conditional", conditions=["An inspection found corrosion"], initial=[b.limit("within", 90, "calendar_day", "Within 90 days", [ev_req2], reference_event="inspection where corrosion is found")])
    cmp4 = b.cmp("From 21 September 2012, do not install an Appendix 1 THSA unless an allowed condition is met", [ev_req4], logic="conditional", conditions=["The THSA has not accumulated 22 years since first flight, or is Type 1 at installation and will be inspected and corrected after installation"], initial=[b.limit("from", None, "calendar_date", "From 21 September 2012", [ev_req4], calendar_date="2012-09-21", reference_event="effective date of the original issue")])
    cmp5 = b.cmp("At installation of a THSA having a P/N not listed in Appendix 1, provided approved modification instructions are used", [ev_req5], logic="conditional", conditions=["P/N is not listed in Appendix 1", "Approved aircraft modification instructions are used"], initial=[])
    requirements = [
        req("REQ-001", "(1)", ["APP-001"], ["inspection"], "mandatory", "Accomplish a detailed inspection of the ballscrew of each affected THSA.", [ev_req1, ev_tab5, ev_tab6], objects=["THSA ballscrew lower splines"], conditions=["THSA P/N is listed in Appendix 1", "Unless accomplished previously"], pubs=["PUB-001"], cmps=[cmp1], follows=["REQ-002"]),
        req("REQ-002", "(2)", ["APP-001"], ["inspection", "replacement"], "conditional", "If corrosion is found, perform the applicable additional inspections and replace the affected THSA as instructed.", [ev_req2, ev_nonterm], objects=["Affected THSA ballscrew", "Affected THSA"], conditions=["Corrosion found during a paragraph (1) inspection"], pubs=["PUB-001"], cmps=[cmp2], parent="REQ-001", follows=["REQ-003"], terminating=term_none([ev_nonterm], explicit=True)),
        req("REQ-003", "(2)", ["APP-001"], ["reporting"], "conditional", "Report to Airbus the results of an inspection where corrosion is found.", [ev_req2], objects=["Inspection results"], conditions=["Corrosion found"], pubs=[], cmps=[cmp3], parent="REQ-002"),
        req("REQ-004", "(4)", ["APP-001"], ["prohibition", "install", "inspection"], "prohibited", "Do not install an Appendix 1 THSA unless it is younger than 22 years since first flight or is Type 1 at installation and is subsequently inspected and corrected as required.", [ev_req4], objects=["THSA with a P/N listed in Appendix 1"], conditions=["Allowed only under the paragraph (4) age or Type 1 conditions"], pubs=["PUB-001"], cmps=[cmp4]),
        req("REQ-005", "(5)", ["APP-001"], ["install", "replacement", "modification"], "optional_terminating", "Install a THSA having a P/N not listed in Appendix 1 using approved aircraft modification instructions.", [ev_req5], objects=["THSA having a P/N not listed in Appendix 1"], conditions=["Installation uses approved aircraft modification instructions"], pubs=["PUB-002"], cmps=[cmp5], terminating=term_yes("Installation of a THSA P/N not listed in Appendix 1 terminates paragraph (1) repetitive inspections for that aeroplane.", ["REQ-001"], [ev_req5])),
    ]
    publication = common_publication(subject="Flight Controls – Trimmable Horizontal Stabilizer Actuator Ballscrew Lower Splines – Inspection / Replacement", subject_raw="ATA 27 – Flight Controls – Trimmable Horizontal Stabilizer Actuator Ballscrew Lower Splines – Inspection / Replacement", subject_ev=ev_subject, issue_date="2016-02-02", issue_raw="Issued: 02 February 2016", issue_ev=ev_cover, effective_date="2016-02-04", effective_raw="Revision 2: 04 February 2016", effective_ev=ev_cover, ata="27", ata_title="Flight Controls", manufacturer_raw="Airbus (formerly Airbus Industrie)", manufacturer_ev=ev_subject, type_designations=["A318", "A319", "A320", "A321"], tcds=["EASA.A.064"], foreign_ev=ev_cover)
    unsafe = {"state": "present", "raw_reason_text": norm("Corrosion was found affecting THSA ballscrew lower splines. Technical investigation identified contact/friction removing Molykote, humidity ingress initiating oxidation, and water retention spreading corrosion. If not detected and corrected, ballscrew rupture may cause loss of transmission of THSA torque loads to the tie-bar, THSA blowback, and possible loss of control of the aeroplane."), "observed_events_or_defects": ["Corrosion affecting THSA ballscrew lower splines"], "causes": ["Contact and friction remove Molykote corrosion protection", "Humidity ingress and water retention initiate and spread oxidation"], "unsafe_conditions": ["Possible THSA ballscrew rupture and loss of torque-load transmission to the tie-bar", "THSA blowback"], "potential_consequences": ["Loss of control of the aeroplane"], "affected_components": ["THSA ballscrew lower splines", "Tie bar", "Screw-jack"], "intended_risk_mitigation": ["Repetitive detailed inspection", "Corrective inspection and affected-THSA replacement", "Optional installation of an unaffected THSA"], "evidence_ids": [ev_reason1, ev_reason2]}
    exceptions = [{"exception_id": "EXC-001", "text": "Aeroplanes with production modification 154170 and/or 156952 are not affected by paragraph (1), provided no Appendix 1 THSA P/N is installed.", "applies_to_requirement_ids": ["REQ-001"], "evidence_ids": [ev_exc]}]
    pubs = [pub("PUB-001", "service_bulletin", "Airbus", "A320-27-1214", "Original issue", "2012-02-23", ["required_method"], [ev_req1, ev_req2, ev_req4, ev_pubs], later=True), pub("PUB-002", "service_bulletin", "Airbus", "A320-27-1222", "Original issue", "2015-07-17", ["optional_method"], [ev_req5, ev_pubs], later=True), pub("PUB-003", "service_bulletin", "Goodrich", "47145-27-16", "Original issue", "2011-11-07", ["referenced_information"], [ev_def, ev_pubs], later=True), pub("PUB-004", "service_bulletin", "UTAS", "47145-27-18", "Original issue", "2015-03-31", ["referenced_information"], [ev_pubs], later=True), pub("PUB-005", "service_bulletin", "UTAS", "47145-27-20", "Original issue", "2015-07-16", ["referenced_information"], [ev_tab5, ev_tab6, ev_pubs], later=True)]
    return b.finish(cover_ev=ev_cover, identity_evs=[ev_cover, ev_status], version_label="Revision 2", lifecycle="superseded", holder_raw="Design Approval Holder’s Name: AIRBUS", holder_value="Airbus", supersedure=grounded_text("Revises EASA AD 2012-0175R1 dated 07 January 2014", "Revision: This AD revises EASA AD 2012-0175R1 dated 07 January 2014.", [ev_cover]), publication=publication, applicability=apps, definitions=[{"definition_id": "DEF-001", "term": "THSA first flight", "definition_text": "The THSA ‘entry into service date’ as listed in Goodrich SB 47145-27-16; if the THSA P/N is not listed there, the manufacturing date engraved on the THSA identification plate.", "evidence_ids": [ev_def]}], unsafe_condition=unsafe, requirements=requirements, exceptions=exceptions, credits=[], publications=pubs, relationships=[rel("REL-001", "revises", "2012-0175R1", "revision_family", "This AD revises EASA AD 2012-0175R1 dated 07 January 2014.", [ev_cover])], contacts=contacts(ev_remarks, ev_remarks, "For technical questions, contact AIRBUS – Airworthiness Office – EIAS, fax +33 5 61 93 44 51, account.airworth-eas@airbus.com."), classification={"airbus_families": ["A320 family"], "ata_chapters": ["27"], "action_types": ["inspection", "replacement", "reporting", "prohibition", "install", "modification"], "frequency": "mixed", "emergency_status": "standard", "terminating_action_present": True, "table_or_appendix_present": True, "compliance_complexity": "mixed", "human_confirmed": False, "evidence_ids": [ev_subject, ev_app, ev_req1, ev_req2, ev_req4, ev_req5, ev_tab5, ev_tab6]}, quality_flags=["complex_table", "complex_applicability", "complex_compliance", "cross_page_clause", "visual_transcription_used"], hybrid_source=True)


def build_2013() -> dict[str, Any]:
    b = Builder("2013-0234R2")
    ev_cover = b.ev(1, "cover", "AD No.: 2013-0234R2. Date: 07 October 2013. Design Approval Holder’s Name: AIRBUS. Type/Model designation(s): A300 and A300-600 aeroplanes. TCDS Number: France No. 145. Foreign AD: Not applicable. Revision: This AD revises EASA AD 2013-0234R1 dated 02 October 2013.", section_raw="Cover identity", method="visual_transcription", quality="visual_transcription", note="Visually transcribed from the rendered two-column cover because native extraction interleaves some labels and values.")
    ev_subject = b.ev(1, "cover", "ATA 57 Wings – Flap Beam Base – Inspection / Replacement. Manufacturer(s): Airbus (formerly Airbus Industrie).", section_raw="ATA / Manufacturer(s)")
    app_raw = "Airbus A300 aeroplanes, all certified models, all manufacturer serial numbers (MSN), and Airbus A300-600 aeroplanes, all certified models, all MSN, except A300F4-622R aeroplanes on which Airbus modifications 11133, 12047, 12048 and 12050 have all been embodied, and A300F4-605R and A300F4-622R aeroplanes on which Airbus modifications 11133 and 12699 have both been embodied."
    ev_app = b.ev(1, "applicability", "Airbus A300 aeroplanes, all certified models, all manufacturer serial numbers (MSN), and Airbus A300-600 aeroplanes, all certified models, all MSN, except: - A300F4-622R aeroplanes on which all of the following Airbus modifications (Mod.) have been embodied: 11133, 12047, 12048 and 12050. - A300F4-605R and A300F4-622R aeroplanes on which both Airbus Mod. 11133 and 12699 have been embodied.", section_raw="Applicability")
    ev_reason1 = b.ev(1, "reason", "Fatigue and ‘fail safe’ tests developed on a test specimen confirmed that cracks may appear and propagate from the bolt holes of the base member and the side members of flap beam No. 2. The development of such cracks, if not detected, could result in a rupture of flap beams No. 2, which could adversely affect the structural integrity of the airframe. Airbus issued SB A300-57-0116 and SB A300-57-6005 and DGAC France issued AD 1986-187-076(B), later revised, to require a repetitive inspection programme.", section_raw="Reason")
    ev_reason2 = b.ev(2, "reason", "For the reasons described above, this AD retains the requirements of DGAC France AD 1986-187-076(B)R4, which is superseded, and requires those inspections to be accomplished at reduced thresholds and intervals. This AD has been revised to correct typographical errors in some compliance times defined in Appendix 1, Tables 1 and 2.", section_raw="Reason continued")
    ev_effective = b.ev(2, "cover", "Effective Date: 08 October 2013 (same as original)", section_raw="Effective Date")
    ev_r1 = b.ev(2, "required_actions_and_compliance_times", "(1) Within the compliance time defined in Table 1 or in Table 2 of Appendix 1 of this AD, as applicable to aeroplane model, and, thereafter, at intervals not to exceed those defined in Table 3 or in Table 4 of Appendix 1 of this AD, as applicable, accomplish an ultrasonic inspection of the steel base member and the aluminium side members’ flap beam on the left hand (LH) and right hand (RH) side in accordance with the instructions of Airbus SB A300-57-0116 Revision 07 or SB A300-57-6005 Revision 05, as applicable to aeroplane model.", section_raw="Required Action(s) and Compliance Time(s)", clause="(1)")
    ev_r2 = b.ev(2, "required_actions_and_compliance_times", "(2) If, during any inspection as required by paragraph (1) of this AD, a crack is found in the base member or a side member, and that crack extends to the edge of or up to 4 mm beyond the bolt hole, within 250 flight cycles (FC) and, thereafter, at intervals not to exceed 250 FC, accomplish an ultrasonic inspection of the steel base member and the aluminium side members’ flap beam on the LH and RH side in accordance with the instructions of Airbus SB A300-57-0116 Revision 07 or SB A300-57-6005 Revision 05, as applicable to aeroplane model.", section_raw="Required Action(s) and Compliance Time(s)", clause="(2)")
    ev_r3 = b.ev(2, "required_actions_and_compliance_times", "(3) If, during any inspection as required by paragraph (1) of this AD, a crack is found in the base member or a side member, and that crack extends more than 4 mm beyond the bolt hole, before next flight, replace the flap beam in accordance with the instructions of the applicable Structural Repair Manual/Aircraft Maintenance Manual, as applicable to aeroplane model. (4) Replacement of the flap beam as required by paragraph (3) of this AD does not constitute terminating action for the inspections required by paragraph (1) of this AD.", section_raw="Required Action(s) and Compliance Time(s)", clause="(3)-(4)")
    ev_credit = b.ev(2, "credit", "(5) Inspections, accomplished before the effective date of this AD in accordance with any previous issue of Airbus SB A300-57-0116 or SB A300-57-6005, as applicable to aeroplane model, are acceptable for compliance with the initial requirements of paragraphs (1) and (2) of this AD.", section_raw="Required Action(s) and Compliance Time(s)", clause="(5)")
    ev_pubs = b.ev(2, "reference_publications", "Airbus SB A300-57-0116 Revision 07 dated 19 September 2011. Airbus SB A300-57-6005 Revision 05 dated 25 April 2013. The use of later approved revisions of these documents is acceptable for compliance with the requirements of this AD.", section_raw="Ref. Publications")
    ev_remarks = b.ev(2, "remarks", "If requested and appropriately substantiated, EASA can approve Alternative Methods of Compliance for this AD.", section_raw="Remarks 1")
    ev_contacts = b.ev(3, "remarks", "Enquiries regarding this AD should be referred to the Safety Information Section, Executive Directorate, EASA. E-mail: ADs@easa.europa.eu. For any question concerning the technical content of the requirements in this AD, please contact: AIRBUS SAS – EIAW (Airworthiness Office), E-mail: continued.airworthiness-wb.external@airbus.com.", section_raw="Remarks 3 and 4")
    ev_tab1 = b.table_ev(4, "Appendix 1 Table 1 – Inspection thresholds for A300", ["Aeroplane configuration", "Average Flight Time (AFT) < 1.5", "AFT ≥ 1.5", "Compliance Time"], rows=["A300B2", "A300B4-100", "A300B4-200 / A300C4-200 / A300F4-200"], note="Full table text retained because thresholds depend on model, modification, bolt diameter and AFT branch.")
    ev_tab2 = b.table_ev(5, "Appendix 1 Tables 2–4 – A300-600 thresholds and A300/A300-600 intervals", ["Aeroplane configuration", "AFT < 1.5", "AFT ≥ 1.5", "Compliance Time"], rows=["A300-600 configurations", "A300 interval rows", "A300-600 interval row"], footnotes=["A300-600 grace period: 300 FC or 640 FH, whichever occurs first after the effective date, for initial and repetitive inspections"], note="Full table and both grace-period notes retained for branch-level review.")
    apps = [
        app("APP-001", "All certified A300 models and all MSN", "Airbus A300 aeroplanes, all certified models, all manufacturer serial numbers (MSN).", ["A300 family"], ["A300"], [all_serials("MSN-001", "all manufacturer serial numbers", [ev_app])], [ev_app, ev_tab1]),
        app("APP-002", "All certified A300-600 models and all MSN, subject to modification exclusions", "Airbus A300-600 aeroplanes, all certified models, all MSN, except the listed A300F4-622R and A300F4-605R modification configurations.", ["A300-600 family"], ["A300-600"], [all_serials("MSN-002", "all manufacturer serial numbers", [ev_app])], [ev_app, ev_tab2], exclusions=["A300F4-622R with Airbus Mods 11133, 12047, 12048 and 12050 all embodied", "A300F4-605R or A300F4-622R with Airbus Mods 11133 and 12699 both embodied"]),
    ]
    cmp_a300 = b.cmp("Initial threshold from Appendix 1 Table 1 for the applicable A300 configuration and AFT branch; thereafter at the applicable Table 3 interval. Each table cell uses whichever occurs first, FC or FH.", [ev_r1, ev_tab1, ev_tab2], logic="conditional", conditions=["Applicable A300 model, modification configuration, bolt size and AFT branch"], initial=[b.limit("other", None, "other", "Applicable Table 1 threshold (whichever occurs first, FC or FH)", [ev_tab1], reference_event="first flight or applicable modification embodiment")], repetitive=[b.limit("not_to_exceed", None, "other", "Applicable Table 3 interval (whichever occurs first, FC or FH)", [ev_tab2], reference_event="last paragraph (1) inspection")])
    cmp_a306 = b.cmp("Initial threshold from Appendix 1 Table 2 for the applicable A300-600 configuration and AFT branch; thereafter at the applicable Table 4 interval. Each table cell uses whichever occurs first, FC or FH. A 300 FC or 640 FH grace period, whichever occurs first after the effective date, may be applied to initial and repetitive inspections.", [ev_r1, ev_tab2], logic="conditional", conditions=["Applicable A300-600 modification configuration and AFT branch"], initial=[b.limit("other", None, "other", "Applicable Table 2 threshold (whichever occurs first, FC or FH)", [ev_tab2], reference_event="first flight or Mod. 5815 embodiment")], repetitive=[b.limit("not_to_exceed", None, "other", "Applicable Table 4 interval (whichever occurs first, FC or FH)", [ev_tab2], reference_event="last paragraph (1) inspection")], grace=[b.limit("within", 300, "flight_cycle", "300 FC", [ev_tab2], reference_event="effective date of this AD"), b.limit("within", 640, "flight_hour", "640 FH", [ev_tab2], reference_event="effective date of this AD")])
    cmp_crack = b.cmp("If a crack extends to the edge of or up to 4 mm beyond the bolt hole, inspect within 250 FC and thereafter at intervals not to exceed 250 FC.", [ev_r2], logic="conditional", conditions=["Crack extends to the edge of or up to 4 mm beyond the bolt hole"], initial=[b.limit("within", 250, "flight_cycle", "within 250 flight cycles", [ev_r2], reference_event="inspection that found the crack")], repetitive=[b.limit("not_to_exceed", 250, "flight_cycle", "intervals not to exceed 250 FC", [ev_r2], reference_event="last paragraph (2) inspection")])
    cmp_replace = b.cmp("If a crack extends more than 4 mm beyond the bolt hole, replace the flap beam before next flight.", [ev_r3], logic="conditional", conditions=["Crack extends more than 4 mm beyond the bolt hole"], initial=[b.limit("before", None, "before_next_flight", "before next flight", [ev_r3], reference_event="inspection that found the crack")])
    requirements = [
        req("REQ-001", "(1)", ["APP-001", "APP-002"], ["inspection"], "mandatory", "Ultrasonically inspect the steel base member and aluminium side members of flap beam No. 2 on the left-hand and right-hand sides.", [ev_r1, ev_tab1, ev_tab2], objects=["Flap beam No. 2 steel base member", "Aluminium side members, LH and RH"], conditions=["Applicable table branch by aeroplane model and configuration", "Unless accomplished previously"], pubs=["PUB-001", "PUB-002"], cmps=[cmp_a300, cmp_a306], follows=["REQ-002", "REQ-003"]),
        req("REQ-002", "(2)", ["APP-001", "APP-002"], ["inspection"], "conditional", "If a crack reaches the bolt-hole edge or extends up to 4 mm beyond it, repeatedly ultrasonically inspect the flap beam members.", [ev_r2], objects=["Flap beam No. 2 base or side member"], conditions=["Crack reaches the edge of or extends no more than 4 mm beyond the bolt hole"], pubs=["PUB-001", "PUB-002"], cmps=[cmp_crack], parent="REQ-001"),
        req("REQ-003", "(3)-(4)", ["APP-001", "APP-002"], ["replacement"], "conditional", "If a crack extends more than 4 mm beyond the bolt hole, replace the flap beam before next flight.", [ev_r3], objects=["Affected flap beam"], conditions=["Crack extends more than 4 mm beyond the bolt hole"], pubs=["PUB-003", "PUB-004"], cmps=[cmp_replace], parent="REQ-001", terminating=term_none([ev_r3], explicit=True)),
    ]
    publication = common_publication(subject="Wings – Flap Beam Base – Inspection / Replacement", subject_raw="ATA 57 Wings – Flap Beam Base – Inspection / Replacement", subject_ev=ev_subject, issue_date="2013-10-07", issue_raw="Date: 07 October 2013", issue_ev=ev_cover, effective_date="2013-10-08", effective_raw="Effective Date: 08 October 2013 (same as original)", effective_ev=ev_effective, ata="57", ata_title="Wings", manufacturer_raw="Airbus (formerly Airbus Industrie)", manufacturer_ev=ev_subject, type_designations=["A300", "A300-600"], tcds=["France No. 145"], foreign_ev=ev_cover)
    unsafe = {"state": "present", "raw_reason_text": norm("Fatigue and fail-safe tests confirmed that cracks may appear and propagate from bolt holes of the base member and side members of flap beam No. 2. If not detected, the cracks could rupture flap beam No. 2 and adversely affect airframe structural integrity. Reduced repetitive inspection thresholds and intervals are required."), "observed_events_or_defects": ["Cracks may initiate and propagate from bolt holes in flap beam No. 2 members"], "causes": ["Fatigue"], "unsafe_conditions": ["Rupture of flap beam No. 2"], "potential_consequences": ["Adverse effect on structural integrity of the airframe"], "affected_components": ["Flap beam No. 2 base member", "Flap beam No. 2 side members"], "intended_risk_mitigation": ["Repetitive ultrasonic inspection at reduced thresholds and intervals", "Replacement when crack extension exceeds 4 mm"], "evidence_ids": [ev_reason1, ev_reason2]}
    credits = [{"credit_id": "CRD-001", "text": "Inspections completed before the effective date under any previous issue of Airbus SB A300-57-0116 or A300-57-6005 receive credit for the initial paragraph (1) and (2) requirements.", "applies_to_requirement_ids": ["REQ-001", "REQ-002"], "credited_publication_ids": ["PUB-005", "PUB-006"], "conditions": ["Inspection accomplished before the effective date", "Applicable previous SB issue used"], "evidence_ids": [ev_credit]}]
    pubs = [pub("PUB-001", "service_bulletin", "Airbus", "A300-57-0116", "Revision 07", "2011-09-19", ["required_method"], [ev_r1, ev_r2, ev_pubs], later=True), pub("PUB-002", "service_bulletin", "Airbus", "A300-57-6005", "Revision 05", "2013-04-25", ["required_method"], [ev_r1, ev_r2, ev_pubs], later=True), pub("PUB-003", "maintenance_manual", "Airbus", "Applicable Structural Repair Manual", None, None, ["required_method"], [ev_r3], later=None), pub("PUB-004", "maintenance_manual", "Airbus", "Applicable Aircraft Maintenance Manual", None, None, ["required_method"], [ev_r3], later=None), pub("PUB-005", "service_bulletin", "Airbus", "A300-57-0116", "Any previous issue", None, ["previous_action_credit"], [ev_credit], later=None), pub("PUB-006", "service_bulletin", "Airbus", "A300-57-6005", "Any previous issue", None, ["previous_action_credit"], [ev_credit], later=None)]
    relationships = [rel("REL-001", "revises", "2013-0234R1", "revision_family", "This AD revises EASA AD 2013-0234R1 dated 02 October 2013.", [ev_cover]), rel("REL-002", "retains_requirements_of", "F-1986-187-076", "explicit_directional_sentence", "This AD retains the requirements of DGAC France AD 1986-187-076(B)R4, which is superseded.", [ev_reason2])]
    return b.finish(cover_ev=ev_cover, identity_evs=[ev_cover], version_label="Revision 2", lifecycle="unknown", holder_raw="Design Approval Holder’s Name: AIRBUS", holder_value="Airbus", supersedure=grounded_text("Revises EASA AD 2013-0234R1 dated 02 October 2013", "Revision: This AD revises EASA AD 2013-0234R1 dated 02 October 2013.", [ev_cover]), publication=publication, applicability=apps, definitions=[], unsafe_condition=unsafe, requirements=requirements, exceptions=[], credits=credits, publications=pubs, relationships=relationships, contacts=contacts(ev_remarks, ev_contacts, "For technical questions, contact AIRBUS SAS – EIAW at continued.airworthiness-wb.external@airbus.com."), classification={"airbus_families": ["A300 family", "A300-600 family"], "ata_chapters": ["57"], "action_types": ["inspection", "replacement"], "frequency": "repetitive", "emergency_status": "standard", "terminating_action_present": False, "table_or_appendix_present": True, "compliance_complexity": "table_driven", "human_confirmed": False, "evidence_ids": [ev_subject, ev_app, ev_r1, ev_r2, ev_r3, ev_tab1, ev_tab2]}, quality_flags=["complex_table", "complex_applicability", "complex_compliance", "cross_page_clause", "visual_transcription_used"], hybrid_source=True)


def build_2015() -> dict[str, Any]:
    b = Builder("2015-0135R3")
    ev_cover = b.ev(1, "cover", "AD No.: 2015-0135R3. Issued: 13 March 2018. Design Approval Holder’s Name: AIRBUS. Type/Model designation(s): A318, A319, A320 and A321 aeroplanes. Effective Date: Revision 3: 13 March 2018; Revision 2: 23 February 2018; Revision 1: 11 January 2018; Original issue: 15 July 2015. TCDS Number(s): EASA.A.064. Foreign AD: Not applicable. Revision: This AD revises EASA AD 2015-0135R2 dated 23 February 2018. The original issue of this AD superseded EASA AD 2015-0087 dated 22 May 2015.", section_raw="Cover identity", method="visual_transcription", quality="visual_transcription", note="Visually transcribed from the rendered two-column cover to preserve identity, revision history and supersedure fields in reading order.")
    ev_subject = b.ev(1, "cover", "ATA 34 – Navigation – Angle of Attack Sensors – Replacement. Manufacturer(s): Airbus (formerly Airbus Industrie).", section_raw="ATA / Manufacturer(s)")
    app_raw = "Airbus A318-111, A318-112, A318-121, A318-122, A319-111, A319-112, A319-113, A319-114, A319-115, A319-131, A319-132, A319-133, A320-211, A320-212, A320-214, A320-215, A320-216, A320-231, A320-232, A320-233, A321-111, A321-112, A321-131, A321-211, A321-212, A321-213, A321-231 and A321-232 aeroplanes, all manufacturer serial numbers."
    ev_app = b.ev(1, "applicability", app_raw, section_raw="Applicability")
    ev_reason1 = b.ev(1, "reason", source_excerpt(b, 1, "      Reason:"), section_raw="Reason", note="Exact native-text excerpt from the Reason heading to the page boundary; the clause continues on page 2.")
    ev_reason2 = b.ev(2, "reason", source_excerpt(b, 2, "     the AOA value", "     Required Action(s)"), section_raw="Reason continued")
    ev_p1 = b.ev(2, "required_actions_and_compliance_times", paragraph_excerpt(b, 2, "1"), section_raw="Modification", clause="(1)")
    ev_p2 = b.ev(3, "required_actions_and_compliance_times", paragraph_excerpt(b, 3, "2", "3"), section_raw="Modification", clause="(2)")
    ev_p3 = b.ev(3, "credit", paragraph_excerpt(b, 3, "3", "4"), section_raw="Credit", clause="(3)")
    ev_p4 = b.ev(3, "required_actions_and_compliance_times", paragraph_excerpt(b, 3, "4", "5"), section_raw="Parts Installation", clause="(4)")
    ev_p5 = b.ev(3, "required_actions_and_compliance_times", paragraph_excerpt(b, 3, "5", "6"), section_raw="Modification", clause="(5)-(5.2)")
    ev_p6 = b.ev(3, "credit", paragraph_excerpt(b, 3, "6", "7"), section_raw="Credit", clause="(6)")
    ev_p7 = b.ev(3, "required_actions_and_compliance_times", paragraph_excerpt(b, 3, "7"), section_raw="Parts Installation", clause="(7)")
    ev_p8 = b.ev(4, "required_actions_and_compliance_times", paragraph_excerpt(b, 4, "8", "9"), section_raw="AFM Amendment", clause="(8)")
    ev_p9 = b.ev(4, "required_actions_and_compliance_times", paragraph_excerpt(b, 4, "9", "10"), section_raw="AFM Amendment", clause="(9)")
    ev_p10 = b.ev(4, "required_actions_and_compliance_times", paragraph_excerpt(b, 4, "10", "11"), section_raw="Modification", clause="(10)")
    ev_p11 = b.ev(4, "required_actions_and_compliance_times", paragraph_excerpt(b, 4, "11", "12"), section_raw="Modification", clause="(11)")
    ev_table1 = b.table_ev(4, "Table 1 – AOA Sensors Replacement", ["Aeroplanes (all models)", "P/N AOA Sensor(s) installed", "Compliance Time after 01 June 2015"], rows=["A318 and A321", "A319 and A320"], note="Full page retained because the merged table cells bind model groups, sensor P/N and four different month limits.")
    ev_p12 = b.ev(4, "required_actions_and_compliance_times", paragraph_excerpt(b, 4, "12", "13"), section_raw="Repetitive Functional Heating Tests", clause="(12)")
    ev_p13a = b.ev(4, "required_actions_and_compliance_times", paragraph_excerpt(b, 4, "13"), section_raw="Corrective Action(s)", clause="(13), page 1 of 2", note="Exact native-text first part through the page boundary; the sentence continues on page 5.")
    ev_p13b = b.ev(5, "required_actions_and_compliance_times", source_excerpt(b, 5, "            Airbus SB A320-34-1415", "     Conditional Credit:"), section_raw="Corrective Action(s)", clause="(13), page 2 of 2")
    ev_p14 = b.ev(5, "credit", paragraph_excerpt(b, 5, "14", "15"), section_raw="Conditional Credit", clause="(14)")
    ev_p15 = b.ev(5, "required_actions_and_compliance_times", paragraph_excerpt(b, 5, "15", "16"), section_raw="Terminating Actions", clause="(15)")
    ev_p16 = b.ev(5, "required_actions_and_compliance_times", paragraph_excerpt(b, 5, "16", "17"), section_raw="Parts Installation", clause="(16)")
    ev_p17 = b.ev(5, "required_actions_and_compliance_times", paragraph_excerpt(b, 5, "17", "18"), section_raw="Parts Installation", clause="(17)")
    ev_p18 = b.ev(5, "required_actions_and_compliance_times", paragraph_excerpt(b, 5, "18", "19"), section_raw="Parts Installation", clause="(18)")
    ev_table2 = b.table_ev(5, "Table 2 – AOA Sensors", ["AOA Sensor Manufacturer", "P/N"], rows=["SEXTANT/THOMSON", "UTAS (formerly Goodrich)"], note="Full page retained to preserve the four prohibited sensor P/N values.")
    ev_p19a = b.ev(5, "required_actions_and_compliance_times", paragraph_excerpt(b, 5, "19"), section_raw="Parts Installation", clause="(19)-(19.1), page 1 of 2", note="Exact native-text first part through the page boundary; paragraph (19.2) continues on page 6.")
    ev_p19b = b.ev(6, "required_actions_and_compliance_times", source_excerpt(b, 6, "             (19.2)", "     AFM Amendment:"), section_raw="Parts Installation", clause="(19.2)")
    ev_p20 = b.ev(6, "required_actions_and_compliance_times", paragraph_excerpt(b, 6, "20"), section_raw="AFM Amendment", clause="(20)")
    ev_tables34 = b.table_ev(6, "Tables 3 and 4 – Minimum ELAC and AOA Sensor Installation Configurations", ["Aeroplane applicability", "ELAC P/N", "Configuration introduced by Airbus mod/SB", "Pilot / First Officer / Standby AOA sensor P/N"], rows=["A320", "A318/A319/A321", "AOA sensor installation configuration"], note="Full page retained because AFM-removal eligibility depends jointly on the ELAC and AOA configurations.")
    ev_pubs = b.ev(7, "reference_publications", source_excerpt(b, 7, "     Ref. Publications:", "     Remarks:"), section_raw="Ref. Publications")
    ev_remarks = b.ev(7, "remarks", source_excerpt(b, 7, "     Remarks:"), section_raw="Remarks")
    ev_appendix = b.ev(8, "appendix", "Appendix 1 – AFM Procedure. At any time, with a speed above VLS, if the aircraft goes to a continuous nose down pitch rate that cannot be stopped with backward sidestick inputs, immediately: Keep on one ADR. Turn off two ADRs. If the Alpha Max strip (red) hides completely the Alpha Prot strip (black and amber) in a stabilized wings-level flight path, keep on one ADR and turn off two ADRs. If the Alpha Prot strip (black and amber) rapidly moves by more than 30 kt during flight manoeuvres, with AP ON and speed brakes retracted, keep on one ADR and turn off two ADRs. In case of dispatch with one ADR inoperative, switch only one ADR to OFF. Caution: Risk of erroneous display of the VSW strip (red and black). Consider using the Flight Path Vector (FPV).", section_raw="Appendix 1 – AFM Procedure", method="visual_transcription", quality="visual_transcription", note="Visually transcribed from the embedded yellow AFM-procedure image on rendered page 8; native PDF text contains only the appendix heading.")

    apps = [
        app("APP-001", "All listed A318/A319/A320/A321 models and all MSN", app_raw, ["A320 family"], A320_MODELS, [all_serials("MSN-001", "all manufacturer serial numbers", [ev_app])], [ev_app]),
        app("APP-002", "A318 and A321 model branches in Table 1", "Applicable A318 and A321 aeroplanes from the AD applicability, with the sensor configuration specified by the linked requirement and Table 1.", ["A320 family"], [m for m in A320_MODELS if m.startswith("A318-") or m.startswith("A321-")], [all_serials("MSN-002", "all manufacturer serial numbers", [ev_app])], [ev_app, ev_table1], conditions=["Sensor P/N/configuration specified by the linked requirement"]),
        app("APP-003", "A319 and A320 model branches in Table 1", "Applicable A319 and A320 aeroplanes from the AD applicability, with the sensor configuration specified by the linked requirement and Table 1.", ["A320 family"], [m for m in A320_MODELS if m.startswith("A319-") or m.startswith("A320-")], [all_serials("MSN-003", "all manufacturer serial numbers", [ev_app])], [ev_app, ev_table1], conditions=["Sensor P/N/configuration specified by the linked requirement"]),
    ]

    def month_rule(raw: str, months: int, evs: list[str], ref_event: str, conditions: list[str] | None = None) -> dict[str, Any]:
        return b.cmp(raw, evs, logic="conditional" if conditions else "single", conditions=conditions, initial=[b.limit("within", months, "calendar_month", f"within {months} months", evs, reference_event=ref_event)])

    cmp1 = month_rule("Within 12 months after 27 October 2011", 12, [ev_p1], "27 October 2011, effective date of EASA AD 2011-0203")
    cmp2 = month_rule("Within 3 months after 23 November 2012", 3, [ev_p2], "23 November 2012, effective date of EASA AD 2012-0236 at original issue")
    cmp3 = b.cmp("From 23 November 2012, do not install an affected C16291AA or C16291AB sensor unless it passed an allowed inspection", [ev_p4], logic="conditional", conditions=["Sensor P/N and s/n are listed in Thales SB C16291A-34-007 Revision 04", "Installation allowed only after a qualifying inspection"], initial=[b.limit("from", None, "calendar_date", "From 23 November 2012", [ev_p4], calendar_date="2012-11-23", reference_event="effective date of EASA AD 2012-0236 at original issue")])
    cmp4 = month_rule("Within 5 months after 15 February 2013", 5, [ev_p5], "15 February 2013, effective date of EASA AD 2013-0022")
    cmp5 = b.cmp("From 15 February 2013, do not install the listed conic plates", [ev_p7], initial=[b.limit("from", None, "calendar_date", "From 15 February 2013", [ev_p7], calendar_date="2013-02-15", reference_event="effective date of EASA AD 2013-0022")])
    cmp6 = b.cmp("From 15 February 2013, do not use AOA protection cover P/N 98D34203003000", [ev_p7], initial=[b.limit("from", None, "calendar_date", "From 15 February 2013", [ev_p7], calendar_date="2013-02-15", reference_event="effective date of EASA AD 2013-0022")])
    cmp7 = b.cmp("Before next flight after 11 December 2014", [ev_p8], initial=[b.limit("before", None, "before_next_flight", "Before next flight after 11 December 2014", [ev_p8], reference_event="11 December 2014, effective date of EASA Emergency AD 2014-0266-E")])
    cmp8 = b.cmp("Concurrent with the paragraph (8) AFM amendment", [ev_p9], logic="conditional", conditions=["Paragraph (8) AFM amendment is made"], initial=[])
    cmp9a = month_rule("A318/A321 with P/N 0861ED: within 7 months after 01 June 2015", 7, [ev_p10, ev_table1], "01 June 2015", ["A318 or A321", "UTAS P/N 0861ED installed"])
    cmp9b = month_rule("A319/A320 with P/N 0861ED: within 22 months after 01 June 2015", 22, [ev_p10, ev_table1], "01 June 2015", ["A319 or A320", "UTAS P/N 0861ED installed"])
    cmp9c = month_rule("A318/A321 with P/N 0861ED2: within 4 months after 01 June 2015", 4, [ev_p10, ev_table1], "01 June 2015", ["A318 or A321", "UTAS P/N 0861ED2 installed"])
    cmp9d = month_rule("A319/A320 with P/N 0861ED2: within 7 months after 01 June 2015", 7, [ev_p10, ev_table1], "01 June 2015", ["A319 or A320", "UTAS P/N 0861ED2 installed"])
    cmp10a = month_rule("A318/A321 with P/N 45150320 or 16990568: within 7 months after 01 June 2015", 7, [ev_p11, ev_table1], "01 June 2015", ["A318 or A321", "SEXTANT/THOMSON P/N 45150320 or 16990568 installed"])
    cmp10b = month_rule("A319/A320 with P/N 45150320 or 16990568: within 22 months after 01 June 2015", 22, [ev_p11, ev_table1], "01 June 2015", ["A319 or A320", "SEXTANT/THOMSON P/N 45150320 or 16990568 installed"])
    cmp11 = b.cmp("Before exceeding 5 200 FH since first installation or within 6 months after 01 June 2015, whichever occurs later; thereafter at intervals not to exceed 2 000 FH", [ev_p12], logic="whichever_occurs_later", conditions=["One or more Thales P/N C16291AA sensors are installed"], initial=[b.limit("before", 5200, "flight_hour", "before exceeding 5 200 flight hours", [ev_p12], reference_event="first installation of each Thales AOA sensor"), b.limit("within", 6, "calendar_month", "within 6 months after 01 June 2015", [ev_p12], reference_event="01 June 2015")], repetitive=[b.limit("not_to_exceed", 2000, "flight_hour", "intervals not to exceed 2 000 FH", [ev_p12], reference_event="last functional heating test")])
    cmp12 = b.cmp("Before next flight if a paragraph (12) functional heating test detects discrepancies", [ev_p13a, ev_p13b], logic="conditional", conditions=["Discrepancies detected during a paragraph (12) functional heating test"], initial=[b.limit("before", None, "before_next_flight", "before next flight", [ev_p13a, ev_p13b], reference_event="functional heating test that detected discrepancies")])
    cmp13 = b.cmp("Optional replacement under paragraph (15)", [ev_p15], logic="conditional", conditions=["Operator elects the terminating modification"], initial=[])
    cmp14 = b.cmp("From 01 June 2015, or after paragraph (15) optional modification, do not install P/N C16291AA", [ev_p16], logic="conditional", conditions=["Only P/N C16291AB sensors are installed, or paragraph (15) modification has been completed"], initial=[b.limit("from", None, "calendar_date", "From 01 June 2015", [ev_p16], calendar_date="2015-06-01", reference_event="effective date of EASA AD 2015-0087")])
    cmp15 = b.cmp("From 01 June 2015, or after paragraph (11) modification, do not install a Table 2 sensor P/N", [ev_p17, ev_table2], logic="conditional", conditions=["P/N C16291AA and/or C16291AB sensors are installed, or paragraph (11) modification has been completed"], initial=[b.limit("from", None, "calendar_date", "From 01 June 2015", [ev_p17], calendar_date="2015-06-01", reference_event="effective date of EASA AD 2015-0087")])
    cmp16 = b.cmp("After paragraph (10) modification, do not install a Table 2 sensor P/N except UTAS P/N 0861ED in the standby position", [ev_p18, ev_table2], logic="conditional", conditions=["Paragraph (10) modification has been completed"], initial=[])
    cmp17 = b.cmp("Installation of a post-01 June 2015 approved AOA sensor P/N equals compliance with paragraph (10) or (11) if both approval conditions are met", [ev_p19a, ev_p19b], logic="conditional", conditions=["Sensor P/N approved by EASA or under Airbus DOA", "Installation instructions approved by EASA or under Airbus DOA"], initial=[])
    cmp18 = b.cmp("AFM procedure may be removed for a Table 3-or-later ELAC configuration together with a Table 4 or paragraph (19) AOA configuration", [ev_p20, ev_tables34], logic="conditional", conditions=["Eligible ELAC configuration", "Eligible AOA sensor configuration"], initial=[])
    cmp19 = b.cmp("After the paragraph (20) AFM amendment, inform all flight crews and operate accordingly", [ev_p20, ev_appendix], logic="conditional", conditions=["Paragraph (20) AFM amendment removing the procedure has been made"], initial=[])

    requirements = [
        req("REQ-001", "(1)", ["APP-001"], ["replacement", "records_review"], "mandatory", "Replace each Thales P/N C16291AA AOA sensor whose s/n is listed in Thales SB C16291A-34-007 Revision 04.", [ev_p1], objects=["Thales P/N C16291AA AOA sensors with listed s/n"], conditions=["P/N C16291AA installed and s/n listed in Thales SB C16291A-34-007 Revision 04"], pubs=["PUB-006", "PUB-007", "PUB-015"], cmps=[cmp1]),
        req("REQ-002", "(2)", ["APP-001"], ["replacement"], "mandatory", "Replace each P/N C16291AB AOA sensor whose s/n is listed in Thales SB C16291A-34-007 Revision 04.", [ev_p2], objects=["Thales P/N C16291AB AOA sensors with listed s/n"], conditions=["P/N C16291AB installed and s/n listed in Thales SB C16291A-34-007 Revision 04"], pubs=["PUB-006", "PUB-007", "PUB-015"], cmps=[cmp2]),
        req("REQ-003", "(4)", ["APP-001"], ["prohibition", "install"], "prohibited", "Do not install a listed-s/n P/N C16291AA or C16291AB sensor unless it passed one of the permitted inspections.", [ev_p4], objects=["P/N C16291AA or C16291AB AOA sensor with listed s/n"], conditions=["Installation allowed only after the specified Thales inspection"], pubs=["PUB-012", "PUB-017"], cmps=[cmp3]),
        req("REQ-004", "(5)-(5.2)", ["APP-001"], ["remove", "install", "modification"], "mandatory", "Remove all listed AOA sensor conic plates and install one of the approved flat-plate configurations.", [ev_p5], objects=["Conic plates P/N F3411060200000 and F3411060900000", "Approved AOA sensor flat plate"], pubs=["PUB-008", "PUB-009"], cmps=[cmp4]),
        req("REQ-005", "(7)", ["APP-001"], ["prohibition", "install"], "prohibited", "Do not install AOA sensor conic plate P/N F3411060200000 or F3411060900000.", [ev_p7], objects=["AOA sensor conic plates F3411060200000 and F3411060900000"], cmps=[cmp5]),
        req("REQ-006", "(7)", ["APP-001"], ["prohibition"], "prohibited", "Do not use AOA protection cover P/N 98D34203003000.", [ev_p7], objects=["AOA protection cover P/N 98D34203003000"], cmps=[cmp6]),
        req("REQ-007", "(8)", ["APP-001"], ["document_amendment"], "mandatory", "Amend the applicable AFM by inserting Airbus AFM A320 TR 502 issue 1 or Appendix 1 of this AD into Emergency Procedures.", [ev_p8, ev_appendix], objects=["Applicable Aircraft Flight Manual"], pubs=["PUB-018"], cmps=[cmp7], follows=["REQ-008"]),
        req("REQ-008", "(9)", ["APP-001"], ["operational_procedure"], "mandatory", "Inform all flight crews and operate the aeroplane according to the inserted emergency procedure.", [ev_p9, ev_appendix], objects=["Flight crews", "Aeroplane operations"], conditions=["Concurrent with the paragraph (8) AFM amendment"], cmps=[cmp8], parent="REQ-007"),
        req("REQ-009", "(10)", ["APP-002", "APP-003"], ["replacement"], "mandatory", "Replace the Captain and First Officer UTAS P/N 0861ED or 0861ED2 AOA sensors with Thales P/N C16291AB sensors.", [ev_p10, ev_table1], objects=["Captain and First Officer AOA sensors"], conditions=["UTAS P/N 0861ED or 0861ED2 installed"], pubs=["PUB-010", "PUB-011"], cmps=[cmp9a, cmp9b, cmp9c, cmp9d]),
        req("REQ-010", "(11)", ["APP-002", "APP-003"], ["replacement"], "mandatory", "Replace each SEXTANT/THOMSON P/N 45150320 or P/N 16990568 AOA sensor with a Thales P/N C16291AB sensor.", [ev_p11, ev_table1], objects=["SEXTANT/THOMSON P/N 45150320 and 16990568 AOA sensors"], conditions=["An affected SEXTANT/THOMSON sensor is installed"], pubs=["PUB-004", "PUB-005"], cmps=[cmp10a, cmp10b]),
        req("REQ-011", "(12)", ["APP-001"], ["test_or_check"], "mandatory", "Perform repetitive functional heating tests of each installed Thales P/N C16291AA AOA sensor.", [ev_p12], objects=["Thales P/N C16291AA AOA sensor"], conditions=["One or more P/N C16291AA sensors are installed"], pubs=["PUB-002", "PUB-003"], cmps=[cmp11], follows=["REQ-012"]),
        req("REQ-012", "(13)", ["APP-001"], ["replacement"], "conditional", "If a functional heating test finds discrepancies, replace all affected sensors with tested P/N C16291AA sensors or P/N C16291AB sensors.", [ev_p13a, ev_p13b], objects=["Affected AOA sensors"], conditions=["Discrepancy detected during paragraph (12) test"], pubs=["PUB-002", "PUB-003"], cmps=[cmp12], parent="REQ-011"),
        req("REQ-013", "(15)", ["APP-001"], ["replacement", "modification"], "optional_terminating", "Replace every Thales P/N C16291AA sensor with a Thales P/N C16291AB sensor.", [ev_p15], objects=["All Thales P/N C16291AA AOA sensors"], pubs=["PUB-004", "PUB-005"], cmps=[cmp13], terminating=term_yes("Replacing every P/N C16291AA sensor with P/N C16291AB under Airbus SB A320-34-1444 terminates paragraph (12) repetitive tests for that aeroplane.", ["REQ-011"], [ev_p15])),
        req("REQ-014", "(16)", ["APP-001"], ["prohibition", "install"], "prohibited", "Do not install a Thales P/N C16291AA sensor on an aeroplane fitted only with P/N C16291AB sensors.", [ev_p16], objects=["Thales P/N C16291AA AOA sensor"], conditions=["Only P/N C16291AB sensors are installed, or paragraph (15) modification completed"], cmps=[cmp14]),
        req("REQ-015", "(17)", ["APP-001"], ["prohibition", "install"], "prohibited", "Do not install any AOA sensor P/N listed in Table 2 on the specified Thales-sensor configurations.", [ev_p17, ev_table2], objects=["Table 2 AOA sensor P/N"], conditions=["P/N C16291AA and/or C16291AB sensors are installed, or paragraph (11) modification completed"], cmps=[cmp15]),
        req("REQ-016", "(18)", ["APP-001"], ["prohibition", "install"], "prohibited", "After paragraph (10) modification, do not install a Table 2 AOA sensor P/N, except P/N 0861ED in the standby position.", [ev_p18, ev_table2], objects=["Table 2 AOA sensor P/N"], conditions=["Paragraph (10) modification completed"], cmps=[cmp16]),
        req("REQ-017", "(19)-(19.2)", ["APP-001"], ["install", "modification"], "conditional", "Install an AOA sensor P/N approved after 01 June 2015 under EASA or Airbus DOA approval, using similarly approved modification instructions, as an alternative compliance method for paragraph (10) or (11).", [ev_p19a, ev_p19b], objects=["Post-01 June 2015 approved AOA sensor P/N"], conditions=["P/N approved by EASA or under Airbus DOA", "Installation instructions approved by EASA or under Airbus DOA"], cmps=[cmp17]),
        req("REQ-018", "(20)", ["APP-001"], ["document_amendment"], "conditional", "For an eligible ELAC and AOA sensor configuration, amend the AFM to remove the previously inserted abnormal-alpha-protection procedure.", [ev_p20, ev_tables34], objects=["Applicable Aircraft Flight Manual"], conditions=["ELAC configuration from Table 3 or later", "AOA configuration from Table 4 or paragraph (19)"], pubs=["PUB-018", "PUB-019", "PUB-020", "PUB-021", "PUB-022"], cmps=[cmp18], follows=["REQ-019"]),
        req("REQ-019", "(20)", ["APP-001"], ["operational_procedure"], "conditional", "After removing the AFM procedure, inform all flight crews and operate the aeroplane accordingly.", [ev_p20, ev_appendix], objects=["Flight crews", "Aeroplane operations"], conditions=["Paragraph (20) AFM amendment completed"], cmps=[cmp19], parent="REQ-018"),
    ]

    exceptions = [
        {"exception_id": "EXC-001", "text": "Paragraph (2) replacement is not required if maintenance records demonstrate that the affected P/N C16291AB sensor passed the inspection under Thales SB C16291A-34-007 Revision 01.", "applies_to_requirement_ids": ["REQ-002"], "evidence_ids": [ev_p2]},
        {"exception_id": "EXC-002", "text": "Paragraph (4) permits installation if the sensor passed the inspection under Thales SB C16291A-34-007 Revision 01 or C16291A-34-009 Revision 01.", "applies_to_requirement_ids": ["REQ-003"], "evidence_ids": [ev_p4]},
        {"exception_id": "EXC-003", "text": "After paragraph (10) modification, UTAS P/N 0861ED remains allowed in the standby position.", "applies_to_requirement_ids": ["REQ-016"], "evidence_ids": [ev_p18]},
    ]
    credits = [
        {"credit_id": "CRD-001", "text": "Production modification 150006 or 26934 provides credit for paragraphs (1) and (2) if no AOA sensor has been replaced since manufacture.", "applies_to_requirement_ids": ["REQ-001", "REQ-002"], "credited_publication_ids": [], "conditions": ["Applicable production modification embodied", "No AOA sensor replaced since manufacture"], "evidence_ids": [ev_p3]},
        {"credit_id": "CRD-002", "text": "Production modifications 154863 and 154864 provide credit for paragraph (5) if no listed conic plate has been installed since first flight.", "applies_to_requirement_ids": ["REQ-004"], "credited_publication_ids": [], "conditions": ["Mods 154863 and 154864 embodied in production", "No listed conic plate installed since first flight"], "evidence_ids": [ev_p6]},
        {"credit_id": "CRD-003", "text": "Production mod 150006 without mod 26934 provides conditional credit for paragraphs (10) through (13) if no Table 2 sensor P/N has been installed since manufacture.", "applies_to_requirement_ids": ["REQ-009", "REQ-010", "REQ-011", "REQ-012"], "credited_publication_ids": [], "conditions": ["Mod 150006 embodied without mod 26934", "No Table 2 AOA sensor P/N installed since manufacture"], "evidence_ids": [ev_p14]},
    ]
    pubs = [
        pub("PUB-001", "other", "Airbus", "OIT 999.0015/15", "Revision 01", "2015-06-29", ["referenced_information"], [ev_reason2, ev_pubs], later=True, title="Operators Information Transmission"),
        pub("PUB-002", "service_bulletin", "Airbus", "A320-34-1415", "Revision 03", "2010-07-08", ["required_method"], [ev_p12, ev_p13a, ev_p13b, ev_pubs], later=True),
        pub("PUB-003", "service_bulletin", "Airbus", "A320-34-1415", "Revision 04", "2015-07-30", ["required_method"], [ev_pubs], later=True),
        pub("PUB-004", "service_bulletin", "Airbus", "A320-34-1444", "Original issue", "2009-10-07", ["required_method", "optional_method"], [ev_p11, ev_p15, ev_pubs], later=True),
        pub("PUB-005", "service_bulletin", "Airbus", "A320-34-1444", "Revision 01", "2011-03-17", ["required_method", "optional_method"], [ev_pubs], later=True),
        pub("PUB-006", "service_bulletin", "Airbus", "A320-34-1452", "Original issue", "2010-01-29", ["required_method"], [ev_p1, ev_p2, ev_pubs], later=True),
        pub("PUB-007", "service_bulletin", "Airbus", "A320-34-1452", "Revision 01", "2013-09-16", ["required_method"], [ev_pubs], later=True),
        pub("PUB-008", "service_bulletin", "Airbus", "A320-34-1564", "Original issue", "2013-01-25", ["required_method"], [ev_p5, ev_pubs], later=True),
        pub("PUB-009", "service_bulletin", "Airbus", "A320-34-1564", "Revision 01", "2013-08-26", ["required_method"], [ev_pubs], later=True),
        pub("PUB-010", "service_bulletin", "Airbus", "A320-34-1610", "Original issue", "2015-03-31", ["required_method"], [ev_p10, ev_pubs], later=True),
        pub("PUB-011", "service_bulletin", "Airbus", "A320-34-1610", "Revision 01", "2015-07-30", ["required_method"], [ev_pubs], later=True),
        pub("PUB-012", "service_bulletin", "Thales", "C16291A-34-007", "Revision 01", "2009-12-03", ["required_method"], [ev_p2, ev_p4, ev_pubs], later=True),
        pub("PUB-013", "service_bulletin", "Thales", "C16291A-34-007", "Revision 02", "2011-12-16", ["referenced_information"], [ev_pubs], later=True),
        pub("PUB-014", "service_bulletin", "Thales", "C16291A-34-007", "Revision 03", "2012-04-10", ["referenced_information"], [ev_pubs], later=True),
        pub("PUB-015", "service_bulletin", "Thales", "C16291A-34-007", "Revision 04", "2012-10-11", ["required_method"], [ev_p1, ev_p2, ev_p4, ev_pubs], later=True),
        pub("PUB-016", "service_bulletin", "Thales", "C16291A-34-009", "Original issue", "2009-09-10", ["referenced_information"], [ev_pubs], later=True),
        pub("PUB-017", "service_bulletin", "Thales", "C16291A-34-009", "Revision 01", "2010-01-07", ["required_method"], [ev_p4, ev_pubs], later=True),
        pub("PUB-018", "other", "Airbus", "AFM A320 TR 502", "Issue 1", "2014-12-05", ["required_method"], [ev_p8, ev_p20, ev_appendix, ev_pubs], later=True, title="Abnormal V alpha Prot"),
        pub("PUB-019", "service_bulletin", "Airbus", "A320-27-1243", None, None, ["referenced_information"], [ev_p20, ev_tables34], later=None),
        pub("PUB-020", "service_bulletin", "Airbus", "A320-27-1244", None, None, ["referenced_information"], [ev_p20, ev_tables34], later=None),
        pub("PUB-021", "service_bulletin", "Airbus", "A320-27-1263", None, None, ["referenced_information"], [ev_p20, ev_tables34], later=None),
        pub("PUB-022", "service_bulletin", "Airbus", "A320-27-1264", None, None, ["referenced_information"], [ev_p20, ev_tables34], later=None),
    ]
    publication = common_publication(subject="Navigation – Angle of Attack Sensors – Replacement", subject_raw="ATA 34 – Navigation – Angle of Attack Sensors – Replacement", subject_ev=ev_subject, issue_date="2018-03-13", issue_raw="Issued: 13 March 2018", issue_ev=ev_cover, effective_date="2018-03-13", effective_raw="Revision 3: 13 March 2018", effective_ev=ev_cover, ata="34", ata_title="Navigation", manufacturer_raw="Airbus (formerly Airbus Industrie)", manufacturer_ev=ev_subject, type_designations=["A318", "A319", "A320", "A321"], tcds=["EASA.A.064"], foreign_ev=ev_cover)
    unsafe = {"state": "present", "raw_reason_text": norm("An A321 experienced blockage of two Angle of Attack probes during climb, activating Alpha Protection while Mach increased. Blocked probes can cause flight-control laws to command a continuous nose-down pitch rate that cannot be stopped with full backward sidestick; increasing Mach lowers the Alpha Protection AOA value and sustains the command. The condition could cause loss of control. Certain UTAS and SEXTANT/THOMSON sensors are more susceptible to adverse environmental conditions than the latest Thales P/N C16291AB sensor."), "observed_events_or_defects": ["Blockage of two AOA probes during climb with Alpha Protection activation"], "causes": ["Certain AOA sensors are more susceptible to adverse environmental conditions"], "unsafe_conditions": ["Continuous nose-down pitch command that may not be stopped by full backward sidestick input"], "potential_consequences": ["Loss of control of the aeroplane"], "affected_components": ["Angle of Attack sensors", "Elevator Aileron Computer configuration", "Aircraft Flight Manual emergency procedure"], "intended_risk_mitigation": ["Replace affected AOA sensors and conic plates", "Apply installation prohibitions", "Perform repetitive functional heating tests", "Insert and conditionally remove an AFM emergency procedure"], "evidence_ids": [ev_reason1, ev_reason2]}
    relationships = [rel("REL-001", "revises", "2015-0135R2", "revision_family", "This AD revises EASA AD 2015-0135R2 dated 23 February 2018.", [ev_cover]), rel("REL-002", "supersedes", "2015-0087", "structured_supersedure_field", "The original issue of this AD superseded EASA AD 2015-0087 dated 22 May 2015.", [ev_cover])]
    action_types = ["replacement", "records_review", "prohibition", "install", "remove", "modification", "document_amendment", "operational_procedure", "test_or_check"]
    return b.finish(cover_ev=ev_cover, identity_evs=[ev_cover], version_label="Revision 3", lifecycle="unknown", holder_raw="Design Approval Holder’s Name: AIRBUS", holder_value="Airbus", supersedure=grounded_text("Revises EASA AD 2015-0135R2; original issue superseded EASA AD 2015-0087", "Revision: This AD revises EASA AD 2015-0135R2 dated 23 February 2018. The original issue of this AD superseded EASA AD 2015-0087 dated 22 May 2015.", [ev_cover]), publication=publication, applicability=apps, definitions=[], unsafe_condition=unsafe, requirements=requirements, exceptions=exceptions, credits=credits, publications=pubs, relationships=relationships, contacts=contacts(ev_remarks, ev_remarks, "For technical questions, contact AIRBUS – Airworthiness Office – EIAS at account.airworth-eas@airbus.com."), classification={"airbus_families": ["A320 family"], "ata_chapters": ["34"], "action_types": action_types, "frequency": "mixed", "emergency_status": "standard", "terminating_action_present": True, "table_or_appendix_present": True, "compliance_complexity": "mixed", "human_confirmed": False, "evidence_ids": [ev_subject, ev_app, ev_p1, ev_p2, ev_p4, ev_p5, ev_p7, ev_p8, ev_p10, ev_p11, ev_table1, ev_p12, ev_p13a, ev_p13b, ev_p15, ev_p16, ev_p17, ev_p18, ev_table2, ev_p19a, ev_p19b, ev_p20, ev_tables34, ev_appendix]}, quality_flags=["complex_table", "complex_applicability", "complex_compliance", "cross_page_clause", "visual_transcription_used"], hybrid_source=True)


def build_2009() -> dict[str, Any]:
    b = Builder("2009-0141")
    ev_cover = b.ev(1, "cover", "AD No.: 2009-0141. Date: 02 July 2009. Type Approval Holder’s Name: AIRBUS. Type/Model designation(s): A318, A319, A320 and A321 aeroplanes. TCDS Number: EASA.A.064. Foreign AD: Not applicable. Supersedure: None.", section_raw="Cover identity", method="visual_transcription", quality="visual_transcription", note="Visually transcribed from the rendered legacy two-column cover because native extraction interleaves labels and values beneath a diagonal status stamp.")
    ev_status = b.ev(1, "other", "SUPERSEDED", section_raw="Document status stamp", method="visual_transcription", quality="visual_transcription", note="Visible diagonal red status stamp on the rendered PDF; it does not identify the superseding AD.")
    ev_subject = b.ev(1, "cover", "ATA 55 Stabilizers – Rudder Side Shell Skin – Inspection. Manufacturer(s): AIRBUS (formerly AIRBUS INDUSTRIE).", section_raw="ATA / Manufacturer(s)")
    ev_app = b.ev(1, "applicability", source_excerpt(b, 1, "          Applicability:", "          Reason:"), section_raw="Applicability")
    ev_reason = b.ev(1, "reason", source_excerpt(b, 1, "          Reason:"), section_raw="Reason")
    ev_effective = b.ev(2, "cover", "Effective Date: 16 July 2009", section_raw="Effective Date", method="visual_transcription", quality="visual_transcription", note="Visually read from the rendered legacy compliance header; native two-column extraction places the label and value far apart.")
    ev_p1a = b.ev(2, "required_actions_and_compliance_times", source_excerpt(b, 2, "(1)"), section_raw="Required action(s) and Compliance Time(s)", clause="(1), page 1 of 2", note="Exact native text through the page boundary; paragraph (1.5) continues on page 3.")
    ev_p1b = b.ev(3, "required_actions_and_compliance_times", source_excerpt(b, 3, "                                                                        the inspection results", "                                                      (2)"), section_raw="Required action(s) and Compliance Time(s)", clause="(1.5), continuation")
    ev_p2a = b.ev(3, "required_actions_and_compliance_times", paragraph_excerpt(b, 3, "2"), section_raw="Required action(s) and Compliance Time(s)", clause="(2), page 1 of 2", note="Exact native text through the page boundary; paragraph (2.3.3) continues on page 4.")
    ev_p2b = b.ev(4, "required_actions_and_compliance_times", b.page_quote(4), section_raw="Required action(s) and Compliance Time(s)", clause="(2), page 2 of 2", note="Full page retained because the legacy extraction begins mid-clause and continues into paragraphs (3) and (4).")
    ev_p3 = b.ev(4, "credit", paragraph_excerpt(b, 4, "3", "4"), section_raw="Required action(s) and Compliance Time(s)", clause="(3)")
    ev_p4 = b.ev(4, "required_actions_and_compliance_times", paragraph_excerpt(b, 4, "4"), section_raw="Required action(s) and Compliance Time(s)", clause="(4)")
    ev_pubs = b.ev(4, "reference_publications", source_excerpt(b, 4, "            Ref. Publications:", "             Remarks:"), section_raw="Ref. Publications")
    ev_remarks = b.ev(4, "remarks", source_excerpt(b, 4, "             Remarks:"), section_raw="Remarks")
    ev_tab5 = b.table_ev(5, "Appendix A – Affected rudders (page 1 of 4)", ["Rudder P/N", "Affected rudder S/N", "Core density of 24 kg/m3"], note="Full appendix page retained for row-level P/N, S/N and core-density review.")
    ev_tab6 = b.table_ev(6, "Appendix A – Affected rudders (page 2 of 4)", ["Rudder P/N", "Affected rudder S/N", "Core density of 24 kg/m3"], note="Full appendix page retained for row-level review.")
    ev_tab7 = b.table_ev(7, "Appendix A – Affected rudders (page 3 of 4)", ["Rudder P/N", "Affected rudder S/N", "Core density of 24 kg/m3"], note="Full appendix page retained for row-level review.")
    ev_tab8 = b.table_ev(8, "Appendix A – Affected rudders (page 4 of 4)", ["Rudder P/N", "Affected rudder S/N", "Core density of 24 kg/m3"], note="Full appendix page retained for row-level review.")

    rows = parse_rudder_rows("\n".join(b.page_text(page) for page in range(5, 9)))
    rows_24 = [row for row in rows if row[2]]
    rows_other = [row for row in rows if not row[2]]
    table_evs = [ev_tab5, ev_tab6, ev_tab7, ev_tab8]
    app_text = "AIRBUS A318-111, A318-112, A318-121, A318-122, A319-111, A319-112, A319-113, A319-114, A319-115, A319-131, A319-132, A319-133, A320-111, A320-211, A320-212, A320-214, A320-215, A320-216, A320-231, A320-232, A320-233, A321-111, A321-112, A321-131, A321-211, A321-212, A321-213, A321-231 and A321-232 aeroplane models, all manufacturer serial numbers, if equipped with CFRP rudders having P/N and S/N listed in Appendix A."
    apps = [
        app("APP-001", "Appendix A rudders with 24 kg/m3 honeycomb core", app_text + " This group is limited to Appendix A rows marked as core density 24 kg/m3.", ["A320 family"], A320_MODELS_WITH_111, [all_serials("MSN-001", "all manufacturer serial numbers", [ev_app]), listed_serials("MSN-002", "affected rudder S/N marked 24 kg/m3 in Appendix A", sorted({sn for _, sn, _ in rows_24}), table_evs, condition="Installed rudder serial number")], [ev_app, *table_evs], part_numbers=sorted({pn for pn, _, _ in rows_24}), conditions=["CFRP rudder P/N and S/N appears in Appendix A", "Appendix A row is marked core density 24 kg/m3"]),
        app("APP-002", "Appendix A rudders not having 24 kg/m3 honeycomb core", app_text + " This group is limited to Appendix A rows not marked as core density 24 kg/m3.", ["A320 family"], A320_MODELS_WITH_111, [all_serials("MSN-003", "all manufacturer serial numbers", [ev_app]), listed_serials("MSN-004", "affected rudder S/N not marked 24 kg/m3 in Appendix A", sorted({sn for _, sn, _ in rows_other}), table_evs, condition="Installed rudder serial number")], [ev_app, *table_evs], part_numbers=sorted({pn for pn, _, _ in rows_other}), conditions=["CFRP rudder P/N and S/N appears in Appendix A", "Appendix A row is not marked core density 24 kg/m3"]),
    ]

    def simple_limit(raw: str, quantity: float | None, unit: str, evs: list[str], ref: str, *, relation: str = "within") -> dict[str, Any]:
        return b.cmp(raw, evs, initial=[b.limit(relation, quantity, unit, raw, evs, reference_event=ref)])

    cmp1 = simple_limit("within 200 days from the effective date of this AD", 200, "calendar_day", [ev_p1a], "effective date of this AD")
    cmp2 = b.cmp("within 20 months from the effective date, then repeat two further times at intervals not exceeding 4 500 FC but not less than 4 000 FC", [ev_p1a], initial=[b.limit("within", 20, "calendar_month", "within 20 months", [ev_p1a], reference_event="effective date of this AD")], repetitive=[b.limit("not_to_exceed", 4500, "flight_cycle", "intervals not to exceed 4 500 FC", [ev_p1a], reference_event="last inspection"), b.limit("other", 4000, "flight_cycle", "not less than 4 000 FC", [ev_p1a], reference_event="last inspection")])
    cmp3 = b.cmp("within 200 days from the effective date, then repeat at intervals not exceeding 1 500 FC or 200 days, whichever occurs first", [ev_p1a], logic="conditional", initial=[b.limit("within", 200, "calendar_day", "within 200 days", [ev_p1a], reference_event="effective date of this AD")], repetitive=[b.limit("not_to_exceed", 1500, "flight_cycle", "intervals not exceeding 1 500 FC", [ev_p1a], reference_event="last inspection"), b.limit("not_to_exceed", 200, "calendar_day", "200 days", [ev_p1a], reference_event="last inspection")])
    cmp4 = simple_limit("within 20 months from the effective date of this AD", 20, "calendar_month", [ev_p1a], "effective date of this AD")
    cmp5 = simple_limit("before next flight after findings", None, "before_next_flight", [ev_p1a], "inspection finding", relation="before")
    cmp6 = simple_limit("within 10 days after each inspection", 10, "calendar_day", [ev_p1a, ev_p1b], "each paragraph (1.1), (1.2) or (1.3) inspection")
    cmp7 = simple_limit("within 200 days from the Reference Date", 200, "calendar_day", [ev_p2a], "Reference Date")
    cmp8 = b.cmp("within 20 months from the Reference Date, then repeat two further times at intervals not exceeding 4 500 FC but not less than 4 000 FC", [ev_p2a], initial=[b.limit("within", 20, "calendar_month", "within 20 months", [ev_p2a], reference_event="Reference Date")], repetitive=[b.limit("not_to_exceed", 4500, "flight_cycle", "intervals not to exceed 4 500 FC", [ev_p2a], reference_event="last inspection"), b.limit("other", 4000, "flight_cycle", "not less than 4 000 FC", [ev_p2a], reference_event="last inspection")])
    cmp9 = b.cmp("within 200 days from the Reference Date, then repeat at intervals not exceeding 1 500 FC or 200 days, whichever occurs first", [ev_p2a], logic="conditional", initial=[b.limit("within", 200, "calendar_day", "within 200 days", [ev_p2a], reference_event="Reference Date")], repetitive=[b.limit("not_to_exceed", 1500, "flight_cycle", "intervals not exceeding 1 500 FC", [ev_p2a], reference_event="last inspection"), b.limit("not_to_exceed", 200, "calendar_day", "200 days", [ev_p2a], reference_event="last inspection")])
    cmp10 = simple_limit("within 20 months from the Reference Date", 20, "calendar_month", [ev_p2a, ev_p2b], "Reference Date")
    cmp11 = simple_limit("before next flight after findings", None, "before_next_flight", [ev_p2a, ev_p2b], "inspection finding", relation="before")
    cmp12 = simple_limit("within 10 days after each inspection", 10, "calendar_day", [ev_p2a, ev_p2b], "each paragraph (2.1), (2.2) or (2.3) inspection")
    cmp13 = b.cmp("After the effective date, do not install an Appendix A rudder unless it complies with this AD", [ev_p4], logic="conditional", conditions=["Rudder is listed in Appendix A", "Installation permitted only when AD requirements are met"], initial=[b.limit("from", None, "calendar_date", "After the effective date of this AD", [ev_p4], calendar_date="2009-07-16", reference_event="effective date of this AD")])

    requirements = [
        req("REQ-001", "(1.1)", ["APP-001"], ["inspection"], "mandatory", "Perform a Vacuum Loss inspection of the rudder reinforced area.", [ev_p1a], objects=["Rudder reinforced area"], conditions=["24 kg/m3 Appendix A rudder", "Unless already accomplished"], pubs=["PUB-001"], cmps=[cmp1]),
        req("REQ-002", "(1.2.1)-(1.2.2)", ["APP-001"], ["inspection"], "mandatory", "Perform and repeat the Elasticity Laminate Checker inspection of the rudder trailing-edge area.", [ev_p1a], objects=["Rudder trailing-edge area"], conditions=["24 kg/m3 Appendix A rudder", "Repeat exactly two further times"], pubs=["PUB-001"], cmps=[cmp2]),
        req("REQ-003", "(1.3.1)-(1.3.2)", ["APP-001"], ["inspection"], "mandatory", "Perform and repeat the Elasticity Laminate Checker inspection of the splice, lower rib, upper edge, leading edge and other specified areas.", [ev_p1a], objects=["Rudder splice, lower rib, upper edge, leading edge and other locations"], conditions=["24 kg/m3 Appendix A rudder"], pubs=["PUB-001"], cmps=[cmp3], follows=["REQ-004"]),
        req("REQ-004", "(1.3.3)-(1.3.4)", ["APP-001"], ["inspection"], "mandatory", "Perform a Vacuum Loss inspection of the specified other rudder areas.", [ev_p1a], objects=["Rudder lower rib, upper edge, leading edge and other locations"], conditions=["24 kg/m3 Appendix A rudder"], pubs=["PUB-001"], cmps=[cmp4], terminating=term_yes("Paragraph (1.3.3) Vacuum Loss inspection cancels the initial and repetitive paragraph (1.3.1)-(1.3.2) inspections.", ["REQ-003"], [ev_p1a])),
        req("REQ-005", "(1.4)", ["APP-001"], ["contact_manufacturer", "repair"], "conditional", "If an inspection finds a defect, contact Airbus and apply its approved instructions and corrective actions before next flight.", [ev_p1a], objects=["Rudder inspection finding"], conditions=["Finding during paragraph (1.1), (1.2) or (1.3) inspection"], cmps=[cmp5]),
        req("REQ-006", "(1.5)", ["APP-001"], ["reporting"], "mandatory", "Report every paragraph (1) inspection result, including no findings, to Airbus.", [ev_p1a, ev_p1b], objects=["Inspection results"], cmps=[cmp6]),
        req("REQ-007", "(2.1)", ["APP-002"], ["inspection"], "mandatory", "Perform a Vacuum Loss inspection of the rudder reinforced area.", [ev_p2a], objects=["Rudder reinforced area"], conditions=["Appendix A rudder not having 24 kg/m3 core density"], pubs=["PUB-001"], cmps=[cmp7]),
        req("REQ-008", "(2.2.1)-(2.2.2)", ["APP-002"], ["inspection"], "mandatory", "Perform and repeat the Elasticity Laminate Checker inspection of the rudder trailing-edge area.", [ev_p2a], objects=["Rudder trailing-edge area"], conditions=["Appendix A rudder not having 24 kg/m3 core density", "Repeat exactly two further times"], pubs=["PUB-001"], cmps=[cmp8]),
        req("REQ-009", "(2.3.1)-(2.3.2)", ["APP-002"], ["inspection"], "mandatory", "Perform and repeat the Elasticity Laminate Checker inspection of the splice, lower rib, upper edge, leading edge and other specified areas.", [ev_p2a], objects=["Rudder splice, lower rib, upper edge, leading edge and other locations"], conditions=["Appendix A rudder not having 24 kg/m3 core density"], pubs=["PUB-001"], cmps=[cmp9], follows=["REQ-010"]),
        req("REQ-010", "(2.3.3)-(2.3.4)", ["APP-002"], ["inspection"], "mandatory", "Perform a Vacuum Loss inspection of the specified other rudder areas.", [ev_p2a, ev_p2b], objects=["Rudder lower rib, upper edge, leading edge and other locations"], conditions=["Appendix A rudder not having 24 kg/m3 core density"], pubs=["PUB-001"], cmps=[cmp10], terminating=term_yes("Paragraph (2.3.3) Vacuum Loss inspection cancels the initial and repetitive paragraph (2.3.1)-(2.3.2) inspections.", ["REQ-009"], [ev_p2a, ev_p2b])),
        req("REQ-011", "(2.4)", ["APP-002"], ["contact_manufacturer", "repair"], "conditional", "If an inspection finds a defect, contact Airbus and apply its approved instructions and corrective actions before next flight.", [ev_p2a, ev_p2b], objects=["Rudder inspection finding"], conditions=["Finding during paragraph (2.1), (2.2) or (2.3) inspection"], cmps=[cmp11]),
        req("REQ-012", "(2.5)", ["APP-002"], ["reporting"], "mandatory", "Report every paragraph (2) inspection result, including no findings, to Airbus.", [ev_p2a, ev_p2b], objects=["Inspection results"], cmps=[cmp12]),
        req("REQ-013", "(4)", ["APP-001", "APP-002"], ["prohibition", "install"], "prohibited", "Do not install an Appendix A rudder unless it complies with this AD.", [ev_p4, *table_evs], objects=["Appendix A rudder"], conditions=["Installation after the effective date"], cmps=[cmp13]),
    ]
    credits = [{"credit_id": "CRD-001", "text": "A rudder that passed a pre-effective-date inspection under AOT A320-55A1038 original issue or TD/K4/S2/27051/2009 issue B receives credit for the inspected areas; additional areas and all repetitive inspections remain required.", "applies_to_requirement_ids": ["REQ-001", "REQ-002", "REQ-003", "REQ-004", "REQ-007", "REQ-008", "REQ-009", "REQ-010"], "credited_publication_ids": ["PUB-002", "PUB-003"], "conditions": ["Inspection passed before the effective date", "Credit limited to areas inspected", "Additional areas and repetitive inspections remain applicable"], "evidence_ids": [ev_p3]}]
    pubs = [pub("PUB-001", "all_operators_telex", "Airbus", "A320-55A1038", "Revision 01", None, ["required_method"], [ev_p1a, ev_p2a, ev_pubs], later=True), pub("PUB-002", "all_operators_telex", "Airbus", "A320-55A1038", "Original issue", None, ["previous_action_credit"], [ev_p3, ev_pubs], later=True), pub("PUB-003", "other", "Airbus", "TD/K4/S2/27051/2009", "Issue B", None, ["previous_action_credit"], [ev_p3, ev_pubs], later=True, title="Sampling instruction Technical Disposition")]
    publication = common_publication(subject="Stabilizers – Rudder Side Shell Skin – Inspection", subject_raw="ATA 55 Stabilizers – Rudder Side Shell Skin – Inspection", subject_ev=ev_subject, issue_date="2009-07-02", issue_raw="Date: 02 July 2009", issue_ev=ev_cover, effective_date="2009-07-16", effective_raw="Effective Date: 16 July 2009", effective_ev=ev_effective, ata="55", ata_title="Stabilizers", manufacturer_raw="AIRBUS (formerly AIRBUS INDUSTRIE)", manufacturer_ev=ev_subject, type_designations=["A318", "A319", "A320", "A321"], tcds=["EASA.A.064"], foreign_ev=ev_cover)
    unsafe = {"state": "present", "raw_reason_text": norm("Surface defects were visually detected on rudders of one A319 and one A321. Investigation found production-rework areas with de-bonding between skin and honeycomb core. Extended de-bonding may degrade rudder structural integrity; loss of the rudder degrades handling qualities and reduces aeroplane controllability. Inspections and finding-dependent corrective actions are required."), "observed_events_or_defects": ["Surface defects on two in-service rudders", "Skin-to-honeycomb-core de-bonding in production-rework areas"], "causes": ["Production rework associated with de-bonding"], "unsafe_conditions": ["Extended rudder de-bonding and degraded rudder structural integrity"], "potential_consequences": ["Loss of the rudder", "Degraded handling qualities", "Reduced aeroplane controllability"], "affected_components": ["CFRP rudder side-shell skin and honeycomb core"], "intended_risk_mitigation": ["Vacuum Loss and Elasticity Laminate Checker inspections", "Corrective actions for findings", "Reporting and installation control"], "evidence_ids": [ev_reason]}
    definitions = [{"definition_id": "DEF-001", "term": "Reference Date", "definition_text": "The effective date of this AD or the date when the rudder will accumulate 20 000 FC from its first installation on an aeroplane, whichever occurs later.", "evidence_ids": [ev_p2a]}]
    action_types = ["inspection", "contact_manufacturer", "repair", "reporting", "prohibition", "install"]
    return b.finish(cover_ev=ev_cover, identity_evs=[ev_cover, ev_status], version_label="Original", lifecycle="superseded", holder_raw="Type Approval Holder’s Name: AIRBUS", holder_value="Airbus", supersedure=explicit_none("Supersedure: None", [ev_cover]), publication=publication, applicability=apps, definitions=definitions, unsafe_condition=unsafe, requirements=requirements, exceptions=[], credits=credits, publications=pubs, relationships=[], contacts=contacts(ev_remarks, ev_remarks, "For technical questions, contact AIRBUS – Airworthiness Office – EAS, fax +33 5 61 93 44 51, account.airworth-eas@airbus.com."), classification={"airbus_families": ["A320 family"], "ata_chapters": ["55"], "action_types": action_types, "frequency": "mixed", "emergency_status": "standard", "terminating_action_present": True, "table_or_appendix_present": True, "compliance_complexity": "mixed", "human_confirmed": False, "evidence_ids": [ev_subject, ev_app, ev_p1a, ev_p1b, ev_p2a, ev_p2b, ev_p3, ev_p4, *table_evs]}, quality_flags=["complex_table", "complex_applicability", "complex_compliance", "cross_page_clause", "visual_transcription_used"], hybrid_source=True)


def build_2010() -> dict[str, Any]:
    b = Builder("2010-0164")
    ev_cover = b.ev(1, "cover", "AD No.: 2010-0164. Date: 05 August 2010. Type Approval Holder’s Name: AIRBUS. Type/Model designation(s): A318, A319, A320 and A321 aeroplanes. TCDS Number: EASA.A.064. Foreign AD: Not applicable. Supersedure: This AD supersedes EASA AD 2009-0141 dated 02 July 2009.", section_raw="Cover identity", method="visual_transcription", quality="visual_transcription", note="Visually transcribed from the rendered legacy two-column cover because native extraction interleaves identity labels and values.")
    ev_subject = b.ev(1, "cover", "ATA 55 Stabilizers – Rudder Side Shell Skin – Inspection. Manufacturer(s): Airbus (formerly Airbus Industrie).", section_raw="ATA / Manufacturer(s)")
    ev_app = b.ev(1, "applicability", source_excerpt(b, 1, "          Applicability:", "          Reason:"), section_raw="Applicability")
    ev_reason1 = b.ev(1, "reason", source_excerpt(b, 1, "          Reason:"), section_raw="Reason", note="Exact native text from the Reason heading through the page boundary; the final list continues on page 2.")
    ev_req2 = b.ev(2, "required_actions_and_compliance_times", b.page_quote(2), section_raw="Reason continuation / Effective Date / Required actions", clause="(1), page 1 of 2", note="Full page retained because the legacy layout combines the Reason continuation, effective date and the beginning of paragraph (1).")
    ev_req3 = b.ev(3, "required_actions_and_compliance_times", b.page_quote(3), section_raw="Required actions", clause="(1) continuation / (2), page 1 of 2")
    ev_req4 = b.ev(4, "required_actions_and_compliance_times", b.page_quote(4), section_raw="Required actions", clause="(2) continuation / (3)-(6)")
    ev_req5 = b.ev(5, "required_actions_and_compliance_times", b.page_quote(5), section_raw="Required actions", clause="(6)")
    ev_req6 = b.ev(6, "required_actions_and_compliance_times", b.page_quote(6), section_raw="Required actions", clause="(7) / (8), page 1 of 2")
    ev_req7 = b.ev(7, "required_actions_and_compliance_times", b.page_quote(7), section_raw="Required actions", clause="(8) continuation / (9), page 1 of 2")
    ev_req8 = b.ev(8, "required_actions_and_compliance_times", b.page_quote(8), section_raw="Required actions / Ref. Publications / Remarks", clause="(9) continuation / (10)")
    ev_effective = b.ev(2, "cover", "Effective Date: 19 August 2010", section_raw="Effective Date", method="visual_transcription", quality="visual_transcription", note="Visually read from the rendered legacy compliance header because native extraction separates the two-column label and value.")
    ev_pubs = b.ev(8, "reference_publications", source_excerpt(b, 8, "         Ref. Publications:", "         Remarks:"), section_raw="Ref. Publications")
    ev_remarks = b.ev(8, "remarks", source_excerpt(b, 8, "         Remarks:"), section_raw="Remarks")
    ev_tab9 = b.table_ev(9, "Appendix A – Affected rudders (page 1 of 4)", ["Rudder P/N", "Affected rudder S/N", "Core density of 24 kg/m3"], note="Full appendix page retained for row-level review.")
    ev_tab10 = b.table_ev(10, "Appendix A – Affected rudders (page 2 of 4)", ["Rudder P/N", "Affected rudder S/N", "Core density of 24 kg/m3"], note="Full appendix page retained for row-level review.")
    ev_tab11 = b.table_ev(11, "Appendix A – Affected rudders (page 3 of 4)", ["Rudder P/N", "Affected rudder S/N", "Core density of 24 kg/m3"], note="Full appendix page retained for row-level review.")
    ev_tab12 = b.table_ev(12, "Appendix A – Affected rudders (page 4 of 4)", ["Rudder P/N", "Affected rudder S/N", "Core density of 24 kg/m3"], note="Full appendix page retained for row-level review.")
    ev_tab13 = b.table_ev(13, "Appendices B and C – Affected rudders", ["Appendix", "Rudder P/N", "Affected rudder S/N", "Core density of 24 kg/m3"], note="Full page retained; Appendix B and both core-density branches of Appendix C are separated structurally in applicability groups.")
    ev_tab14 = b.table_ev(14, "Appendix D – Affected P/N and associated S/N (page 1 of 3)", ["Affected Rudder P/N", "Associated S/N"], note="Full appendix page retained for row-level review.")
    ev_tab15 = b.table_ev(15, "Appendix D – Associated S/N (page 2 of 3)", ["Associated S/N"], note="Full appendix page retained for row-level review.")
    ev_tab16 = b.table_ev(16, "Appendix D – Associated S/N (page 3 of 3)", ["Associated S/N"], note="Full appendix page retained for row-level review.")
    ev_tab17 = b.table_ev(17, "Appendix E – Affected P/N and associated S/N", ["Affected Rudder P/N", "Associated S/N"], note="Full appendix page retained for row-level review.")

    rows_a = parse_rudder_rows("\n".join(b.page_text(page) for page in range(9, 13)))
    text13 = b.page_text(13)
    split_b = text13.index("Appendix B")
    split_c = text13.index("Appendix C", split_b)
    rows_b = parse_rudder_rows(text13[split_b:split_c])
    rows_c = parse_rudder_rows(text13[split_c:])
    rows_a24, rows_a_other = [r for r in rows_a if r[2]], [r for r in rows_a if not r[2]]
    rows_c24, rows_c_other = [r for r in rows_c if r[2]], [r for r in rows_c if not r[2]]
    text_d = "\n".join(b.page_text(page) for page in range(14, 17))
    text_e = b.page_text(17)
    pns_d = sorted(set(re.findall(r"\bD554[0-9]{10}\b", b.page_text(14))))
    pns_e = sorted(set(re.findall(r"\bD554[0-9]{10}\b", text_e)))
    sns_d = sorted(set(re.findall(r"\bTS-[0-9]+\b", text_d)))
    sns_e = sorted(set(re.findall(r"\bTS-[0-9]+\b", text_e)))
    evs_a = [ev_tab9, ev_tab10, ev_tab11, ev_tab12]
    models = A320_MODELS_WITH_111
    app_text = "Applicable A318/A319/A320/A321 models, all manufacturer serial numbers, when equipped with a rudder P/N and S/N listed in the specified appendix."

    def rudder_app(aid: str, serial_base: int, label: str, appendix: str, rows: list[tuple[str, str, bool]], evs: list[str], condition: str) -> dict[str, Any]:
        return app(aid, label, f"{app_text} {appendix}; {condition}.", ["A320 family"], models, [all_serials(f"MSN-{serial_base:03d}", "all manufacturer serial numbers", [ev_app]), listed_serials(f"MSN-{serial_base + 1:03d}", f"affected rudder S/N listed in {appendix}", sorted({sn for _, sn, _ in rows}), evs, condition="Installed rudder serial number")], [ev_app, *evs], part_numbers=sorted({pn for pn, _, _ in rows}), conditions=[f"Rudder P/N and S/N listed in {appendix}", condition])

    apps = [
        rudder_app("APP-001", 1, "Appendix A rudders with 24 kg/m3 core", "Appendix A", rows_a24, evs_a, "row marked core density 24 kg/m3"),
        rudder_app("APP-002", 3, "Appendix A rudders not having 24 kg/m3 core", "Appendix A", rows_a_other, evs_a, "row not marked core density 24 kg/m3"),
        rudder_app("APP-003", 5, "Appendix B rudders", "Appendix B", rows_b, [ev_tab13], "Appendix B population"),
        rudder_app("APP-004", 7, "Appendix C rudders with 24 kg/m3 core", "Appendix C", rows_c24, [ev_tab13], "row marked core density 24 kg/m3"),
        rudder_app("APP-005", 9, "Appendix C rudders not having 24 kg/m3 core", "Appendix C", rows_c_other, [ev_tab13], "row not marked core density 24 kg/m3"),
        app("APP-006", "Appendix D rudders", f"{app_text} Appendix D.", ["A320 family"], models, [all_serials("MSN-011", "all manufacturer serial numbers", [ev_app]), listed_serials("MSN-012", "associated rudder S/N listed in Appendix D", sns_d, [ev_tab14, ev_tab15, ev_tab16], condition="Installed rudder serial number")], [ev_app, ev_tab14, ev_tab15, ev_tab16], part_numbers=pns_d, conditions=["Rudder P/N and associated S/N listed in Appendix D"]),
        app("APP-007", "Appendix E rudders", f"{app_text} Appendix E.", ["A320 family"], models, [all_serials("MSN-013", "all manufacturer serial numbers", [ev_app]), listed_serials("MSN-014", "associated rudder S/N listed in Appendix E", sns_e, [ev_tab17], condition="Installed rudder serial number")], [ev_app, ev_tab17], part_numbers=pns_e, conditions=["Rudder P/N and associated S/N listed in Appendix E"]),
    ]

    def limcmp(raw: str, q: float | None, unit: str, evs: list[str], ref: str, relation: str = "within", conditions: list[str] | None = None) -> dict[str, Any]:
        return b.cmp(raw, evs, logic="conditional" if conditions else "single", conditions=conditions, initial=[b.limit(relation, q, unit, raw, evs, reference_event=ref)])

    def repeat_range(raw: str, evs: list[str], initial_q: float, initial_unit: str, initial_ref: str) -> dict[str, Any]:
        return b.cmp(raw, evs, initial=[b.limit("within", initial_q, initial_unit, f"within {initial_q:g} {initial_unit}", evs, reference_event=initial_ref)], repetitive=[b.limit("not_to_exceed", 4500, "flight_cycle", "not to exceed 4 500 FC", evs, reference_event="last inspection"), b.limit("other", 4000, "flight_cycle", "not less than 4 000 FC", evs, reference_event="last inspection")])

    cmp1 = limcmp("within 200 days from 16 July 2009", 200, "calendar_day", [ev_req2], "16 July 2009")
    cmp2 = repeat_range("within 20 months from 16 July 2009; repeat two further times at 4 000 to 4 500 FC", [ev_req2], 20, "calendar_month", "16 July 2009")
    cmp3 = b.cmp("within 200 days from 16 July 2009; repeat at intervals not exceeding 1 500 FC or 200 days, whichever occurs first", [ev_req2], logic="conditional", initial=[b.limit("within", 200, "calendar_day", "within 200 days", [ev_req2], reference_event="16 July 2009")], repetitive=[b.limit("not_to_exceed", 1500, "flight_cycle", "not exceeding 1 500 FC", [ev_req2], reference_event="last inspection"), b.limit("not_to_exceed", 200, "calendar_day", "200 days", [ev_req2], reference_event="last inspection")])
    cmp4 = limcmp("within 20 months from 16 July 2009", 20, "calendar_month", [ev_req2], "16 July 2009")
    cmp5 = limcmp("before next flight", None, "before_next_flight", [ev_req3], "inspection finding", "before", ["Finding during a paragraph (1) inspection"])
    cmp6 = limcmp("before next flight", None, "before_next_flight", [ev_req3], "no-finding Vacuum Loss inspection", "before", ["No findings during paragraph (1.1) or (1.3.3) inspection"])
    cmp7 = limcmp("within 10 days after each paragraph (1) inspection", 10, "calendar_day", [ev_req3], "each applicable inspection")
    cmp8 = limcmp("within 200 days from the paragraph (2) Reference Date", 200, "calendar_day", [ev_req3], "paragraph (2) Reference Date")
    cmp9 = repeat_range("within 20 months from the paragraph (2) Reference Date; repeat two further times at 4 000 to 4 500 FC", [ev_req3], 20, "calendar_month", "paragraph (2) Reference Date")
    cmp10 = b.cmp("within 200 days from the paragraph (2) Reference Date; repeat at intervals not exceeding 1 500 FC or 200 days, whichever occurs first", [ev_req3], logic="conditional", initial=[b.limit("within", 200, "calendar_day", "within 200 days", [ev_req3], reference_event="paragraph (2) Reference Date")], repetitive=[b.limit("not_to_exceed", 1500, "flight_cycle", "not exceeding 1 500 FC", [ev_req3], reference_event="last inspection"), b.limit("not_to_exceed", 200, "calendar_day", "200 days", [ev_req3], reference_event="last inspection")])
    cmp11 = limcmp("within 20 months from the paragraph (2) Reference Date", 20, "calendar_month", [ev_req3, ev_req4], "paragraph (2) Reference Date")
    cmp12 = limcmp("before next flight", None, "before_next_flight", [ev_req4], "inspection finding", "before", ["Finding during a paragraph (2) inspection"])
    cmp13 = limcmp("before next flight", None, "before_next_flight", [ev_req4], "no-finding Vacuum Loss inspection", "before", ["No findings during paragraph (2.1) or (2.3.3) inspection"])
    cmp14 = limcmp("within 10 days after each paragraph (2) inspection", 10, "calendar_day", [ev_req4], "each applicable inspection")
    cmp15 = limcmp("within 4 500 FC from the restoration date", 4500, "flight_cycle", [ev_req4], "temporary-resin or permanent restoration date", conditions=["Applicable restoration performed before the effective date in the reinforced area"])
    cmp16 = b.cmp("within 20 months from the effective date or 200 days from the paragraph (6) Reference Date, whichever occurs first", [ev_req5], logic="whichever_occurs_first", initial=[b.limit("within", 20, "calendar_month", "within 20 months", [ev_req5], reference_event="effective date of this AD"), b.limit("within", 200, "calendar_day", "within 200 days", [ev_req5], reference_event="paragraph (6) Reference Date")])
    cmp17 = limcmp("within 10 days after paragraph (6.1) inspections", 10, "calendar_day", [ev_req5], "paragraph (6.1) inspections")
    cmp18 = b.cmp("within 1 500 FC or 200 days after paragraph (6.1), whichever occurs first; if no findings, repeat trailing-edge inspection twice at 4 000 to 4 500 FC", [ev_req5], logic="whichever_occurs_first", initial=[b.limit("within", 1500, "flight_cycle", "within 1 500 FC", [ev_req5], reference_event="paragraph (6.1) inspection"), b.limit("within", 200, "calendar_day", "within 200 days", [ev_req5], reference_event="paragraph (6.1) inspection")], repetitive=[b.limit("not_to_exceed", 4500, "flight_cycle", "not to exceed 4 500 FC", [ev_req5], reference_event="last trailing-edge inspection"), b.limit("other", 4000, "flight_cycle", "not less than 4 000 FC", [ev_req5], reference_event="last trailing-edge inspection")])
    cmp19 = b.cmp("within 1 500 FC or 200 days after paragraph (6.1), whichever occurs first", [ev_req5], logic="whichever_occurs_first", initial=[b.limit("within", 1500, "flight_cycle", "within 1 500 FC", [ev_req5], reference_event="paragraph (6.1) inspection"), b.limit("within", 200, "calendar_day", "within 200 days", [ev_req5], reference_event="paragraph (6.1) inspection")])
    cmp20 = limcmp("before next flight", None, "before_next_flight", [ev_req5], "paragraph (6) inspection finding", "before", ["Finding during paragraph (6.1) or (6.3)"])
    cmp21 = limcmp("before next flight", None, "before_next_flight", [ev_req5], "no-finding vacuum-loss inspection", "before", ["No findings during paragraph (6.1) or (6.3.2)"])
    cmp22 = limcmp("within 10 days after each paragraph (6.1) or (6.3) inspection", 10, "calendar_day", [ev_req5], "each applicable inspection")
    cmp23 = limcmp("within 200 days from the effective date", 200, "calendar_day", [ev_req6], "effective date of this AD", conditions=["Appendix C rudder with 24 kg/m3 core"])
    cmp24 = b.cmp("within 20 months from the effective date or 200 days from the paragraph (7) Reference Date, whichever occurs first", [ev_req6], logic="whichever_occurs_first", conditions=["Appendix C rudder not having 24 kg/m3 core"], initial=[b.limit("within", 20, "calendar_month", "within 20 months", [ev_req6], reference_event="effective date of this AD"), b.limit("within", 200, "calendar_day", "200 days", [ev_req6], reference_event="paragraph (7) Reference Date")])
    cmp25 = b.cmp("whichever occurs later: before 17 000 FC since first installation without exceeding 20 months from the effective date, or within 200 days after the effective date", [ev_req6], logic="conditional", conditions=["Appendix D rudder"], initial=[b.limit("before", 17000, "flight_cycle", "before 17 000 FC", [ev_req6], reference_event="rudder first installation"), b.limit("within", 20, "calendar_month", "without exceeding 20 months", [ev_req6], reference_event="effective date of this AD"), b.limit("within", 200, "calendar_day", "within 200 days", [ev_req6], reference_event="effective date of this AD")])
    cmp26 = repeat_range("within 20 months after the effective date; repeat two further times at 4 000 to 4 500 FC", [ev_req6], 20, "calendar_month", "effective date of this AD")
    cmp27 = b.cmp("initial limit as in paragraph (8.3.1), then repeat at intervals not exceeding 1 500 FC or 200 days, whichever occurs first", [ev_req6, ev_req7], logic="conditional", initial=[b.limit("other", None, "other", "paragraph (8.3.1.1)/(8.3.1.2) whichever-later threshold", [ev_req6], reference_event="rudder first installation and effective date")], repetitive=[b.limit("not_to_exceed", 1500, "flight_cycle", "not exceeding 1 500 FC", [ev_req7], reference_event="last inspection"), b.limit("not_to_exceed", 200, "calendar_day", "200 days", [ev_req7], reference_event="last inspection")])
    cmp28 = limcmp("within 20 months after the effective date", 20, "calendar_month", [ev_req7], "effective date of this AD")
    cmp29 = limcmp("before next flight", None, "before_next_flight", [ev_req7], "paragraph (8) inspection finding", "before", ["Finding during paragraph (8.1), (8.2) or (8.3)"])
    cmp30 = limcmp("before next flight", None, "before_next_flight", [ev_req7], "no-finding vacuum-loss inspection", "before", ["No findings during paragraph (8.1) or (8.3.3)"])
    cmp31 = limcmp("within 10 days after each paragraph (8) inspection", 10, "calendar_day", [ev_req7], "each applicable inspection")
    cmp32 = b.cmp("within 4 500 FC but not less than 4 000 FC from the sampling inspection; repeat once at the same range", [ev_req8], initial=[b.limit("within", 4500, "flight_cycle", "within 4 500 FC", [ev_req8], reference_event="sampling inspection"), b.limit("other", 4000, "flight_cycle", "not less than 4 000 FC", [ev_req8], reference_event="sampling inspection")], repetitive=[b.limit("not_to_exceed", 4500, "flight_cycle", "not to exceed 4 500 FC", [ev_req8], reference_event="last inspection"), b.limit("other", 4000, "flight_cycle", "not less than 4 000 FC", [ev_req8], reference_event="last inspection")])
    cmp33 = limcmp("before next flight", None, "before_next_flight", [ev_req8], "paragraph (9) inspection finding", "before", ["Finding during paragraph (9.1) or (9.2)"])
    cmp34 = limcmp("within 10 days after each paragraph (9) inspection", 10, "calendar_day", [ev_req8], "each applicable inspection")
    cmp35 = b.cmp("After the effective date, do not install an Appendix A, B, C, D or E rudder unless it complies with this AD", [ev_req8], logic="conditional", conditions=["Rudder listed in Appendix A, B, C, D or E", "Installation permitted only when AD requirements are met"], initial=[b.limit("from", None, "calendar_date", "After the effective date of this AD", [ev_req8], calendar_date="2010-08-19", reference_event="effective date of this AD")])

    # Requirements intentionally mirror each independently mandated inspection,
    # restoration, corrective, reporting, replacement, and installation action.
    requirements = [
        req("REQ-001", "(1.1)", ["APP-001"], ["inspection"], "mandatory", "Vacuum Loss inspect the reinforced area.", [ev_req2], objects=["Rudder reinforced area"], pubs=["PUB-001"], cmps=[cmp1]),
        req("REQ-002", "(1.2)", ["APP-001"], ["inspection"], "mandatory", "Elasticity Laminate Checker inspect and repeat the trailing-edge inspection twice.", [ev_req2], objects=["Rudder trailing edge"], pubs=["PUB-001"], cmps=[cmp2]),
        req("REQ-003", "(1.3.1)-(1.3.2)", ["APP-001"], ["inspection"], "mandatory", "Elasticity Laminate Checker inspect and repeat the specified other rudder areas.", [ev_req2], objects=["Splice, lower rib, upper edge, leading edge and other locations"], pubs=["PUB-001"], cmps=[cmp3], follows=["REQ-004"]),
        req("REQ-004", "(1.3.3)-(1.3.4)", ["APP-001"], ["inspection"], "mandatory", "Vacuum Loss inspect the specified other rudder areas.", [ev_req2], objects=["Lower rib, upper edge, leading edge and other locations"], pubs=["PUB-001"], cmps=[cmp4], terminating=term_yes("Paragraph (1.3.3) cancels the paragraph (1.3.1)-(1.3.2) inspections.", ["REQ-003"], [ev_req2])),
        req("REQ-005", "(1.4)", ["APP-001"], ["contact_manufacturer", "repair"], "conditional", "For a finding, contact Airbus and apply approved corrective instructions before next flight.", [ev_req3], conditions=["Finding during paragraph (1) inspection"], cmps=[cmp5]),
        req("REQ-006", "(1.5)", ["APP-001"], ["repair"], "conditional", "When no finding is detected, restore Vacuum Loss holes using an allowed temporary or permanent method and follow the associated instructions until permanent restoration.", [ev_req3], conditions=["No finding during paragraph (1.1) or (1.3.3)"], pubs=["PUB-001"], cmps=[cmp6]),
        req("REQ-007", "(1.6)", ["APP-001"], ["reporting"], "mandatory", "Report every paragraph (1) inspection result, including no findings, to Airbus.", [ev_req3], cmps=[cmp7]),
        req("REQ-008", "(2.1)", ["APP-002"], ["inspection"], "mandatory", "Vacuum Loss inspect the reinforced area.", [ev_req3], objects=["Rudder reinforced area"], pubs=["PUB-001"], cmps=[cmp8]),
        req("REQ-009", "(2.2)", ["APP-002"], ["inspection"], "mandatory", "Elasticity Laminate Checker inspect and repeat the trailing-edge inspection twice.", [ev_req3], objects=["Rudder trailing edge"], pubs=["PUB-001"], cmps=[cmp9]),
        req("REQ-010", "(2.3.1)-(2.3.2)", ["APP-002"], ["inspection"], "mandatory", "Elasticity Laminate Checker inspect and repeat the specified other rudder areas.", [ev_req3], objects=["Splice, lower rib, upper edge, leading edge and other locations"], pubs=["PUB-001"], cmps=[cmp10], follows=["REQ-011"]),
        req("REQ-011", "(2.3.3)-(2.3.4)", ["APP-002"], ["inspection"], "mandatory", "Vacuum Loss inspect the specified other rudder areas.", [ev_req3, ev_req4], objects=["Lower rib, upper edge, leading edge and other locations"], pubs=["PUB-001"], cmps=[cmp11], terminating=term_yes("Paragraph (2.3.3) cancels the paragraph (2.3.1)-(2.3.2) inspections.", ["REQ-010"], [ev_req3, ev_req4])),
        req("REQ-012", "(2.4)", ["APP-002"], ["contact_manufacturer", "repair"], "conditional", "For a finding, contact Airbus and apply approved corrective instructions before next flight.", [ev_req4], conditions=["Finding during paragraph (2) inspection"], cmps=[cmp12]),
        req("REQ-013", "(2.5)", ["APP-002"], ["repair"], "conditional", "When no finding is detected, restore Vacuum Loss holes using an allowed temporary or permanent method and follow instructions until permanent restoration.", [ev_req4], conditions=["No finding during paragraph (2.1) or (2.3.3)"], pubs=["PUB-001"], cmps=[cmp13]),
        req("REQ-014", "(2.6)", ["APP-002"], ["reporting"], "mandatory", "Report every paragraph (2) inspection result, including no findings, to Airbus.", [ev_req4], cmps=[cmp14]),
        req("REQ-015", "(5)", ["APP-001", "APP-002"], ["inspection"], "mandatory", "Ultrasonically inspect a reinforced area previously restored with resin or by permanent restoration.", [ev_req4], conditions=["Applicable restoration completed before the effective date"], pubs=["PUB-001"], cmps=[cmp15]),
        req("REQ-016", "(6.1)", ["APP-003"], ["inspection", "test_or_check"], "mandatory", "Perform the applicable X-Ray, Elasticity Laminate Checker, Vacuum Loss and/or thermography inspections.", [ev_req5], objects=["Appendix B rudder locations"], pubs=["PUB-004"], cmps=[cmp16], follows=["REQ-017", "REQ-018", "REQ-019"]),
        req("REQ-017", "(6.2)", ["APP-003"], ["reporting"], "mandatory", "Send developed X-Ray films and the film-layout arrangement to Airbus.", [ev_req5], conditions=["X-Ray inspection performed"], cmps=[cmp17], parent="REQ-016"),
        req("REQ-018", "(6.3.1)", ["APP-003"], ["inspection"], "mandatory", "Elasticity Laminate Checker inspect the trailing edge and, if no finding, repeat twice.", [ev_req5], objects=["Rudder trailing edge"], pubs=["PUB-004"], cmps=[cmp18], parent="REQ-016"),
        req("REQ-019", "(6.3.2)", ["APP-003"], ["inspection"], "mandatory", "Vacuum Loss inspect the specified other rudder areas.", [ev_req5], objects=["Lower rib, upper edge, leading edge and other locations"], pubs=["PUB-004"], cmps=[cmp19], parent="REQ-016"),
        req("REQ-020", "(6.4)", ["APP-003"], ["contact_manufacturer", "repair"], "conditional", "For a finding, contact Airbus and apply approved corrective instructions before next flight.", [ev_req5], conditions=["Finding during paragraph (6.1) or (6.3)"], cmps=[cmp20]),
        req("REQ-021", "(6.5)", ["APP-003"], ["repair"], "conditional", "When no finding is detected, restore Vacuum Loss holes and follow instructions until permanent restoration.", [ev_req5], conditions=["No finding during paragraph (6.1) or (6.3.2)"], pubs=["PUB-004"], cmps=[cmp21]),
        req("REQ-022", "(6.6)", ["APP-003"], ["reporting"], "mandatory", "Report every paragraph (6.1) and (6.3) inspection result, including no findings, to Airbus.", [ev_req5], cmps=[cmp22]),
        req("REQ-023", "(7.1)", ["APP-004"], ["replacement"], "mandatory", "Replace the Appendix C rudder with 24 kg/m3 core density.", [ev_req6], pubs=["PUB-004"], cmps=[cmp23]),
        req("REQ-024", "(7.2)", ["APP-005"], ["replacement"], "mandatory", "Replace the Appendix C rudder not having 24 kg/m3 core density.", [ev_req6], pubs=["PUB-004"], cmps=[cmp24]),
        req("REQ-025", "(8.1)", ["APP-006"], ["inspection"], "mandatory", "Vacuum Loss inspect the reinforced area of an Appendix D rudder.", [ev_req6], pubs=["PUB-005", "PUB-007", "PUB-009"], cmps=[cmp25]),
        req("REQ-026", "(8.2)", ["APP-006"], ["inspection"], "mandatory", "Elasticity Laminate Checker inspect and repeat the trailing-edge inspection twice.", [ev_req6], pubs=["PUB-005", "PUB-007", "PUB-009"], cmps=[cmp26]),
        req("REQ-027", "(8.3.1)-(8.3.2)", ["APP-006"], ["inspection"], "mandatory", "Elasticity Laminate Checker inspect and repeat the specified other rudder areas.", [ev_req6, ev_req7], pubs=["PUB-005", "PUB-007", "PUB-009"], cmps=[cmp27], follows=["REQ-028"]),
        req("REQ-028", "(8.3.3)-(8.3.4)", ["APP-006"], ["inspection"], "mandatory", "Vacuum Loss inspect the specified other rudder areas.", [ev_req7], pubs=["PUB-005", "PUB-007", "PUB-009"], cmps=[cmp28], terminating=term_yes("Paragraph (8.3.3) cancels paragraph (8.3.1)-(8.3.2) inspections.", ["REQ-027"], [ev_req7])),
        req("REQ-029", "(8.4)", ["APP-006"], ["contact_manufacturer", "repair"], "conditional", "For a finding, contact Airbus and apply approved corrective instructions before next flight.", [ev_req7], conditions=["Finding during paragraph (8.1), (8.2) or (8.3)"], cmps=[cmp29]),
        req("REQ-030", "(8.5)", ["APP-006"], ["repair"], "conditional", "When no finding is detected, restore Vacuum Loss holes and follow instructions until permanent restoration.", [ev_req7], conditions=["No finding during paragraph (8.1) or (8.3.3)"], pubs=["PUB-005", "PUB-007", "PUB-009"], cmps=[cmp30]),
        req("REQ-031", "(8.6)", ["APP-006"], ["reporting"], "mandatory", "Report every paragraph (8) inspection result, including no findings, to Airbus.", [ev_req7], cmps=[cmp31]),
        req("REQ-032", "(9.1)-(9.2)", ["APP-007"], ["inspection"], "mandatory", "Elasticity Laminate Checker inspect the trailing edge and repeat once.", [ev_req7, ev_req8], pubs=["PUB-005", "PUB-007", "PUB-009"], cmps=[cmp32]),
        req("REQ-033", "(9.3)", ["APP-007"], ["contact_manufacturer", "repair"], "conditional", "For a finding, contact Airbus and apply approved corrective instructions before next flight.", [ev_req8], conditions=["Finding during paragraph (9.1) or (9.2)"], cmps=[cmp33]),
        req("REQ-034", "(9.4)", ["APP-007"], ["reporting"], "mandatory", "Report every paragraph (9) inspection result, including no findings, to Airbus.", [ev_req8], cmps=[cmp34]),
        req("REQ-035", "(10)", ["APP-001", "APP-002", "APP-003", "APP-004", "APP-005", "APP-006", "APP-007"], ["prohibition", "install"], "prohibited", "Do not install a rudder listed in Appendix A, B, C, D or E unless it complies with this AD.", [ev_req8, ev_tab9, ev_tab10, ev_tab11, ev_tab12, ev_tab13, ev_tab14, ev_tab15, ev_tab16, ev_tab17], cmps=[cmp35]),
    ]

    credits = [
        {"credit_id": "CRD-001", "text": "Pre-16 July 2009 inspection under AOT A320-55A1038 original issue or TD/K4/S2/27051/2009 issue B credits inspected areas under paragraphs (1) or (2); additional areas and repetitive inspections remain required.", "applies_to_requirement_ids": ["REQ-001", "REQ-002", "REQ-003", "REQ-004", "REQ-008", "REQ-009", "REQ-010", "REQ-011"], "credited_publication_ids": ["PUB-002", "PUB-011"], "conditions": ["Inspection passed before 16 July 2009", "Credit limited to areas inspected"], "evidence_ids": [ev_req4]},
        {"credit_id": "CRD-002", "text": "Pre-effective-date inspection under AOT A320-55A1038 Revision 01 credits inspected areas under paragraphs (1) or (2); additional areas and repetitive inspections remain required.", "applies_to_requirement_ids": ["REQ-001", "REQ-002", "REQ-003", "REQ-004", "REQ-008", "REQ-009", "REQ-010", "REQ-011"], "credited_publication_ids": ["PUB-003"], "conditions": ["Inspection passed before the current AD effective date", "Credit limited to areas inspected"], "evidence_ids": [ev_req4]},
        {"credit_id": "CRD-003", "text": "Pre-effective-date inspection/restoration under original issue SB A320-55-1035, -1036 or -1037 credits the inspected Appendix D area; repetitive inspections remain required.", "applies_to_requirement_ids": ["REQ-025", "REQ-026", "REQ-027", "REQ-028"], "credited_publication_ids": ["PUB-006", "PUB-008", "PUB-010"], "conditions": ["Accomplished before the effective date", "Credit limited to inspected area"], "evidence_ids": [ev_req7]},
        {"credit_id": "CRD-004", "text": "Pre-effective-date inspection/restoration under original issue SB A320-55-1035, -1036 or -1037 credits the inspected Appendix E area; repetitive inspections remain required.", "applies_to_requirement_ids": ["REQ-032"], "credited_publication_ids": ["PUB-006", "PUB-008", "PUB-010"], "conditions": ["Accomplished before the effective date", "Credit limited to inspected area"], "evidence_ids": [ev_req8]},
    ]
    pubs = [
        pub("PUB-001", "all_operators_telex", "Airbus", "A320-55A1038", "Revision 02", None, ["required_method"], [ev_req2, ev_req3, ev_req4, ev_pubs], later=True),
        pub("PUB-002", "all_operators_telex", "Airbus", "A320-55A1038", "Original issue", None, ["previous_action_credit"], [ev_req4], later=True),
        pub("PUB-003", "all_operators_telex", "Airbus", "A320-55A1038", "Revision 01", None, ["previous_action_credit"], [ev_req4], later=True),
        pub("PUB-004", "all_operators_telex", "Airbus", "A320-55A1039", "Original issue", None, ["required_method"], [ev_req5, ev_req6, ev_pubs], later=True),
        pub("PUB-005", "service_bulletin", "Airbus", "A320-55-1035", "Revision 01", None, ["required_method"], [ev_req6, ev_req7, ev_req8], later=True),
        pub("PUB-006", "service_bulletin", "Airbus", "A320-55-1035", "Original issue", None, ["previous_action_credit"], [ev_req7, ev_req8, ev_pubs], later=True),
        pub("PUB-007", "service_bulletin", "Airbus", "A320-55-1036", "Revision 01", None, ["required_method"], [ev_req6, ev_req7, ev_req8], later=True),
        pub("PUB-008", "service_bulletin", "Airbus", "A320-55-1036", "Original issue", None, ["previous_action_credit"], [ev_req7, ev_req8, ev_pubs], later=True),
        pub("PUB-009", "service_bulletin", "Airbus", "A320-55-1037", "Revision 01", None, ["required_method"], [ev_req6, ev_req7, ev_req8], later=True),
        pub("PUB-010", "service_bulletin", "Airbus", "A320-55-1037", "Original issue", None, ["previous_action_credit"], [ev_req7, ev_req8, ev_pubs], later=True),
        pub("PUB-011", "other", "Airbus", "TD/K4/S2/27051/2009", "Issue B", None, ["previous_action_credit"], [ev_req4, ev_pubs], later=True, title="Sampling instruction Technical Disposition"),
    ]
    publication = common_publication(subject="Stabilizers – Rudder Side Shell Skin – Inspection", subject_raw="ATA 55 Stabilizers – Rudder Side Shell Skin – Inspection", subject_ev=ev_subject, issue_date="2010-08-05", issue_raw="Date: 05 August 2010", issue_ev=ev_cover, effective_date="2010-08-19", effective_raw="Effective Date: 19 August 2010", effective_ev=ev_effective, ata="55", ata_title="Stabilizers", manufacturer_raw="Airbus (formerly Airbus Industrie)", manufacturer_ev=ev_subject, type_designations=["A318", "A319", "A320", "A321"], tcds=["EASA.A.064"], foreign_ev=ev_cover)
    unsafe = {"state": "present", "raw_reason_text": norm("Surface defects on two in-service rudders were linked to production-rework de-bonding between skin and honeycomb core. Extended de-bonding may degrade rudder structural integrity; rudder loss degrades handling and controllability. This AD retains AD 2009-0141 requirements, changes reinforced-area inspection methods, adds work after prior thermography, and addresses additional AOT/SB rudder populations."), "observed_events_or_defects": ["Surface defects and skin-to-core de-bonding in production-rework areas"], "causes": ["Production rework associated with de-bonding"], "unsafe_conditions": ["Extended rudder de-bonding and degraded structural integrity"], "potential_consequences": ["Loss of rudder", "Degraded handling qualities", "Reduced aeroplane controllability"], "affected_components": ["CFRP rudder side-shell skin and honeycomb core"], "intended_risk_mitigation": ["Multiple inspection methods by appendix population", "Rudder replacement for Appendix C", "Corrective/restoration actions", "Reporting and installation control"], "evidence_ids": [ev_reason1, ev_req2]}
    definitions = [
        {"definition_id": "DEF-001", "term": "Reference Date for paragraph (2)", "definition_text": "16 July 2009 or the date when the rudder will accumulate 20 000 FC from first installation, whichever occurs later.", "evidence_ids": [ev_req3]},
        {"definition_id": "DEF-002", "term": "Reference Date for paragraphs (6) and (7)", "definition_text": "The effective date of this AD or the date when the rudder will accumulate 20 000 FC from first installation, whichever occurs later.", "evidence_ids": [ev_req5, ev_req6]},
    ]
    relationship = rel("REL-001", "supersedes", "2009-0141", "structured_supersedure_field", "This AD supersedes EASA AD 2009-0141 dated 02 July 2009.", [ev_cover])
    action_types = ["inspection", "test_or_check", "contact_manufacturer", "repair", "reporting", "replacement", "prohibition", "install"]
    all_table_evs = [ev_tab9, ev_tab10, ev_tab11, ev_tab12, ev_tab13, ev_tab14, ev_tab15, ev_tab16, ev_tab17]
    return b.finish(cover_ev=ev_cover, identity_evs=[ev_cover], version_label="Original", lifecycle="unknown", holder_raw="Type Approval Holder’s Name: AIRBUS", holder_value="Airbus", supersedure=grounded_text("Supersedes EASA AD 2009-0141 dated 02 July 2009", "Supersedure: This AD supersedes EASA AD 2009-0141 dated 02 July 2009.", [ev_cover]), publication=publication, applicability=apps, definitions=definitions, unsafe_condition=unsafe, requirements=requirements, exceptions=[], credits=credits, publications=pubs, relationships=[relationship], contacts=contacts(ev_remarks, ev_remarks, "For technical questions, contact AIRBUS – Airworthiness Office – EAS, fax +33 5 61 93 44 51, account.airworth-eas@airbus.com."), classification={"airbus_families": ["A320 family"], "ata_chapters": ["55"], "action_types": action_types, "frequency": "mixed", "emergency_status": "standard", "terminating_action_present": True, "table_or_appendix_present": True, "compliance_complexity": "mixed", "human_confirmed": False, "evidence_ids": [ev_subject, ev_app, ev_req2, ev_req3, ev_req4, ev_req5, ev_req6, ev_req7, ev_req8, *all_table_evs]}, quality_flags=["complex_table", "complex_applicability", "complex_compliance", "cross_page_clause", "visual_transcription_used"], hybrid_source=True)


def flap_serials(builder: Builder) -> list[str]:
    text = "\n".join(builder.page_text(page) for page in range(4, 7))
    return sorted(set(re.findall(r"\b(?:TBE|TB)[0-9]{4}\b", text)))


def build_2016() -> dict[str, Any]:
    b = Builder("2016-0095")
    ev_cover = b.ev(1, "cover", "AD No.: 2016-0095. Issued: 19 May 2016. Design Approval Holder’s Name: AIRBUS. Type/Model designation(s): A380 aeroplanes. Effective Date: 02 June 2016. TCDS Number(s): EASA.A.110. Foreign AD: Not applicable. Supersedure: None.", section_raw="Cover identity", method="visual_transcription", quality="visual_transcription", note="Visually transcribed from the rendered cover because the prominent diagonal status stamp interrupts native reading order.")
    ev_status = b.ev(1, "other", "SUPERSEDED", section_raw="Document status stamp", method="visual_transcription", quality="visual_transcription", note="Visible diagonal red status stamp on the rendered source PDF; it does not identify the superseding AD.")
    ev_subject = b.ev(1, "cover", "ATA 57 – Wings – Flap Parts – Identification / Inspection [Wrong material]. Manufacturer(s): Airbus.", section_raw="ATA / Manufacturer(s)")
    app_raw = "Airbus A380-841, A380-842 and A380-861 aeroplanes, all manufacturer serial numbers (MSN)."
    ev_app = b.ev(1, "applicability", app_raw, section_raw="Applicability")
    ev_reason = b.ev(1, "reason", "Following an Airbus quality control review on the final assembly line, it was discovered that non-conforming aluminium alloy had been used to manufacture several structural parts located on the middle and outboard flaps. This condition, if not detected and corrected, could reduce the structural integrity of the aeroplane. Airbus issued Service Bulletin A380-57-8111 to provide instructions to identify and inspect the potentially affected parts. This AD requires identification of the potentially affected middle and outboard flap parts, a one-time Special Detailed Inspection to identify which material they are made of and, depending on findings, replacement with serviceable parts.", section_raw="Reason")
    ev_note1 = b.ev(2, "definitions", "Note 1: Appendix 1 of this AD lists the potentially affected middle (Table 1) and outboard (Table 2) flaps by serial number (s/n).", section_raw="Note 1")
    ev_r1 = b.ev(2, "required_actions_and_compliance_times", "(1) Within 3 months after the effective date of this AD, identify the s/n of the left hand (LH) and right hand (RH) middle and outboard flaps installed on the aeroplane. A review of aeroplane delivery and/or maintenance records is acceptable for identifying the installed flaps, provided those records can be relied upon for that purpose and the s/n of the affected parts can be positively identified from that review.", section_raw="Required Action(s) and Compliance Time(s)", clause="(1)")
    ev_r2 = b.ev(2, "required_actions_and_compliance_times", "(2) For each middle and outboard flap, identified as required by paragraph (1) of this AD, and having a s/n as listed in Appendix 1 of this AD, within 7 years or 4 300 flight cycles (FC), whichever occurs first, accumulated by the affected flap from the date as defined in Appendix 1 of this AD, depending on the affected flap s/n, accomplish a SDI of the affected flap parts, in accordance with the instructions of Airbus SB A380-57-8111.", section_raw="Required Action(s) and Compliance Time(s)", clause="(2)")
    ev_r3 = b.ev(2, "required_actions_and_compliance_times", "(3) If, during the SDI as required by paragraph (2) of this AD, a part manufactured from non-conforming material is detected, within 30 days after the SDI as required by paragraph (2) of this AD, contact Airbus for replacement instructions and within the compliance time indicated in those instructions, accomplish the replacement accordingly.", section_raw="Required Action(s) and Compliance Time(s)", clause="(3)")
    ev_r4 = b.ev(2, "required_actions_and_compliance_times", "(4) From the effective date of this AD, it is allowed to install on an aeroplane a middle or outboard flap having a s/n listed in Appendix 1 of this AD, provided that, prior to installation, it has been determined that the part is a serviceable part as defined in Note 3 of this AD.", section_raw="Required Action(s) and Compliance Time(s)", clause="(4)")
    ev_def_service = b.ev(2, "definitions", "Note 3: For the purpose of this AD, a serviceable middle or outboard flap is a part that is not listed by s/n in Appendix 1 of this AD, or has a s/n listed in Appendix 1 of this AD but has passed an SDI in accordance with the instructions of Airbus SB A380-57-8111.", section_raw="Note 3")
    ev_pub = b.ev(2, "reference_publications", "Airbus SB A380-57-8111 original issue, dated 07 January 2016. The use of later approved revisions of this document is acceptable for compliance with the requirements of this AD.", section_raw="Ref. Publications")
    ev_amoc = b.ev(2, "remarks", "If requested and appropriately substantiated, EASA can approve Alternative Methods of Compliance for this AD.", section_raw="Remarks 1")
    ev_contacts = b.ev(3, "remarks", "Enquiries regarding this AD should be referred to the EASA Safety Information Section, Certification Directorate. E-mail: ADs@easa.europa.eu. For any question concerning the technical content of the requirements in this AD, please contact: AIRBUS - EIANA (Airworthiness Office), Telephone: +33 562 110 253; Fax: +33 562 110 307, E-mail: account.airworth-A380@airbus.com.", section_raw="Remarks 3 and 4")
    ev_tab4 = b.table_ev(4, "Appendix 1 Table 1 – Middle Flaps (part 1)", ["s/n LH", "s/n RH", "Starting date for service life calculation"], footnotes=["Starting date is shown as dd/mm/yyyy", "Starting date corresponds to transfer of title at first delivery to an operator"], note="Full table page retained for serial/date mapping.")
    ev_tab5 = b.table_ev(5, "Appendix 1 Table 1 – Middle Flaps (continued)", ["s/n LH", "s/n RH", "Starting date for service life calculation"], note="Full table page retained for serial/date mapping.")
    ev_tab6 = b.table_ev(6, "Appendix 1 Table 2 – Outboard Flaps", ["s/n LH", "s/n RH", "Starting date for service life calculation"], note="Full table page retained for serial/date mapping.")
    ev_def_date = b.ev(4, "definitions", "The starting date for the service life calculation is shown as day/month/year (dd/mm/yyyy). Note 4: The starting date for service life calculation corresponds to the transfer of title of aeroplane where the s/n of the flap has been recorded and referenced in Airbus documentation at the time of aeroplane first delivery to an operator.", section_raw="Appendix 1 / Note 4")
    models = ["A380-841", "A380-842", "A380-861"]
    serial_values = flap_serials(b)
    apps = [
        app("APP-001", "All A380-841/-842/-861 aeroplanes and all MSN", app_raw, ["A380 family"], models, [all_serials("MSN-001", "all manufacturer serial numbers", [ev_app])], [ev_app]),
        app("APP-002", "A380 aeroplanes with a middle or outboard flap s/n listed in Appendix 1", app_raw + " Potentially affected flaps are those whose serial number appears in Appendix 1 Tables 1 or 2.", ["A380 family"], models, [all_serials("MSN-002", "all manufacturer serial numbers", [ev_app]), listed_serials("MSN-003", "middle or outboard flap s/n listed in Appendix 1", serial_values, [ev_note1, ev_tab4, ev_tab5, ev_tab6], condition="Installed flap serial number")], [ev_app, ev_note1, ev_tab4, ev_tab5, ev_tab6], conditions=["A listed middle or outboard flap is installed"]),
    ]
    cmp1 = b.cmp("Within 3 months after the effective date of this AD", [ev_r1], initial=[b.limit("within", 3, "calendar_month", "Within 3 months", [ev_r1], reference_event="effective date of this AD")])
    cmp2 = b.cmp("Within 7 years or 4 300 FC, whichever occurs first, accumulated by the affected flap from its Appendix 1 starting date", [ev_r2, ev_tab4, ev_tab5, ev_tab6], logic="whichever_occurs_first", conditions=["Flap s/n is listed in Appendix 1", "Use the row-specific starting date"], initial=[b.limit("within", 7, "calendar_year", "within 7 years", [ev_r2], reference_event="Appendix 1 starting date for the affected flap s/n"), b.limit("within", 4300, "flight_cycle", "4 300 flight cycles", [ev_r2], reference_event="Appendix 1 starting date for the affected flap s/n")])
    cmp3 = b.cmp("Within 30 days after the Special Detailed Inspection", [ev_r3], logic="conditional", conditions=["A non-conforming-material part is detected"], initial=[b.limit("within", 30, "calendar_day", "within 30 days", [ev_r3], reference_event="Special Detailed Inspection required by paragraph (2)")])
    cmp4 = b.cmp("Within the compliance time indicated in Airbus replacement instructions", [ev_r3], logic="conditional", conditions=["Airbus has provided replacement instructions after a non-conforming part was detected"], initial=[])
    cmp5 = b.cmp("From the effective date, a listed flap may be installed only if it is serviceable before installation", [ev_r4, ev_def_service], logic="conditional", conditions=["Prior to installation, the flap meets the Note 3 serviceable-part definition"], initial=[b.limit("from", None, "calendar_date", "From the effective date of this AD", [ev_r4], reference_event="effective date of this AD", calendar_date="2016-06-02")])
    requirements = [
        req("REQ-001", "(1)", ["APP-001"], ["test_or_check", "records_review"], "mandatory", "Identify the serial numbers of the installed LH and RH middle and outboard flaps.", [ev_r1], objects=["Installed LH and RH middle flaps", "Installed LH and RH outboard flaps"], conditions=["Unless accomplished previously"], pubs=[], cmps=[cmp1], follows=["REQ-002"]),
        req("REQ-002", "(2)", ["APP-002"], ["inspection"], "mandatory", "Perform a one-time Special Detailed Inspection of each affected middle and outboard flap part.", [ev_r2, ev_tab4, ev_tab5, ev_tab6], objects=["Affected middle and outboard flap parts"], conditions=["Flap s/n is listed in Appendix 1"], pubs=["PUB-001"], cmps=[cmp2], parent="REQ-001", follows=["REQ-003"]),
        req("REQ-003", "(3)", ["APP-002"], ["contact_manufacturer"], "conditional", "Contact Airbus for replacement instructions if a non-conforming-material part is detected.", [ev_r3], objects=["Non-conforming middle or outboard flap part"], conditions=["Non-conforming material detected during the paragraph (2) inspection"], pubs=[], cmps=[cmp3], parent="REQ-002", follows=["REQ-004"]),
        req("REQ-004", "(3)", ["APP-002"], ["replacement"], "conditional", "Replace each detected non-conforming-material part in accordance with Airbus instructions.", [ev_r3], objects=["Non-conforming middle or outboard flap part"], conditions=["Airbus replacement instructions received"], pubs=[], cmps=[cmp4], parent="REQ-003"),
        req("REQ-005", "(4)", ["APP-002"], ["install", "test_or_check", "prohibition"], "conditional", "Install a listed middle or outboard flap only if it is determined to be serviceable before installation.", [ev_r4, ev_def_service], objects=["Middle or outboard flap whose s/n is listed in Appendix 1"], conditions=["Part is serviceable under Note 3 before installation"], pubs=["PUB-001"], cmps=[cmp5]),
    ]
    publication = common_publication(subject="Wings – Flap Parts – Identification / Inspection [Wrong material]", subject_raw="ATA 57 – Wings – Flap Parts – Identification / Inspection [Wrong material]", subject_ev=ev_subject, issue_date="2016-05-19", issue_raw="Issued: 19 May 2016", issue_ev=ev_cover, effective_date="2016-06-02", effective_raw="Effective Date: 02 June 2016", effective_ev=ev_cover, ata="57", ata_title="Wings", manufacturer_raw="Airbus", manufacturer_ev=ev_subject, type_designations=["A380"], tcds=["EASA.A.110"], foreign_ev=ev_cover)
    unsafe = {"state": "present", "raw_reason_text": norm("An Airbus quality-control review found that non-conforming aluminium alloy had been used to manufacture structural parts on middle and outboard flaps. If not detected and corrected, this could reduce aeroplane structural integrity. Identification, one-time material inspection and finding-dependent replacement are required."), "observed_events_or_defects": ["Non-conforming aluminium alloy used in several middle- and outboard-flap structural parts"], "causes": ["Manufacturing material non-conformity"], "unsafe_conditions": ["Reduced structural integrity of the aeroplane"], "potential_consequences": ["Degraded aeroplane structural integrity"], "affected_components": ["Middle flap structural parts", "Outboard flap structural parts"], "intended_risk_mitigation": ["Identify affected flap serial numbers", "One-time Special Detailed Inspection", "Replace non-conforming parts"], "evidence_ids": [ev_reason]}
    definitions = [{"definition_id": "DEF-001", "term": "Serviceable middle or outboard flap", "definition_text": "A part not listed by s/n in Appendix 1, or a listed part that has passed a Special Detailed Inspection under Airbus SB A380-57-8111.", "evidence_ids": [ev_def_service]}, {"definition_id": "DEF-002", "term": "Starting date for service life calculation", "definition_text": "The dd/mm/yyyy Appendix 1 date corresponding to transfer of title at first delivery of the aeroplane on which the flap s/n was recorded in Airbus documentation.", "evidence_ids": [ev_def_date]}]
    return b.finish(cover_ev=ev_cover, identity_evs=[ev_cover, ev_status], version_label="Original", lifecycle="superseded", holder_raw="Design Approval Holder’s Name: AIRBUS", holder_value="Airbus", supersedure=explicit_none("Supersedure: None", [ev_cover]), publication=publication, applicability=apps, definitions=definitions, unsafe_condition=unsafe, requirements=requirements, exceptions=[], credits=[], publications=[pub("PUB-001", "service_bulletin", "Airbus", "A380-57-8111", "Original issue", "2016-01-07", ["required_method"], [ev_r2, ev_def_service, ev_pub], later=True)], relationships=[], contacts=contacts(ev_amoc, ev_contacts, "For technical questions, contact AIRBUS - EIANA (Airworthiness Office), telephone +33 562 110 253, fax +33 562 110 307, account.airworth-A380@airbus.com."), classification={"airbus_families": ["A380 family"], "ata_chapters": ["57"], "action_types": ["test_or_check", "records_review", "inspection", "contact_manufacturer", "replacement", "install", "prohibition"], "frequency": "mixed", "emergency_status": "standard", "terminating_action_present": False, "table_or_appendix_present": True, "compliance_complexity": "table_driven", "human_confirmed": False, "evidence_ids": [ev_subject, ev_app, ev_r1, ev_r2, ev_r3, ev_r4, ev_tab4, ev_tab5, ev_tab6]}, quality_flags=["complex_table", "complex_applicability", "complex_compliance", "visual_transcription_used"], hybrid_source=True)


def build_2017() -> dict[str, Any]:
    b = Builder("2017-0013")
    ev_cover = b.ev(1, "cover", "AD No.: 2017-0013. Issued: 27 January 2017. Design Approval Holder’s Name: AIRBUS. Type/Model designation(s): A380 aeroplanes. Effective Date: 10 February 2017. TCDS Number(s): EASA.A.110. Foreign AD: Not applicable. Supersedure: This AD supersedes EASA AD 2016-0095 dated 19 May 2016.", section_raw="Cover identity", method="visual_transcription", quality="visual_transcription", note="Visually transcribed from the rendered cover to preserve the two-column identity and supersedure fields in reading order.")
    ev_subject = b.ev(1, "cover", "ATA 57 – Wings – Flap Parts – Identification / Inspection [Wrong material]. Manufacturer(s): Airbus.", section_raw="ATA / Manufacturer(s)")
    app_raw = "Airbus A380-841, A380-842 and A380-861 aeroplanes, all manufacturer serial numbers (MSN)."
    ev_app = b.ev(1, "applicability", app_raw, section_raw="Applicability")
    ev_reason1 = b.ev(1, "reason", "Following an Airbus quality control review on the final assembly line, it was discovered that non-conforming aluminium alloy had been used to manufacture several structural parts located on the middle and outboard flaps. This condition, if not detected and corrected, could reduce the structural integrity of the aeroplane. To address this potential unsafe condition, Airbus issued Service Bulletin (SB) A380-57-8111 to provide instructions to identify and inspect the potentially affected parts, and EASA issued AD 2016-0095 to require identification of the potentially affected middle and outboard flap parts, a one-time Special Detailed Inspection (SDI) to identify which material they are made of and, depending on findings, replacement with serviceable parts. Since that AD was issued, Airbus identified that the list of potentially affected structural parts defined in the original issue of SB A380-57-8111 was incorrect and issued Revision 1 of SB A380-57-8111 to specify that for the outboard flap serial number (s/n) TB1056 installed on the right", section_raw="Reason", note="Exact native-text excerpt through the page-1 boundary; the sentence continues on page 2.")
    ev_reason2 = b.ev(2, "reason", "For the reasons described above, this AD retains the requirements of EASA AD 2016-0095, which is superseded, introduces a reduced starting date for service life calculation for RH outboard flap s/n TB1056, and removes middle flap s/n TB2101 from Appendix 1, Table 1, of this AD.", section_raw="Reason continued")
    ev_note1 = b.ev(2, "definitions", "Note 1: Appendix 1 of this AD lists the s/n of the potentially affected middle flaps (Table 1) and outboard flaps (Table 2).", section_raw="Note 1")
    ev_r1 = b.ev(2, "required_actions_and_compliance_times", "(1) Within 3 months after 02 June 2016 [the effective date of EASA AD 2016-0095], identify the s/n of the left hand (LH) and RH middle and outboard flaps installed on the aeroplane. A review of aeroplane delivery and/or maintenance records is acceptable for identifying the installed flaps, provided those records can be relied upon for that purpose and the s/n of the affected parts can be positively identified from that review.", section_raw="Required Action(s) and Compliance Time(s)", clause="(1)")
    ev_r2 = b.ev(2, "required_actions_and_compliance_times", "(2) For each middle and outboard flap, identified as required by paragraph (1) of this AD, and having a s/n as listed in Appendix 1 of this AD, within 7 years or 4 300 flight cycles (FC), whichever occurs first, accumulated by the affected flap from the applicable date as defined in Appendix 1 of this AD, depending on the affected flap s/n, accomplish an SDI of the affected flap parts, in accordance with the instructions of Airbus SB A380-57-8111.", section_raw="Required Action(s) and Compliance Time(s)", clause="(2)")
    ev_r3 = b.ev(2, "required_actions_and_compliance_times", "(3) If, during the SDI as required by paragraph (2) of this AD, a part manufactured from non-conforming material is detected, within 30 days after the SDI as required by paragraph (2) of this AD, contact Airbus for replacement instructions and within the compliance time indicated in those instructions, accomplish the replacement accordingly.", section_raw="Required Action(s) and Compliance Time(s)", clause="(3)")
    ev_r4 = b.ev(2, "required_actions_and_compliance_times", "(4) From 02 June 2016 [the effective date of EASA AD 2016-0095], it is allowed to install on an aeroplane a middle or outboard flap having a s/n listed in Appendix 1 of this AD, provided that, prior to installation, it has been determined that the part is a serviceable part as defined in Note 3 of this AD.", section_raw="Required Action(s) and Compliance Time(s)", clause="(4)")
    ev_def_service = b.ev(2, "definitions", "Note 3: For the purpose of this AD, a serviceable middle or outboard flap is a part that is not listed by s/n in Appendix 1 of this AD, or has a s/n listed in Appendix 1 of this AD but has passed an SDI in accordance with the instructions of Airbus SB A380-57-8111.", section_raw="Note 3")
    ev_pub = b.ev(3, "reference_publications", "Airbus SB A380-57-8111 original issue dated 07 January 2016, or Revision 1 dated 25 November 2016. The use of later approved revisions of this document is acceptable for compliance with the requirements of this AD.", section_raw="Ref. Publications")
    ev_remarks = b.ev(3, "remarks", "If requested and appropriately substantiated, EASA can approve Alternative Methods of Compliance for this AD. Enquiries regarding this AD should be referred to the EASA Safety Information Section, Certification Directorate. E-mail: ADs@easa.europa.eu. For any question concerning the technical content of the requirements in this AD, please contact: AIRBUS - EIANA (Airworthiness Office), Telephone: +33 562 110 253; Fax: +33 562 110 307, E-mail: account.airworth-A380@airbus.com.", section_raw="Remarks 1, 3 and 4")
    ev_tab4 = b.table_ev(4, "Appendix 1 Table 1 – Middle Flaps (part 1)", ["s/n LH", "s/n RH", "Starting date for service life calculation"], footnotes=["Starting date is shown as dd/mm/yyyy", "Starting date corresponds to transfer of title at first delivery to an operator"], note="Full table page retained for serial/date mapping.")
    ev_tab5 = b.table_ev(5, "Appendix 1 Table 1 – Middle Flaps (continued)", ["s/n LH", "s/n RH", "Starting date for service life calculation"], note="Full table page retained; TB2101 is not listed in this revision.")
    ev_tab6 = b.table_ev(6, "Appendix 1 Table 2 – Outboard Flaps", ["s/n LH", "s/n RH", "Starting date for service life calculation"], note="Full table page retained; RH TB1056 uses the reduced 05/11/2010 starting date.")
    ev_def_date = b.ev(4, "definitions", "The starting date for the service life calculation is shown as day/month/year (dd/mm/yyyy). Note 4: The starting date for service life calculation corresponds to the transfer of title of aeroplane where the s/n of the flap has been recorded and referenced in Airbus documentation at the time of aeroplane first delivery to an operator.", section_raw="Appendix 1 / Note 4")
    models = ["A380-841", "A380-842", "A380-861"]
    serial_values = flap_serials(b)
    apps = [
        app("APP-001", "All A380-841/-842/-861 aeroplanes and all MSN", app_raw, ["A380 family"], models, [all_serials("MSN-001", "all manufacturer serial numbers", [ev_app])], [ev_app]),
        app("APP-002", "A380 aeroplanes with a middle or outboard flap s/n listed in this AD's Appendix 1", app_raw + " Potentially affected flaps are those whose serial number appears in this AD's Appendix 1 Tables 1 or 2.", ["A380 family"], models, [all_serials("MSN-002", "all manufacturer serial numbers", [ev_app]), listed_serials("MSN-003", "middle or outboard flap s/n listed in this AD's Appendix 1", serial_values, [ev_note1, ev_tab4, ev_tab5, ev_tab6], condition="Installed flap serial number")], [ev_app, ev_note1, ev_tab4, ev_tab5, ev_tab6], conditions=["A listed middle or outboard flap is installed"]),
    ]
    cmp1 = b.cmp("Within 3 months after 02 June 2016", [ev_r1], initial=[b.limit("within", 3, "calendar_month", "Within 3 months", [ev_r1], reference_event="02 June 2016, effective date of EASA AD 2016-0095")])
    cmp2 = b.cmp("Within 7 years or 4 300 FC, whichever occurs first, accumulated by the affected flap from its applicable Appendix 1 starting date", [ev_r2, ev_tab4, ev_tab5, ev_tab6], logic="whichever_occurs_first", conditions=["Flap s/n is listed in this AD's Appendix 1", "Use the row-specific starting date"], initial=[b.limit("within", 7, "calendar_year", "within 7 years", [ev_r2], reference_event="applicable Appendix 1 starting date for the affected flap s/n"), b.limit("within", 4300, "flight_cycle", "4 300 flight cycles", [ev_r2], reference_event="applicable Appendix 1 starting date for the affected flap s/n")])
    cmp3 = b.cmp("Within 30 days after the Special Detailed Inspection", [ev_r3], logic="conditional", conditions=["A non-conforming-material part is detected"], initial=[b.limit("within", 30, "calendar_day", "within 30 days", [ev_r3], reference_event="Special Detailed Inspection required by paragraph (2)")])
    cmp4 = b.cmp("Within the compliance time indicated in Airbus replacement instructions", [ev_r3], logic="conditional", conditions=["Airbus has provided replacement instructions after a non-conforming part was detected"], initial=[])
    cmp5 = b.cmp("From 02 June 2016, a listed flap may be installed only if it is serviceable before installation", [ev_r4, ev_def_service], logic="conditional", conditions=["Prior to installation, the flap meets the Note 3 serviceable-part definition"], initial=[b.limit("from", None, "calendar_date", "From 02 June 2016", [ev_r4], reference_event="effective date of EASA AD 2016-0095", calendar_date="2016-06-02")])
    requirements = [
        req("REQ-001", "(1)", ["APP-001"], ["test_or_check", "records_review"], "mandatory", "Identify the serial numbers of the installed LH and RH middle and outboard flaps.", [ev_r1], objects=["Installed LH and RH middle flaps", "Installed LH and RH outboard flaps"], conditions=["Unless accomplished previously"], cmps=[cmp1], follows=["REQ-002"]),
        req("REQ-002", "(2)", ["APP-002"], ["inspection"], "mandatory", "Perform a one-time Special Detailed Inspection of each affected middle and outboard flap part.", [ev_r2, ev_tab4, ev_tab5, ev_tab6], objects=["Affected middle and outboard flap parts"], conditions=["Flap s/n is listed in Appendix 1"], pubs=["PUB-001", "PUB-002"], cmps=[cmp2], parent="REQ-001", follows=["REQ-003"]),
        req("REQ-003", "(3)", ["APP-002"], ["contact_manufacturer"], "conditional", "Contact Airbus for replacement instructions if a non-conforming-material part is detected.", [ev_r3], objects=["Non-conforming middle or outboard flap part"], conditions=["Non-conforming material detected during the paragraph (2) inspection"], cmps=[cmp3], parent="REQ-002", follows=["REQ-004"]),
        req("REQ-004", "(3)", ["APP-002"], ["replacement"], "conditional", "Replace each detected non-conforming-material part in accordance with Airbus instructions.", [ev_r3], objects=["Non-conforming middle or outboard flap part"], conditions=["Airbus replacement instructions received"], cmps=[cmp4], parent="REQ-003"),
        req("REQ-005", "(4)", ["APP-002"], ["install", "test_or_check", "prohibition"], "conditional", "Install a listed middle or outboard flap only if it is determined to be serviceable before installation.", [ev_r4, ev_def_service], objects=["Middle or outboard flap whose s/n is listed in Appendix 1"], conditions=["Part is serviceable under Note 3 before installation"], pubs=["PUB-001", "PUB-002"], cmps=[cmp5]),
    ]
    publication = common_publication(subject="Wings – Flap Parts – Identification / Inspection [Wrong material]", subject_raw="ATA 57 – Wings – Flap Parts – Identification / Inspection [Wrong material]", subject_ev=ev_subject, issue_date="2017-01-27", issue_raw="Issued: 27 January 2017", issue_ev=ev_cover, effective_date="2017-02-10", effective_raw="Effective Date: 10 February 2017", effective_ev=ev_cover, ata="57", ata_title="Wings", manufacturer_raw="Airbus", manufacturer_ev=ev_subject, type_designations=["A380"], tcds=["EASA.A.110"], foreign_ev=ev_cover)
    unsafe = {"state": "present", "raw_reason_text": norm("Non-conforming aluminium alloy was used in middle- and outboard-flap structural parts, which could reduce aeroplane structural integrity. After AD 2016-0095, Airbus found its original SB list incorrect: RH outboard flap TB1056 needed a reduced starting date and middle flap TB2101 was not affected. This AD retains the prior requirements with those corrections."), "observed_events_or_defects": ["Non-conforming aluminium alloy in flap structural parts", "Original affected-parts list contained errors"], "causes": ["Manufacturing material non-conformity", "Incorrect original SB affected-parts list"], "unsafe_conditions": ["Reduced structural integrity of the aeroplane"], "potential_consequences": ["Degraded aeroplane structural integrity"], "affected_components": ["Middle flap structural parts", "Outboard flap structural parts"], "intended_risk_mitigation": ["Identify affected flap serial numbers", "One-time Special Detailed Inspection", "Replace non-conforming parts", "Use corrected Appendix 1 serial/date data"], "evidence_ids": [ev_reason1, ev_reason2]}
    definitions = [{"definition_id": "DEF-001", "term": "Serviceable middle or outboard flap", "definition_text": "A part not listed by s/n in Appendix 1, or a listed part that has passed a Special Detailed Inspection under Airbus SB A380-57-8111.", "evidence_ids": [ev_def_service]}, {"definition_id": "DEF-002", "term": "Starting date for service life calculation", "definition_text": "The dd/mm/yyyy Appendix 1 date corresponding to transfer of title at first delivery of the aeroplane on which the flap s/n was recorded in Airbus documentation.", "evidence_ids": [ev_def_date]}]
    pubs = [pub("PUB-001", "service_bulletin", "Airbus", "A380-57-8111", "Original issue", "2016-01-07", ["required_method"], [ev_pub], later=True), pub("PUB-002", "service_bulletin", "Airbus", "A380-57-8111", "Revision 1", "2016-11-25", ["required_method"], [ev_reason1, ev_pub], later=True)]
    relationships = [rel("REL-001", "supersedes", "2016-0095", "structured_supersedure_field", "This AD supersedes EASA AD 2016-0095 dated 19 May 2016.", [ev_cover]), rel("REL-002", "retains_requirements_of", "2016-0095", "explicit_directional_sentence", "This AD retains the requirements of EASA AD 2016-0095, which is superseded.", [ev_reason2])]
    return b.finish(cover_ev=ev_cover, identity_evs=[ev_cover], version_label="Original", lifecycle="unknown", holder_raw="Design Approval Holder’s Name: AIRBUS", holder_value="Airbus", supersedure=grounded_text("Supersedes EASA AD 2016-0095 dated 19 May 2016", "Supersedure: This AD supersedes EASA AD 2016-0095 dated 19 May 2016.", [ev_cover]), publication=publication, applicability=apps, definitions=definitions, unsafe_condition=unsafe, requirements=requirements, exceptions=[], credits=[], publications=pubs, relationships=relationships, contacts=contacts(ev_remarks, ev_remarks, "For technical questions, contact AIRBUS - EIANA (Airworthiness Office), telephone +33 562 110 253, fax +33 562 110 307, account.airworth-A380@airbus.com."), classification={"airbus_families": ["A380 family"], "ata_chapters": ["57"], "action_types": ["test_or_check", "records_review", "inspection", "contact_manufacturer", "replacement", "install", "prohibition"], "frequency": "mixed", "emergency_status": "standard", "terminating_action_present": False, "table_or_appendix_present": True, "compliance_complexity": "table_driven", "human_confirmed": False, "evidence_ids": [ev_subject, ev_app, ev_r1, ev_r2, ev_r3, ev_r4, ev_tab4, ev_tab5, ev_tab6]}, quality_flags=["complex_table", "complex_applicability", "complex_compliance", "visual_transcription_used"], hybrid_source=True)


BUILDERS = [build_2009, build_2010, build_2011, build_2012, build_2013, build_2014, build_2015, build_2016, build_2017, build_2018]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = [write_record(build()) for build in BUILDERS]
    for path in paths:
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
