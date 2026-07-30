#!/usr/bin/env python3
"""Prepare blind, reviewer-QC, and blank annotation packets for Step 3.

Real packet generation is intentionally blocked while any selection row has a
pending audit status.  ``--audit-only`` validates the current selection and
template mappings without creating packet or annotation files and without
requiring the source PDF/page cache to be present.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
DEFAULT_SELECTION = ROOT / "selection" / "pilot_selection.json"
DEFAULT_PAGE_TEXT_DIR = ROOT / "page_text"
DEFAULT_PDF_DIR = ROOT / "source_pdfs"
DEFAULT_TEMPLATE = PROJECT_ROOT / "step2_ad_schema" / "blank_ad_annotation.json"
DEFAULT_OUTPUT_ROOT = ROOT

EXPECTED_RECORDS = 30
EXPECTED_DOUBLE_ANNOTATIONS = 10
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
ID16_RE = re.compile(r"^[a-f0-9]{16}$")
AD_RE = re.compile(
    r"^(?P<base>(?:19|20)[0-9]{2}-[0-9]{4})"
    r"(?:R(?P<revision>[1-9][0-9]*))?(?P<emergency>-E)?$"
)
ALLOWED_SELECTION_STRATA = {
    "simple",
    "complex_applicability",
    "revised",
    "corrected",
    "emergency",
    "table_heavy",
    "long_document",
    "stc_conditioned",
    "near_duplicate_cluster",
    "other",
}
PROHIBITED_BLIND_KEYS = {
    "strata",
    "selection_strata",
    "rationale",
    "selection_rationale",
    "near_duplicate_cluster",
    "supersedes_ad_numbers",
    "candidate_links",
    "candidate_supersedure_links",
    "candidate_near_duplicate_links",
    "selection_screening",
}
SUBSTANTIVE_TEMPLATE_KEYS = {
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
    "evidence_spans",
    "field_assertions",
}


class PacketError(RuntimeError):
    """Raised when selection, provenance, or output invariants fail."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_path(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PacketError(f"Cannot read JSON file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise PacketError(f"Invalid JSON in {path}: {exc}") from exc


def parse_bool(value: Any, label: str) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise PacketError(f"{label} must be boolean, got {value!r}")


def parse_int(value: Any, label: str, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise PacketError(f"{label} must be an integer, got {value!r}") from exc
    if parsed < minimum:
        raise PacketError(f"{label} must be >= {minimum}, got {parsed}")
    return parsed


def split_pipe(value: Any) -> list[str]:
    return [part.strip() for part in str(value or "").split("|") if part.strip()]


def ensure_safe_output_root(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if any(part.lower() == "corpus_raw" for part in resolved.parts):
        raise PacketError(f"Output root must not be inside corpus_raw: {resolved}")
    return resolved


def validate_selection_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    prefix = f"selection row {index + 1}"
    required = {
        "ad_number",
        "base_ad_number",
        "logical_version_key",
        "revision_number",
        "is_correction",
        "correction_date",
        "page_count",
        "file_name",
        "relative_path",
        "file_instance_id",
        "content_id",
        "file_sha256",
        "normalized_text_sha256",
        "pdf_url",
        "detail_url",
        "strata",
        "rationale",
        "near_duplicate_cluster",
        "supersedes_ad_numbers",
        "double_annotation",
        "selection_status",
    }
    missing = sorted(required - row.keys())
    if missing:
        raise PacketError(f"{prefix} is missing fields: {', '.join(missing)}")

    normalized = dict(row)
    ad_number = str(row["ad_number"]).strip()
    match = AD_RE.fullmatch(ad_number)
    if not match:
        raise PacketError(f"{prefix}: invalid ad_number {ad_number!r}")
    base = str(row["base_ad_number"]).strip()
    if base != match.group("base"):
        raise PacketError(
            f"{prefix}: base_ad_number {base!r} is inconsistent with {ad_number!r}"
        )
    revision = parse_int(row["revision_number"], f"{prefix}.revision_number")
    expected_revision = int(match.group("revision") or 0)
    if revision != expected_revision:
        raise PacketError(
            f"{prefix}: revision_number {revision} is inconsistent with {ad_number!r}"
        )
    logical_key = str(row["logical_version_key"]).strip()
    if not logical_key or not logical_key.startswith(ad_number + "|"):
        raise PacketError(
            f"{prefix}: logical_version_key must preserve the Step 1 AD prefix"
        )
    file_name = str(row["file_name"]).strip()
    if not file_name or Path(file_name).name != file_name or not file_name.lower().endswith(".pdf"):
        raise PacketError(f"{prefix}: unsafe PDF file_name {file_name!r}")
    file_instance_id = str(row["file_instance_id"]).strip().lower()
    content_id = str(row["content_id"]).strip().lower()
    if not ID16_RE.fullmatch(file_instance_id):
        raise PacketError(f"{prefix}: invalid file_instance_id {file_instance_id!r}")
    if not ID16_RE.fullmatch(content_id):
        raise PacketError(f"{prefix}: invalid content_id {content_id!r}")
    file_hash = str(row["file_sha256"]).strip().lower()
    text_hash = str(row["normalized_text_sha256"]).strip().lower()
    if not SHA256_RE.fullmatch(file_hash):
        raise PacketError(f"{prefix}: invalid file_sha256")
    if not SHA256_RE.fullmatch(text_hash):
        raise PacketError(f"{prefix}: invalid normalized_text_sha256")
    page_count = parse_int(row["page_count"], f"{prefix}.page_count", minimum=1)
    correction = parse_bool(row["is_correction"], f"{prefix}.is_correction")
    correction_date = str(row["correction_date"] or "").strip()
    if correction and not correction_date:
        raise PacketError(f"{prefix}: corrected publication requires correction_date")
    if not correction and correction_date:
        raise PacketError(f"{prefix}: non-correction must not carry correction_date")
    double_annotation = parse_bool(
        row["double_annotation"], f"{prefix}.double_annotation"
    )
    strata = split_pipe(row["strata"])
    unknown_strata = sorted(set(strata) - ALLOWED_SELECTION_STRATA)
    if unknown_strata:
        raise PacketError(f"{prefix}: unsupported strata {unknown_strata}")
    if len(strata) != len(set(strata)):
        raise PacketError(f"{prefix}: duplicate selection stratum")

    normalized.update(
        {
            "ad_number": ad_number,
            "base_ad_number": base,
            "revision_number": revision,
            "is_emergency": bool(match.group("emergency")),
            "is_correction": correction,
            "correction_date": correction_date or None,
            "page_count": page_count,
            "file_name": file_name,
            "file_instance_id": file_instance_id,
            "content_id": content_id,
            "file_sha256": file_hash,
            "normalized_text_sha256": text_hash,
            "double_annotation": double_annotation,
            "selection_strata": strata,
            "supersedure_candidates": split_pipe(row["supersedes_ad_numbers"]),
            "near_duplicate_cluster": str(row["near_duplicate_cluster"] or "").strip()
            or None,
            "selection_status": str(row["selection_status"] or "").strip(),
        }
    )
    return normalized


def load_selection(path: Path) -> list[dict[str, Any]]:
    raw = load_json(path)
    if not isinstance(raw, list):
        raise PacketError(f"Selection must be a JSON array: {path}")
    if len(raw) != EXPECTED_RECORDS:
        raise PacketError(
            f"Expected exactly {EXPECTED_RECORDS} selection records, found {len(raw)}"
        )
    rows = [validate_selection_row(item, index) for index, item in enumerate(raw)]
    unique_fields = [
        "ad_number",
        "logical_version_key",
        "file_instance_id",
        "file_name",
        "file_sha256",
    ]
    for field in unique_fields:
        values = [row[field] for row in rows]
        duplicates = sorted({value for value in values if values.count(value) > 1})
        if duplicates:
            raise PacketError(f"Duplicate selection {field} value(s): {duplicates}")
    double_count = sum(row["double_annotation"] for row in rows)
    if double_count != EXPECTED_DOUBLE_ANNOTATIONS:
        raise PacketError(
            f"Expected exactly {EXPECTED_DOUBLE_ANNOTATIONS} Annotator B assignments, "
            f"found {double_count}"
        )
    return rows


def selection_is_final(rows: Iterable[dict[str, Any]]) -> tuple[bool, list[str]]:
    statuses = sorted({str(row["selection_status"]).strip() for row in rows})
    final_tokens = ("verified", "audited", "final", "confirmed", "approved")
    all_positive_final = bool(statuses) and all(
        status
        and "pending" not in status.lower()
        and any(token in status.lower() for token in final_tokens)
        for status in statuses
    )
    return all_positive_final, statuses


def load_template(path: Path) -> dict[str, Any]:
    template = load_json(path)
    if not isinstance(template, dict):
        raise PacketError(f"Blank annotation template is not an object: {path}")
    expected_top_level = {
        "schema_version",
        "record_id",
        "source_document",
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
        "evidence_spans",
        "field_assertions",
        "annotation_metadata",
        "benchmark_metadata",
    }
    missing = sorted(expected_top_level - template.keys())
    if missing:
        raise PacketError(f"Blank template is missing fields: {missing}")
    if template.get("schema_version") != "1.0.0":
        raise PacketError(
            f"Expected Step 2 schema version 1.0.0, got {template.get('schema_version')!r}"
        )
    return template


def page_jsonl_path(row: dict[str, Any], page_dir: Path) -> Path:
    return page_dir / f"{row['ad_number']}__{row['file_instance_id']}.pages.jsonl"


def load_page_records(row: dict[str, Any], page_dir: Path) -> list[dict[str, Any]]:
    path = page_jsonl_path(row, page_dir)
    if not path.is_file():
        raise PacketError(f"Missing page JSONL for {row['ad_number']}: {path}")
    pages: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise PacketError(f"Blank JSONL line {line_number}: {path}")
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise PacketError(
                    f"Invalid JSONL line {line_number} in {path}: {exc}"
                ) from exc
            if item.get("ad_number") != row["ad_number"]:
                raise PacketError(f"AD mismatch on line {line_number}: {path}")
            if item.get("file_instance_id") != row["file_instance_id"]:
                raise PacketError(
                    f"file_instance_id mismatch on line {line_number}: {path}"
                )
            if item.get("pdf_sha256") != row["file_sha256"]:
                raise PacketError(f"PDF hash mismatch on line {line_number}: {path}")
            page_number = item.get("page_number")
            if page_number != line_number:
                raise PacketError(
                    f"Expected page_number {line_number}, got {page_number!r}: {path}"
                )
            if item.get("page_count") != row["page_count"]:
                raise PacketError(f"Page-count provenance mismatch: {path}")
            text = item.get("text")
            if not isinstance(text, str):
                raise PacketError(f"Page text is not a string on line {line_number}: {path}")
            if item.get("page_text_sha256") != sha256_text(text):
                raise PacketError(f"Page-text SHA-256 mismatch on line {line_number}: {path}")
            pages.append(item)
    if len(pages) != row["page_count"]:
        raise PacketError(
            f"Expected {row['page_count']} pages for {row['ad_number']}, found {len(pages)}"
        )
    return pages


def verify_source_pdf(row: dict[str, Any], pdf_dir: Path) -> Path:
    path = pdf_dir / row["file_name"]
    if not path.is_file():
        raise PacketError(f"Missing verified source PDF for {row['ad_number']}: {path}")
    actual = sha256_path(path)
    if actual != row["file_sha256"]:
        raise PacketError(
            f"Source PDF SHA-256 mismatch for {row['ad_number']}: expected "
            f"{row['file_sha256']}, got {actual}"
        )
    return path


def packet_pages(pages: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed = [
        "page_id",
        "page_number",
        "page_count",
        "page_text_sha256",
        "text_char_count",
        "extraction_library",
        "extraction_library_version",
        "extraction_mode",
        "text",
    ]
    return [{key: page.get(key) for key in allowed} for page in pages]


def common_packet_source(row: dict[str, Any], pdf_path: Path) -> dict[str, Any]:
    return {
        "record_id": f"adann-{row['file_instance_id']}",
        "document_identity": {
            "authority": "EASA",
            "ad_number": row["ad_number"],
            "base_ad_number": row["base_ad_number"],
            "revision_number": row["revision_number"],
            "is_emergency": row["is_emergency"],
            "is_correction": row["is_correction"],
            "correction_date_from_manifest": row["correction_date"],
            "logical_version_key": row["logical_version_key"],
        },
        "pdf_provenance": {
            "file_instance_id": row["file_instance_id"],
            "content_id": row["content_id"],
            "file_name": row["file_name"],
            "relative_path": row["relative_path"],
            "local_pdf_path": str(pdf_path),
            "official_pdf_url": row["pdf_url"],
            "official_detail_url": row["detail_url"],
            "file_sha256": row["file_sha256"],
            "manifest_normalized_text_sha256": row["normalized_text_sha256"],
            "page_count": row["page_count"],
        },
    }


def build_blind_packet(
    row: dict[str, Any], pdf_path: Path, pages: list[dict[str, Any]]
) -> dict[str, Any]:
    packet = {
        "packet_version": "1.0.0",
        "packet_type": "blind_annotation_source",
        **common_packet_source(row, pdf_path),
        "instructions": [
            "Annotate only what the rendered PDF and supplied page text state.",
            "Do not infer relationships, applicability, actions, or deadlines from filenames.",
            "Add exact page evidence for every safety-critical value.",
        ],
        "pages": packet_pages(pages),
    }
    assert_blind_packet(packet, row)
    return packet


def assert_blind_packet(packet: dict[str, Any], row: dict[str, Any]) -> None:
    def walk(value: Any) -> Iterable[tuple[str, Any]]:
        if isinstance(value, dict):
            for key, child in value.items():
                yield key, child
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)

    keys = {key for key, _ in walk(packet)}
    leaked_keys = sorted(keys & PROHIBITED_BLIND_KEYS)
    if leaked_keys:
        raise PacketError(
            f"Blind packet for {row['ad_number']} leaks prohibited keys: {leaked_keys}"
        )
    packet_metadata = dict(packet)
    packet_metadata.pop("pages", None)
    serialized_metadata = canonical_json(packet_metadata)
    rationale = str(row.get("rationale") or "")
    cluster = str(row.get("near_duplicate_cluster") or "")
    if rationale and rationale in serialized_metadata:
        raise PacketError(f"Blind packet for {row['ad_number']} leaks selection rationale")
    if cluster and cluster in serialized_metadata:
        raise PacketError(
            f"Blind packet for {row['ad_number']} leaks near-duplicate cluster"
        )


def build_reviewer_packet(
    row: dict[str, Any],
    all_rows: list[dict[str, Any]],
    pdf_path: Path,
    pages: list[dict[str, Any]],
) -> dict[str, Any]:
    selected_ads = {item["ad_number"] for item in all_rows}
    cluster = row["near_duplicate_cluster"]
    near_candidates: list[dict[str, Any]] = []
    if cluster:
        members = [
            {
                "ad_number": item["ad_number"],
                "file_instance_id": item["file_instance_id"],
            }
            for item in all_rows
            if item["near_duplicate_cluster"] == cluster
        ]
        near_candidates.append(
            {
                "cluster_id": cluster,
                "members_in_pilot": members,
                "verification_status": "candidate_unverified",
                "manually_verified": False,
                "review_rule": (
                    "Compare every member PDF. Similarity does not authorize merging "
                    "or prove a supersedure relationship."
                ),
            }
        )
    supersedure_candidates = [
        {
            "source_ad_number": row["ad_number"],
            "target_ad_number": target,
            "candidate_relationship": "supersedes",
            "target_is_in_pilot": target in selected_ads,
            "verification_status": "candidate_unverified",
            "manually_verified": False,
            "review_rule": (
                "Confirm only from the structured field or an explicit directional "
                "sentence in the current PDF; otherwise reject or classify as historical."
            ),
        }
        for target in row["supersedure_candidates"]
    ]
    return {
        "packet_version": "1.0.0",
        "packet_type": "reviewer_qc_source",
        **common_packet_source(row, pdf_path),
        "candidate_warning": (
            "Everything under selection_screening and candidate_links is unverified "
            "screening metadata. It must never be copied into gold without PDF review."
        ),
        "selection_screening": {
            "cohort": row.get("cohort"),
            "family": row.get("family"),
            "ata": row.get("ata"),
            "selection_strata": row["selection_strata"],
            "selection_rationale": row["rationale"],
            "double_annotation": row["double_annotation"],
            "adjudication_assignment": row.get("adjudication"),
        },
        "candidate_links": {
            "candidate_near_duplicate_links": near_candidates,
            "candidate_supersedure_links": supersedure_candidates,
        },
        "pages": packet_pages(pages),
    }


def build_annotation_template(
    row: dict[str, Any], blank_template: dict[str, Any]
) -> dict[str, Any]:
    record = copy.deepcopy(blank_template)
    record["record_id"] = f"adann-{row['file_instance_id']}"
    source = record["source_document"]
    source.update(
        {
            "file_instance_id": row["file_instance_id"],
            "content_id": row["content_id"],
            "canonical_file_instance_id": row["file_instance_id"],
            "file_aliases": [],
            "file_name": row["file_name"],
            "relative_path": row["relative_path"],
            "file_sha256": row["file_sha256"],
            "normalized_text_sha256": row["normalized_text_sha256"],
            "page_count": row["page_count"],
            "extraction_status": "ok",
            "needs_ocr": False,
            "manifest_review_flags": [],
            "source_url": row["pdf_url"],
            "text_extraction_method": "native_text",
            "exact_duplicate_group": None,
            "near_duplicate_cluster": row["near_duplicate_cluster"],
        }
    )

    identity = record["ad_identity"]
    correction_date = row["correction_date"]
    identity.update(
        {
            "authority": "EASA",
            "document_type": "airworthiness_directive",
            "ad_number": row["ad_number"],
            "base_ad_number": row["base_ad_number"],
            "revision_number": row["revision_number"],
            "publication_kind": "emergency_ad"
            if row["is_emergency"]
            else "standard_ad",
            "is_emergency": row["is_emergency"],
            "is_correction": row["is_correction"],
            "correction_date": {
                "state": "present" if row["is_correction"] else "not_stated",
                "value": correction_date,
                "raw_text": None,
                "evidence_ids": [],
            },
            "version_label": (
                f"{row['ad_number']} [Corrected: {correction_date}]"
                if row["is_correction"]
                else row["ad_number"]
            ),
            "logical_version_key": row["logical_version_key"],
            "is_latest_version": None,
            "lifecycle_status": "unknown",
            "design_approval_holder": None,
            "supersedure_statement": {
                "state": "not_stated",
                "value": None,
                "raw_text": None,
                "evidence_ids": [],
            },
            "evidence_ids": [],
        }
    )

    metadata = record["annotation_metadata"]
    notes = [
        "Immutable source and identity provenance was prefilled from the frozen Step 1 selection.",
        "All substantive fields, evidence, relationships, and review decisions require manual annotation.",
    ]
    if row["is_correction"]:
        notes.append(
            "The normalized correction date is imported identity metadata; add exact raw text and page evidence before validation."
        )
    metadata.update(
        {
            "record_status": "draft",
            "creation_method": "manual",
            "machine_provenance": None,
            "annotators": [],
            "events": [],
            "quality_flags": ["missing_required_action"],
            "uncertainty_flags": [],
            "notes": notes,
            "source_text_sha256": row["normalized_text_sha256"],
            "created_at": None,
            "updated_at": None,
        }
    )
    record["benchmark_metadata"] = {
        "split": "unassigned",
        "split_group": row["base_ad_number"],
        "selection_strata": row["selection_strata"],
        "duplicate_cluster_ids": [row["near_duplicate_cluster"]]
        if row["near_duplicate_cluster"]
        else [],
        "gold_record": False,
    }
    assert_annotation_prefill(record, row, blank_template)
    return record


def assert_annotation_prefill(
    record: dict[str, Any], row: dict[str, Any], blank_template: dict[str, Any]
) -> None:
    if record["record_id"] != f"adann-{row['file_instance_id']}":
        raise PacketError(f"Non-deterministic record ID for {row['ad_number']}")
    if record["ad_identity"]["logical_version_key"] != row["logical_version_key"]:
        raise PacketError(f"Step 1 logical key changed for {row['ad_number']}")
    if record["relationships"]:
        raise PacketError(f"Relationship candidate leaked into {row['ad_number']} draft")
    if record["annotation_metadata"]["record_status"] != "draft":
        raise PacketError(f"Non-draft record generated for {row['ad_number']}")
    if record["annotation_metadata"]["creation_method"] != "manual":
        raise PacketError(f"Non-manual record generated for {row['ad_number']}")
    if record["classification"]["human_confirmed"] is not False:
        raise PacketError(f"Human confirmation leaked into {row['ad_number']} draft")
    benchmark = record["benchmark_metadata"]
    if benchmark["gold_record"] is not False or benchmark["split"] != "unassigned":
        raise PacketError(f"Gold/split status leaked into {row['ad_number']} draft")
    for key in SUBSTANTIVE_TEMPLATE_KEYS:
        if record[key] != blank_template[key]:
            raise PacketError(
                f"Substantive field {key!r} was prefilled for {row['ad_number']}"
            )


def output_name(row: dict[str, Any], suffix: str) -> str:
    return f"{row['ad_number']}__{row['file_instance_id']}.{suffix}.json"


def planned_outputs(rows: list[dict[str, Any]], output_root: Path) -> list[Path]:
    paths: list[Path] = []
    for row in rows:
        paths.extend(
            [
                output_root
                / "packets"
                / "blind"
                / output_name(row, "blind-packet"),
                output_root
                / "packets"
                / "reviewer_qc"
                / output_name(row, "reviewer-qc-packet"),
                output_root
                / "annotations"
                / "annotator_a"
                / output_name(row, "annotation"),
            ]
        )
        if row["double_annotation"]:
            paths.append(
                output_root
                / "annotations"
                / "annotator_b"
                / output_name(row, "annotation")
            )
    paths.append(output_root / "packet_inventory.json")
    return paths


def write_staged_json(stage_root: Path, relative: Path, value: Any) -> dict[str, Any]:
    content = canonical_json(value)
    target = stage_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {
        "path": str(relative),
        "sha256": sha256_text(content),
        "bytes": len(content.encode("utf-8")),
    }


def generate(
    rows: list[dict[str, Any]],
    template: dict[str, Any],
    *,
    selection_path: Path,
    pdf_dir: Path,
    page_dir: Path,
    output_root: Path,
) -> dict[str, Any]:
    final_paths = planned_outputs(rows, output_root)
    existing = [path for path in final_paths if path.exists()]
    if existing:
        preview = "\n- ".join(str(path) for path in existing[:10])
        raise PacketError(
            "Refusing to overwrite existing packet/annotation outputs:\n- " + preview
        )

    source_data: dict[str, tuple[Path, list[dict[str, Any]]]] = {}
    for row in rows:
        pdf_path = verify_source_pdf(row, pdf_dir)
        pages = load_page_records(row, page_dir)
        source_data[row["file_instance_id"]] = (pdf_path, pages)

    selection_hash = sha256_path(selection_path)
    inventory_entries: list[dict[str, Any]] = []
    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".packet-stage-", dir=output_root) as temporary:
        stage_root = Path(temporary)
        for row in rows:
            pdf_path, pages = source_data[row["file_instance_id"]]
            blind = build_blind_packet(row, pdf_path, pages)
            reviewer = build_reviewer_packet(row, rows, pdf_path, pages)
            annotation = build_annotation_template(row, template)

            targets = [
                (
                    Path("packets")
                    / "blind"
                    / output_name(row, "blind-packet"),
                    blind,
                    "blind_packet",
                ),
                (
                    Path("packets")
                    / "reviewer_qc"
                    / output_name(row, "reviewer-qc-packet"),
                    reviewer,
                    "reviewer_qc_packet",
                ),
                (
                    Path("annotations")
                    / "annotator_a"
                    / output_name(row, "annotation"),
                    annotation,
                    "annotator_a_template",
                ),
            ]
            if row["double_annotation"]:
                targets.append(
                    (
                        Path("annotations")
                        / "annotator_b"
                        / output_name(row, "annotation"),
                        copy.deepcopy(annotation),
                        "annotator_b_template",
                    )
                )
            for relative, value, artifact_type in targets:
                entry = write_staged_json(stage_root, relative, value)
                entry.update(
                    {
                        "artifact_type": artifact_type,
                        "ad_number": row["ad_number"],
                        "file_instance_id": row["file_instance_id"],
                    }
                )
                inventory_entries.append(entry)

        inventory = {
            "inventory_version": "1.0.0",
            "selection_file": str(selection_path),
            "selection_sha256": selection_hash,
            "schema_version": template["schema_version"],
            "counts": {
                "selected_records": len(rows),
                "blind_packets": len(rows),
                "reviewer_qc_packets": len(rows),
                "annotator_a_templates": len(rows),
                "annotator_b_templates": sum(
                    row["double_annotation"] for row in rows
                ),
            },
            "artifacts": sorted(inventory_entries, key=lambda item: item["path"]),
        }
        write_staged_json(stage_root, Path("packet_inventory.json"), inventory)

        staged_files = sorted(path for path in stage_root.rglob("*") if path.is_file())
        for staged in staged_files:
            relative = staged.relative_to(stage_root)
            final = output_root / relative
            final.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged, final)
    return inventory


def audit_only(
    rows: list[dict[str, Any]],
    template: dict[str, Any],
    *,
    pdf_dir: Path,
    page_dir: Path,
) -> dict[str, Any]:
    # Exercise every deterministic builder. Existing source inputs are fully
    # verified, while genuinely absent inputs remain a reported availability
    # count rather than blocking a configuration-only audit.
    present_pdfs = 0
    verified_pdfs = 0
    present_pages = 0
    verified_page_files = 0
    for row in rows:
        pdf_path = pdf_dir / row["file_name"]
        page_path = page_jsonl_path(row, page_dir)
        pages: list[dict[str, Any]] = []
        if pdf_path.exists():
            present_pdfs += 1
            verify_source_pdf(row, pdf_dir)
            verified_pdfs += 1
        if page_path.exists():
            present_pages += 1
            pages = load_page_records(row, page_dir)
            verified_page_files += 1
        annotation = build_annotation_template(row, template)
        blind = build_blind_packet(row, pdf_path, pages)
        reviewer = build_reviewer_packet(
            row, rows, pdf_path, pages
        )
        if annotation["relationships"] or blind.get("candidate_links"):
            raise PacketError(f"Candidate leakage during audit for {row['ad_number']}")
        if reviewer["candidate_warning"].lower().find("unverified") < 0:
            raise PacketError(f"Reviewer warning is not explicit for {row['ad_number']}")

    final, statuses = selection_is_final(rows)
    return {
        "selected_records": len(rows),
        "double_annotation_records": sum(row["double_annotation"] for row in rows),
        "selection_statuses": statuses,
        "selection_is_final": final,
        "source_pdfs_present": present_pdfs,
        "source_pdfs_verified": verified_pdfs,
        "page_jsonl_files_present": present_pages,
        "page_jsonl_files_verified": verified_page_files,
        "planned_blind_packets": len(rows),
        "planned_reviewer_qc_packets": len(rows),
        "planned_annotator_a_templates": len(rows),
        "planned_annotator_b_templates": sum(
            row["double_annotation"] for row in rows
        ),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--page-text-dir", type=Path, default=DEFAULT_PAGE_TEXT_DIR)
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help=(
            "validate selection/template mappings without reading source content "
            "or writing generated artifacts"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        selection_path = args.selection.expanduser().resolve()
        template_path = args.template.expanduser().resolve()
        page_dir = args.page_text_dir.expanduser().resolve()
        pdf_dir = args.pdf_dir.expanduser().resolve()
        output_root = ensure_safe_output_root(args.output_root)
        rows = load_selection(selection_path)
        template = load_template(template_path)

        if args.audit_only:
            result = audit_only(
                rows, template, pdf_dir=pdf_dir, page_dir=page_dir
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            if not result["selection_is_final"]:
                print(
                    "AUDIT NOTE: selection is still pending; real packet generation "
                    "remains blocked.",
                    file=sys.stderr,
                )
            return 0

        final, statuses = selection_is_final(rows)
        if not final:
            raise PacketError(
                "Packet generation is blocked until the selection audit is final. "
                f"Current selection_status values: {statuses}. Use --audit-only now."
            )
        inventory = generate(
            rows,
            template,
            selection_path=selection_path,
            pdf_dir=pdf_dir,
            page_dir=page_dir,
            output_root=output_root,
        )
        print(json.dumps(inventory["counts"], indent=2))
        print(f"Inventory: {output_root / 'packet_inventory.json'}")
        return 0
    except PacketError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
