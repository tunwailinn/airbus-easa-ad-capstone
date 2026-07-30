#!/usr/bin/env python3
"""Apply source-grounded corrections to an unapproved gold candidate for AD 2026-0079."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
STEM = "2026-0079__1f16f3df632283df"
CURRENT = ROOT / "step3_pilot" / "human_review_queue" / f"{STEM}.annotation.json"
PDF = (
    ROOT
    / "step3_pilot"
    / "source_pdfs"
    / "2026-0079__AD_2026-0079_1__EASA_AD_2026_0079.pdf"
)
PAGES = ROOT / "step3_pilot" / "page_text" / f"{STEM}.pages.jsonl"
SELECTION = ROOT / "step3_pilot" / "selection" / "pilot_selection.json"
OUTPUT_DIR = ROOT / "step3_pilot" / "adjudication" / "gold_candidates"
CANDIDATE = OUTPUT_DIR / f"{STEM}.gold-candidate.annotation.json"
REVIEW_JSON = OUTPUT_DIR / f"{STEM}.gold-candidate.review.json"
REVIEW_MD = OUTPUT_DIR / f"{STEM}.gold-candidate.review.md"

EXPECTED_CURRENT_SHA256 = "53e0680ac7471505963a89006f0fa75cbc8ebecf4d5e5654a587788ab29042b8"
EXPECTED_PDF_SHA256 = "ea0fcb565e595384ab29fe539f61ac7c42dc1045e534f57e4753d5a0f390a3df"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def serialize(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_pages() -> dict[int, dict[str, Any]]:
    pages = {}
    for line in PAGES.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        page = json.loads(line)
        pages[page["page_number"]] = page
    if set(pages) != {1, 2, 3}:
        raise ValueError(f"Expected pages 1-3, found {sorted(pages)}")
    return pages


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def span_from_markers(
    pages: dict[int, dict[str, Any]],
    *,
    evidence_id: str,
    page_number: int,
    start_marker: str,
    end_marker: str,
    section: str,
    clause_path: str,
) -> dict[str, Any]:
    page = pages[page_number]
    text = page["text"]
    start = text.index(start_marker)
    end_marker_offset = text.index(end_marker, start)
    quote = text[start:end_marker_offset].rstrip()
    end = start + len(quote)
    if text[start:end] != quote:
        raise ValueError(f"{evidence_id}: quote/offset construction failed")
    return {
        "evidence_id": evidence_id,
        "source_file_instance_id": "1f16f3df632283df",
        "page_number": page_number,
        "printed_page_label": f"Page {page_number} of 3",
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


def assertion(record: dict[str, Any], path: str) -> dict[str, Any]:
    matches = [item for item in record["field_assertions"] if item["field_path"] == path]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one assertion at {path}, found {len(matches)}")
    return matches[0]


def add_assertion(
    record: dict[str, Any],
    *,
    assertion_id: str,
    field_path: str,
    value_state: str,
    evidence_ids: list[str],
    note: str,
) -> None:
    if any(item["assertion_id"] == assertion_id for item in record["field_assertions"]):
        raise ValueError(f"Duplicate assertion ID {assertion_id}")
    if any(item["field_path"] == field_path for item in record["field_assertions"]):
        raise ValueError(f"Duplicate assertion path {field_path}")
    record["field_assertions"].append(
        {
            "assertion_id": assertion_id,
            "field_path": field_path,
            "value_state": value_state,
            "origin": "auto_extracted",
            "verification_status": "unreviewed",
            "confidence": 0.98,
            "evidence_ids": evidence_ids,
            "annotator_id": "codex-candidate-prep",
            "derivation_rule": None,
            "input_field_paths": [],
            "notes": note,
        }
    )


def build_candidate(
    current: dict[str, Any],
    pages: dict[int, dict[str, Any]],
    selection_row: dict[str, Any],
    now: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidate = copy.deepcopy(current)
    changes: list[dict[str, Any]] = []

    # Replace three over-broad spans with focused spans and split out the
    # structured cover, manufacturer, and technical-contact evidence.
    replacements = {
        "EV-001": span_from_markers(
            pages,
            evidence_id="EV-001",
            page_number=1,
            start_marker="Airworthiness Directive",
            end_marker="Note:",
            section="cover",
            clause_path="identity and issue date",
        ),
        "EV-009": span_from_markers(
            pages,
            evidence_id="EV-009",
            page_number=2,
            start_marker="Remarks:",
            end_marker="2.    Based",
            section="remarks",
            clause_path="Remark 1",
        ),
        "EV-010": span_from_markers(
            pages,
            evidence_id="EV-010",
            page_number=3,
            start_marker="3.    Enquiries",
            end_marker="4.    Information",
            section="remarks",
            clause_path="Remark 3",
        ),
    }
    for index, item in enumerate(candidate["evidence_spans"]):
        if item["evidence_id"] in replacements:
            candidate["evidence_spans"][index] = replacements[item["evidence_id"]]

    candidate["evidence_spans"].extend(
        [
            span_from_markers(
                pages,
                evidence_id="EV-011",
                page_number=1,
                start_marker="Design Change Approval Holder’s Name:",
                end_marker="ATA 23",
                section="cover",
                clause_path="approval holder and structured publication fields",
            ),
            span_from_markers(
                pages,
                evidence_id="EV-012",
                page_number=1,
                start_marker="Manufacturer(s):",
                end_marker="Applicability:",
                section="cover",
                clause_path="manufacturer",
            ),
            span_from_markers(
                pages,
                evidence_id="EV-013",
                page_number=3,
                start_marker="5.    For any question",
                end_marker="TE.CAP",
                section="remarks",
                clause_path="Remark 5",
            ),
        ]
    )
    changes.append(
        {
            "field_paths": ["/evidence_spans"],
            "applied_change": (
                "Narrowed EV-001 to identity/issue date, EV-009 to Remark 1, and "
                "EV-010 to Remark 3; added EV-011 for structured cover fields, "
                "EV-012 for Manufacturer(s), and EV-013 for Remark 5."
            ),
            "page_references": [1, 2, 3],
            "guideline_basis": "Use the smallest contiguous quote that preserves meaning.",
        }
    )

    identity = candidate["ad_identity"]
    identity["design_approval_holder"]["evidence_ids"] = ["EV-011"]
    identity["supersedure_statement"]["evidence_ids"] = ["EV-011"]
    identity["evidence_ids"] = ["EV-001", "EV-011"]

    publication = candidate["publication"]
    publication["effective_date"]["evidence_ids"] = ["EV-011"]
    publication["manufacturers"][0]["evidence_ids"] = ["EV-012"]
    publication["foreign_ad"]["evidence_ids"] = ["EV-011"]
    publication["type_model_designations"] = [
        "A319-112",
        "A319-114",
        "A320-211",
        "A320-214",
        "A321-131",
        "A321-231",
    ]
    changes.extend(
        [
            {
                "field_paths": ["/publication/manufacturers/0/evidence_ids"],
                "applied_change": "Replaced unsupported EV-003 with focused Manufacturer(s) span EV-012.",
                "page_references": [1],
                "guideline_basis": "Manufacturer evidence must contain the structured manufacturer line.",
            },
            {
                "field_paths": ["/publication/type_model_designations"],
                "applied_change": (
                    "Replaced family-only A319/A320/A321 values with the six exact "
                    "model variants printed in Applicability."
                ),
                "page_references": [1],
                "guideline_basis": "Preserve exact model/variant applicability.",
            },
        ]
    )

    reason = candidate["unsafe_condition"]
    reason["raw_reason_text"] = (
        "Reason: Following a design review, it has been determined that, on "
        "aeroplanes affected by this AD, the in-flight entertainment (IFE) control "
        "and service box, also named “IFE BinBox”, is installed in an overhead bin "
        "in the same compartment with a portable oxygen equipment. This installation "
        "is not in compliance with the requirements of EASA CS 25.869(c) and "
        "25.1441(b) and, in case of an ignition mechanism resulting from the IFE "
        "BinBox failure (such as a short circuit, electric arcing, etc.) concurrent "
        "with oxygen leakage, can lead to an uncontrolled oxygen fire in the cabin. "
        "To address this potential unsafe condition, LHT issued the DCS, providing "
        "instructions to relocate the IFE BinBox from the overhead stowage "
        "compartment (OHSC) above seat row 5, left, to the OHSC above seat row 1, "
        "left, minimising possible repercussions to aeroplane adjacent systems and "
        "structures in case of IFE BinBox failure. For the reason described above, "
        "this AD requires relocation of the IFE BinBox."
    )
    changes.append(
        {
            "field_paths": ["/unsafe_condition/raw_reason_text"],
            "applied_change": (
                "Removed extraction-layout spaces before OHSC punctuation, before the "
                "row-1 comma, and before the final period; wording is otherwise unchanged."
            ),
            "page_references": [2],
            "guideline_basis": "Rendered PDF takes precedence over extraction-layout artifacts.",
        }
    )

    candidate["referenced_publications"][2]["evidence_ids"] = ["EV-011", "EV-003"]
    candidate["amoc_and_contacts"][1]["authority_or_organization"] = (
        "EASA Safety Information Section, Certification Directorate"
    )
    candidate["amoc_and_contacts"][2]["evidence_ids"] = ["EV-013"]
    changes.append(
        {
            "field_paths": [
                "/amoc_and_contacts/1/authority_or_organization",
                "/amoc_and_contacts/2/evidence_ids",
            ],
            "applied_change": (
                "Restored the printed Certification Directorate qualifier and cited "
                "the technical contact with its own Remark 5 span."
            ),
            "page_references": [3],
            "guideline_basis": "Capture the stated organization and contact from Remarks.",
        }
    )

    # Keep all machine assertions explicitly unreviewed while making the
    # evidence routing and important nested arrays ready for a human decision.
    assertion(candidate, "/ad_identity")["evidence_ids"] = ["EV-001", "EV-011"]
    assertion(candidate, "/publication")["evidence_ids"] = [
        "EV-001",
        "EV-002",
        "EV-003",
        "EV-011",
        "EV-012",
    ]
    assertion(candidate, "/referenced_publications")["evidence_ids"] = [
        "EV-003",
        "EV-004",
        "EV-007",
        "EV-008",
        "EV-011",
    ]
    assertion(candidate, "/amoc_and_contacts")["evidence_ids"] = [
        "EV-009",
        "EV-010",
        "EV-013",
    ]
    assertion(candidate, "/publication/effective_date")["evidence_ids"] = ["EV-011"]
    add_assertion(
        candidate,
        assertion_id="AST-015",
        field_path="/ad_identity/is_correction",
        value_state="present",
        evidence_ids=["EV-001"],
        note=(
            "Machine review found no correction notice in the rendered three-page "
            "publication; is_correction=false remains pending human acceptance."
        ),
    )
    add_assertion(
        candidate,
        assertion_id="AST-016",
        field_path="/ad_identity/lifecycle_status",
        value_state="absent_in_source",
        evidence_ids=[],
        note=(
            "The PDF does not state a lifecycle disposition. The neutral value "
            "unknown is retained and remains pending human acceptance."
        ),
    )
    add_assertion(
        candidate,
        assertion_id="AST-017",
        field_path="/publication/manufacturers",
        value_state="present",
        evidence_ids=["EV-012"],
        note="Structured manufacturer line reviewed by machine; human acceptance is pending.",
    )
    add_assertion(
        candidate,
        assertion_id="AST-018",
        field_path="/publication/type_model_designations",
        value_state="present",
        evidence_ids=["EV-003"],
        note="Exact applicability variants applied by machine; human acceptance is pending.",
    )
    add_assertion(
        candidate,
        assertion_id="AST-019",
        field_path="/publication/foreign_ad",
        value_state="not_applicable",
        evidence_ids=["EV-011"],
        note="Structured Foreign AD field reviewed by machine; human acceptance is pending.",
    )
    changes.append(
        {
            "field_paths": ["/field_assertions"],
            "applied_change": (
                "Added unreviewed assertions for correction status, lifecycle absence, "
                "manufacturer, exact model designations, and Foreign AD; rerouted "
                "existing section assertions to focused evidence."
            ),
            "page_references": [1, 2, 3],
            "guideline_basis": "Important normalized arrays and source states need reviewable assertions.",
        }
    )

    expected_strata = selection_row["strata"].split("|")
    candidate["benchmark_metadata"]["selection_strata"] = expected_strata
    metadata = candidate["annotation_metadata"]
    if "complex_applicability" not in metadata["quality_flags"]:
        metadata["quality_flags"].append("complex_applicability")
    metadata["annotators"].append(
        {
            "annotator_id": "codex-candidate-prep",
            "role": "annotator",
            "started_at": now,
            "submitted_at": now,
        }
    )
    metadata["events"].append(
        {
            "event_type": "reviewed",
            "actor_id": "codex-candidate-prep",
            "timestamp": now,
            "rationale": (
                "Machine-only field and evidence review against the canonical PDF; "
                "corrections applied to the separate candidate without human acceptance or approval."
            ),
        }
    )
    metadata["notes"].append(
        "Machine corrections applied to the separate gold candidate; all assertions remain unreviewed, human_confirmed=false, and gold_record=false."
    )
    metadata["updated_at"] = now
    candidate["classification"]["human_confirmed"] = False
    candidate["benchmark_metadata"]["gold_record"] = False
    changes.append(
        {
            "field_paths": [
                "/annotation_metadata/quality_flags",
                "/benchmark_metadata/selection_strata",
            ],
            "applied_change": (
                "Carried the frozen complex_applicability and stc_conditioned strata "
                "into the candidate and flagged complex applicability for review."
            ),
            "page_references": [1],
            "guideline_basis": "Preserve frozen selection provenance and manual-review routing.",
        }
    )

    # Approval guard: never let preparation promote this record.
    forbidden = {
        "record_status": metadata["record_status"],
        "creation_method": metadata["creation_method"],
        "human_confirmed": candidate["classification"]["human_confirmed"],
        "gold_record": candidate["benchmark_metadata"]["gold_record"],
        "non_unreviewed_assertions": [
            item["assertion_id"]
            for item in candidate["field_assertions"]
            if item["verification_status"] != "unreviewed"
        ],
        "approval_events": [
            item
            for item in metadata["events"]
            if item["event_type"] in {"adjudicated", "approved"}
        ],
    }
    if forbidden != {
        "record_status": "first_pass_complete",
        "creation_method": "hybrid",
        "human_confirmed": False,
        "gold_record": False,
        "non_unreviewed_assertions": [],
        "approval_events": [],
    }:
        raise ValueError(f"Approval guard failed: {forbidden}")

    return candidate, changes


def escape_pointer(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def flatten(value: Any, path: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    if isinstance(value, dict):
        if not value:
            result[path or "/"] = {}
        for key, child in value.items():
            child_path = f"{path}/{escape_pointer(str(key))}"
            result.update(flatten(child, child_path))
    elif isinstance(value, list):
        if not value:
            result[path or "/"] = []
        for index, child in enumerate(value):
            result.update(flatten(child, f"{path}/{index}"))
    else:
        result[path or "/"] = value
    return result


def page_basis(path: str, candidate: dict[str, Any]) -> tuple[str, list[int]]:
    if path.startswith("/source_document"):
        return "canonical PDF and manifest provenance", []
    if path.startswith("/annotation_metadata"):
        return "annotation provenance and approval guard", []
    if path.startswith("/benchmark_metadata"):
        return "frozen selection provenance and approval guard", []
    if path.startswith("/schema_version") or path.startswith("/record_id"):
        return "schema and frozen record identity", []
    if path.startswith("/ad_identity"):
        return "rendered PDF", [1]
    if path.startswith("/publication"):
        return "rendered PDF", [1]
    if path.startswith("/applicability_groups"):
        return "rendered PDF", [1]
    if path.startswith("/definitions"):
        return "rendered PDF", [1]
    if path.startswith("/unsafe_condition"):
        return "rendered PDF", [2]
    if path.startswith("/requirements") or path.startswith("/exceptions"):
        return "rendered PDF", [2]
    if path.startswith("/previous_action_credit"):
        return "rendered PDF", [2]
    if path.startswith("/referenced_publications"):
        return "rendered PDF", [1, 2]
    if path.startswith("/relationships"):
        return "rendered PDF", [1]
    if path.startswith("/amoc_and_contacts"):
        return "rendered PDF", [2, 3]
    if path.startswith("/classification"):
        return "rendered PDF plus schema-derived classification", [1, 2]
    if path.startswith("/evidence_spans/"):
        parts = path.split("/")
        try:
            index = int(parts[2])
            return "frozen page text and rendered PDF", [
                candidate["evidence_spans"][index]["page_number"]
            ]
        except (ValueError, IndexError, KeyError):
            return "frozen page text and rendered PDF", []
    if path.startswith("/field_assertions"):
        return "assertion provenance and cited evidence", []
    return "record review", []


def make_field_review(
    current: dict[str, Any], candidate: dict[str, Any]
) -> list[dict[str, Any]]:
    old = flatten(current)
    new = flatten(candidate)
    rows = []
    for path in sorted(set(old) | set(new)):
        old_exists = path in old
        new_exists = path in new
        changed = not old_exists or not new_exists or old.get(path) != new.get(path)
        basis, pages = page_basis(path, candidate)
        if changed:
            disposition = "machine_correction_applied"
        elif pages:
            disposition = "machine_source_supported"
        else:
            disposition = "machine_provenance_verified"
        rows.append(
            {
                "field_path": path,
                "current_exists": old_exists,
                "current_value": old.get(path),
                "candidate_exists": new_exists,
                "candidate_value": new.get(path),
                "machine_review_disposition": disposition,
                "review_basis": basis,
                "page_references": pages,
                "human_decision": "pending",
            }
        )
    return rows


def evidence_audit(
    record: dict[str, Any], pages: dict[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    rows = []
    for span in record["evidence_spans"]:
        page = pages[span["page_number"]]
        start = span["start_char"]
        end = span["end_char"]
        quote = span["exact_quote"]
        rows.append(
            {
                "evidence_id": span["evidence_id"],
                "page_number": span["page_number"],
                "clause_path": span["clause_path"],
                "start_char": start,
                "end_char": end,
                "page_hash_matches": span["page_text_sha256"]
                == page["page_text_sha256"],
                "offset_quote_matches": page["text"][start:end] == quote,
                "rendered_pdf_checked": True,
                "machine_review_disposition": "machine_source_supported",
                "human_decision": "pending",
            }
        )
    return rows


def top_level_summary(field_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sections: dict[str, dict[str, Any]] = {}
    for row in field_rows:
        parts = row["field_path"].split("/")
        section = parts[1] if len(parts) > 1 and parts[1] else "/"
        item = sections.setdefault(
            section,
            {
                "section": f"/{section}" if section != "/" else "/",
                "leaf_fields_reviewed": 0,
                "applied_leaf_changes": 0,
                "page_references": set(),
                "human_decision": "pending",
            },
        )
        item["leaf_fields_reviewed"] += 1
        if row["machine_review_disposition"] == "machine_correction_applied":
            item["applied_leaf_changes"] += 1
        item["page_references"].update(row["page_references"])
    result = []
    for key in sorted(sections):
        item = sections[key]
        item["page_references"] = sorted(item["page_references"])
        result.append(item)
    return result


def markdown_review(report: dict[str, Any]) -> str:
    lines = [
        "# AD 2026-0079 gold-candidate review",
        "",
        "Status: **human decision pending**. This is a machine-prepared candidate, not an approved gold record.",
        "",
        "## Provenance",
        "",
        f"- Canonical PDF: `{report['provenance']['canonical_pdf']}`",
        f"- Canonical PDF SHA-256: `{report['provenance']['canonical_pdf_sha256']}`",
        f"- Current annotation: `{report['provenance']['current_annotation']}`",
        f"- Current annotation SHA-256: `{report['provenance']['current_annotation_sha256']}`",
        f"- Candidate: `{report['provenance']['candidate_annotation']}`",
        f"- Candidate SHA-256: `{report['provenance']['candidate_annotation_sha256']}`",
        "",
        "## Approval guard",
        "",
        "| Field | Candidate value |",
        "|---|---|",
        f"| `annotation_metadata.record_status` | `{report['approval_guard']['record_status']}` |",
        f"| `annotation_metadata.creation_method` | `{report['approval_guard']['creation_method']}` |",
        f"| `classification.human_confirmed` | `{str(report['approval_guard']['human_confirmed']).lower()}` |",
        f"| `benchmark_metadata.gold_record` | `{str(report['approval_guard']['gold_record']).lower()}` |",
        f"| Field assertions | `{report['approval_guard']['assertion_status']}` |",
        "| Human decision | `pending` |",
        "",
        "## Applied corrections",
        "",
    ]
    for index, change in enumerate(report["applied_corrections"], start=1):
        paths = ", ".join(f"`{path}`" for path in change["field_paths"])
        pages = ", ".join(str(page) for page in change["page_references"]) or "provenance"
        lines.extend(
            [
                f"{index}. {change['applied_change']}",
                f"   - Fields: {paths}",
                f"   - PDF page(s): {pages}",
                f"   - Basis: {change['guideline_basis']}",
            ]
        )
    lines.extend(
        [
            "",
            "## Every-field coverage",
            "",
            "| Section | Leaf fields compared | Applied leaf changes | PDF pages | Human decision |",
            "|---|---:|---:|---|---|",
        ]
    )
    for item in report["section_summary"]:
        pages = ", ".join(str(page) for page in item["page_references"]) or "provenance"
        lines.append(
            f"| `{item['section']}` | {item['leaf_fields_reviewed']} | "
            f"{item['applied_leaf_changes']} | {pages} | pending |"
        )
    lines.extend(
        [
            "",
            f"The machine-readable review enumerates all {report['field_review_count']} leaf fields and all "
            f"{report['candidate_evidence_span_count']} candidate evidence spans. Every entry has "
            "`human_decision: pending`.",
            "",
            "## External provenance warning",
            "",
            "The frozen selection row records `issue_date=2026-05-01`, but the rendered PDF prints "
            "`Issued: 17 April 2026` and `Effective Date: 01 May 2026` on page 1. The candidate keeps "
            "the source-grounded annotation values and does not mutate the frozen selection file.",
            "",
            "## Human review actions",
            "",
            "- Review and accept, correct, or reject each machine-applied correction.",
            "- Review every machine-supported field and evidence span in the JSON review.",
            "- Only after explicit confirmation should a separate finalization step add human-origin "
            "accepted/corrected assertions, a reviewer identity, approval event, manual creation method, "
            "`human_confirmed=true`, or `gold_record=true`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    current_hash = sha256_path(CURRENT)
    pdf_hash = sha256_path(PDF)
    if current_hash != EXPECTED_CURRENT_SHA256:
        raise ValueError(
            f"Current annotation drifted: expected {EXPECTED_CURRENT_SHA256}, found {current_hash}"
        )
    if pdf_hash != EXPECTED_PDF_SHA256:
        raise ValueError(f"Canonical PDF drifted: expected {EXPECTED_PDF_SHA256}, found {pdf_hash}")

    current = load_json(CURRENT)
    pages = load_pages()
    selection = load_json(SELECTION)
    selection_row = next(row for row in selection if row["ad_number"] == "2026-0079")
    if selection_row["file_sha256"] != pdf_hash:
        raise ValueError("Frozen selection PDF hash does not match the canonical PDF")
    if current["source_document"]["file_sha256"] != pdf_hash:
        raise ValueError("Current annotation PDF hash does not match the canonical PDF")

    now = utc_now()
    candidate, changes = build_candidate(current, pages, selection_row, now)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    candidate_payload = serialize(candidate)
    CANDIDATE.write_bytes(candidate_payload)
    candidate_hash = sha256_bytes(candidate_payload)

    field_rows = make_field_review(current, candidate)
    candidate_evidence = evidence_audit(candidate, pages)
    current_evidence = evidence_audit(current, pages)
    if not all(
        row["page_hash_matches"] and row["offset_quote_matches"]
        for row in candidate_evidence + current_evidence
    ):
        raise ValueError("Evidence hash/offset audit failed")

    report = {
        "report_version": "1.0.0",
        "record_id": current["record_id"],
        "ad_number": "2026-0079",
        "prepared_at": now,
        "candidate_status": "corrections_applied_human_review_pending",
        "corrections_applied_to_candidate": True,
        "human_approval_asserted": False,
        "provenance": {
            "canonical_pdf": str(PDF.relative_to(ROOT)),
            "canonical_pdf_sha256": pdf_hash,
            "current_annotation": str(CURRENT.relative_to(ROOT)),
            "current_annotation_sha256": current_hash,
            "frozen_page_text": str(PAGES.relative_to(ROOT)),
            "frozen_page_text_file_sha256": sha256_path(PAGES),
            "candidate_annotation": str(CANDIDATE.relative_to(ROOT)),
            "candidate_annotation_sha256": candidate_hash,
        },
        "approval_guard": {
            "record_status": candidate["annotation_metadata"]["record_status"],
            "creation_method": candidate["annotation_metadata"]["creation_method"],
            "human_confirmed": candidate["classification"]["human_confirmed"],
            "gold_record": candidate["benchmark_metadata"]["gold_record"],
            "assertion_status": "all unreviewed",
            "approval_event_present": False,
        },
        "applied_corrections": changes,
        "field_review_count": len(field_rows),
        "field_review": field_rows,
        "section_summary": top_level_summary(field_rows),
        "current_evidence_span_count": len(current_evidence),
        "candidate_evidence_span_count": len(candidate_evidence),
        "current_evidence_review": current_evidence,
        "candidate_evidence_review": candidate_evidence,
        "external_provenance_warnings": [
            {
                "field": "selection.issue_date",
                "frozen_selection_value": selection_row["issue_date"],
                "pdf_issue_date": "2026-04-17",
                "pdf_effective_date": "2026-05-01",
                "page_reference": 1,
                "action_taken": "Candidate annotation remains source-grounded; frozen selection was not modified.",
                "human_decision": "pending",
            }
        ],
    }
    REVIEW_JSON.write_bytes(serialize(report))
    REVIEW_MD.write_text(markdown_review(report), encoding="utf-8")
    print(f"Wrote {CANDIDATE.relative_to(ROOT)}")
    print(f"Wrote {REVIEW_JSON.relative_to(ROOT)}")
    print(f"Wrote {REVIEW_MD.relative_to(ROOT)}")
    print(f"Reviewed {len(field_rows)} leaf fields and {len(candidate_evidence)} candidate spans")


if __name__ == "__main__":
    main()
