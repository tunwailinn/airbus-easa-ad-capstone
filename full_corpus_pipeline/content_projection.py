#!/usr/bin/env python3
"""Project validated evidence-bearing annotations into content-only AD records.

The source gold release is read-only. System, review, benchmark, evidence, and
synthetic link fields are resolved or removed from the derived records. A
sidecar manifest preserves the technical mapping back to the audit source.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from jsonschema import Draft202012Validator, FormatChecker

from full_corpus_pipeline import CONTENT_SCHEMA_VERSION, PROJECTION_VERSION


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "gold_releases/easa_airbus_ad_gold_v2/annotations"
DEFAULT_OUTPUT = ROOT / "evaluation_sets/easa_airbus_ad_content_gold_50_v2"
SCHEMA_PATH = Path(__file__).with_name("content_record.schema.json")
MISSING = object()

FORBIDDEN_KEYS = {
    "annotation_metadata",
    "benchmark_metadata",
    "classification",
    "confidence",
    "creation_method",
    "evidence_ids",
    "evidence_spans",
    "field_assertions",
    "gold_record",
    "human_confirmed",
    "machine_provenance",
    "manually_verified",
    "record_status",
    "source_document",
    "verification_status",
}


@dataclass
class ProjectionContext:
    source_path: Path
    warnings: list[str] = field(default_factory=list)
    source_paths: set[str] = field(default_factory=set)

    def fail(self, message: str) -> None:
        raise ValueError(f"{self.source_path}: {message}")

    def used(self, path: str) -> None:
        self.source_paths.add(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--expected-count", type=int, default=50)
    return parser.parse_args()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def compact(value: Any) -> Any:
    """Remove absent/empty values while retaining false and zero."""
    if value is MISSING or value is None:
        return MISSING
    if isinstance(value, str):
        value = re.sub(r"\s+", " ", value).strip()
        return value if value else MISSING
    if isinstance(value, list):
        items = [item for raw in value if (item := compact(raw)) is not MISSING]
        return items if items else MISSING
    if isinstance(value, dict):
        result = {
            key: item
            for key, raw in value.items()
            if (item := compact(raw)) is not MISSING
        }
        return result if result else MISSING
    return value


def grounded(record: dict[str, Any], path: str, *, explicit_none: bool = False) -> Any:
    state = record.get("state")
    if state in {"not_stated", "not_applicable"}:
        return MISSING
    value = record.get("value")
    if value not in (None, ""):
        return value
    raw = record.get("raw_text")
    if raw not in (None, "") and (state != "explicit_none" or explicit_none):
        return raw
    return MISSING


def string_list(values: Iterable[Any]) -> Any:
    return compact([str(value) for value in values if value not in (None, "")])


def project_record(source: dict[str, Any], source_path: Path) -> tuple[dict[str, Any], ProjectionContext]:
    """Project an evidence-bearing annotation into schema version 2.1.0.

    Reliable fields remain structured. Difficult semantics are represented by
    reviewed content text where available, while live extraction preserves the
    corresponding raw PDF sections for RAG-time interpretation.
    """
    ctx = ProjectionContext(source_path=source_path)
    identity = source.get("ad_identity") or {}
    publication = source.get("publication") or {}
    ad_number = identity.get("ad_number")
    if not ad_number:
        ctx.fail("missing AD number")

    revision_match = re.search(r"R(\d+)$", str(ad_number), re.IGNORECASE)
    projected_identity = compact(
        {
            "ad_number": ad_number,
            "authority": identity.get("authority"),
            "document_type": identity.get("document_type"),
            "revision": f"R{revision_match.group(1)}" if revision_match else MISSING,
            "emergency": True if identity.get("is_emergency") is True else MISSING,
            "correction_date": grounded(identity.get("correction_date") or {}, "correction_date"),
            "design_approval_holder": grounded(
                identity.get("design_approval_holder") or {}, "design_approval_holder"
            ),
        }
    )

    ata_chapters = [
        compact({"code": item.get("code"), "title": item.get("title")})
        for item in publication.get("ata_chapters", [])
    ]
    manufacturers = [
        item.get("raw_name") or item.get("normalized_name")
        for item in publication.get("manufacturers", [])
    ]
    projected_publication = compact(
        {
            "subject": grounded(publication.get("subject") or {}, "publication.subject"),
            "issue_date": grounded(publication.get("issue_date") or {}, "publication.issue_date"),
            "effective_date": grounded(
                publication.get("effective_date") or {}, "publication.effective_date"
            ),
            "effective_date_statement": (publication.get("effective_date") or {}).get("raw_text"),
            "ata_chapters": ata_chapters,
            "manufacturers": string_list(manufacturers),
            "type_model_designations": string_list(publication.get("type_model_designations", [])),
            "tcds_numbers": string_list(publication.get("tcds_numbers", [])),
            "foreign_ad": grounded(
                publication.get("foreign_ad") or {}, "publication.foreign_ad", explicit_none=True
            ),
        }
    )

    projected_applicability: list[dict[str, Any]] = []
    for item in source.get("applicability_groups", []):
        projected = compact(
            {
                "text": item.get("raw_text"),
                "aircraft_families": string_list(item.get("aircraft_families", [])),
                "models": string_list(item.get("models", item.get("model_designations", []))),
            }
        )
        if projected is not MISSING:
            projected_applicability.append(projected)

    projected_actions: list[dict[str, Any]] = []
    for item in source.get("requirements", []):
        projected = compact(
            {
                "paragraph": item.get("paragraph_reference"),
                "action": item.get("action_text"),
            }
        )
        if projected is MISSING or "action" not in projected:
            ctx.fail(f"requirement {item.get('requirement_id')} has no high-level action text")
        projected_actions.append(projected)

    definitions_text = compact(
        [
            f"{item.get('term')}: {item.get('definition_text')}"
            for item in source.get("definitions", [])
            if item.get("term") and item.get("definition_text")
        ]
    )
    reason_text = (source.get("unsafe_condition") or {}).get("raw_reason_text")
    remarks_text = compact(
        [
            item.get("contact_text")
            for item in source.get("amoc_and_contacts", [])
            if item.get("contact_text")
        ]
    )

    projected_publications = []
    for item in source.get("referenced_publications", []):
        projected = compact(
            {
                "type": item.get("publication_type"),
                "issuer": item.get("issuer"),
                "number": item.get("number"),
                "revision": item.get("revision"),
                "date": item.get("publication_date"),
                "title": item.get("title"),
            }
        )
        if projected is not MISSING:
            projected_publications.append(projected)

    supersedure_statement = grounded(
        identity.get("supersedure_statement") or {},
        "ad_identity.supersedure_statement",
        explicit_none=True,
    )
    superseded_numbers = [
        item.get("target_ad_number")
        for item in source.get("relationships", [])
        if item.get("relationship_type") == "supersedes" and item.get("target_ad_number")
    ]
    projected_supersedure = compact(
        {
            "statement": supersedure_statement,
            "superseded_ad_numbers": string_list(superseded_numbers),
        }
    )

    record = compact(
        {
            "ad_identity": projected_identity,
            "publication": projected_publication,
            "applicability": projected_applicability,
            "definitions": (
                {"text": " ".join(definitions_text)}
                if definitions_text is not MISSING
                else MISSING
            ),
            "reason": {"text": reason_text} if reason_text else MISSING,
            "required_actions": projected_actions,
            "referenced_publications": projected_publications,
            "supersedure": projected_supersedure,
            "remarks": (
                {"text": " ".join(remarks_text)}
                if remarks_text is not MISSING
                else MISSING
            ),
        }
    )
    if record is MISSING:
        ctx.fail("projection produced an empty record")
    return record, ctx


def forbidden_paths(value: Any, path: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}/{key}"
            if key in FORBIDDEN_KEYS or "evidence" in key.casefold():
                errors.append(child)
            errors.extend(forbidden_paths(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(forbidden_paths(item, f"{path}/{index}"))
    return errors


def validate_record(record: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = [
        f"/{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(record), key=lambda item: list(item.absolute_path))
    ]
    errors.extend(f"{path}: forbidden key" for path in forbidden_paths(record))
    return errors


def leaf_json_paths(value: Any, path: str = "") -> list[str]:
    """Return a JSON-pointer-like path for every retained scalar value."""
    if isinstance(value, dict):
        return [leaf for key, item in value.items() for leaf in leaf_json_paths(item, f"{path}/{key}")]
    if isinstance(value, list):
        return [leaf for index, item in enumerate(value) for leaf in leaf_json_paths(item, f"{path}/{index}")]
    return [path]


SOURCE_ROOT_BY_SECTION = {
    "ad_identity": "/ad_identity",
    "publication": "/publication",
    "applicability": "/applicability_groups",
    "definitions": "/definitions",
    "reason": "/unsafe_condition/raw_reason_text",
    "required_actions": "/requirements",
    "referenced_publications": "/referenced_publications",
    "referenced_publications_text": "/referenced_publications",
    "supersedure": "/ad_identity/supersedure_statement and /relationships",
    "remarks": "/amoc_and_contacts",
}


def projection_lineage(output_name: str, source_name: str, record: dict[str, Any]) -> dict[str, Any]:
    mappings = []
    for derived_path in leaf_json_paths(record):
        section = derived_path.split("/", 2)[1]
        mappings.append(
            {
                "derived_path": derived_path,
                "source_path": SOURCE_ROOT_BY_SECTION[section],
            }
        )
    return {
        "derived_filename": output_name,
        "source_gold_filename": source_name,
        "mappings": mappings,
    }


def aggregate_source_hash(paths: list[Path]) -> str:
    lines = [f"{sha256_path(path)}  {path.name}\n" for path in sorted(paths)]
    return sha256_bytes("".join(lines).encode("utf-8"))


def write_manifest_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    source_paths = sorted(args.source_dir.glob("*.json"))
    if len(source_paths) != args.expected_count:
        raise ValueError(
            f"expected {args.expected_count} source annotations, found {len(source_paths)}"
        )
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError(f"refusing to overwrite non-empty output: {args.output_dir}")

    source_hash_before = aggregate_source_hash(source_paths)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    projected: list[tuple[str, dict[str, Any]]] = []
    lineage_rows: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    for source_path in source_paths:
        source_bytes = source_path.read_bytes()
        source = json.loads(source_bytes)
        record, context = project_record(source, source_path)
        errors = validate_record(record, schema)
        if errors:
            raise ValueError(f"{source_path}: " + "; ".join(errors))
        output_name = source_path.name.replace(".annotation.json", ".json")
        record_bytes = canonical_json_bytes(record)
        source_document = source.get("source_document") or {}
        manifest_rows.append(
            {
                "derived_filename": output_name,
                "source_gold_filename": source_path.name,
                "ad_number": (source.get("ad_identity") or {}).get("ad_number"),
                "source_file_instance_id": source_document.get("file_instance_id"),
                "original_annotation_sha256": sha256_bytes(source_bytes),
                "derived_json_sha256": sha256_bytes(record_bytes),
                "source_pdf_sha256": source_document.get("file_sha256"),
                "projection_schema_version": CONTENT_SCHEMA_VERSION,
                "projection_script_version": PROJECTION_VERSION,
                "projection_timestamp": generated_at,
                "projection_warnings": " | ".join(context.warnings),
            }
        )
        projected.append((output_name, record))
        lineage_rows.append(projection_lineage(output_name, source_path.name, record))

    args.output_dir.mkdir(parents=True, exist_ok=False)
    records_dir = args.output_dir / "records"
    records_dir.mkdir()
    for output_name, record in projected:
        (records_dir / output_name).write_bytes(canonical_json_bytes(record))
    with (args.output_dir / "records.jsonl").open("w", encoding="utf-8") as handle:
        for _, record in projected:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    with (args.output_dir / "projection_lineage.jsonl").open("w", encoding="utf-8") as handle:
        for lineage in lineage_rows:
            handle.write(json.dumps(lineage, ensure_ascii=False) + "\n")

    frame = pd.DataFrame(manifest_rows)
    frame.to_parquet(args.output_dir / "projection_manifest.parquet", index=False)
    write_manifest_csv(args.output_dir / "projection_manifest.csv", manifest_rows)
    source_hash_after = aggregate_source_hash(source_paths)
    if source_hash_before != source_hash_after:
        raise ValueError("source gold annotations changed during projection")
    report = {
        "passed": True,
        "record_count": len(projected),
        "jsonl_line_count": len(projected),
        "lineage_record_count": len(lineage_rows),
        "content_schema_version": CONTENT_SCHEMA_VERSION,
        "projection_version": PROJECTION_VERSION,
        "source_gold_directory": str(args.source_dir),
        "source_gold_aggregate_sha256_before": source_hash_before,
        "source_gold_aggregate_sha256_after": source_hash_after,
        "records_with_warnings": sum(bool(row["projection_warnings"]) for row in manifest_rows),
        "forbidden_key_errors": 0,
        "schema_errors": 0,
        "generated_at": generated_at,
    }
    (args.output_dir / "projection_report.json").write_bytes(canonical_json_bytes(report))
    (args.output_dir / "README.md").write_text(
        "# Airbus EASA AD content gold 50 v2\n\n"
        "This is a reproducible, content-only projection of the immutable validated "
        "`gold_releases/easa_airbus_ad_gold_v2/` audit source. It contains no evidence "
        "spans, review state, confidence, benchmark metadata, machine provenance, or "
        "technical source fields inside the records. Difficult compliance semantics are not "
        "machine-normalized; local extraction preserves the complete raw sections for "
        "retrieval-time interpretation.\n\n"
        "- `records/`: one content JSON record per AD.\n"
        "- `records.jsonl`: the same 50 records for streaming evaluation.\n"
        "- `projection_manifest.*`: technical mapping to the immutable audit source.\n"
        "- `projection_lineage.jsonl`: retained-value paths mapped to original annotation sections.\n"
        "- `projection_report.json`: build and integrity result.\n\n"
        "Run `full_corpus_pipeline.freeze_evaluation_design` after projection to add the "
        "frozen 30-development/20-test split.\n\n"
        "Regenerate from the repository root with:\n\n"
        "```bash\n"
        ".venv/bin/python -m full_corpus_pipeline.content_projection\n"
        "```\n",
        encoding="utf-8",
    )
    print(
        f"Projected {len(projected)} content records to {args.output_dir}; "
        f"source aggregate={source_hash_after}"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
