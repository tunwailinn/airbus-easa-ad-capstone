#!/usr/bin/env python3
"""Validate EASA AD annotations structurally and semantically.

JSON Schema checks shape, types, formats, and controlled vocabularies.  The
checks in ``semantic_errors`` cover relationships that JSON Schema cannot
express cleanly: ID references, evidence integrity, identity consistency, and
approval gates.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:  # pragma: no cover - handled by the CLI
    Draft202012Validator = None  # type: ignore[assignment]
    FormatChecker = None  # type: ignore[assignment]


SCHEMA_PATH = Path(__file__).with_name("easa_airbus_ad_annotation.schema.json")
EASA_AD_RE = re.compile(
    r"^(?P<base>(?:19|20)[0-9]{2}-[0-9]{4})"
    r"(?:R(?P<revision>[1-9][0-9]*))?(?P<emergency>-E)?$"
)
APPROVED_STATUSES = {"approved"}
HUMAN_OR_DERIVED_ORIGINS = {
    "imported_manifest",
    "human_annotated",
    "human_corrected",
    "derived",
    "adjudicated",
}


def _path(parts: Iterable[Any]) -> str:
    values = [str(part) for part in parts]
    return "$" + "".join(
        f"[{value}]" if value.isdigit() else f".{value}" for value in values
    )


def _walk(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    repeated: set[str] = set()
    for value in values:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    return repeated


def _json_pointer_exists(document: Any, pointer: str) -> bool:
    if not pointer.startswith("/"):
        return False
    current = document
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit():
            index = int(token)
            if index >= len(current):
                return False
            current = current[index]
        else:
            return False
    return True


def _iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_schema(path: Path = SCHEMA_PATH) -> dict[str, Any]:
    schema = load_json(path)
    if Draft202012Validator is None:
        raise RuntimeError(
            "The 'jsonschema' package is required. Install it with "
            "'python -m pip install jsonschema'."
        )
    Draft202012Validator.check_schema(schema)
    return schema


def structural_errors(
    record: Any, schema: dict[str, Any]
) -> list[str]:
    if Draft202012Validator is None or FormatChecker is None:
        raise RuntimeError("The 'jsonschema' package is required.")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        f"{_path(error.absolute_path)}: {error.message}"
        for error in sorted(
            validator.iter_errors(record),
            key=lambda item: [str(part) for part in item.absolute_path],
        )
    ]


def semantic_errors(record: dict[str, Any], strict: bool = False) -> list[str]:
    """Return cross-field and approval-gate validation errors.

    The function is deliberately defensive so that it can still report useful
    findings when called on a structurally incomplete draft.
    """

    errors: list[str] = []
    source = record.get("source_document") or {}
    identity = record.get("ad_identity") or {}
    publication = record.get("publication") or {}
    metadata = record.get("annotation_metadata") or {}
    classification = record.get("classification") or {}
    benchmark = record.get("benchmark_metadata")
    requirements = record.get("requirements") or []
    applicability = record.get("applicability_groups") or []
    publications = record.get("referenced_publications") or []
    relationships = record.get("relationships") or []
    evidence = record.get("evidence_spans") or []
    assertions = record.get("field_assertions") or []

    # Empty strings defeat the null-versus-not-stated convention.
    for path, value in _walk(record):
        if isinstance(value, str) and not value.strip():
            errors.append(f"{path}: empty strings are forbidden; use null or []")

    # Each typed ID must be unique within the record.
    id_groups: dict[str, list[str]] = {
        "applicability group": [x.get("group_id") for x in applicability],
        "definition": [x.get("definition_id") for x in record.get("definitions", [])],
        "requirement": [x.get("requirement_id") for x in requirements],
        "exception": [x.get("exception_id") for x in record.get("exceptions", [])],
        "credit": [x.get("credit_id") for x in record.get("previous_action_credit", [])],
        "publication": [x.get("publication_id") for x in publications],
        "relationship": [x.get("relationship_id") for x in relationships],
        "AMOC/contact": [x.get("entry_id") for x in record.get("amoc_and_contacts", [])],
        "evidence": [x.get("evidence_id") for x in evidence],
        "field assertion": [x.get("assertion_id") for x in assertions],
    }
    compliance_ids: list[str] = []
    limit_ids: list[str] = []
    serial_ids: list[str] = []
    for group in applicability:
        serial_ids.extend(
            item.get("restriction_id") for item in group.get("serial_restrictions", [])
        )
    for requirement in requirements:
        for rule in requirement.get("compliance_rules", []):
            compliance_ids.append(rule.get("compliance_id"))
            for bucket in ("initial_limits", "repetitive_intervals", "grace_periods"):
                limit_ids.extend(item.get("limit_id") for item in rule.get(bucket, []))
    id_groups["compliance rule"] = compliance_ids
    id_groups["compliance limit"] = limit_ids
    id_groups["serial restriction"] = serial_ids
    for label, values in id_groups.items():
        clean = [value for value in values if isinstance(value, str)]
        for duplicate in sorted(_duplicates(clean)):
            errors.append(f"duplicate {label} ID: {duplicate}")

    evidence_ids = {
        item.get("evidence_id") for item in evidence if item.get("evidence_id")
    }
    for path, value in _walk(record):
        if path.endswith(".evidence_ids") and isinstance(value, list):
            for evidence_id in value:
                if evidence_id not in evidence_ids:
                    errors.append(f"{path}: unresolved evidence ID {evidence_id!r}")

    source_id = source.get("file_instance_id")
    page_count = source.get("page_count")
    for index, span in enumerate(evidence):
        prefix = f"$.evidence_spans[{index}]"
        if source_id and span.get("source_file_instance_id") != source_id:
            errors.append(
                f"{prefix}.source_file_instance_id: must equal source_document.file_instance_id"
            )
        page_number = span.get("page_number")
        if isinstance(page_count, int) and isinstance(page_number, int) and page_number > page_count:
            errors.append(f"{prefix}.page_number: exceeds source page_count {page_count}")
        start, end = span.get("start_char"), span.get("end_char")
        if (start is None) != (end is None):
            errors.append(f"{prefix}: start_char and end_char must both be null or both be integers")
        if isinstance(start, int) and isinstance(end, int) and end <= start:
            errors.append(f"{prefix}: end_char must be greater than start_char")
        bbox = span.get("bbox_normalized")
        if isinstance(bbox, list) and len(bbox) == 4:
            x0, y0, x1, y1 = bbox
            if not (x0 < x1 and y0 < y1):
                errors.append(f"{prefix}.bbox_normalized: expected [x0, y0, x1, y1] with positive area")

    # Canonical source and record identity.
    canonical_id = source.get("canonical_file_instance_id")
    if canonical_id and record.get("record_id") != f"adann-{canonical_id}":
        errors.append("$.record_id: must be adann-<canonical_file_instance_id>")
    normalized_hash = source.get("normalized_text_sha256")
    annotation_hash = metadata.get("source_text_sha256")
    if normalized_hash and annotation_hash and normalized_hash != annotation_hash:
        errors.append("$.annotation_metadata.source_text_sha256: does not match source_document.normalized_text_sha256")

    ad_number = identity.get("ad_number")
    match = EASA_AD_RE.fullmatch(ad_number or "")
    if match:
        parsed_revision = int(match.group("revision") or 0)
        parsed_emergency = bool(match.group("emergency"))
        if identity.get("base_ad_number") != match.group("base"):
            errors.append("$.ad_identity.base_ad_number: inconsistent with ad_number")
        if identity.get("revision_number") != parsed_revision:
            errors.append("$.ad_identity.revision_number: inconsistent with ad_number")
        if identity.get("is_emergency") != parsed_emergency:
            errors.append("$.ad_identity.is_emergency: inconsistent with the -E suffix")
    emergency = identity.get("is_emergency")
    expected_kind = "emergency_ad" if emergency else "standard_ad"
    expected_class = "emergency" if emergency else "standard"
    if identity.get("publication_kind") != expected_kind:
        errors.append("$.ad_identity.publication_kind: inconsistent with is_emergency")
    if classification.get("emergency_status") not in {expected_class, "unknown"}:
        errors.append("$.classification.emergency_status: inconsistent with is_emergency")

    correction = identity.get("correction_date") or {}
    if identity.get("is_correction") and not correction.get("value"):
        errors.append("$.ad_identity.correction_date.value: required when is_correction is true")
    if not identity.get("is_correction") and correction.get("value") is not None:
        errors.append("$.ad_identity.correction_date.value: must be null when is_correction is false")

    # Grounded scalar conventions.
    for path, value in _walk(record):
        if not isinstance(value, dict):
            continue
        if {"state", "value", "raw_text", "evidence_ids"}.issubset(value):
            state = value.get("state")
            scalar = value.get("value")
            raw = value.get("raw_text")
            refs = value.get("evidence_ids") or []
            if state == "present" and (scalar is None or raw is None or not refs):
                errors.append(f"{path}: state 'present' requires value, raw_text, and evidence")
            if state == "explicit_none" and (scalar is not None or raw is None or not refs):
                errors.append(f"{path}: state 'explicit_none' requires null value plus raw_text and evidence")
            if state == "not_stated" and (scalar is not None or raw is not None):
                errors.append(f"{path}: state 'not_stated' requires null value and raw_text")

    app_ids = {item.get("group_id") for item in applicability}
    req_ids = {item.get("requirement_id") for item in requirements}
    pub_ids = {item.get("publication_id") for item in publications}
    for index, requirement in enumerate(requirements):
        prefix = f"$.requirements[{index}]"
        for app_id in requirement.get("applicability_group_ids", []):
            if app_id not in app_ids:
                errors.append(f"{prefix}.applicability_group_ids: unresolved ID {app_id!r}")
        parent_id = requirement.get("parent_requirement_id")
        if parent_id and parent_id not in req_ids:
            errors.append(f"{prefix}.parent_requirement_id: unresolved ID {parent_id!r}")
        if parent_id == requirement.get("requirement_id"):
            errors.append(f"{prefix}.parent_requirement_id: a requirement cannot parent itself")
        for follow_id in requirement.get("follow_on_requirement_ids", []):
            if follow_id not in req_ids:
                errors.append(f"{prefix}.follow_on_requirement_ids: unresolved ID {follow_id!r}")
            if follow_id == requirement.get("requirement_id"):
                errors.append(f"{prefix}.follow_on_requirement_ids: a requirement cannot follow itself")
        for pub_id in requirement.get("method_publication_ids", []):
            if pub_id not in pub_ids:
                errors.append(f"{prefix}.method_publication_ids: unresolved ID {pub_id!r}")
        terminating = requirement.get("terminating_action") or {}
        for target in terminating.get("terminates_requirement_ids", []):
            if target not in req_ids:
                errors.append(f"{prefix}.terminating_action: unresolved requirement ID {target!r}")
            if target == requirement.get("requirement_id"):
                errors.append(
                    f"{prefix}.terminating_action: a terminating action cannot target "
                    "its own enclosing requirement"
                )
        present = terminating.get("present")
        if present is True and (
            not terminating.get("action_text")
            or not terminating.get("evidence_ids")
            or not terminating.get("terminates_requirement_ids")
            or terminating.get("scope") in {"none", "unknown"}
        ):
            errors.append(
                f"{prefix}.terminating_action: present=true requires text, evidence, "
                "at least one target requirement, and partial/full scope"
            )
        if present is False and (
            terminating.get("action_text") is not None
            or terminating.get("terminates_requirement_ids")
            or terminating.get("scope") != "none"
        ):
            errors.append(f"{prefix}.terminating_action: present=false requires null text, no targets, and scope=none")
        for rule_index, rule in enumerate(requirement.get("compliance_rules", [])):
            rule_prefix = f"{prefix}.compliance_rules[{rule_index}]"
            repetitive = rule.get("repetitive_intervals") or []
            if rule.get("is_repetitive") and not repetitive:
                errors.append(f"{rule_prefix}: is_repetitive=true requires repetitive_intervals")
            if not rule.get("is_repetitive") and repetitive:
                errors.append(f"{rule_prefix}: repetitive_intervals require is_repetitive=true")
            limits = rule.get("initial_limits") or []
            if rule.get("logic") == "whichever_occurs_first" and len(limits) < 2:
                errors.append(f"{rule_prefix}: whichever_occurs_first requires at least two initial limits")
            for bucket in ("initial_limits", "repetitive_intervals", "grace_periods"):
                for limit_index, limit in enumerate(rule.get(bucket, [])):
                    limit_prefix = f"{rule_prefix}.{bucket}[{limit_index}]"
                    if limit.get("unit") == "calendar_date" and not limit.get("calendar_date"):
                        errors.append(f"{limit_prefix}.calendar_date: required for unit=calendar_date")
                    if limit.get("unit") != "calendar_date" and limit.get("calendar_date") is not None:
                        errors.append(f"{limit_prefix}.calendar_date: only allowed for unit=calendar_date")

    for collection_name in ("exceptions", "previous_action_credit"):
        for index, item in enumerate(record.get(collection_name, [])):
            for req_id in item.get("applies_to_requirement_ids", []):
                if req_id not in req_ids:
                    errors.append(f"$.{collection_name}[{index}]: unresolved requirement ID {req_id!r}")
    for index, credit in enumerate(record.get("previous_action_credit", [])):
        for pub_id in credit.get("credited_publication_ids", []):
            if pub_id not in pub_ids:
                errors.append(f"$.previous_action_credit[{index}]: unresolved publication ID {pub_id!r}")

    # Relationship direction and verification status are safety-critical.
    supersedure_statement = identity.get("supersedure_statement") or {}
    for index, relationship in enumerate(relationships):
        prefix = f"$.relationships[{index}]"
        relation_type = relationship.get("relationship_type")
        target_record_id = relationship.get("target_record_id")
        target_version_key = relationship.get("target_logical_version_key")
        same_ad_number = relationship.get("target_ad_number") == ad_number
        if same_ad_number and relation_type not in {"corrects", "corrected_by"}:
            errors.append(
                f"{prefix}.target_ad_number: same-number targets are allowed only "
                "for correction relationships"
            )
        if relation_type in {"corrects", "corrected_by"} and not same_ad_number:
            errors.append(
                f"{prefix}.target_ad_number: correction relationships must target "
                "the same printed AD number"
            )
        if relation_type in {"corrects", "corrected_by"} and same_ad_number and not (
            target_record_id or target_version_key
        ):
            errors.append(
                f"{prefix}: a same-number correction requires target_record_id or "
                "target_logical_version_key"
            )
        if target_record_id == record.get("record_id"):
            errors.append(f"{prefix}.target_record_id: cannot equal the current record_id")
        if target_version_key == identity.get("logical_version_key"):
            errors.append(
                f"{prefix}.target_logical_version_key: cannot equal the current logical_version_key"
            )
        if relation_type == "corrects" and not identity.get("is_correction"):
            errors.append(f"{prefix}: relationship_type=corrects requires is_correction=true")
        if (
            supersedure_statement.get("state") == "explicit_none"
            and relation_type == "supersedes"
        ):
            errors.append(
                f"{prefix}: relationship_type=supersedes conflicts with "
                "supersedure_statement.state=explicit_none"
            )
        status = relationship.get("verification_status")
        manual = relationship.get("manually_verified")
        if status == "candidate" and manual:
            errors.append(f"{prefix}: candidate relationships cannot be manually_verified")
        if status in {"annotator_verified", "adjudicated"} and not manual:
            errors.append(f"{prefix}: verified relationships require manually_verified=true")
        if relationship.get("source") == "historical_reference" and relationship.get("relationship_type") != "referenced_only":
            errors.append(f"{prefix}: historical_reference source must use relationship_type=referenced_only")
        if strict and metadata.get("record_status") in APPROVED_STATUSES and status in {
            "candidate",
            "conflicting",
            "rejected",
        }:
            errors.append(f"{prefix}: approved records cannot retain {status!r} relationships")

    annotator_entries = metadata.get("annotators", [])
    annotator_id_list = [item.get("annotator_id") for item in annotator_entries]
    annotator_ids = set(annotator_id_list)
    for duplicate in sorted(_duplicates(value for value in annotator_id_list if value)):
        errors.append(
            f"$.annotation_metadata.annotators: duplicate annotator_id {duplicate!r}; "
            "one person cannot occupy multiple review roles in one record"
        )
    for index, assertion in enumerate(assertions):
        prefix = f"$.field_assertions[{index}]"
        field_path = assertion.get("field_path")
        if field_path and not _json_pointer_exists(record, field_path):
            errors.append(f"{prefix}.field_path: JSON Pointer does not resolve: {field_path!r}")
        for input_path in assertion.get("input_field_paths", []):
            if not _json_pointer_exists(record, input_path):
                errors.append(f"{prefix}.input_field_paths: JSON Pointer does not resolve: {input_path!r}")
        origin = assertion.get("origin")
        confidence = assertion.get("confidence")
        if origin == "auto_extracted" and confidence is None:
            errors.append(f"{prefix}.confidence: automatic extraction requires a confidence value")
        if origin in HUMAN_OR_DERIVED_ORIGINS and confidence is not None:
            errors.append(f"{prefix}.confidence: confidence is reserved for automatic extraction")
        assertion_annotator = assertion.get("annotator_id")
        if assertion_annotator and assertion_annotator not in annotator_ids:
            errors.append(f"{prefix}.annotator_id: unknown annotator {assertion_annotator!r}")
        if origin == "derived" and not assertion.get("derivation_rule"):
            errors.append(f"{prefix}.derivation_rule: required for derived assertions")

    if benchmark is not None and benchmark.get("split_group") != identity.get("base_ad_number"):
        errors.append("$.benchmark_metadata.split_group: must equal ad_identity.base_ad_number")
    if benchmark is not None and benchmark.get("gold_record") and metadata.get("record_status") != "approved":
        errors.append("$.benchmark_metadata.gold_record: gold records must be approved")

    ata_codes = {item.get("code") for item in publication.get("ata_chapters", [])}
    classified_ata = set(classification.get("ata_chapters", []))
    if strict and ata_codes != classified_ata:
        errors.append("$.classification.ata_chapters: must match publication.ata_chapters")
    action_types = {
        action
        for requirement in requirements
        for action in requirement.get("action_types", [])
    }
    if strict and action_types != set(classification.get("action_types", [])):
        errors.append("$.classification.action_types: must match the requirement action-type union")
    terminating_present = any(
        (requirement.get("terminating_action") or {}).get("present") is True
        for requirement in requirements
    )
    if strict and classification.get("terminating_action_present") != terminating_present:
        errors.append("$.classification.terminating_action_present: inconsistent with requirements")

    created = _iso_datetime(metadata.get("created_at"))
    updated = _iso_datetime(metadata.get("updated_at"))
    if created and updated and updated < created:
        errors.append("$.annotation_metadata.updated_at: cannot precede created_at")
    for index, event in enumerate(metadata.get("events", [])):
        if event.get("actor_id") not in annotator_ids:
            errors.append(f"$.annotation_metadata.events[{index}].actor_id: unknown annotator")

    if strict:
        status = metadata.get("record_status")
        if status != "approved":
            errors.append("$.annotation_metadata.record_status: strict validation requires approved")
        if not applicability:
            errors.append("$.applicability_groups: approved records require at least one group")
        if not requirements:
            errors.append("$.requirements: approved records require at least one requirement")
        if not evidence:
            errors.append("$.evidence_spans: approved records require evidence")
        if not classification.get("human_confirmed"):
            errors.append("$.classification.human_confirmed: strict validation requires true")
        roles = {item.get("role") for item in annotator_entries}
        if "annotator" not in roles:
            errors.append("$.annotation_metadata.annotators: an approved record requires an annotator")
        if not roles.intersection({"reviewer", "adjudicator", "domain_approver"}):
            errors.append("$.annotation_metadata.annotators: an approved record requires independent review")
        review_actor_ids = {
            item.get("annotator_id")
            for item in annotator_entries
            if item.get("role") in {"reviewer", "adjudicator", "domain_approver"}
        }
        annotation_actor_ids = {
            item.get("annotator_id")
            for item in annotator_entries
            if item.get("role") == "annotator"
        }
        approved_events = [
            event
            for event in metadata.get("events", [])
            if event.get("event_type") == "approved"
        ]
        if not approved_events:
            errors.append("$.annotation_metadata.events: an approved record requires an approved event")
        for event in approved_events:
            if (
                event.get("actor_id") not in review_actor_ids
                or event.get("actor_id") in annotation_actor_ids
            ):
                errors.append(
                    "$.annotation_metadata.events: each approved event must be performed "
                    "by a reviewer, adjudicator, or domain approver"
                )

        def require_evidence(item: Any, path: str) -> None:
            if isinstance(item, dict) and not item.get("evidence_ids"):
                errors.append(f"{path}.evidence_ids: required for approval")

        require_evidence(identity, "$.ad_identity")
        require_evidence(classification, "$.classification")
        if record.get("unsafe_condition") is not None:
            require_evidence(record["unsafe_condition"], "$.unsafe_condition")
        for index, chapter in enumerate(publication.get("ata_chapters", [])):
            require_evidence(chapter, f"$.publication.ata_chapters[{index}]")
        for index, manufacturer in enumerate(publication.get("manufacturers", [])):
            require_evidence(manufacturer, f"$.publication.manufacturers[{index}]")
        for index, group in enumerate(applicability):
            require_evidence(group, f"$.applicability_groups[{index}]")
            for serial_index, restriction in enumerate(group.get("serial_restrictions", [])):
                require_evidence(
                    restriction,
                    f"$.applicability_groups[{index}].serial_restrictions[{serial_index}]",
                )
        for index, definition in enumerate(record.get("definitions", [])):
            require_evidence(definition, f"$.definitions[{index}]")
        for index, requirement in enumerate(requirements):
            require_evidence(requirement, f"$.requirements[{index}]")
            if not requirement.get("compliance_rules"):
                errors.append(f"$.requirements[{index}].compliance_rules: required for approval")
            terminating = requirement.get("terminating_action") or {}
            if terminating.get("present") is True:
                require_evidence(
                    terminating, f"$.requirements[{index}].terminating_action"
                )
            for rule_index, rule in enumerate(requirement.get("compliance_rules", [])):
                rule_path = f"$.requirements[{index}].compliance_rules[{rule_index}]"
                require_evidence(rule, rule_path)
                for bucket in ("initial_limits", "repetitive_intervals", "grace_periods"):
                    for limit_index, limit in enumerate(rule.get(bucket, [])):
                        require_evidence(
                            limit, f"{rule_path}.{bucket}[{limit_index}]"
                        )
        for collection_name in (
            "exceptions",
            "previous_action_credit",
            "referenced_publications",
            "relationships",
            "amoc_and_contacts",
        ):
            for index, item in enumerate(record.get(collection_name, [])):
                require_evidence(item, f"$.{collection_name}[{index}]")

    return sorted(set(errors))


def batch_semantic_errors(
    records: list[tuple[str, dict[str, Any]]],
    allow_unresolved_targets: bool = False,
) -> list[str]:
    """Check split leakage and resolvable record links across valid records."""

    errors: list[str] = []
    groups: dict[str, list[tuple[str, str]]] = {}
    assigned_splits = {"train", "validation", "test"}
    records_by_id: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    records_by_version: dict[
        tuple[str, str], list[tuple[str, dict[str, Any]]]
    ] = {}

    def add_group(group_key: str | None, label: str, split: str) -> None:
        if group_key and split in assigned_splits:
            groups.setdefault(group_key, []).append((label, split))

    for label, record in records:
        identity = record.get("ad_identity") or {}
        source = record.get("source_document") or {}
        benchmark = record.get("benchmark_metadata") or {}
        split = benchmark.get("split")
        record_id = record.get("record_id")
        version_key = identity.get("logical_version_key")
        ad_number = identity.get("ad_number")
        if record_id:
            records_by_id.setdefault(record_id, []).append((label, record))
        if ad_number and version_key:
            records_by_version.setdefault((ad_number, version_key), []).append(
                (label, record)
            )
        add_group(f"base_ad_number:{identity.get('base_ad_number')}", label, split)
        add_group(f"content_id:{source.get('content_id')}", label, split)
        exact_group = source.get("exact_duplicate_group")
        near_group = source.get("near_duplicate_cluster")
        add_group(f"exact_duplicate:{exact_group}" if exact_group else None, label, split)
        add_group(f"near_duplicate:{near_group}" if near_group else None, label, split)
        for cluster_id in benchmark.get("duplicate_cluster_ids", []):
            add_group(f"benchmark_cluster:{cluster_id}", label, split)

    for group_key, members in sorted(groups.items()):
        splits = {split for _, split in members}
        if len(splits) > 1:
            rendered = ", ".join(f"{label}={split}" for label, split in members)
            errors.append(f"split leakage for {group_key}: {rendered}")

    for record_id, members in sorted(records_by_id.items()):
        if len(members) > 1:
            labels = ", ".join(label for label, _ in members)
            errors.append(f"duplicate record_id {record_id}: {labels}")
    for version_key, members in sorted(records_by_version.items()):
        if len(members) > 1:
            labels = ", ".join(label for label, _ in members)
            errors.append(
                f"duplicate (ad_number, logical_version_key) {version_key!r}: {labels}"
            )

    for label, record in records:
        for index, relationship in enumerate(record.get("relationships", [])):
            prefix = f"{label}:$.relationships[{index}]"
            target_ad_number = relationship.get("target_ad_number")
            target_record_id = relationship.get("target_record_id")
            target_version_key = relationship.get("target_logical_version_key")
            record_matches = records_by_id.get(target_record_id, []) if target_record_id else []
            version_matches = (
                records_by_version.get((target_ad_number, target_version_key), [])
                if target_version_key
                else []
            )
            if target_record_id and not record_matches and not allow_unresolved_targets:
                errors.append(
                    f"{prefix}.target_record_id: unresolved batch target {target_record_id!r}"
                )
            if target_version_key and not version_matches and not allow_unresolved_targets:
                errors.append(
                    f"{prefix}.target_logical_version_key: unresolved batch target "
                    f"({target_ad_number!r}, {target_version_key!r})"
                )
            if len(record_matches) == 1:
                resolved_identity = record_matches[0][1].get("ad_identity") or {}
                if resolved_identity.get("ad_number") != target_ad_number:
                    errors.append(
                        f"{prefix}.target_ad_number: does not match target_record_id"
                    )
            if len(record_matches) == 1 and len(version_matches) == 1:
                record_target = record_matches[0][1].get("record_id")
                version_target = version_matches[0][1].get("record_id")
                if record_target != version_target:
                    errors.append(
                        f"{prefix}: target_record_id and target_logical_version_key "
                        "resolve to different records"
                    )
    return errors


def validate_record(
    record: dict[str, Any], schema: dict[str, Any], strict: bool = False
) -> list[str]:
    schema_errors = structural_errors(record, schema)
    if schema_errors:
        return schema_errors
    return semantic_errors(record, strict=strict)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path, help="annotation JSON file(s)")
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH, help="schema path")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="apply approval/gold-record gates in addition to normal checks",
    )
    parser.add_argument(
        "--allow-unresolved-targets",
        action="store_true",
        help=(
            "allow target_record_id/target_logical_version_key values whose target "
            "record was not supplied in this validation batch"
        ),
    )
    args = parser.parse_args(argv)

    try:
        schema = load_schema(args.schema)
    except (OSError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"Schema error: {exc}", file=sys.stderr)
        return 2

    failed = False
    structurally_valid_records: list[tuple[str, dict[str, Any]]] = []
    for path in args.files:
        try:
            record = load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"FAIL {path}: {exc}")
            failed = True
            continue
        schema_errors = structural_errors(record, schema)
        if schema_errors:
            errors = schema_errors
        else:
            structurally_valid_records.append((str(path), record))
            errors = semantic_errors(record, strict=args.strict)
        if errors:
            failed = True
            print(f"FAIL {path} ({len(errors)} error(s))")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {path}")
    if args.allow_unresolved_targets:
        print(
            "WARNING cross-record targets not supplied in this batch are not resolved"
        )
    batch_errors = batch_semantic_errors(
        structurally_valid_records,
        allow_unresolved_targets=args.allow_unresolved_targets,
    )
    if batch_errors:
        failed = True
        print(f"FAIL corpus-level checks ({len(batch_errors)} error(s))")
        for error in batch_errors:
            print(f"  - {error}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
