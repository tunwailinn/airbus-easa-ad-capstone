#!/usr/bin/env python3
"""Build Codex annotator-a2 first-pass records from blind source packets only.

The file is intentionally source-local: it reads the frozen Step 2 blank
template and the ten named blind packets.  It does not read pilot-selection
metadata, reviewer-QC packets, or another annotator's records.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
BLANK_PATH = ROOT / "step2_ad_schema" / "blank_ad_annotation.json"
BLIND_DIR = ROOT / "step3_pilot" / "packets" / "blind"
OUTPUT_DIR = ROOT / "step3_pilot" / "submitted" / "annotator_a"

TARGETS = {
    "2024-0095": "53e4fefd2d273164",
    "2025-0008": "b829efee031a2fcf",
    "2025-0068": "6e80e67e640ba6d1",
    "2026-0017": "1f3af1a66dad0ea4",
    "2026-0079": "1f16f3df632283df",
    "2006-0047": "8dd9dd9099deb529",
    "2007-0022": "cdccd0ff024c4b72",
    "2007-0278": "0b6a17dbe6f95907",
    "2008-0012": "f2112ddc18baa008",
    "2009-0025": "46511578be7115fd",
}


def unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def grounded_text(
    value: str | None,
    raw_text: str | None,
    evidence_ids: list[str],
    state: str | None = None,
) -> dict[str, Any]:
    if state is None:
        state = "present" if value is not None else "not_stated"
    return {
        "state": state,
        "value": value,
        "raw_text": raw_text,
        "evidence_ids": evidence_ids,
    }


def grounded_date(
    value: str | None,
    raw_text: str | None,
    evidence_ids: list[str],
    state: str | None = None,
) -> dict[str, Any]:
    return grounded_text(value, raw_text, evidence_ids, state)


class AnnotationBuilder:
    def __init__(self, ad_number: str) -> None:
        file_id = TARGETS[ad_number]
        packet_path = BLIND_DIR / f"{ad_number}__{file_id}.blind-packet.json"
        self.packet = json.loads(packet_path.read_text(encoding="utf-8"))
        self.pages = {
            page["page_number"]: page for page in self.packet["pages"]
        }
        self.record = copy.deepcopy(
            json.loads(BLANK_PATH.read_text(encoding="utf-8"))
        )
        self.ad_number = ad_number
        self.file_id = file_id
        self.counters = {
            "EV": 0,
            "APP": 0,
            "MSN": 0,
            "DEF": 0,
            "REQ": 0,
            "CMP": 0,
            "LIM": 0,
            "EXC": 0,
            "CRD": 0,
            "PUB": 0,
            "REL": 0,
            "AMC": 0,
            "AST": 0,
        }
        self.named_evidence: dict[str, str] = {}
        self.context_evidence: dict[str, list[str]] = {}
        self._initialize_source_and_metadata()

    def next_id(self, prefix: str) -> str:
        self.counters[prefix] += 1
        return f"{prefix}-{self.counters[prefix]:03d}"

    def _initialize_source_and_metadata(self) -> None:
        identity = self.packet["document_identity"]
        pdf = self.packet["pdf_provenance"]
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )
        self.record["record_id"] = f"adann-{self.file_id}"
        self.record["source_document"] = {
            "file_instance_id": self.file_id,
            "content_id": pdf["content_id"],
            "canonical_file_instance_id": self.file_id,
            "file_aliases": [],
            "file_name": pdf["file_name"],
            "relative_path": pdf["relative_path"],
            "file_sha256": pdf["file_sha256"],
            "normalized_text_sha256": pdf["manifest_normalized_text_sha256"],
            "page_count": pdf["page_count"],
            "extraction_status": "native_text",
            "needs_ocr": False,
            "manifest_review_flags": [],
            "source_url": pdf["official_pdf_url"],
            "text_extraction_method": "native_text",
            "exact_duplicate_group": None,
            "near_duplicate_cluster": None,
        }
        correction_date = identity.get("correction_date_from_manifest")
        self.record["ad_identity"].update(
            {
                "authority": "EASA",
                "document_type": "airworthiness_directive",
                "ad_number": identity["ad_number"],
                "base_ad_number": identity["base_ad_number"],
                "revision_number": identity["revision_number"],
                "publication_kind": (
                    "emergency_ad" if identity["is_emergency"] else "standard_ad"
                ),
                "is_emergency": identity["is_emergency"],
                "is_correction": identity["is_correction"],
                "correction_date": grounded_date(None, None, [], "not_stated"),
                "version_label": (
                    "Corrected" if identity["is_correction"] else "Original"
                ),
                "logical_version_key": identity["logical_version_key"],
                "is_latest_version": None,
                "lifecycle_status": "unknown",
            }
        )
        if correction_date:
            # The value and evidence are attached by each corrected-source builder.
            self.record["ad_identity"]["correction_date"]["value"] = correction_date
        self.record["annotation_metadata"] = {
            "guideline_version": "1.0.0",
            "record_status": "first_pass_complete",
            "creation_method": "hybrid",
            "machine_provenance": {
                "system": "OpenAI Codex",
                "model": "GPT-5",
                "prompt_or_rules_version": "step2-guidelines-1.0.0-manual-pass-a2",
                "generated_at": now,
            },
            "annotators": [
                {
                    "annotator_id": "codex-a2",
                    "role": "annotator",
                    "started_at": now,
                    "submitted_at": now,
                }
            ],
            "events": [
                {
                    "event_type": "created",
                    "actor_id": "codex-a2",
                    "timestamp": now,
                    "rationale": "Source-only machine-assisted first annotation pass.",
                },
                {
                    "event_type": "submitted",
                    "actor_id": "codex-a2",
                    "timestamp": now,
                    "rationale": (
                        "First pass completed from the rendered source PDF and blind "
                        "page-text packet; no human approval is asserted."
                    ),
                },
            ],
            "quality_flags": ["manual_review_required"],
            "uncertainty_flags": [],
            "notes": [
                "Independent Codex annotator-a2 first pass; requires human review.",
                "Only the source PDF, blind page packet, section index, and frozen Step 2 rules were used.",
            ],
            "source_text_sha256": pdf["manifest_normalized_text_sha256"],
            "created_at": now,
            "updated_at": now,
        }
        self.record["benchmark_metadata"] = {
            "split": "unassigned",
            "split_group": identity["base_ad_number"],
            "selection_strata": [],
            "duplicate_cluster_ids": [],
            "gold_record": False,
        }

    @staticmethod
    def _normalized_with_map(text: str) -> tuple[str, list[int]]:
        output: list[str] = []
        mapping: list[int] = []
        in_space = True
        for index, char in enumerate(text):
            if char.isspace():
                if not in_space and output:
                    output.append(" ")
                    mapping.append(index)
                in_space = True
            else:
                output.append(char)
                mapping.append(index)
                in_space = False
        if output and output[-1] == " ":
            output.pop()
            mapping.pop()
        return "".join(output), mapping

    def evidence(
        self,
        name: str,
        page_number: int,
        section: str,
        start_phrase: str,
        end_phrase: str | None = None,
        *,
        clause_path: str | None = None,
        section_raw: str | None = None,
        occurrence: int = 1,
        table_context: dict[str, Any] | None = None,
        annotation_note: str | None = None,
    ) -> str:
        page = self.pages[page_number]
        raw = page["text"]
        normalized, mapping = self._normalized_with_map(raw)
        start_phrase = " ".join(start_phrase.split())
        end_phrase = " ".join(end_phrase.split()) if end_phrase else None
        cursor = 0
        start_norm = -1
        for _ in range(occurrence):
            start_norm = normalized.find(start_phrase, cursor)
            if start_norm < 0:
                raise ValueError(
                    f"{self.ad_number} p{page_number}: start phrase not found: {start_phrase!r}"
                )
            cursor = start_norm + len(start_phrase)
        if end_phrase:
            end_norm = normalized.find(end_phrase, cursor)
            if end_norm < 0:
                raise ValueError(
                    f"{self.ad_number} p{page_number}: end phrase not found: {end_phrase!r}"
                )
        else:
            footer_candidates = [
                normalized.find("TE.CAP.00110-012", cursor),
                normalized.find("EASA Form 110", cursor),
            ]
            footer_candidates = [value for value in footer_candidates if value >= 0]
            end_norm = min(footer_candidates) if footer_candidates else len(normalized)
        raw_start = mapping[start_norm]
        raw_end = mapping[end_norm - 1] + 1 if end_norm > start_norm else mapping[cursor - 1] + 1
        quote = raw[raw_start:raw_end].rstrip()
        evidence_id = self.next_id("EV")
        self.record["evidence_spans"].append(
            {
                "evidence_id": evidence_id,
                "source_file_instance_id": self.file_id,
                "page_number": page_number,
                "printed_page_label": f"Page {page_number} of {page['page_count']}",
                "section": section,
                "section_raw": section_raw,
                "clause_path": clause_path,
                "exact_quote": quote,
                "start_char": raw_start,
                "end_char": raw_start + len(quote),
                "page_text_sha256": page["page_text_sha256"],
                "bbox_normalized": None,
                "extraction_method": "native_text",
                "quality": "exact",
                "table_context": table_context,
                "annotation_note": annotation_note,
            }
        )
        self.named_evidence[name] = evidence_id
        return evidence_id

    def visual_evidence(
        self,
        name: str,
        page_number: int,
        section: str,
        exact_quote: str,
        *,
        clause_path: str | None = None,
        table_context: dict[str, Any] | None = None,
        annotation_note: str,
    ) -> str:
        page = self.pages[page_number]
        evidence_id = self.next_id("EV")
        self.record["evidence_spans"].append(
            {
                "evidence_id": evidence_id,
                "source_file_instance_id": self.file_id,
                "page_number": page_number,
                "printed_page_label": f"Page {page_number} of {page['page_count']}",
                "section": section,
                "section_raw": None,
                "clause_path": clause_path,
                "exact_quote": exact_quote,
                "start_char": None,
                "end_char": None,
                "page_text_sha256": page["page_text_sha256"],
                "bbox_normalized": None,
                "extraction_method": "visual_transcription",
                "quality": "visual_transcription",
                "table_context": table_context,
                "annotation_note": annotation_note,
            }
        )
        self.named_evidence[name] = evidence_id
        return evidence_id

    def add_publication(
        self,
        publication_type: str,
        issuer: str | None,
        number: str,
        evidence_ids: list[str],
        *,
        revision: str | None = None,
        publication_date: str | None = None,
        title: str | None = None,
        roles: list[str] | None = None,
        later: bool | None = None,
    ) -> str:
        publication_id = self.next_id("PUB")
        self.record["referenced_publications"].append(
            {
                "publication_id": publication_id,
                "publication_type": publication_type,
                "issuer": issuer,
                "number": number,
                "revision": revision,
                "publication_date": publication_date,
                "title": title,
                "roles": roles or ["required_method"],
                "later_approved_revisions_allowed": later,
                "evidence_ids": evidence_ids,
            }
        )
        return publication_id

    def add_group(
        self,
        label: str,
        raw_text: str,
        evidence_ids: list[str],
        *,
        families: list[str],
        models: list[str],
        serial_restrictions: list[dict[str, Any]] | None = None,
        part_numbers: list[str] | None = None,
        configuration_conditions: list[str] | None = None,
        exclusions: list[str] | None = None,
        boolean_logic: str = "all",
    ) -> str:
        group_id = self.next_id("APP")
        self.record["applicability_groups"].append(
            {
                "group_id": group_id,
                "label": label,
                "state": "present",
                "raw_text": raw_text,
                "aircraft_families": families,
                "models": models,
                "serial_restrictions": serial_restrictions or [],
                "part_numbers": part_numbers or [],
                "configuration_conditions": configuration_conditions or [],
                "exclusions": exclusions or [],
                "boolean_logic": boolean_logic,
                "evidence_ids": evidence_ids,
            }
        )
        return group_id

    def serial(
        self,
        kind: str,
        raw_expression: str,
        evidence_ids: list[str],
        *,
        lower: str | None = None,
        upper: str | None = None,
        values: list[str] | None = None,
        condition: str | None = None,
    ) -> dict[str, Any]:
        return {
            "restriction_id": self.next_id("MSN"),
            "kind": kind,
            "raw_expression": raw_expression,
            "lower_bound": lower,
            "upper_bound": upper,
            "explicit_values": values or [],
            "condition": condition,
            "evidence_ids": evidence_ids,
        }

    def add_definition(self, term: str, text: str, evidence_ids: list[str]) -> str:
        definition_id = self.next_id("DEF")
        self.record["definitions"].append(
            {
                "definition_id": definition_id,
                "term": term,
                "definition_text": text,
                "evidence_ids": evidence_ids,
            }
        )
        return definition_id

    def limit(
        self,
        relation: str,
        raw_value: str,
        evidence_ids: list[str],
        *,
        quantity: float | int | None,
        unit: str,
        reference_event: str | None = None,
        calendar_date: str | None = None,
    ) -> dict[str, Any]:
        return {
            "limit_id": self.next_id("LIM"),
            "relation": relation,
            "quantity": quantity,
            "unit": unit,
            "raw_value": raw_value,
            "reference_event": reference_event,
            "calendar_date": calendar_date,
            "evidence_ids": evidence_ids,
        }

    def rule(
        self,
        raw_text: str,
        evidence_ids: list[str],
        *,
        logic: str = "single",
        conditions: list[str] | None = None,
        initial_limits: list[dict[str, Any]] | None = None,
        repetitive_intervals: list[dict[str, Any]] | None = None,
        grace_periods: list[dict[str, Any]] | None = None,
        state: str = "present",
    ) -> dict[str, Any]:
        repetitive = repetitive_intervals or []
        return {
            "compliance_id": self.next_id("CMP"),
            "state": state,
            "raw_text": raw_text,
            "logic": logic,
            "conditions": conditions or [],
            "initial_limits": initial_limits or [],
            "is_repetitive": bool(repetitive),
            "repetitive_intervals": repetitive,
            "grace_periods": grace_periods or [],
            "evidence_ids": evidence_ids,
        }

    @staticmethod
    def no_terminating_action() -> dict[str, Any]:
        return {
            "state": "not_stated",
            "present": False,
            "scope": "none",
            "action_text": None,
            "terminates_requirement_ids": [],
            "evidence_ids": [],
        }

    @staticmethod
    def terminating_action(
        text: str,
        target_requirement_ids: list[str],
        evidence_ids: list[str],
        scope: str = "full",
    ) -> dict[str, Any]:
        return {
            "state": "present",
            "present": True,
            "scope": scope,
            "action_text": text,
            "terminates_requirement_ids": target_requirement_ids,
            "evidence_ids": evidence_ids,
        }

    def add_requirement(
        self,
        paragraph_reference: str | None,
        group_ids: list[str],
        action_types: list[str],
        obligation: str,
        action_text: str,
        evidence_ids: list[str],
        *,
        objects: list[str] | None = None,
        conditions: list[str] | None = None,
        publications: list[str] | None = None,
        rules: list[dict[str, Any]] | None = None,
        parent: str | None = None,
        follows: list[str] | None = None,
        terminating: dict[str, Any] | None = None,
    ) -> str:
        requirement_id = self.next_id("REQ")
        self.record["requirements"].append(
            {
                "requirement_id": requirement_id,
                "paragraph_reference": paragraph_reference,
                "parent_requirement_id": parent,
                "applicability_group_ids": group_ids,
                "action_types": unique(action_types),
                "obligation": obligation,
                "action_text": action_text,
                "objects_or_components": objects or [],
                "conditions": conditions or [],
                "method_publication_ids": publications or [],
                "compliance_rules": rules or [],
                "follow_on_requirement_ids": follows or [],
                "terminating_action": terminating or self.no_terminating_action(),
                "evidence_ids": evidence_ids,
            }
        )
        return requirement_id

    def add_exception(
        self, text: str, requirement_ids: list[str], evidence_ids: list[str]
    ) -> str:
        exception_id = self.next_id("EXC")
        self.record["exceptions"].append(
            {
                "exception_id": exception_id,
                "text": text,
                "applies_to_requirement_ids": requirement_ids,
                "evidence_ids": evidence_ids,
            }
        )
        return exception_id

    def add_credit(
        self,
        text: str,
        requirement_ids: list[str],
        publication_ids: list[str],
        evidence_ids: list[str],
        *,
        conditions: list[str] | None = None,
    ) -> str:
        credit_id = self.next_id("CRD")
        self.record["previous_action_credit"].append(
            {
                "credit_id": credit_id,
                "text": text,
                "applies_to_requirement_ids": requirement_ids,
                "credited_publication_ids": publication_ids,
                "conditions": conditions or [],
                "evidence_ids": evidence_ids,
            }
        )
        return credit_id

    def add_relationship(
        self,
        relationship_type: str,
        target_ad_number: str,
        raw_text: str,
        evidence_ids: list[str],
        *,
        source: str,
        target_logical_version_key: str | None = None,
    ) -> str:
        relationship_id = self.next_id("REL")
        self.record["relationships"].append(
            {
                "relationship_id": relationship_id,
                "relationship_type": relationship_type,
                "target_ad_number": target_ad_number,
                "target_record_id": None,
                "target_logical_version_key": target_logical_version_key,
                "source": source,
                "verification_status": "candidate",
                "manually_verified": False,
                "raw_text": raw_text,
                "evidence_ids": evidence_ids,
            }
        )
        return relationship_id

    def add_contact(
        self,
        entry_type: str,
        organization: str | None,
        text: str,
        evidence_ids: list[str],
        conditions: list[str] | None = None,
    ) -> str:
        entry_id = self.next_id("AMC")
        self.record["amoc_and_contacts"].append(
            {
                "entry_id": entry_id,
                "entry_type": entry_type,
                "authority_or_organization": organization,
                "contact_text": text,
                "conditions": conditions or [],
                "evidence_ids": evidence_ids,
            }
        )
        return entry_id

    def add_assertions(self) -> None:
        paths = [
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
            "/publication/issue_date",
            "/publication/effective_date",
        ]
        for path in paths:
            value: Any = self.record
            for token in path.strip("/").split("/"):
                value = value[token]
            evidence_ids = collect_evidence_ids(value)
            if not evidence_ids:
                evidence_ids = self.context_evidence.get(path, [])
            if value is None or value == []:
                value_state = (
                    "not_applicable"
                    if path in {"/relationships", "/previous_action_credit"}
                    else "absent_in_source"
                )
            else:
                value_state = "present"
            self.record["field_assertions"].append(
                {
                    "assertion_id": self.next_id("AST"),
                    "field_path": path,
                    "value_state": value_state,
                    "origin": "auto_extracted",
                    "verification_status": "unreviewed",
                    "confidence": 0.92 if value_state == "present" else 0.85,
                    "evidence_ids": evidence_ids,
                    "annotator_id": "codex-a2",
                    "derivation_rule": None,
                    "input_field_paths": [],
                    "notes": "Source-grounded first-pass assertion; independent review pending.",
                }
            )

    def finalize(
        self,
        *,
        families: list[str],
        ata_code: str,
        frequency: str,
        table_present: bool,
        compliance_complexity: str,
        classification_evidence: list[str],
        quality_flags: list[str] | None = None,
    ) -> dict[str, Any]:
        action_types = unique(
            action
            for requirement in self.record["requirements"]
            for action in requirement["action_types"]
        )
        terminating_present = any(
            requirement["terminating_action"]["present"] is True
            for requirement in self.record["requirements"]
        )
        self.record["classification"] = {
            "airbus_families": unique(families),
            "ata_chapters": [ata_code],
            "action_types": action_types,
            "frequency": frequency,
            "emergency_status": "standard",
            "terminating_action_present": terminating_present,
            "table_or_appendix_present": table_present,
            "compliance_complexity": compliance_complexity,
            "human_confirmed": False,
            "evidence_ids": unique(classification_evidence),
        }
        flags = self.record["annotation_metadata"]["quality_flags"]
        for flag in quality_flags or []:
            if flag not in flags:
                flags.append(flag)
        self.add_assertions()
        return self.record

    def write(self) -> Path:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / f"{self.ad_number}__{self.file_id}.annotation.json"
        path.write_text(
            json.dumps(self.record, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path


def collect_evidence_ids(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        if isinstance(value.get("evidence_ids"), list):
            found.extend(value["evidence_ids"])
        for child in value.values():
            found.extend(collect_evidence_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(collect_evidence_ids(child))
    return unique(found)


def common_identity_publication(
    b: AnnotationBuilder,
    *,
    cover_ev: str,
    subject_ev: str,
    app_ev: str,
    issue_date: str,
    issue_raw: str,
    effective_date: str,
    effective_raw: str,
    design_holder: str,
    subject: str,
    ata_code: str,
    ata_title: str,
    manufacturers: list[tuple[str, str, str]],
    type_models: list[str],
    tcds_numbers: list[str],
    foreign_raw: str,
    supersedure_value: str | None,
    supersedure_raw: str,
    supersedure_state: str,
) -> None:
    b.record["ad_identity"]["design_approval_holder"] = grounded_text(
        design_holder, design_holder, [cover_ev]
    )
    b.record["ad_identity"]["supersedure_statement"] = grounded_text(
        supersedure_value,
        supersedure_raw,
        [cover_ev],
        supersedure_state,
    )
    b.record["ad_identity"]["evidence_ids"] = unique([cover_ev, subject_ev])
    b.record["publication"] = {
        "subject": grounded_text(subject, subject, [subject_ev]),
        "issue_date": grounded_date(issue_date, issue_raw, [cover_ev]),
        "effective_date": grounded_date(
            effective_date, effective_raw, [cover_ev]
        ),
        "ata_chapters": [
            {"code": ata_code, "title": ata_title, "evidence_ids": [subject_ev]}
        ],
        "manufacturers": [
            {
                "raw_name": raw_name,
                "normalized_name": normalized_name,
                "role": role,
                "evidence_ids": [app_ev],
            }
            for raw_name, normalized_name, role in manufacturers
        ],
        "type_model_designations": type_models,
        "tcds_numbers": tcds_numbers,
        "foreign_ad": grounded_text(
            None, foreign_raw, [cover_ev], "explicit_none"
        ),
    }


def set_unsafe(
    b: AnnotationBuilder,
    evidence_ids: list[str],
    raw_reason_text: str,
    *,
    observed: list[str],
    causes: list[str],
    conditions: list[str],
    consequences: list[str],
    components: list[str],
    mitigation: list[str],
) -> None:
    b.record["unsafe_condition"] = {
        "state": "present",
        "raw_reason_text": raw_reason_text,
        "observed_events_or_defects": observed,
        "causes": causes,
        "unsafe_conditions": conditions,
        "potential_consequences": consequences,
        "affected_components": components,
        "intended_risk_mitigation": mitigation,
        "evidence_ids": evidence_ids,
    }


def page_text_between(
    b: AnnotationBuilder, page: int, start: str, end: str | None = None
) -> str:
    raw = b.pages[page]["text"]
    normalized, _ = b._normalized_with_map(raw)
    start = " ".join(start.split())
    pos = normalized.find(start)
    if pos < 0:
        raise ValueError(f"{b.ad_number} p{page}: phrase not found: {start!r}")
    if end:
        end_pos = normalized.find(" ".join(end.split()), pos + len(start))
        if end_pos < 0:
            raise ValueError(f"{b.ad_number} p{page}: end phrase not found: {end!r}")
    else:
        end_pos = len(normalized)
    return normalized[pos:end_pos].strip()


def extract_modern_models(text: str) -> list[str]:
    return unique(re.findall(r"A(?:300|310|318|319|320|321|330|340|350)-[0-9A-Z/-]+", text))


def extract_appendix_part_numbers(b: AnnotationBuilder) -> list[str]:
    text = " ".join(b.pages[page]["text"] for page in range(6, 11))
    text = re.sub(r"\s*-\s*", "-", text)
    values = unique(re.findall(r"\b[0-9A-Z]{6}-[0-9X]+\b", text))
    # These series are visibly struck through in the rendered Appendix. Native
    # extraction retains their text but not the strikeout, so they must not be
    # treated as affected parts.
    struck_series = {
        "601537", "601854", "601866", "601883", "601889", "601897",
        "6018A4", "601920", "901920", "601958", "6019A3", "6019A8",
        "6019A9", "6019C1",
    }
    return [value for value in values if value.split("-", 1)[0] not in struck_series]


def table_context(
    label: str,
    row_headers: list[str],
    column_headers: list[str],
    footnotes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "table_label": label,
        "row_headers": row_headers,
        "column_headers": column_headers,
        "footnotes": footnotes or [],
    }


def build_2026_0079() -> AnnotationBuilder:
    b = AnnotationBuilder("2026-0079")
    cover = b.evidence(
        "cover",
        1,
        "cover",
        "Airworthiness Directive AD No.: 2026-0079",
        "ATA 23",
        clause_path="cover",
    )
    subject = b.evidence(
        "subject", 1, "cover", "ATA 23", "Manufacturer(s):", clause_path="subject"
    )
    app = b.evidence(
        "app", 1, "applicability", "Applicability:", "Definitions:", clause_path="Applicability"
    )
    defs = b.evidence(
        "defs", 1, "definitions", "Definitions:", clause_path="Definitions"
    )
    reason = b.evidence(
        "reason", 2, "reason", "Reason:", "Required Action(s) and Compliance Time(s):", clause_path="Reason"
    )
    actions = b.evidence(
        "actions", 2, "required_actions_and_compliance_times", "Required Action(s) and Compliance Time(s):", "Credit:", clause_path="paragraph (1)"
    )
    credit = b.evidence(
        "credit", 2, "credit", "Credit:", "Ref. Publications:", clause_path="paragraph (2)"
    )
    refs = b.evidence(
        "refs", 2, "reference_publications", "Ref. Publications:", "Remarks:", clause_path="Ref. Publications"
    )
    remarks = b.evidence(
        "remarks", 2, "remarks", "Remarks:", clause_path="Remarks 1-2"
    )
    contacts = b.evidence(
        "contacts", 3, "remarks", "3. Enquiries regarding this AD", clause_path="Remarks 3-5"
    )

    common_identity_publication(
        b,
        cover_ev=cover,
        subject_ev=subject,
        app_ev=app,
        issue_date="2026-04-17",
        issue_raw="Issued: 17 April 2026",
        effective_date="2026-05-01",
        effective_raw="Effective Date: 01 May 2026",
        design_holder="LUFTHANSA TECHNIK AG",
        subject="ATA 23 – Communications – IFE Control and Service Box – Modification",
        ata_code="23",
        ata_title="Communications",
        manufacturers=[
            ("Airbus, formerly Airbus Industrie", "Airbus", "manufacturer"),
        ],
        type_models=["A319", "A320", "A321"],
        tcds_numbers=[],
        foreign_raw="Not applicable",
        supersedure_value=None,
        supersedure_raw="None",
        supersedure_state="explicit_none",
    )
    app_raw = page_text_between(b, 1, "Applicability:", "Definitions:")
    serial_segment = app_raw.split("manufacture serial number", 1)[1].split(", if modified", 1)[0]
    serial_values = re.findall(r"\b[0-9]{3,4}\b", serial_segment)
    group = b.add_group(
        "STC-conditioned A319/A320/A321 aeroplanes",
        app_raw,
        [app],
        families=["A320 Family"],
        models=["A319-112", "A319-114", "A320-211", "A320-214", "A321-131", "A321-231"],
        serial_restrictions=[
            b.serial(
                "include_list",
                "manufacturer serial number " + ", ".join(serial_values),
                [app],
                values=serial_values,
                condition="Aeroplane is modified by EASA STC 10049524.",
            )
        ],
        configuration_conditions=["Modified by EASA STC 10049524."],
    )
    b.add_definition(
        "The DCS",
        "Lufthansa Technik AG (LHT) Design Change Summary (DCS) AQD-23-DCS-09 revision (rev.) 1.",
        [defs],
    )
    set_unsafe(
        b,
        [reason],
        page_text_between(b, 2, "Reason:", "Required Action(s) and Compliance Time(s):"),
        observed=["The IFE BinBox is installed in an overhead bin with portable oxygen equipment."],
        causes=["Possible IFE BinBox ignition mechanism concurrent with oxygen leakage."],
        conditions=["Installation does not comply with EASA CS 25.869(c) and 25.1441(b)."],
        consequences=["Uncontrolled oxygen fire in the cabin."],
        components=["In-flight entertainment control and service box (IFE BinBox)", "portable oxygen equipment"],
        mitigation=["Relocate the IFE BinBox from the row 5 left OHSC to the row 1 left OHSC."],
    )
    pub_dcs_1 = b.add_publication(
        "other", "Lufthansa Technik AG", "AQD-23-DCS-09", [defs, refs],
        revision="1", publication_date="2026-01-14", title="Design Change Summary",
        roles=["required_method"], later=True,
    )
    pub_dcs_0 = b.add_publication(
        "other", "Lufthansa Technik AG", "AQD-23-DCS-09", [credit, refs],
        revision="0", publication_date="2025-05-20", title="Design Change Summary",
        roles=["previous_action_credit"], later=None,
    )
    b.add_publication(
        "stc", "EASA", "10049524", [cover, app], revision="up to revision 5",
        title="Activation of Wireless IFE System Board Connect",
        roles=["referenced_information"], later=None,
    )
    req1 = b.add_requirement(
        "(1)", [group], ["modification"], "mandatory",
        "Within 30 days after the effective date of this AD, relocate the IFE BinBox in accordance with the instructions of the DCS.",
        [actions], objects=["IFE BinBox"], publications=[pub_dcs_1],
        rules=[b.rule(
            "Within 30 days after the effective date of this AD",
            [actions],
            initial_limits=[b.limit(
                "within", "30 days after the effective date of this AD", [actions],
                quantity=30, unit="calendar_day", reference_event="effective date of this AD",
            )],
        )],
    )
    b.add_credit(
        "Modification of an aeroplane, accomplished before the effective date of this AD in accordance with LHT DCS AQD-23-DCS-09 rev. 0, is acceptable for compliance with paragraph (1).",
        [req1], [pub_dcs_0], [credit],
        conditions=["Accomplished before the effective date of this AD."],
    )
    b.add_contact(
        "amoc_authority", "EASA", "EASA can approve Alternative Methods of Compliance for this AD.", [remarks],
        ["Requested and appropriately substantiated."],
    )
    b.add_contact(
        "regulatory_contact", "EASA Safety Information Section", "E-mail: ADs@easa.europa.eu.", [contacts]
    )
    b.add_contact(
        "technical_contact", "Lufthansa Technik AG (Airworthiness Office)", "E-mail: hamtolmus@lht.dlh.de.", [contacts]
    )
    b.context_evidence.update(
        {
            "/exceptions": [actions],
            "/relationships": [cover],
            "/classification": [subject, app, actions],
        }
    )
    b.finalize(
        families=["A320 Family"], ata_code="23", frequency="one_time",
        table_present=False, compliance_complexity="simple",
        classification_evidence=[subject, app, actions],
    )
    return b


def build_2025_0008() -> AnnotationBuilder:
    b = AnnotationBuilder("2025-0008")
    cover = b.evidence(
        "cover", 1, "cover", "Airworthiness Directive AD No.: 2025-0008", "ATA 27", clause_path="cover"
    )
    subject = b.evidence("subject", 1, "cover", "ATA 27", "Manufacturer(s):", clause_path="subject")
    app = b.evidence("app", 1, "applicability", "Applicability:", "Definitions:", clause_path="Applicability")
    defs = b.evidence("defs", 1, "definitions", "Definitions:", clause_path="Definitions")
    reason = b.evidence("reason", 2, "reason", "Reason:", "Required Action(s) and Compliance Time(s):", clause_path="Reason")
    actions = b.evidence(
        "actions", 2, "required_actions_and_compliance_times", "Required Action(s) and Compliance Time(s):",
        clause_path="paragraphs (1)-(2)",
        table_context=table_context(
            "Table 1 - Affected Parts Replacement",
            ["Compliance Time A", "Compliance Time B: at least 5 000 FC", "Compliance Time B: at least 3 000 and less than 5 000 FC", "Compliance Time B: less than 3 000 FC"],
            ["Aeroplane accumulated FC on the effective date of this AD", "Compliance Time"],
        ),
    )
    refs = b.evidence("refs", 3, "reference_publications", "Ref. Publications:", "Remarks:", clause_path="Ref. Publications")
    remarks = b.evidence("remarks", 3, "remarks", "Remarks:", clause_path="Remarks")
    common_identity_publication(
        b,
        cover_ev=cover, subject_ev=subject, app_ev=app,
        issue_date="2025-01-09", issue_raw="Issued: 09 January 2025",
        effective_date="2025-01-23", effective_raw="Effective Date: 23 January 2025",
        design_holder="AIRBUS S.A.S.",
        subject="ATA 27 – Flight Controls – Flight Control Remote Module – Replacement / Life Limitation",
        ata_code="27", ata_title="Flight Controls",
        manufacturers=[("Airbus", "Airbus", "manufacturer")],
        type_models=["A350-941", "A350-1041"], tcds_numbers=["EASA.A.151"],
        foreign_raw="Not applicable", supersedure_value=None, supersedure_raw="None", supersedure_state="explicit_none",
    )
    app_raw = page_text_between(b, 1, "Applicability:", "Definitions:")
    group = b.add_group(
        "All A350-941 and A350-1041 manufacturer serial numbers", app_raw, [app],
        families=["A350"], models=["A350-941", "A350-1041"],
        serial_restrictions=[b.serial("all", "all manufacturer serial numbers", [app])],
    )
    b.add_definition("Affected parts", "Flight Control Remote Module (FCRM) P/N CA71323-013, CA71323-014, CA71323-015 and CA71323-016.", [defs])
    b.add_definition("Serviceable parts", "An FCRM eligible for installation in accordance with Airbus instructions, which is not an affected part, or an affected part that has accumulated less than 9 000 flight cycles and less than 50 000 flight hours since first installation.", [defs])
    b.add_definition("The SB", "Airbus Service Bulletin A350-27-P066.", [defs])
    b.add_definition("Aeroplane date of manufacture", "The date of transfer of title (ownership) at first delivery to an operator, as referenced in Airbus documentation.", [defs])
    set_unsafe(
        b, [reason], page_text_between(b, 2, "Reason:", "Required Action(s) and Compliance Time(s):"),
        observed=["ECAM messages led to replacement of FCRMs."],
        causes=["Structural fatigue in solder connections."],
        conditions=["Failure of a flight-control remote module."],
        consequences=["Failure of a flight-control actuator and possibly reduced control of the aeroplane."],
        components=["Flight Control Remote Module", "flight-control actuator"],
        mitigation=["Replace each affected FCRM before its life limit."],
    )
    pub_sb = b.add_publication(
        "service_bulletin", "Airbus", "A350-27-P066", [defs, refs],
        revision="original issue", publication_date="2024-11-12",
        roles=["required_method"], later=True,
    )
    replacement_rules = []
    for label, fc_condition, months in [
        ("B1", "At least 5 000 FC on the effective date", 5),
        ("B2", "At least 3 000 FC but less than 5 000 FC on the effective date", 7),
        ("B3", "Less than 3 000 FC on the effective date", 9),
    ]:
        replacement_rules.append(
            b.rule(
                f"Compliance Time A or Compliance Time {label}, whichever occurs later; A is before 9 000 FC or 50 000 FH, whichever occurs first; {fc_condition}: within {months} months after the effective date.",
                [actions], logic="whichever_occurs_later",
                conditions=[fc_condition, "Compliance Time A is the first occurrence of 9 000 FC or 50 000 FH."],
                initial_limits=[
                    b.limit("before", "before 9 000 FC or 50 000 FH, whichever occurs first", [actions], quantity=None, unit="other", reference_event="since first installation of the affected part"),
                    b.limit("within", f"within {months} months after the effective date of this AD", [actions], quantity=months, unit="calendar_month", reference_event="effective date of this AD"),
                ],
            )
        )
    req1 = b.add_requirement(
        "(1)", [group], ["replacement", "limitation"], "mandatory",
        "Within the compliance time specified in Table 1, replace each affected part with a serviceable part in accordance with the instructions of the SB.",
        [actions], objects=["affected FCRM"], publications=[pub_sb], rules=replacement_rules,
    )
    req2 = b.add_requirement(
        "(2)", [group], ["install", "prohibition", "replacement"], "prohibited",
        "From the effective date of this AD, an affected part may be installed on an aeroplane only if it is a serviceable part and is replaced as required by paragraph (1).",
        [actions], objects=["affected FCRM"], conditions=["The part is serviceable and will be replaced in accordance with paragraph (1)."],
        publications=[pub_sb],
        rules=[b.rule(
            "From the effective date of this AD", [actions], conditions=["Continuous installation restriction."],
            initial_limits=[b.limit("from", "from the effective date of this AD", [actions], quantity=None, unit="other", reference_event="effective date of this AD")],
        )],
        follows=[req1],
    )
    b.add_contact("amoc_authority", "EASA", "EASA can approve Alternative Methods of Compliance for this AD.", [remarks], ["Requested and appropriately substantiated."])
    b.add_contact("regulatory_contact", "EASA Safety Information Section", "E-mail: ADs@easa.europa.eu.", [remarks])
    b.add_contact("technical_contact", "Airbus A350 Airworthiness Office", "E-mail: continued-airworthiness.a350@airbus.com.", [remarks])
    b.context_evidence.update({
        "/exceptions": [actions], "/previous_action_credit": [actions, refs],
        "/relationships": [cover], "/classification": [subject, app, actions],
    })
    b.finalize(
        families=["A350"], ata_code="27", frequency="mixed", table_present=True,
        compliance_complexity="table_driven", classification_evidence=[subject, app, actions],
        quality_flags=["complex_table", "complex_compliance"],
    )
    return b


def build_2007_0022() -> AnnotationBuilder:
    b = AnnotationBuilder("2007-0022")
    cover = b.evidence("cover", 1, "cover", "EASA AIRWORTHINESS DIRECTIVE", "ATA 24", clause_path="cover")
    subject = b.evidence("subject", 1, "cover", "ATA 24", "Manufacturer(s):", clause_path="subject")
    app = b.evidence("app", 1, "applicability", "Applicability:", "Reason:", clause_path="Applicability")
    reason = b.evidence("reason", 1, "reason", "Reason:", "Effective Date:", clause_path="Reason")
    effective = b.evidence("effective", 1, "cover", "Effective Date:", clause_path="effective date")
    actions = b.evidence("actions", 2, "compliance", "Compliance:", "Ref. Publications:", clause_path="Compliance")
    refs = b.evidence("refs", 2, "reference_publications", "Ref. Publications:", "Remarks :", clause_path="Ref. Publications")
    remarks = b.evidence("remarks", 2, "remarks", "Remarks :", clause_path="Remarks")
    common_identity_publication(
        b, cover_ev=cover, subject_ev=subject, app_ev=app,
        issue_date="2007-01-22", issue_raw="Date: 22 January 2007",
        effective_date="2007-02-05", effective_raw="Effective Date: 05 February 2007",
        design_holder="AIRBUS", subject="ATA 24 – Electrical System – Prevention against Fuel Tank explosion risks – Fuel Pump Wiring – Modification",
        ata_code="24", ata_title="Electrical System",
        manufacturers=[("AIRBUS (formerly AIRBUS INDUSTRIE)", "Airbus", "manufacturer")],
        type_models=["A300-600ST"], tcds_numbers=["EASA A.014"], foreign_raw="Not applicable",
        supersedure_value=None, supersedure_raw="Not applicable", supersedure_state="explicit_none",
    )
    b.record["publication"]["effective_date"]["evidence_ids"] = [effective]
    app_raw = page_text_between(b, 1, "Applicability:", "Reason:")
    group = b.add_group(
        "A300F4-608ST without SB A300-24-9008", app_raw, [app],
        families=["A300-600ST"], models=["A300F4-608ST"],
        serial_restrictions=[b.serial("all", "all serial numbers", [app])],
        exclusions=["Aircraft that have received application of Airbus SB A300-24-9008."],
    )
    set_unsafe(
        b, [reason], page_text_between(b, 1, "Reason:", "Effective Date:"),
        observed=["TWA800 fuel-tank explosion prompted an SFAR 88 design review."], causes=["Potential short circuit in fuel-pump wiring."],
        conditions=["Fuel-pump wiring susceptible to short circuit."], consequences=["Fuel-tank explosion risk."],
        components=["route 1P and 2P harnesses", "fuel pump wiring"], mitigation=["Modify the affected harness routes."],
    )
    pub = b.add_publication("service_bulletin", "Airbus", "A300-24-9008", [actions, refs], revision="original issue", roles=["required_method"], later=True)
    b.add_requirement(
        None, [group], ["modification"], "mandatory",
        "Not later than 31 October 2010, modify route 1P and 2P harnesses 631/633VB in the left wing and 632/634VB in the right wing in accordance with SB A300-24-9008.",
        [actions], objects=["route 1P and 2P harnesses 631/633VB and 632/634VB"], publications=[pub],
        rules=[b.rule(
            "Not later than 31 October 2010", [actions],
            initial_limits=[b.limit("not_later_than", "31 October 2010", [actions], quantity=None, unit="calendar_date", calendar_date="2010-10-31")],
        )],
    )
    b.add_contact("amoc_authority", "EASA", "The responsible EASA manager may accept Alternative Methods of Compliance for this AD.", [remarks], ["Requested and appropriately substantiated."])
    b.add_contact("regulatory_contact", "EASA Certification Directorate", "E-mail: ADs@easa.europa.eu.", [remarks])
    b.add_contact("technical_contact", "Airbus SAS Airworthiness Office – EAL", "Fax: +33 5 61 93 45 80.", [remarks])
    b.context_evidence.update({
        "/definitions": [app, reason], "/exceptions": [actions], "/previous_action_credit": [actions, refs],
        "/relationships": [cover], "/classification": [subject, app, actions],
    })
    b.finalize(
        families=["A300-600ST"], ata_code="24", frequency="one_time", table_present=False,
        compliance_complexity="simple", classification_evidence=[subject, app, actions],
    )
    return b


def build_2009_0025() -> AnnotationBuilder:
    b = AnnotationBuilder("2009-0025")
    cover = b.evidence("cover", 1, "cover", "EASA AIRWORTHINESS DIRECTIVE", "ATA 57", clause_path="cover")
    subject = b.evidence("subject", 1, "cover", "ATA 57", "Manufacturer(s):", clause_path="subject")
    app = b.evidence("app", 1, "applicability", "Applicability:", "Reason:", clause_path="Applicability")
    reason = b.evidence("reason", 1, "reason", "Reason:", clause_path="Reason")
    correction = b.evidence("correction", 2, "other", "This Correction is issued", "Effective Date:", clause_path="correction notice")
    effective = b.evidence("effective", 2, "cover", "Effective Date:", "Required Action(s)", clause_path="effective date")
    actions = b.evidence("actions", 2, "required_actions_and_compliance_times", "Required Action(s)", "Ref. Publications:", clause_path="paragraphs 1-3")
    refs = b.evidence("refs", 2, "reference_publications", "Ref. Publications:", clause_path="Ref. Publications")
    remarks = b.evidence("remarks", 3, "remarks", "Remarks :", clause_path="Remarks")
    common_identity_publication(
        b, cover_ev=cover, subject_ev=subject, app_ev=app,
        issue_date="2009-02-10", issue_raw="Date: 10 February 2009",
        effective_date="2009-02-24", effective_raw="Effective Date: 24 February 2009",
        design_holder="AIRBUS",
        subject="ATA 57 – Wings – Flap Track No.1 Pendulum Assembly – Inspection / Replacement",
        ata_code="57", ata_title="Wings",
        manufacturers=[("AIRBUS (formerly AIRBUS INDUSTRIE)", "Airbus", "manufacturer")],
        type_models=["A318", "A319", "A320", "A321"], tcds_numbers=["EASA.A.064"],
        foreign_raw="Not applicable", supersedure_value=None, supersedure_raw="None", supersedure_state="explicit_none",
    )
    b.record["publication"]["effective_date"]["evidence_ids"] = [effective]
    b.record["ad_identity"]["correction_date"] = grounded_date("2009-02-11", "[Corrected: 11 February 2009]", [cover])
    b.record["ad_identity"]["version_label"] = "Corrected 11 February 2009"
    b.record["ad_identity"]["evidence_ids"] = unique([cover, subject, correction])
    app_raw = page_text_between(b, 1, "Applicability:", "Reason:")
    models = extract_modern_models(app_raw)
    group = b.add_group(
        "All listed A318/A319/A320/A321 models", app_raw, [app],
        families=["A320 Family"], models=models,
        serial_restrictions=[b.serial("all", "all manufacturer serial numbers", [app])],
    )
    set_unsafe(
        b, [reason], page_text_between(b, 1, "Reason:"),
        observed=["A flap-track No.1 pendulum bearing migrated out of position."],
        causes=["In-service bearing replacement without the necessary special tools, fixtures and equipment."],
        conditions=["Pendulum-bearing migration or incorrect swaging."],
        consequences=["Bearing/flap-track separation, detachment of the affected flap surface, and consequent loss of control."],
        components=["flap track No.1 pendulum assembly", "pendulum bearing", "flap surface"],
        mitigation=["One-time inspection and replacement or corrective action when migration or incorrect swaging is found."],
    )
    pub_a321 = b.add_publication(
        "service_bulletin", "Airbus", "A320-57-1144", [actions, refs],
        revision="original issue or Revision 1", publication_date=None,
        roles=["required_method"], later=True,
    )
    pub_a318_320 = b.add_publication(
        "alert_service_bulletin", "Airbus", "A320-57A1146", [actions, refs],
        revision="original issue", publication_date="2007-09-21",
        roles=["required_method"], later=True,
    )
    req1 = b.add_requirement(
        "1.a", [group], ["inspection"], "mandatory",
        "Within 600 flight hours after the effective date, inspect the flap track No.1 pendulum assembly using SB A320-57A1146 for A318/A319/A320 or SB A320-57-1144 for A321, as applicable.",
        [actions], objects=["flap track No.1 pendulum assembly"],
        conditions=["Use the service bulletin applicable to the aircraft model."],
        publications=[pub_a318_320, pub_a321],
        rules=[b.rule(
            "Within 600 flight hours after the effective date of this AD", [actions],
            initial_limits=[b.limit("within", "600 flight hours after the effective date of this AD", [actions], quantity=600, unit="flight_hour", reference_event="effective date of this AD")],
        )],
    )
    req2 = b.add_requirement(
        "1.b", [group], ["replacement"], "conditional",
        "If a pendulum-assembly bearing has migrated, replace the affected flap-track pendulum assembly before further flight.",
        [actions], objects=["affected flap track pendulum assembly"],
        conditions=["Bearing migration is found."],
        rules=[b.rule(
            "before further flight", [actions], conditions=["Bearing migration is found."],
            initial_limits=[b.limit("before", "before further flight", [actions], quantity=None, unit="before_next_flight")],
        )], parent=req1,
    )
    req3 = b.add_requirement(
        "1.c", [group], ["contact_manufacturer", "repair"], "conditional",
        "If a bearing is found incorrectly swaged, contact Airbus before next flight and accomplish the relevant corrective actions using the applicable service bulletin.",
        [actions], objects=["incorrectly swaged pendulum bearing"],
        conditions=["A pendulum-assembly bearing is found incorrectly swaged."],
        publications=[pub_a318_320, pub_a321],
        rules=[b.rule(
            "before next flight contact Airbus for further instructions and accomplish the relevant corrective actions", [actions],
            conditions=["A bearing is found incorrectly swaged."],
            initial_limits=[b.limit("before", "before next flight", [actions], quantity=None, unit="before_next_flight")],
        )], parent=req1,
    )
    req4 = b.add_requirement(
        "3", [group], ["replacement", "install", "prohibition", "records_review"], "prohibited",
        "After the effective date, do not replace a bearing in the flap-track pendulum assembly or install a pendulum assembly unless it is new manufacture or records demonstrate that its bearing has not been replaced or re-swaged since new manufacture.",
        [actions], objects=["pendulum bearing", "pendulum assembly"],
        conditions=["Allowed only for a new-manufacture assembly or with qualifying records."],
        rules=[b.rule(
            "After the effective date of this AD", [actions], conditions=["Continuous parts-installation restriction."],
            initial_limits=[b.limit("after", "after the effective date of this AD", [actions], quantity=None, unit="other", reference_event="effective date of this AD")],
        )],
    )
    for text in [
        "Aircraft originally delivered after the effective date of this AD.",
        "Records demonstrate that no pendulum-assembly bearing has been replaced or re-swaged since original delivery.",
        "The aircraft was inspected before the effective date with the applicable SB and records show no subsequent installation of an assembly whose bearing was replaced or re-swaged since new manufacture.",
        "The aircraft was inspected before the effective date with the applicable SB and records show no subsequent bearing replacement or re-swaging.",
    ]:
        b.add_exception(text, [req1, req2, req3], [actions])
    b.record["annotation_metadata"]["uncertainty_flags"].append(
        "correction_target_publication_not_present_in_pilot"
    )
    b.record["annotation_metadata"]["notes"].append(
        "The PDF explicitly identifies this as a correction, but the distinct uncorrected publication is not present in the pilot; no correction relationship target was fabricated."
    )
    b.add_contact("amoc_authority", "EASA", "EASA can approve Alternative Methods of Compliance for this AD.", [remarks], ["Requested and appropriately substantiated."])
    b.add_contact("regulatory_contact", "EASA Airworthiness Directives, Safety Management & Research Section", "E-mail: ADs@easa.europa.eu.", [remarks])
    b.add_contact("technical_contact", "Airbus Airworthiness Office – EAS", "Fax: +33 5 61 93 44 51; E-mail: account.airworth-eas@airbus.com.", [remarks])
    b.context_evidence.update({
        "/definitions": [app, reason], "/previous_action_credit": [actions, refs], "/relationships": [cover, correction],
        "/classification": [subject, app, reason, actions],
    })
    b.finalize(
        families=["A320 Family"], ata_code="57", frequency="mixed", table_present=False,
        compliance_complexity="conditional_branches", classification_evidence=[subject, app, reason, actions],
        quality_flags=["complex_applicability", "complex_compliance"],
    )
    return b


def build_2008_0012() -> AnnotationBuilder:
    b = AnnotationBuilder("2008-0012")
    cover = b.evidence("cover", 1, "cover", "EASA AIRWORTHINESS DIRECTIVE", "ATA 55", clause_path="cover")
    subject = b.evidence("subject", 1, "cover", "ATA 55", "Manufacturer:", clause_path="subject")
    app = b.evidence("app", 1, "applicability", "Applicability:", clause_path="Applicability and Notes 1-3")
    reason = b.evidence("reason", 2, "reason", "Reason:", "Effective Date:", clause_path="Reason")
    effective = b.evidence("effective", 2, "cover", "Effective Date:", "Compliance:", clause_path="effective date")
    actions = b.evidence("actions", 2, "compliance", "Compliance:", clause_path="paragraphs 1-3")
    refs = b.evidence("refs", 3, "reference_publications", "Ref. Publications:", "Remarks :", clause_path="Ref. Publications")
    remarks = b.evidence("remarks", 3, "remarks", "Remarks :", clause_path="Remarks")
    common_identity_publication(
        b, cover_ev=cover, subject_ev=subject, app_ev=app,
        issue_date="2008-01-14", issue_raw="Date: 14 January 2008",
        effective_date="2008-01-28", effective_raw="Effective Date: 28 January 2008",
        design_holder="AIRBUS",
        subject="ATA 55 – Stabilizers – Carbon Fiber Reinforced Plastic (CFRP) Rudder – Inspection / Repair",
        ata_code="55", ata_title="Stabilizers",
        manufacturers=[("AIRBUS (formerly AIRBUS INDUSTRIE)", "Airbus", "manufacturer")],
        type_models=["A330-300", "A340-200", "A340-300"], tcds_numbers=["EASA A.004", "EASA A.015"],
        foreign_raw="Not applicable", supersedure_value=None, supersedure_raw="None", supersedure_state="explicit_none",
    )
    b.record["publication"]["effective_date"]["evidence_ids"] = [effective]
    app_raw = page_text_between(b, 1, "Applicability:")
    aircraft_group = b.add_group(
        "Affected A330/A340 aeroplanes", app_raw, [app], families=["A330", "A340"],
        models=["A330-300", "A340-200", "A340-300"],
        serial_restrictions=[b.serial("all", "all serial numbers", [app], condition="CFRP rudder P/N A55471500 series is fitted.")],
        part_numbers=["A55471500 series"],
        configuration_conditions=["CFRP rudder P/N A55471500 series is fitted."],
    )
    spare_group = b.add_group(
        "Spare CFRP rudders", "any rudder PN A55471500 series held as a spare", [app],
        families=["A330", "A340"], models=[], part_numbers=["A55471500 series"],
        configuration_conditions=["The rudder is held as a spare."],
    )
    set_unsafe(
        b, [reason], page_text_between(b, 2, "Reason:", "Effective Date:"),
        observed=["Fluid ingress and/or inner-skin disbond damage was found on rudders."],
        causes=["Fluid ingress and inner-skin disbond damage."],
        conditions=["Damage in rudder hoisting-point, trailing-edge screw, or Z-profile areas."],
        consequences=["Reduced structural integrity of the rudder."],
        components=["CFRP rudder", "rudder Z-profile", "rudder hoisting points", "trailing-edge screw areas"],
        mitigation=["One-time and repetitive structural inspections, reporting, and repair."],
    )
    p1 = b.add_publication("service_bulletin", "Airbus", "A330-55-3037", [actions, refs], revision="original issue", roles=["required_method"], later=True)
    p2 = b.add_publication("service_bulletin", "Airbus", "A340-55-4033", [actions, refs], revision="original issue", roles=["required_method"], later=True)
    p3 = b.add_publication("service_bulletin", "Airbus", "A330-55-3038", [actions, refs], revision="original issue", roles=["required_method"], later=True)
    p4 = b.add_publication("service_bulletin", "Airbus", "A340-55-4034", [actions, refs], revision="original issue", roles=["required_method"], later=True)
    req1 = b.add_requirement(
        "1.1", [aircraft_group], ["inspection"], "mandatory",
        "Within 500 flight cycles or 6 months from the effective date, whichever occurs first, perform a one-time special detailed inspection at rudder hoisting points and trailing-edge screw areas.",
        [actions], objects=["rudder hoisting points", "trailing-edge screw areas"], publications=[p1, p2],
        rules=[b.rule(
            "within 500 FC or 6 months from the effective date, whichever occurs first", [actions], logic="whichever_occurs_first",
            initial_limits=[
                b.limit("within", "500 Flight Cycles", [actions], quantity=500, unit="flight_cycle", reference_event="effective date of this AD"),
                b.limit("within", "6 months", [actions], quantity=6, unit="calendar_month", reference_event="effective date of this AD"),
            ],
        )],
    )
    req2 = b.add_requirement(
        "1.2", [aircraft_group], ["reporting"], "conditional",
        "If no damage is found, report to Airbus within 10 days after the inspection.",
        [actions], conditions=["No damage is found during paragraph 1.1 inspection."], publications=[p1, p2], parent=req1,
        rules=[b.rule(
            "within 10 days after the inspection", [actions], conditions=["No damage is found."],
            initial_limits=[b.limit("within", "10 days after the inspection", [actions], quantity=10, unit="calendar_day", reference_event="paragraph 1.1 inspection")],
        )],
    )
    req3 = b.add_requirement(
        "1.3", [aircraft_group], ["reporting", "contact_manufacturer", "repair"], "conditional",
        "If findings exist, report to Airbus, obtain repair instructions, and accomplish the repair within the timescale in Flow Chart 1.",
        [actions], conditions=["Damage is found."], publications=[p1, p2], parent=req1,
        rules=[b.rule("Accomplish the repair within the timescale(s) indicated in Flow Chart 1", [actions], conditions=["Findings are present."], initial_limits=[])],
    )
    req4 = b.add_requirement(
        "2.1", [aircraft_group], ["inspection"], "mandatory",
        "Within 500 flight cycles or 6 months from the effective date, whichever occurs first, and thereafter at intervals not exceeding 5 000 flight cycles, inspect along the rudder Z-profile.",
        [actions], objects=["rudder Z-profile"], publications=[p3, p4],
        rules=[b.rule(
            "Within 500 FC or 6 months from the effective date, whichever occurs first, and thereafter at intervals not exceeding 5 000 FC", [actions], logic="whichever_occurs_first",
            initial_limits=[
                b.limit("within", "500 FC", [actions], quantity=500, unit="flight_cycle", reference_event="effective date of this AD"),
                b.limit("within", "6 months", [actions], quantity=6, unit="calendar_month", reference_event="effective date of this AD"),
            ],
            repetitive_intervals=[b.limit("not_to_exceed", "5 000 FC", [actions], quantity=5000, unit="flight_cycle", reference_event="previous paragraph 2.1 inspection")],
        )],
    )
    req5 = b.add_requirement(
        "2.2", [aircraft_group], ["reporting"], "conditional",
        "If no damage is found, report to Airbus within 10 days after each inspection.",
        [actions], conditions=["No damage is found during paragraph 2.1 inspection."], publications=[p3, p4], parent=req4,
        rules=[b.rule(
            "within 10 days after each inspection", [actions], conditions=["No damage is found."],
            initial_limits=[b.limit("within", "10 days after each inspection", [actions], quantity=10, unit="calendar_day", reference_event="each paragraph 2.1 inspection")],
        )],
    )
    req6 = b.add_requirement(
        "2.3", [aircraft_group], ["test_or_check", "repair", "reporting"], "conditional",
        "If findings occur, check them, apply associated corrective actions within the Flow Chart 1 timescales, and report within 10 days after inspection or repair.",
        [actions], conditions=["Findings occur during a paragraph 2.1 inspection."], publications=[p3, p4], parent=req4,
        rules=[b.rule(
            "Within 10 days after the inspection / repair, submit a report", [actions], conditions=["Findings occur; corrective-action times are governed by Flow Chart 1."],
            initial_limits=[b.limit("within", "10 days after the inspection / repair", [actions], quantity=10, unit="calendar_day", reference_event="inspection or repair")],
        )],
    )
    req7 = b.add_requirement(
        "3", [aircraft_group, spare_group], ["install", "prohibition", "inspection", "repair"], "prohibited",
        "After 6 months from the effective date, do not install a spare rudder P/N A55471500 series unless it has been inspected and, as necessary, repaired under the applicable service bulletins.",
        [actions], objects=["spare rudder P/N A55471500 series"], conditions=["Installation is permitted only after required inspection and repair."],
        publications=[p1, p2, p3, p4],
        rules=[b.rule(
            "After 6 months from the effective date of this AD", [actions],
            initial_limits=[b.limit("after", "6 months from the effective date of this AD", [actions], quantity=6, unit="calendar_month", reference_event="effective date of this AD")],
        )],
    )
    b.add_contact("amoc_authority", "EASA", "EASA can accept Alternative Methods of Compliance for this AD.", [remarks], ["Requested and appropriately substantiated."])
    b.add_contact("regulatory_contact", "EASA Airworthiness Directive Focal Point", "E-mail: ADs@easa.europa.eu.", [remarks])
    b.add_contact("technical_contact", "Airbus SAS Airworthiness Office – EAL", "E-mail: airworthiness.A330-A340@airbus.com.", [remarks])
    b.context_evidence.update({
        "/definitions": [app, reason], "/exceptions": [actions], "/previous_action_credit": [actions, refs],
        "/relationships": [cover], "/classification": [subject, app, reason, actions],
    })
    b.finalize(
        families=["A330", "A340"], ata_code="55", frequency="mixed", table_present=False,
        compliance_complexity="conditional_branches", classification_evidence=[subject, app, reason, actions],
        quality_flags=["complex_applicability", "complex_compliance"],
    )
    return b


def build_2006_0047() -> AnnotationBuilder:
    b = AnnotationBuilder("2006-0047")
    cover = b.evidence("cover", 1, "cover", "EASA AIRWORTHINESS DIRECTIVE", "ATA 25", clause_path="cover")
    subject = b.evidence("subject", 1, "cover", "ATA 25", "Manufacturer(s):", clause_path="subject")
    app = b.evidence("app", 1, "applicability", "Applicability:", "Reason:", clause_path="Applicability")
    reason1 = b.evidence("reason1", 1, "reason", "Reason:", clause_path="Reason")
    reason2 = b.evidence("reason2", 2, "reason", "takes over the AD F-2004-140 inspection requirements", "Effective Date:", clause_path="Reason continuation")
    effective = b.evidence("effective", 2, "cover", "Effective Date:", "Compliance:", clause_path="effective date")
    actions1 = b.evidence("actions1", 2, "compliance", "Compliance:", clause_path="paragraphs 1.1-1.5")
    actions2 = b.evidence("actions2", 3, "compliance", "Note 2", "Ref. Publications:", clause_path="Note 2 and paragraphs 2.1-2.2")
    refs = b.evidence("refs", 3, "reference_publications", "Ref. Publications:", "Remarks :", clause_path="Ref. Publications")
    remarks = b.evidence("remarks", 3, "remarks", "Remarks :", clause_path="Remarks 1-3")
    technical = b.evidence("technical", 4, "remarks", "4. For any question concerning the technical content", clause_path="Remark 4")
    common_identity_publication(
        b, cover_ev=cover, subject_ev=subject, app_ev=app,
        issue_date="2006-02-16", issue_raw="Date: 16 February 2006",
        effective_date="2006-03-01", effective_raw="Effective Date: 01 March 2006",
        design_holder="AIRBUS SAS",
        subject="ATA 25 – Equipment/Furnishings – Inspection and modification of cockpit instrument panel",
        ata_code="25", ata_title="Equipment/Furnishings",
        manufacturers=[("AIRBUS SAS, AIRBUS INDUSTRIE", "Airbus", "manufacturer")],
        type_models=["A330"], tcds_numbers=["EASA A.004"], foreign_raw="NONE",
        supersedure_value="DGAC AD F-2004-140(B)", supersedure_raw="DGAC AD F-2004-140(B)", supersedure_state="present",
    )
    b.record["publication"]["effective_date"]["evidence_ids"] = [effective]
    app_raw = page_text_between(b, 1, "Applicability:", "Reason:")
    group = b.add_group(
        "A330 without production modification 53446 or in-service SB A330-25-3249", app_raw, [app],
        families=["A330"], models=["A330 (all certified models)"],
        serial_restrictions=[b.serial("all", "all serial numbers", [app])],
        exclusions=["Airbus modification 53446 embodied in production.", "Airbus SB A330-25-3249 embodied in service."],
    )
    set_unsafe(
        b, [reason1, reason2],
        page_text_between(b, 1, "Reason:") + " " + page_text_between(b, 2, "takes over the AD F-2004-140 inspection requirements", "Effective Date:"),
        observed=["Bracket P/N F2511012920000 was cracked on two aeroplanes; both vertical flanges were completely broken on one."],
        causes=["Bending crack caused by bracket tightening combined with lateral loads from differential pressure and inertia."],
        conditions=["Hidden bracket failure combined with failure of the horizontal beam."],
        consequences=["Collapse of the left cockpit-panel section and, in the worst case, reduced controllability."],
        components=["LH cockpit instrument-panel bracket P/N F2511012920000", "horizontal beam"],
        mitigation=["Repetitive detailed inspections and mandatory replacement with a reinforced titanium bracket."],
    )
    pub_inspect = b.add_publication(
        "service_bulletin", "Airbus", "A330-25-3227", [actions1, actions2, refs],
        revision="Revision 01", roles=["required_method", "previous_action_credit"], later=True,
    )
    pub_modify = b.add_publication(
        "service_bulletin", "Airbus", "A330-25-3249", [actions1, actions2, refs],
        revision=None, roles=["required_method"], later=True,
    )
    r11 = b.add_requirement(
        "1.1", [group], ["inspection"], "mandatory",
        "Before accumulation of 16 500 flight cycles, perform a detailed visual inspection of the left-hand bracket without removing fasteners.",
        [actions1], objects=["LH bracket P/N F2511012920000"], publications=[pub_inspect],
        rules=[b.rule("before accumulation of 16 500 flight cycles", [actions1], initial_limits=[b.limit("before", "16 500 flight cycles", [actions1], quantity=16500, unit="flight_cycle", reference_event="bracket accumulation")])],
    )
    r12 = b.add_requirement(
        "1.2", [group], ["inspection"], "conditional",
        "If both bracket flanges are fully broken, perform a detailed visual inspection of the horizontal beam.",
        [actions1], objects=["horizontal beam"], conditions=["Both bracket flanges are fully broken."], publications=[pub_inspect],
        rules=[b.rule("If the two flanges of the bracket are fully broken", [actions1], conditions=["Both bracket flanges are fully broken."], initial_limits=[])], parent=r11,
    )
    r12a = b.add_requirement(
        "1.2 first bullet", [group], ["contact_manufacturer"], "conditional",
        "If a crack is found on the horizontal beam, contact Airbus before next flight.",
        [actions1], objects=["horizontal beam"], conditions=["A horizontal-beam crack is found."], parent=r12,
        rules=[b.rule("before next flight", [actions1], conditions=["A horizontal-beam crack is found."], initial_limits=[b.limit("before", "before next flight", [actions1], quantity=None, unit="before_next_flight")])],
    )
    r12b = b.add_requirement(
        "1.2 second bullet", [group], ["modification", "repair"], "conditional",
        "If no horizontal-beam crack is found, apply Airbus SB A330-25-3249 before next flight.",
        [actions1], objects=["LH instrument-panel bracket"], conditions=["No horizontal-beam crack is found."], publications=[pub_modify], parent=r12,
        rules=[b.rule("before next flight", [actions1], conditions=["No horizontal-beam crack is found."], initial_limits=[b.limit("before", "before next flight", [actions1], quantity=None, unit="before_next_flight")])],
    )
    r13a = b.add_requirement(
        "1.3 first dash", [group], ["replacement"], "conditional",
        "If any bracket crack is found during paragraph 1.1 inspection, replace the affected bracket before next flight.",
        [actions1], objects=["affected bracket"], conditions=["Any crack is found on the bracket."], publications=[pub_inspect], parent=r11,
        rules=[b.rule("before next flight", [actions1], conditions=["Any bracket crack is found."], initial_limits=[b.limit("before", "before next flight", [actions1], quantity=None, unit="before_next_flight")])],
    )
    r13b = b.add_requirement(
        "1.3 second dash", [group], ["inspection"], "conditional",
        "Inspect the newly installed bracket at 16 500 flight cycles from the last replacement.",
        [actions1], objects=["newly installed bracket"], conditions=["A bracket was replaced under paragraph 1.3."], publications=[pub_inspect], parent=r13a,
        rules=[b.rule("at a threshold of 16 500 FC from the last replacement", [actions1], conditions=["A bracket was replaced."], initial_limits=[b.limit("at", "16 500 FC from the last replacement", [actions1], quantity=16500, unit="flight_cycle", reference_event="last bracket replacement")])],
    )
    r13c = b.add_requirement(
        "1.3 third dash", [group], ["inspection", "repair", "replacement"], "conditional",
        "According to the inspection result, perform the actions in paragraph 1.2, 1.3, or 1.4.",
        [actions1], conditions=["Based on results of the new-bracket inspection."], publications=[pub_inspect, pub_modify], parent=r13b,
        rules=[b.rule("according to the results of this inspection", [actions1], conditions=["Apply the applicable branch in paragraph 1.2, 1.3 or 1.4."], initial_limits=[])],
    )
    r14 = b.add_requirement(
        "1.4", [group], ["inspection"], "mandatory",
        "If no crack is detected, repeat the paragraph 1.1 inspection at intervals not exceeding 13 800 flight cycles.",
        [actions1], objects=["LH bracket"], conditions=["No crack is detected."], publications=[pub_inspect], parent=r11,
        rules=[b.rule(
            "repeat the inspection at intervals not exceeding 13 800 FC", [actions1], conditions=["No crack is detected."],
            repetitive_intervals=[b.limit("not_to_exceed", "13 800 FC", [actions1], quantity=13800, unit="flight_cycle", reference_event="previous bracket inspection")],
        )],
    )
    r15 = b.add_requirement(
        "1.5", [group], ["reporting"], "mandatory",
        "Report any cracked or broken bracket occurrence to Airbus.", [actions1], objects=["cracked or broken bracket"],
        rules=[b.rule("Report any cracked or broken bracket occurrence to AIRBUS", [actions1], initial_limits=[])],
    )
    r21 = b.add_requirement(
        "2.1", [group], ["remove"], "mandatory",
        "No later than 31 January 2012, remove the concerned bracket from the left-hand instrument-panel section.",
        [actions2], objects=["concerned LH instrument-panel bracket"], publications=[pub_modify],
        rules=[b.rule("no later than 31 January 2012", [actions2], initial_limits=[b.limit("not_later_than", "31 January 2012", [actions2], quantity=None, unit="calendar_date", calendar_date="2012-01-31")])],
    )
    r22 = b.add_requirement(
        "2.2", [group], ["inspection"], "mandatory",
        "Perform a detailed visual inspection of the removed bracket.",
        [actions2], objects=["removed bracket"], publications=[pub_modify], parent=r21,
        rules=[b.rule("Perform a detailed visual inspection of the removed bracket", [actions2], initial_limits=[])],
    )
    r22a = b.add_requirement(
        "2.2 broken-flange branch", [group], ["inspection", "contact_manufacturer"], "conditional",
        "If both flanges are fully broken, inspect the horizontal beam and, if a crack is found, contact Airbus before next flight.",
        [actions2], objects=["horizontal beam"], conditions=["Both removed-bracket flanges are fully broken."], publications=[pub_modify], parent=r22,
        rules=[b.rule("if a crack is found on the horizontal beam, contact AIRBUS before next flight", [actions2], conditions=["Both flanges are broken and a beam crack is found."], initial_limits=[b.limit("before", "before next flight", [actions2], quantity=None, unit="before_next_flight")])],
    )
    r22b = b.add_requirement(
        "2.2 replacement branches", [group], ["replacement", "modification"], "conditional",
        "If no horizontal-beam crack is found, or if the bracket flanges are not fully broken, install a new reinforced bracket in accordance with SB A330-25-3249.",
        [actions2], objects=["new reinforced bracket"], conditions=["No horizontal-beam crack is found, or both flanges are not fully broken."], publications=[pub_modify], parent=r22,
        rules=[b.rule("replace the bracket by a new reinforced bracket", [actions2], conditions=["Applicable paragraph 2.2 replacement branch."], initial_limits=[])],
    )
    r22b_record = next(item for item in b.record["requirements"] if item["requirement_id"] == r22b)
    r22b_record["terminating_action"] = b.terminating_action(
        "Replacement by a new reinforced bracket under SB A330-25-3249 cancels the repetitive-inspection requirements.",
        [r14], [actions2], "full",
    )
    b.add_credit(
        "Accomplishment of SB A330-25-3227 at original issue is acceptable for the initial inspection requirements of paragraphs 1.1, 1.2 or 1.3, provided the additional corrective actions for two fully broken flanges are applied; repetitive inspections continue under Revision 01.",
        [r11, r12, r12a, r12b, r13a, r13b, r13c], [pub_inspect], [actions2],
        conditions=["Additional corrective actions are applied when both bracket flanges are fully broken.", "Repetitive inspections and subsequent actions continue under Revision 01."],
    )
    b.add_relationship("supersedes", "DGAC-2004-F-140-B", "Supersedure: DGAC AD F-2004-140(B)", [cover], source="structured_supersedure_field")
    b.add_relationship("retains_requirements_of", "DGAC-2004-F-140-B", "takes over the AD F-2004-140 inspection requirements", [reason2], source="explicit_directional_sentence")
    b.add_contact("amoc_authority", "EASA", "The responsible EASA manager may accept Alternative Methods of Compliance for this AD.", [remarks], ["Requested and appropriately substantiated."])
    b.add_contact("regulatory_contact", "EASA Certification Directorate", "E-mail: ADs@easa.eu.int.", [remarks])
    b.add_contact("technical_contact", "Airbus SAS Airworthiness Office", "Phone: +33 5 61 93 36 96; Fax: +33 5 61 93 44 51.", [technical])
    b.context_evidence.update({"/definitions": [app, reason1], "/exceptions": [actions1, actions2], "/classification": [subject, app, reason1, actions1, actions2]})
    b.finalize(
        families=["A330"], ata_code="25", frequency="mixed", table_present=False,
        compliance_complexity="mixed", classification_evidence=[subject, app, reason1, actions1, actions2],
        quality_flags=["complex_compliance"],
    )
    return b


def build_2007_0278() -> AnnotationBuilder:
    b = AnnotationBuilder("2007-0278")
    cover = b.evidence("cover", 1, "cover", "EASA AIRWORTHINESS DIRECTIVE", "ATA 28", clause_path="cover")
    subject = b.evidence("subject", 1, "cover", "ATA 28", "Manufacturer:", clause_path="subject")
    app = b.evidence("app", 1, "applicability", "Applicability:", "Reason:", clause_path="Applicability")
    reason1 = b.evidence("reason1", 1, "reason", "Reason:", clause_path="Reason")
    reason2 = b.evidence("reason2", 2, "reason", "modification of electrical bonding", "Effective Date:", clause_path="Reason continuation and correction notice")
    effective = b.evidence("effective", 2, "cover", "Effective Date:", "Compliance:", clause_path="effective date")
    action1 = b.evidence("action1", 2, "compliance", "Compliance:", "Action n°2 applicable to:", clause_path="Action 1")
    action2a = b.evidence("action2a", 2, "compliance", "Action n°2 applicable to:", clause_path="Action 2 applicability")
    action2b = b.evidence("action2b", 3, "compliance", "production or modified in-service", "Action n°3 applicable to:", clause_path="Action 2 requirements and credit")
    action3 = b.evidence("action3", 3, "compliance", "Action n°3 applicable to:", "Action n°4 applicable to:", clause_path="Action 3")
    action4a = b.evidence("action4a", 3, "compliance", "Action n°4 applicable to:", clause_path="Action 4")
    action4b = b.evidence("action4b", 4, "compliance", "1996 (\"solution A\")", "Action n°5 applicable to:", clause_path="Action 4 alternative compliance")
    action5 = b.evidence("action5", 4, "compliance", "Action n°5 applicable to:", "Ref. Publications:", clause_path="Action 5")
    refs = b.evidence("refs", 4, "reference_publications", "Ref. Publications:", "Remarks :", clause_path="Ref. Publications")
    remarks = b.evidence("remarks", 4, "remarks", "Remarks :", clause_path="Remarks")
    common_identity_publication(
        b, cover_ev=cover, subject_ev=subject, app_ev=app,
        issue_date="2007-11-05", issue_raw="Date: 05 November 2007",
        effective_date="2007-11-19", effective_raw="Effective Date: 19 November 2007",
        design_holder="AIRBUS",
        subject="ATA 28 – Fuel – Fuel tanks – Prevention against Fuel Explosion Risks – Modification / Installation",
        ata_code="28", ata_title="Fuel",
        manufacturers=[("AIRBUS (formerly AIRBUS INDUSTRIE)", "Airbus", "manufacturer")],
        type_models=["A330", "A340-200", "A340-300"], tcds_numbers=["EASA A.004", "EASA A.015"],
        foreign_raw="Not applicable", supersedure_value="EASA AD 2006-0322", supersedure_raw="EASA AD 2006-0322 dated 18 October 2006.", supersedure_state="present",
    )
    b.record["publication"]["effective_date"]["evidence_ids"] = [effective]
    b.record["ad_identity"]["correction_date"] = grounded_date("2007-11-08", "[Corrected: 08 November 2007]", [cover])
    b.record["ad_identity"]["version_label"] = "Corrected 08 November 2007"
    b.record["ad_identity"]["evidence_ids"] = unique([cover, subject, reason2])
    general_raw = page_text_between(b, 1, "Applicability:", "Reason:")
    general = b.add_group(
        "All A330/A340-200/A340-300 aeroplanes", general_raw, [app],
        families=["A330", "A340"], models=["A330 (all certified models)", "A340-200 (all certified models)", "A340-300 (all certified models)"],
        serial_restrictions=[b.serial("all", "all serial numbers", [app])],
    )
    g1 = b.add_group(
        "Action 1 aeroplanes", page_text_between(b, 2, "Action n°1 applicable to:", "Action n°2 applicable to:"), [action1],
        families=["A330", "A340"], models=["A330", "A340-200", "A340-300"],
        serial_restrictions=[b.serial("all", "all serial numbers", [action1])],
        exclusions=["Airbus modification 47634 embodied in production."],
    )
    g2 = b.add_group(
        "Action 2 aeroplanes",
        page_text_between(b, 2, "Action n°2 applicable to:") + " " + page_text_between(b, 3, "production or modified in-service", "Action n°3 applicable to:"),
        [action2a, action2b], families=["A330", "A340"], models=["A330", "A340-200", "A340-300"],
        serial_restrictions=[b.serial("all", "all serial numbers", [action2a, action2b])],
        exclusions=["All four modifications 49135, 49630, 51825 and 55118 embodied in production.", "Modified in service with the applicable paired bonding service bulletins."],
    )
    g3 = b.add_group(
        "Action 3 ACT-equipped A340 aeroplanes", page_text_between(b, 3, "Action n°3 applicable to:", "Action n°4 applicable to:"), [action3],
        families=["A340"], models=["A340-200", "A340-300"],
        serial_restrictions=[b.serial("all", "all serial numbers", [action3])],
        configuration_conditions=["ACT installed by modification 42612/SB A340-28-4047, 44002/SB A340-28-4066, or 44005/SB A340-28-4067."],
        exclusions=["Modified in service by SB A340-28-4078 Revision 01."],
    )
    g4 = b.add_group(
        "Action 4 THS trim-tank aeroplanes",
        page_text_between(b, 3, "Action n°4 applicable to:") + " " + page_text_between(b, 4, "1996 (\"solution A\")", "Action n°5 applicable to:"),
        [action4a, action4b], families=["A330", "A340"],
        models=["A330-301", "A330-321", "A330-322", "A330-341", "A330-342", "A340-200", "A340-300"],
        serial_restrictions=[b.serial("all", "all serial numbers", [action4a, action4b])],
        exclusions=["Airbus modification 44252 embodied in production.", "Modified in service by SB A330-55-3016 or SB A340-55-4017."],
    )
    g5 = b.add_group(
        "Action 5 A340 aeroplanes", page_text_between(b, 4, "Action n°5 applicable to:", "Ref. Publications:"), [action5],
        families=["A340"], models=["A340-200", "A340-300"],
        serial_restrictions=[b.serial("all", "all serial numbers", [action5])],
        exclusions=["Modification 46142 embodied in production.", "Modified in service by SB A340-28-4073 Revision 02."],
    )
    set_unsafe(
        b, [reason1, reason2], page_text_between(b, 1, "Reason:") + " " + page_text_between(b, 2, "modification of electrical bonding", "Effective Date:"),
        observed=["The TWA800 accident prompted an SFAR 88 fuel-tank explosion-hazard design review."],
        causes=["Fuel-system wire chafing, inadequate electrical bonding, insufficient metallic-part separation, and absent bonding leads."],
        conditions=["Potential ignition sources within fuel tanks or associated systems."],
        consequences=["Fuel-tank explosion hazard."],
        components=["FQI and FLSS harnesses and P-clips", "fuel-tank equipment bonding", "Additional Centre Tank", "THS Trim Tank", "jettison-valve actuator and drive assembly"],
        mitigation=["Inspect P-clips and complete the five bonding, separation, and installation actions."],
    )
    pub_specs = [
        ("A330-28-3092", "Revision 01"), ("A340-28-4107", "Revision 01"),
        ("A330-28-3082", "Revision 04"), ("A330-28-3101", "Revision 01"),
        ("A340-28-4097", "Revision 03"), ("A340-28-4118", "Revision 02"),
        ("A340-28-4078", "Revision 01"), ("A330-55-3016", None),
        ("A340-55-4017", None), ("A340-28-4073", "Revision 02"),
    ]
    pubs: list[str] = []
    for number, revision in pub_specs:
        roles = ["required_method"]
        if number in {"A330-28-3082", "A330-28-3101", "A340-28-4118", "A340-28-4078", "A340-28-4073"}:
            roles.append("previous_action_credit")
        pubs.append(b.add_publication("service_bulletin", "Airbus", number, [refs], revision=revision, roles=roles, later=True))
    r1 = b.add_requirement(
        "Action 1", [g1], ["inspection", "repair"], "mandatory",
        "Not later than 31 December 2009, perform a detailed visual inspection of P-clips in wing and centre fuel tanks and apply corrective actions if necessary.",
        [action1], objects=["P-clips in wing and centre fuel tanks"], publications=pubs[0:2],
        rules=[b.rule("Not later than December 31st, 2009", [action1], initial_limits=[b.limit("not_later_than", "31 December 2009", [action1], quantity=None, unit="calendar_date", calendar_date="2009-12-31")])],
    )
    r2 = b.add_requirement(
        "Action 2", [g2], ["modification"], "mandatory",
        "Not later than 31 December 2009, modify the electrical bonding of equipment installed in fuel tanks under the applicable A330 or A340 service bulletins.",
        [action2a, action2b], objects=["electrical bonding of fuel-tank equipment"], publications=pubs[2:6],
        rules=[b.rule("Not later than December 31st, 2009", [action2b], initial_limits=[b.limit("not_later_than", "31 December 2009", [action2b], quantity=None, unit="calendar_date", calendar_date="2009-12-31")])],
    )
    r2a = b.add_requirement(
        "Action 2 additional work", [g2], ["modification"], "conditional",
        "For aircraft previously modified with A330-28-3082 original issue or A340-28-4097 before Revision 03, accomplish the additional work not later than 31 December 2011.",
        [action2b], conditions=["Previously modified under the specified earlier service-bulletin issue."], publications=[pubs[2], pubs[4]], parent=r2,
        rules=[b.rule("Not later than December 31st, 2011", [action2b], conditions=["Earlier bonding SB issue was used."], initial_limits=[b.limit("not_later_than", "31 December 2011", [action2b], quantity=None, unit="calendar_date", calendar_date="2011-12-31")])],
    )
    r3 = b.add_requirement(
        "Action 3", [g3], ["modification"], "mandatory",
        "Not later than 31 December 2009, modify the electrical bonding in the Additional Centre Tank under SB A340-28-4078 Revision 01.",
        [action3], objects=["Additional Centre Tank electrical bonding"], publications=[pubs[6]],
        rules=[b.rule("Not later than December 31st, 2009", [action3], initial_limits=[b.limit("not_later_than", "31 December 2009", [action3], quantity=None, unit="calendar_date", calendar_date="2009-12-31")])],
    )
    r4 = b.add_requirement(
        "Action 4", [g4], ["modification", "adjust"], "mandatory",
        "Increase the distance between metallic parts on the THS Trim Tank under the applicable A330 or A340 service bulletin.",
        [action4a, action4b], objects=["metallic parts on the THS Trim Tank"], publications=[pubs[7], pubs[8]],
        rules=[
            b.rule("Not later than December 31st, 2009", [action4a], conditions=["Standard Action 4 compliance."], initial_limits=[b.limit("not_later_than", "31 December 2009", [action4a], quantity=None, unit="calendar_date", calendar_date="2009-12-31")]),
            b.rule(
                "For aircraft already compliant with AOT 55-03 solution A, after 31 December 2009 at the first THS ground removal or first maintenance task requiring THS lifting/resting fittings.",
                [action4b], logic="conditional",
                conditions=["AOT 55-03 solution A was already accomplished under the named DGAC ADs.", "Perform at the first qualifying THS removal or maintenance event after 31 December 2009."],
                initial_limits=[b.limit("upon", "first qualifying THS removal or maintenance task after 31 December 2009", [action4b], quantity=None, unit="other", reference_event="first qualifying event after 31 December 2009")],
            ),
        ],
    )
    r5 = b.add_requirement(
        "Action 5", [g5], ["install", "modification"], "mandatory",
        "Not later than 31 December 2009, install a bonding lead between the jettison-valve actuator and drive-assembly bonding tags.",
        [action5], objects=["jettison-valve actuator and drive-assembly bonding tags"], publications=[pubs[9]],
        rules=[b.rule("Not later than December 31st, 2009", [action5], initial_limits=[b.limit("not_later_than", "31 December 2009", [action5], quantity=None, unit="calendar_date", calendar_date="2009-12-31")])],
    )
    b.add_credit(
        "Original or specified earlier issues of A330-28-3101, A340-28-4118 and A330-28-3082 are acceptable for the applicable Action 2 requirements.",
        [r2], [pubs[2], pubs[3], pubs[5]], [action2b],
        conditions=["Only the service-bulletin issues explicitly listed in the AD are credited."],
    )
    b.add_credit("A340-28-4078 original issue is acceptable for Action 3.", [r3], [pubs[6]], [action3])
    b.add_credit("A340-28-4073 original issue or Revision 01 is acceptable for Action 5.", [r5], [pubs[9]], [action5])
    b.add_relationship("supersedes", "2006-0322", "This new AD supersedes EASA AD 2006-0322", [cover, reason2], source="structured_supersedure_field")
    b.add_relationship("retains_requirements_of", "2006-0322", "taking over its requirements", [reason2], source="explicit_directional_sentence")
    b.record["annotation_metadata"]["uncertainty_flags"].append(
        "correction_target_publication_not_present_in_pilot"
    )
    b.record["annotation_metadata"]["notes"].append(
        "The PDF explicitly identifies this as a correction, but the distinct uncorrected publication is not present in the pilot; no correction relationship target was fabricated."
    )
    b.add_contact("amoc_authority", "EASA", "EASA can accept Alternative Methods of Compliance for this AD.", [remarks], ["Requested and appropriately substantiated."])
    b.add_contact("regulatory_contact", "EASA Airworthiness Directive Focal Point", "E-mail: ADs@easa.europa.eu.", [remarks])
    b.add_contact("technical_contact", "Airbus SAS Airworthiness Office – EAL", "E-mail: airworthiness.A330-A340@airbus.com.", [remarks])
    b.context_evidence.update({"/definitions": [app, reason1], "/exceptions": [action1, action2b, action3, action4b, action5], "/classification": [subject, app, reason1, action1, action2b, action3, action4a, action5]})
    b.finalize(
        families=["A330", "A340"], ata_code="28", frequency="one_time", table_present=False,
        compliance_complexity="mixed", classification_evidence=[subject, app, reason1, action1, action2b, action3, action4a, action5],
        quality_flags=["complex_applicability", "complex_compliance"],
    )
    return b


def build_galley_ad(ad_number: str) -> AnnotationBuilder:
    if ad_number not in {"2025-0068", "2026-0017"}:
        raise ValueError(ad_number)
    b = AnnotationBuilder(ad_number)
    is_2026 = ad_number == "2026-0017"
    cover = b.evidence("cover", 1, "cover", f"Airworthiness Directive AD No.: {ad_number}", "ATA 25", clause_path="cover")
    subject = b.evidence("subject", 1, "cover", "ATA 25", "Manufacturer(s):", clause_path="subject")
    app = b.evidence("app", 1, "applicability", "Applicability:", "Definitions:", clause_path="Applicability")
    defs1 = b.evidence("defs1", 1, "definitions", "Definitions:", clause_path="Definitions, part and SB terms")
    date_term = "Aeroplane reference date:" if is_2026 else "Aeroplane date of manufacture:"
    defs2 = b.evidence("defs2", 2, "definitions", date_term, "Reason:", clause_path="Definitions, date and groups")
    reason1 = b.evidence("reason1", 2, "reason", "Reason:", clause_path="Reason")
    reason_cont_start = "For the reasons described above" if is_2026 else "installed under the responsibility"
    reason2 = b.evidence("reason2", 3, "reason", reason_cont_start, "Required Action(s) and Compliance Time(s):", clause_path="Reason continuation")
    actions1 = b.evidence(
        "actions1", 3, "required_actions_and_compliance_times", "Required Action(s) and Compliance Time(s):",
        clause_path="paragraphs (1)-(2)",
        table_context=table_context(
            "Tables 1 and 2", ["Group 1 aeroplane configurations", "Group 2 aeroplane configurations"],
            ["Configuration", "Compliance Time"], ["Note 1 provides an alternative reference date when first-installation date is unknown."],
        ),
    )
    if is_2026:
        actions2 = b.evidence("actions2", 4, "required_actions_and_compliance_times", "Table 2", clause_path="Table 2 and paragraphs (3)-(8)", table_context=table_context("Table 2", ["Group 2 configuration branches"], ["Configuration", "Compliance Time"]))
        refs = b.evidence("refs", 5, "reference_publications", "Ref. Publications:", "Remarks:", clause_path="Ref. Publications")
        remarks = b.evidence("remarks", 5, "remarks", "Remarks:", clause_path="Remarks")
    else:
        actions2 = b.evidence("actions2", 4, "required_actions_and_compliance_times", "(3) If, during any GVI", "Ref. Publications:", clause_path="paragraphs (3)-(8)")
        refs = b.evidence("refs", 4, "reference_publications", "Ref. Publications:", clause_path="Ref. Publications")
        remarks = b.evidence("remarks", 5, "remarks", "Remarks:", clause_path="Remarks")
    appendix_evidence: list[str] = []
    for page in range(6, 11):
        start = "Appendix 1:" if page == 6 else "Series P/N"
        appendix_evidence.append(
            b.evidence(
                f"appendix{page}", page, "appendix", start,
                clause_path=f"Appendix 1 page {page}",
                table_context=table_context("Appendix 1: Reference of the Affected Galleys", ["Series"], ["Series", "P/N"]),
            )
        )
    visual_removed = [
        b.visual_evidence(
            "removed6", 6, "table",
            "601537 601537-XXXXXX\n601854 601854-XXXXXX",
            clause_path="Appendix 1 removed series",
            table_context=table_context("Appendix 1: Reference of the Affected Galleys", ["601537", "601854"], ["Series", "P/N"]),
            annotation_note="Rendered Appendix page shows both rows struck through; they are excluded from affected part numbers.",
        ),
        b.visual_evidence(
            "removed8", 8, "table",
            "601866 601866-000501, 601866-000601, 601866-000701\n601883 601883-XXXXXX",
            clause_path="Appendix 1 removed series",
            table_context=table_context("Appendix 1: Reference of the Affected Galleys", ["601866", "601883"], ["Series", "P/N"]),
            annotation_note="Rendered Appendix page shows both rows struck through; they are excluded from affected part numbers.",
        ),
        b.visual_evidence(
            "removed9", 9, "table",
            "601889 601889-XXXXXX\n601897 601897-XXXXXX\n6018A4 6018A4-000101, 6018A4-000301\n601920 601920-XXXXXX",
            clause_path="Appendix 1 removed series",
            table_context=table_context("Appendix 1: Reference of the Affected Galleys", ["601889", "601897", "6018A4", "601920"], ["Series", "P/N"]),
            annotation_note="Rendered Appendix page shows these rows struck through; they are excluded from affected part numbers.",
        ),
        b.visual_evidence(
            "removed10", 10, "table",
            "601958 601958-XXXXXX\n6019A3 6019A3-000101\n6019A8 6019A8-XXXXXX\n6019A9 6019A9-XXXXXX\n6019C1 6019C1-XXXXXX",
            clause_path="Appendix 1 removed series",
            table_context=table_context("Appendix 1: Reference of the Affected Galleys", ["601958", "6019A3", "6019A8", "6019A9", "6019C1"], ["Series", "P/N"]),
            annotation_note="Rendered Appendix page shows these rows struck through; they are excluded from affected part numbers.",
        ),
    ]
    b.record["source_document"]["extraction_status"] = "hybrid"
    b.record["source_document"]["text_extraction_method"] = "hybrid"
    if is_2026:
        issue_date, issue_raw = "2026-01-23", "Issued: 23 January 2026"
        effective_date, effective_raw = "2026-02-06", "Effective Date: 06 February 2026"
        superseded_ad, supersedure_raw = "2025-0068", "This AD supersedes EASA AD 2025-0068 dated 28 March 2025."
        subject_text = "ATA 25 – Equipment / Furnishings – Galley – Inspection"
    else:
        issue_date, issue_raw = "2025-03-28", "Issued: 28 March 2025"
        effective_date, effective_raw = "2025-04-11", "Effective Date: 11 April 2025"
        superseded_ad, supersedure_raw = "2024-0038", "This AD supersedes EASA AD 2024-0038 dated 05 February 2024."
        subject_text = "ATA 25 – Equipment / Furnishings – Galleys – Inspection"
    common_identity_publication(
        b, cover_ev=cover, subject_ev=subject, app_ev=app,
        issue_date=issue_date, issue_raw=issue_raw, effective_date=effective_date, effective_raw=effective_raw,
        design_holder="AIRBUS S.A.S.", subject=subject_text, ata_code="25", ata_title="Equipment / Furnishings",
        manufacturers=[("Airbus, formerly Airbus Industrie", "Airbus", "manufacturer")],
        type_models=["A318", "A319", "A320", "A321"], tcds_numbers=["EASA.A.064"], foreign_raw="Not applicable",
        supersedure_value=f"EASA AD {superseded_ad}", supersedure_raw=supersedure_raw, supersedure_state="present",
    )
    app_raw = page_text_between(b, 1, "Applicability:", "Definitions:")
    models = extract_modern_models(app_raw)
    affected_pns = extract_appendix_part_numbers(b)
    general_serial = b.serial("all", "all manufacturer serial numbers", [app])
    g1_raw = page_text_between(b, 2, "Group 1 aeroplanes", "Group 2 aeroplanes")
    g1 = b.add_group(
        "Group 1 aeroplanes", g1_raw, [app, defs1, defs2, *appendix_evidence, *visual_removed],
        families=["A320 Family"], models=models, serial_restrictions=[general_serial], part_numbers=affected_pns,
        configuration_conditions=["An affected forward-facing galley listed in Appendix 1 is installed."],
    )
    g2_raw = page_text_between(b, 2, "Group 2 aeroplanes", "Group 3 aeroplanes")
    g2 = b.add_group(
        "Group 2 aeroplanes", g2_raw, [app, defs2], families=["A320 Family"], models=models,
        serial_restrictions=[b.serial("all", "all manufacturer serial numbers", [app, defs2])],
        configuration_conditions=["A galley was initially installed as an affected part and later re-identified with a non-affected P/N without embodiment of the modification SB."],
    )
    g3_raw = page_text_between(b, 2, "Group 3 aeroplanes", "Reason:")
    g3 = b.add_group(
        "Group 3 aeroplanes", g3_raw, [app, defs2], families=["A320 Family"], models=models,
        serial_restrictions=[b.serial("all", "all manufacturer serial numbers", [app, defs2])],
        configuration_conditions=["Not Group 2 and no affected part is installed."],
    )
    b.add_definition("Affected part", "Forward-facing galleys having a P/N listed as affected in Appendix 1 of this AD.", [defs1, *appendix_evidence, *visual_removed])
    b.add_definition("The inspection SB", "Airbus SB A320-25-1BVS or Airbus SB A320-25-1BVT, as applicable.", [defs1])
    b.add_definition("The modification SB", "Airbus SB A320-25-1CBN or Airbus SB A320-25-1CBP, as applicable.", [defs1])
    b.add_definition("Aeroplane reference date" if is_2026 else "Aeroplane date of manufacture", "The date of transfer of title (ownership) at first delivery to an operator, as referenced in Airbus documentation.", [defs2])
    b.add_definition("Group 1 aeroplanes", g1_raw, [defs2])
    b.add_definition("Group 2 aeroplanes", g2_raw, [defs2])
    b.add_definition("Group 3 aeroplanes", g3_raw, [defs2])
    set_unsafe(
        b, [reason1, reason2],
        page_text_between(b, 2, "Reason:") + " " + page_text_between(b, 3, reason_cont_start, "Required Action(s) and Compliance Time(s):"),
        observed=["Galley inspections found work-deck delamination and corroded or cracked retainer blocks."],
        causes=["Damage to work decks and retainer blocks in affected forward-facing galleys."],
        conditions=["An affected galley may not retain its trolley under emergency landing loads."],
        consequences=["Trolley detachment and possible blockage of an escape path during an emergency exit."],
        components=["forward-facing galley", "work deck", "retainer blocks", "trolley"],
        mitigation=["Repetitive general visual inspections, corrective actions, installation controls, and optional terminating modification or replacement."],
    )
    if is_2026:
        rev_bvs, rev_bvt = "original issue through Revision 03", "original issue through Revision 2"
    else:
        rev_bvs, rev_bvt = "original issue through Revision 2", "original issue through Revision 1"
    pub_bvs = b.add_publication("service_bulletin", "Airbus", "A320-25-1BVS", [defs1, refs], revision=rev_bvs, roles=["required_method"], later=True)
    pub_bvt = b.add_publication("service_bulletin", "Airbus", "A320-25-1BVT", [defs1, refs], revision=rev_bvt, roles=["required_method"], later=True)
    pub_cbn = b.add_publication("service_bulletin", "Airbus", "A320-25-1CBN", [defs1, refs], revision="original issue through Revision 02", roles=["required_method", "optional_method"], later=True)
    pub_cbp = b.add_publication("service_bulletin", "Airbus", "A320-25-1CBP", [defs1, refs], revision="original issue through Revision 02", roles=["required_method", "optional_method"], later=True)
    inspection_pubs = [pub_bvs, pub_bvt]
    modification_pubs = [pub_cbn, pub_cbp]

    req1_rules = [
        b.rule(
            "Group 1 except listed special P/Ns: 36 months since first installation or within 12 months after 18 August 2021, whichever occurs later; thereafter intervals not exceeding 6 months.",
            [actions1], logic="whichever_occurs_later", conditions=["Group 1 aeroplane except the special P/N branches."],
            initial_limits=[
                b.limit("within", "36 months since first installation of an affected part", [actions1], quantity=36, unit="calendar_month", reference_event="first installation of an affected part"),
                b.limit("within", "12 months after 18 August 2021", [actions1], quantity=12, unit="calendar_month", reference_event="18 August 2021"),
            ],
            repetitive_intervals=[b.limit("not_to_exceed", "6 months", [actions1], quantity=6, unit="calendar_month", reference_event="previous GVI")],
        ),
        b.rule(
            "P/N 6018A7-000101 or 6018C1-000101: within 12 months after 19 February 2024; thereafter intervals not exceeding 6 months.",
            [actions1], conditions=["Affected part P/N 6018A7-000101 or 6018C1-000101 is installed."],
            initial_limits=[b.limit("within", "12 months after 19 February 2024", [actions1], quantity=12, unit="calendar_month", reference_event="19 February 2024")],
            repetitive_intervals=[b.limit("not_to_exceed", "6 months", [actions1], quantity=6, unit="calendar_month", reference_event="previous GVI")],
        ),
    ]
    if is_2026:
        req1_rules.extend([
            b.rule(
                "P/N 601891-006801, 601891-003701 or 601891-010001: within 12 months after 11 April 2025; thereafter intervals not exceeding 6 months.",
                [actions1], conditions=["One of the three specified 601891 P/Ns is installed."],
                initial_limits=[b.limit("within", "12 months after 11 April 2025", [actions1], quantity=12, unit="calendar_month", reference_event="11 April 2025")],
                repetitive_intervals=[b.limit("not_to_exceed", "6 months", [actions1], quantity=6, unit="calendar_month", reference_event="previous GVI")],
            ),
            b.rule(
                "P/N 6019F2-000001: within 12 months after the effective date of this AD; thereafter intervals not exceeding 6 months.",
                [actions1], conditions=["Affected part P/N 6019F2-000001 is installed."],
                initial_limits=[b.limit("within", "12 months after the effective date of this AD", [actions1], quantity=12, unit="calendar_month", reference_event="effective date of this AD")],
                repetitive_intervals=[b.limit("not_to_exceed", "6 months", [actions1], quantity=6, unit="calendar_month", reference_event="previous GVI")],
            ),
        ])
    else:
        req1_rules.append(
            b.rule(
                "P/N 601891-006801, 601891-003701 or 601891-010001: within 12 months after the effective date of this AD; thereafter intervals not exceeding 6 months.",
                [actions1], conditions=["One of the three specified 601891 P/Ns is installed."],
                initial_limits=[b.limit("within", "12 months after the effective date of this AD", [actions1], quantity=12, unit="calendar_month", reference_event="effective date of this AD")],
                repetitive_intervals=[b.limit("not_to_exceed", "6 months", [actions1], quantity=6, unit="calendar_month", reference_event="previous GVI")],
            )
        )
    req1 = b.add_requirement(
        "(1)", [g1], ["inspection"], "mandatory",
        "For Group 1 aeroplanes, accomplish a general visual inspection of each affected part within the applicable Table 1 time and thereafter at intervals not exceeding 6 months.",
        [actions1], objects=["each affected forward-facing galley"], publications=inspection_pubs, rules=req1_rules,
    )
    req2_rules = [
        b.rule(
            "Group 2 except listed special P/Ns: 12 months after 19 February 2024.", [actions1],
            conditions=["Group 2 except the special P/N branches."],
            initial_limits=[b.limit("within", "12 months after 19 February 2024", [actions1], quantity=12, unit="calendar_month", reference_event="19 February 2024")],
        )
    ]
    if is_2026:
        req2_rules.extend([
            b.rule(
                "Group 2 galley initially installed as one of the three specified 601891 P/Ns: within 12 months after 11 April 2025.", [actions1, actions2],
                conditions=["Galley was initially installed as P/N 601891-006801, 601891-003701 or 601891-010001."],
                initial_limits=[b.limit("within", "12 months after 11 April 2025", [actions1, actions2], quantity=12, unit="calendar_month", reference_event="11 April 2025")],
            ),
            b.rule(
                "Group 2 galley initially installed as P/N 6019F2-000001: within 12 months after the effective date of this AD.", [actions2],
                conditions=["Galley was initially installed as P/N 6019F2-000001."],
                initial_limits=[b.limit("within", "12 months after the effective date of this AD", [actions2], quantity=12, unit="calendar_month", reference_event="effective date of this AD")],
            ),
        ])
    else:
        req2_rules.append(
            b.rule(
                "Group 2 galley initially installed as one of the three specified 601891 P/Ns: within 12 months after the effective date of this AD.", [actions1],
                conditions=["Galley was initially installed as P/N 601891-006801, 601891-003701 or 601891-010001."],
                initial_limits=[b.limit("within", "12 months after the effective date of this AD", [actions1], quantity=12, unit="calendar_month", reference_event="effective date of this AD")],
            )
        )
    req2 = b.add_requirement(
        "(2)", [g2], ["contact_manufacturer", "repair", "modification"], "mandatory",
        "Within the applicable Table 2 time, contact the galley manufacturer, Airbus, or responsible design approval holder for approved instructions and accomplish them.",
        [actions1, actions2], objects=["re-identified galley"], conditions=["Instructions must be approved by EASA or under an EASA Design Organisation Approval holder."], rules=req2_rules,
    )
    req3 = b.add_requirement(
        "(3)", [g1], ["repair"], "conditional",
        "If discrepancies are detected during a required GVI, accomplish the applicable corrective actions before next flight.",
        [actions2], objects=["affected galley discrepancy"], conditions=["A discrepancy is detected during paragraph (1) GVI."], publications=inspection_pubs, parent=req1,
        rules=[b.rule("before next flight", [actions2], conditions=["A discrepancy is detected."], initial_limits=[b.limit("before", "before next flight", [actions2], quantity=None, unit="before_next_flight")])],
    )
    req4 = b.add_requirement(
        "(4)", [g1, g2, g3], ["install", "inspection", "repair"], "conditional",
        "From the effective date, an affected part may be installed only if it is inspected after installation and corrected depending on findings.",
        [actions2], objects=["affected galley"], conditions=["Post-installation inspection and applicable correction are accomplished."], publications=inspection_pubs,
        rules=[b.rule("From the effective date of this AD", [actions2], initial_limits=[b.limit("from", "from the effective date of this AD", [actions2], quantity=None, unit="other", reference_event="effective date of this AD")])],
    )
    req5 = b.add_requirement(
        "(5)", [g1], ["inspection"], "conditional",
        "After an intermediate repair of an affected panel or retainer block, the next GVI may be deferred until 36 months after repair; thereafter inspect at intervals not exceeding 6 months.",
        [actions2], objects=["repaired panel or retainer block"], conditions=["An intermediate repair was accomplished under the inspection SB."], publications=inspection_pubs, parent=req1,
        rules=[b.rule(
            "next GVI can be deferred until 36 months after repair; thereafter intervals not exceeding 6 months", [actions2],
            conditions=["Intermediate repair was accomplished."],
            initial_limits=[b.limit("within", "36 months after that repair", [actions2], quantity=36, unit="calendar_month", reference_event="intermediate repair")],
            repetitive_intervals=[b.limit("not_to_exceed", "6 months", [actions2], quantity=6, unit="calendar_month", reference_event="previous GVI")],
        )],
    )
    ta6_text = "Modification of an affected part under the modification SB terminates paragraph (1) and (5) inspections for that galley."
    req6 = b.add_requirement(
        "(6)", [g1], ["modification"], "optional_terminating", ta6_text, [actions2],
        objects=["one affected galley"], publications=modification_pubs,
        rules=[b.rule(ta6_text, [actions2], initial_limits=[])],
        terminating=b.terminating_action(ta6_text, [req1, req5], [actions2], "partial"),
    )
    ta7_text = "Modification of all affected parts under the modification SB terminates paragraph (1) and (5) inspections for the aeroplane, provided no affected part is re-installed."
    req7 = b.add_requirement(
        "(7)", [g1], ["modification", "prohibition"], "optional_terminating", ta7_text, [actions2],
        objects=["all affected galleys on an aeroplane"], conditions=["No affected part is re-installed after modification."], publications=modification_pubs,
        rules=[b.rule(ta7_text, [actions2], conditions=["No affected part is re-installed."], initial_limits=[])],
        terminating=b.terminating_action(ta7_text, [req1, req5], [actions2], "full"),
    )
    ta8_text = "Replacement with a galley modified under approved instructions including post-modification SB instructions terminates paragraphs (1), (2) and (5) inspections for that galley."
    req8 = b.add_requirement(
        "(8)", [g1, g2], ["replacement", "modification"], "optional_terminating", ta8_text, [actions2],
        objects=["forward-facing galley"], conditions=["Approved instructions include post-modification SB instructions."], publications=modification_pubs,
        rules=[b.rule(ta8_text, [actions2], conditions=["Replacement galley has the approved modification."], initial_limits=[])],
        terminating=b.terminating_action(ta8_text, [req1, req2, req5], [actions2], "partial"),
    )
    b.add_relationship("supersedes", superseded_ad, supersedure_raw, [cover], source="structured_supersedure_field")
    b.add_relationship("retains_requirements_of", superseded_ad, f"This AD retains the requirements of EASA AD {superseded_ad}, which is superseded", [reason1, reason2], source="explicit_directional_sentence")
    b.add_contact("amoc_authority", "EASA", "EASA can approve Alternative Methods of Compliance for this AD.", [remarks], ["Requested and appropriately substantiated."])
    b.add_contact("regulatory_contact", "EASA Safety Information Section", "E-mail: ADs@easa.europa.eu.", [remarks])
    b.add_contact("technical_contact", "Airbus Airworthiness Office – 1IASA", "E-mail: account.airworth-eas@airbus.com.", [remarks])
    b.context_evidence.update({"/exceptions": [actions1, actions2], "/previous_action_credit": [actions2, refs], "/classification": [subject, app, defs2, reason1, actions1, actions2, *appendix_evidence, *visual_removed]})
    b.finalize(
        families=["A320 Family"], ata_code="25", frequency="mixed", table_present=True,
        compliance_complexity="table_driven", classification_evidence=[subject, app, defs2, reason1, actions1, actions2, *appendix_evidence, *visual_removed],
        quality_flags=["complex_applicability", "complex_table", "complex_compliance", "visual_transcription_used"],
    )
    return b


def build_2025_0068() -> AnnotationBuilder:
    return build_galley_ad("2025-0068")


def build_2026_0017() -> AnnotationBuilder:
    return build_galley_ad("2026-0017")


def build_2024_0095() -> AnnotationBuilder:
    b = AnnotationBuilder("2024-0095")
    cover = b.evidence("cover", 1, "cover", "Airworthiness Directive AD No.: 2024-0095", "ATA 53", clause_path="cover")
    subject = b.evidence("subject", 1, "cover", "ATA 53", "Manufacturer(s):", clause_path="subject")
    app = b.evidence("app", 1, "applicability", "Applicability:", "Definitions:", clause_path="Applicability")
    defs = b.evidence("defs", 1, "definitions", "Definitions:", clause_path="Definitions")
    reason = b.evidence("reason", 2, "reason", "Reason:", clause_path="Reason")
    actions1 = b.evidence(
        "actions1", 3, "required_actions_and_compliance_times", "Required Action(s) and Compliance Time(s):",
        clause_path="paragraph (1) and Table 1",
        table_context=table_context(
            "Table 1 – Inspection Threshold", ["A330-MRTT GOS/FAF", "A330-MRTT RAAF/RSAF/UAE", "A330-FSTA STC2", "A330-FSTA STC1 2PT", "A330-FSTA STC1 3PT"],
            ["Aeroplane Configuration", "Compliance Time A, B or C, whichever occurs later"],
        ),
    )
    actions2 = b.evidence(
        "actions2", 4, "required_actions_and_compliance_times", "Note 1:", clause_path="paragraph (2), Table 2 and Notes 1-3",
        table_context=table_context(
            "Table 2 – Inspection Intervals", ["Inspection Method 1 DET", "Inspection Method 2 HFEC/ultrasonic/roto"],
            ["Inspection Method and Area", "Aeroplane Configuration", "Inspection Interval"],
            ["Chosen method determines the next interval; alternating or inter-mixing is allowed.", "FSTA STC1 change-of-role factors in Table 3 apply."],
        ),
    )
    actions3 = b.evidence(
        "actions3", 5, "required_actions_and_compliance_times", "Table 3", "Ref. Publications:", clause_path="Table 3 and paragraphs (3)-(8)",
        table_context=table_context(
            "Table 3 – Transfer Factors (Kmil-civ)", ["A330-FSTA STC1 2PT", "A330-FSTA STC1 3PT"],
            ["Configuration", "Threshold/Interval", "Kmil-civ for FC", "Kmil-civ for FH"],
        ),
    )
    refs1 = b.evidence("refs1", 5, "reference_publications", "Ref. Publications:", clause_path="Ref. Publications continuation on page 6")
    refs2 = b.evidence("refs2", 6, "reference_publications", "The use of later approved revisions", "Remarks:", clause_path="Ref. Publications continuation")
    remarks = b.evidence("remarks", 6, "remarks", "Remarks:", clause_path="Remarks")
    common_identity_publication(
        b, cover_ev=cover, subject_ev=subject, app_ev=app,
        issue_date="2024-04-30", issue_raw="Issued: 30 April 2024",
        effective_date="2024-05-14", effective_raw="Effective Date: 14 May 2024",
        design_holder="AIRBUS DEFENCE AND SPACE S.A.",
        subject="ATA 53 – Fuselage – Bulk Cargo Door Frames – Inspection / Repair",
        ata_code="53", ata_title="Fuselage",
        manufacturers=[("Airbus, formerly Airbus Industrie", "Airbus", "manufacturer")],
        type_models=["A330-202", "A330-203", "A330-243"], tcds_numbers=[], foreign_raw="Not applicable",
        supersedure_value=None, supersedure_raw="None", supersedure_state="explicit_none",
    )
    app_raw = page_text_between(b, 1, "Applicability:", "Definitions:")
    group = b.add_group(
        "A330 MRTT/FSTA conversions within the affected MSN/configuration scope", app_raw, [app],
        families=["A330"], models=["A330-202", "A330-203", "A330-243"],
        serial_restrictions=[b.serial("include_range", "all manufacturer serial numbers up to MSN 1779 inclusive", [app], lower="0001", upper="1779")],
        configuration_conditions=[
            "Modified under EASA STC 10029272, 10063084, 10064192, 10034690 or 10035945.",
            "Airbus SB A330-53-3275 original issue or Revision 01 was embodied in service.",
        ],
        exclusions=["During SB A330-53-3275 embodiment, the specified roto test was accomplished and defects were absent or corrected as applicable."],
    )
    b.add_definition("The SB", "Airbus Defence and Space SB A330MRTT-53-0048 Revision 01.", [defs])
    b.add_definition("Aeroplane date of manufacture", "The date of transfer of title (ownership) at first delivery to an operator, as referenced in Airbus documentation.", [defs])
    set_unsafe(
        b, [reason], page_text_between(b, 2, "Reason:"),
        observed=["Affected bulk-cargo-door fitting holes have CAA/TSA treatment or a similar fatigue issue."],
        causes=["Surface treatment in attachment holes and the associated detrimental fatigue behaviour."],
        conditions=["Undetected fatigue cracks in primary structure at frames 67 and 69 right-hand side."],
        consequences=["In-flight loss of a bulk cargo door, decompression, damage to the aeroplane, and reduced control."],
        components=["FR67 and FR69 RH bulk-cargo-door support-fitting holes", "FR69 door-latch fitting holes", "bulk-cargo-door frames"],
        mitigation=["One-time roto testing or alternative repetitive DET/HFEC/ultrasonic inspections, plus corrective action and bushes."],
    )
    pub_sb_current = b.add_publication(
        "service_bulletin", "Airbus Defence and Space", "A330MRTT-53-0048", [defs, refs1],
        revision="Revision 01", publication_date="2024-01-29", roles=["required_method"], later=True,
    )
    pub_sb_original = b.add_publication(
        "service_bulletin", "Airbus Defence and Space", "A330MRTT-53-0048", [refs1],
        revision="original issue", publication_date="2022-01-21", roles=["previous_action_credit"], later=None,
    )
    pub_3303 = b.add_publication(
        "service_bulletin", "Airbus", "A330-53-3303", [reason, refs2],
        revision="any issue through Revision 02", publication_date=None,
        roles=["previous_action_credit", "referenced_information"], later=None,
    )
    pub_3275 = b.add_publication(
        "service_bulletin", "Airbus", "A330-53-3275", [app, reason, refs2],
        revision="original issue through Revision 02", publication_date=None,
        roles=["referenced_information"], later=None,
    )
    pub_als = b.add_publication(
        "airworthiness_limitations_section", "Airbus Defence and Space", "A330 FSTA STC1 ALS Part 2", [actions2, actions3],
        title="Airworthiness Limitations Section Part 2", roles=["required_method"], later=None,
    )
    for stc in ["10029272", "10063084", "10064192", "10034690", "10035945"]:
        b.add_publication("stc", "EASA", stc, [cover, app], roles=["referenced_information"], later=None)

    table1_rows = [
        (
            "A330-MRTT GOS and FAF",
            "before 6 672 FC or 16 680 FH, whichever occurs first",
            "before 2 318 FC since embodiment of Airbus SB A330-53-3275",
            "within 72 FC after 10 November 2021",
        ),
        (
            "A330-MRTT RAAF, RSAF and UAE",
            "before 6 672 FC or 23 349 FH, whichever occurs first",
            "before 2 318 FC since embodiment of Airbus SB A330-53-3275",
            "within 72 FC after 10 November 2021",
        ),
        (
            "A330-FSTA STC2",
            "before 6 672 FC or 15 669 FH, whichever occurs first",
            "before 2 318 FC since embodiment of Airbus SB A330-53-3275",
            "within 72 FC after 10 November 2021",
        ),
        (
            "A330-FSTA STC1 2PT",
            "before 13 880 FC or 42 056 FH, whichever occurs first",
            "before 4 262 FC or 12 913 FH, whichever occurs first, since embodiment of Airbus SB A330-53-3275",
            "within 116 FC or 351 FH, whichever occurs first, after 10 November 2021",
        ),
        (
            "A330-FSTA STC1 3PT",
            "before 9 415 FC or 28 527 FH, whichever occurs first",
            "before 3 284 FC or 9 950 FH, whichever occurs first, since embodiment of Airbus SB A330-53-3275",
            "within 102 FC or 309 FH, whichever occurs first, after 10 November 2021",
        ),
    ]
    table1_rules: list[dict[str, Any]] = []
    for config, limit_a, limit_b, limit_c in table1_rows:
        conditions = [
            f"Aeroplane configuration: {config}.",
            "Use Compliance Time A, B or C, whichever occurs later.",
        ]
        if "STC1" in config:
            conditions.append("If there is a Change of Role, apply the Table 3 Kmil-civ FC/FH transfer factors under the A330 FSTA STC1 ALS Part 2.")
        table1_rules.append(
            b.rule(
                f"{config}: A={limit_a}; B={limit_b}; C={limit_c}; A, B or C whichever occurs later.",
                [actions1, actions3], logic="whichever_occurs_later", conditions=conditions,
                initial_limits=[
                    b.limit("before", limit_a, [actions1], quantity=None, unit="other", reference_event="aeroplane accumulation since manufacture unless otherwise indicated"),
                    b.limit("before", limit_b, [actions1], quantity=None, unit="other", reference_event="embodiment of Airbus SB A330-53-3275"),
                    b.limit("within", limit_c, [actions1], quantity=None, unit="other", reference_event="10 November 2021")
                ],
            )
        )
    req1 = b.add_requirement(
        "(1)", [group], ["inspection"], "mandatory",
        "Within the applicable Table 1 time, perform a roto test inspection of upper and lower door-support fitting holes at FR67 and FR69 RH and door-latch fitting holes at FR69 RH.",
        [actions1], objects=["FR67/FR69 RH upper and lower door-support fitting holes", "FR69 RH door-latch fitting holes"],
        publications=[pub_sb_current, pub_3275, pub_als], rules=table1_rules,
    )
    interval_rows = [
        ("DET; A330-MRTT all and A330-FSTA STC2", "129 FC", 129, "flight_cycle", None),
        ("DET; A330-FSTA STC1 2PT", "150 FC or 454 FH, whichever occurs first", None, "other", "Table 3 transfer factors apply after Change of Role."),
        ("DET; A330-FSTA STC1 3PT", "117 FC or 354 FH, whichever occurs first", None, "other", "Table 3 transfer factors apply after Change of Role."),
        ("HFEC/ultrasonic/roto; A330-MRTT GOS and FAF", "1 204 FC or 3 010 FH, whichever occurs first", None, "other", None),
        ("HFEC/ultrasonic/roto; A330-MRTT RAAF, RSAF and UAE", "1 204 FC or 4 213 FH, whichever occurs first", None, "other", None),
        ("HFEC/ultrasonic/roto; A330-FSTA STC2", "1 204 FC or 2 828 FH, whichever occurs first", None, "other", None),
        ("HFEC/ultrasonic/roto; A330-FSTA STC1 2PT", "1 400 FC or 4 241 FH, whichever occurs first", None, "other", "Table 3 transfer factors apply after Change of Role."),
        ("HFEC/ultrasonic/roto; A330-FSTA STC1 3PT", "1 092 FC or 3 308 FH, whichever occurs first", None, "other", "Table 3 transfer factors apply after Change of Role."),
    ]
    table2_rules: list[dict[str, Any]] = []
    for branch, raw_interval, quantity, unit, extra in interval_rows:
        conditions = [branch, "Initial threshold is the applicable Table 1 threshold.", "Chosen method determines the interval to the next inspection; alternating or inter-mixing is allowed."]
        if extra:
            conditions.append(extra)
        table2_rules.append(
            b.rule(
                f"{branch}: initial threshold per Table 1; thereafter {raw_interval}.",
                [actions1, actions2, actions3], logic="conditional", conditions=conditions,
                initial_limits=[b.limit("within", "applicable threshold specified in Table 1", [actions1, actions2], quantity=None, unit="other", reference_event="applicable Table 1 threshold")],
                repetitive_intervals=[b.limit("not_to_exceed", raw_interval, [actions2], quantity=quantity, unit=unit, reference_event="last accomplished inspection")],
            )
        )
    req2 = b.add_requirement(
        "(2)", [group], ["inspection"], "mandatory",
        "As an alternative to paragraph (1), inspect within the Table 1 thresholds and repetitively at the Table 2 interval determined by the last inspection method and configuration.",
        [actions2], objects=["FR67/FR69 frame and fitting areas"],
        conditions=["Choose Table 2 inspection method 1 or 2; the chosen method sets the next interval."],
        publications=[pub_sb_current, pub_3275, pub_als], rules=table2_rules,
    )
    req3 = b.add_requirement(
        "(3)", [group], ["install"], "conditional",
        "If no discrepancy is found during paragraph (1) or (2) inspection, install new, not previously installed, bushes on the FR69 latch fittings before next flight.",
        [actions3], objects=["new bushes on FR69 latch fittings"], conditions=["No discrepancy is found."], publications=[pub_sb_current], parent=req1,
        rules=[b.rule("before next flight", [actions3], conditions=["No discrepancy is found."], initial_limits=[b.limit("before", "before next flight", [actions3], quantity=None, unit="before_next_flight")])],
    )
    req4 = b.add_requirement(
        "(4)", [group], ["contact_manufacturer", "repair"], "conditional",
        "If any discrepancy is found, contact Airbus Defence and Space for approved repair instructions before next flight and accomplish them within the specified times.",
        [actions3], objects=["discrepant bulk-cargo-door frame or fitting area"], conditions=["A discrepancy is found during paragraph (1) or (2) inspection."], publications=[pub_sb_current], parent=req1,
        rules=[b.rule(
            "before next flight, contact ADS; accomplish approved instructions within the compliance times specified therein", [actions3],
            conditions=["A discrepancy is found."],
            initial_limits=[b.limit("before", "before next flight", [actions3], quantity=None, unit="before_next_flight")],
        )],
    )
    req6 = b.add_requirement(
        "(6)", [group], ["repair"], "conditional",
        "A repair accomplished under paragraph (4) does not terminate paragraph (2) repetitive inspections unless the approved ADS repair instructions specify otherwise.",
        [actions3], conditions=["A repair was accomplished under paragraph (4)."], publications=[pub_sb_current], parent=req4,
        rules=[b.rule("does not constitute terminating action unless otherwise specified in approved ADS repair instructions", [actions3], conditions=["Approved repair instructions may explicitly provide otherwise."], initial_limits=[])],
        terminating={"state": "explicit_none", "present": False, "scope": "none", "action_text": None, "terminates_requirement_ids": [], "evidence_ids": [actions3]},
    )
    ta7 = "A discrepancy-free paragraph (1) roto test followed by paragraph (3) new-bush installation under the SB terminates paragraph (2) repetitive inspections for that aeroplane."
    req7 = b.add_requirement(
        "(7)", [group], ["inspection", "install"], "optional_terminating", ta7,
        [actions3], objects=["roto-tested holes and new FR69 latch-fitting bushes"],
        conditions=["Paragraph (1) roto test finds no discrepancy and paragraph (3) new bushes are installed."], publications=[pub_sb_current],
        rules=[b.rule(ta7, [actions3], conditions=["Both prerequisite actions are accomplished."], initial_limits=[])],
        terminating=b.terminating_action(ta7, [req2], [actions3], "full"),
    )
    req8 = b.add_requirement(
        "(8)", [group], ["other"], "conditional",
        "Accomplishment of this AD's requirements constitutes compliance with EASA AD 2021-0233 for that aeroplane.",
        [actions3], conditions=["All applicable requirements of this AD are accomplished."],
        rules=[b.rule("constitutes compliance with EASA AD 2021-0233 for that aeroplane", [actions3], conditions=["All applicable requirements of this AD are accomplished."], initial_limits=[])],
    )
    b.add_credit(
        "Inspections and corrective actions completed before the effective date under ADS SB A330MRTT-53-0048 original issue or Airbus SB A330-53-3303 any issue satisfy the initial paragraph (1) or (2) requirements, as applicable.",
        [req1, req2], [pub_sb_original, pub_3303], [actions3],
        conditions=["Accomplished before the effective date of this AD.", "Credit applies to the corresponding initial requirement for that aeroplane."],
    )
    b.add_relationship(
        "related", "2021-0233", "Accomplishment on an aeroplane of the requirements of this AD, constitutes compliance with EASA AD 2021-0233 for that aeroplane.",
        [actions3], source="explicit_directional_sentence",
    )
    b.add_contact("amoc_authority", "EASA", "EASA can approve Alternative Methods of Compliance for this AD.", [remarks], ["Requested and appropriately substantiated."])
    b.add_contact("regulatory_contact", "EASA Safety Information Section", "E-mail: ADs@easa.europa.eu.", [remarks])
    b.add_contact("technical_contact", "Airbus Defence and Space Engineering Support / AMTAC", "Telephone: +34 91 600 7999; E-mail: mtad.militaryderivatives@airbus.com.", [remarks])
    b.context_evidence.update({"/exceptions": [actions1, actions2, actions3], "/relationships": [cover, actions3], "/classification": [subject, app, reason, actions1, actions2, actions3]})
    b.finalize(
        families=["A330"], ata_code="53", frequency="mixed", table_present=True,
        compliance_complexity="table_driven", classification_evidence=[subject, app, reason, actions1, actions2, actions3],
        quality_flags=["complex_applicability", "complex_table", "complex_compliance"],
    )
    return b


BUILDERS = {
    "2024-0095": build_2024_0095,
    "2026-0017": build_2026_0017,
    "2026-0079": build_2026_0079,
    "2025-0008": build_2025_0008,
    "2025-0068": build_2025_0068,
    "2006-0047": build_2006_0047,
    "2007-0022": build_2007_0022,
    "2007-0278": build_2007_0278,
    "2008-0012": build_2008_0012,
    "2009-0025": build_2009_0025,
}


def main(argv: list[str] | None = None) -> int:
    import sys

    requested = (argv if argv is not None else sys.argv[1:]) or list(BUILDERS)
    unknown = [ad_number for ad_number in requested if ad_number not in BUILDERS]
    if unknown:
        raise SystemExit(f"No builder registered for: {', '.join(unknown)}")
    for ad_number in requested:
        builder = BUILDERS[ad_number]()
        path = builder.write()
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
