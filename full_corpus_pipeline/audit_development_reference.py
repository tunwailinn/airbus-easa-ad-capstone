#!/usr/bin/env python3
"""Audit the 30-record development reference without opening the locked test set.

This verifies that each development reference record is still exactly tied to
its immutable, human-approved source annotation and frozen split hashes. It
also checks evidence-span integrity and, when the document-text cache is
available, source-text containment of the exact evidence quotations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from full_corpus_pipeline.content_projection import project_record, validate_record


ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "evaluation_sets/easa_airbus_ad_content_gold_50_v2"
ANNOTATION_DIR = ROOT / "gold_releases/easa_airbus_ad_gold_v2/annotations"
ANNOTATION_MANIFEST = ROOT / "gold_releases/easa_airbus_ad_gold_v2/annotation_manifest.csv"
DEFAULT_SOURCE_TEXT = ROOT / "step3_pilot/source_metadata/corpus_extracted_text.parquet"
SCHEMA = json.loads(
    (Path(__file__).with_name("content_record.schema.json")).read_text(encoding="utf-8")
)

SUBSTANTIVE_ASSERTION_PATHS = {
    "/ad_identity",
    "/publication",
    "/applicability_groups",
    "/definitions",
    "/unsafe_condition",
    "/requirements",
    "/referenced_publications",
    "/relationships",
    "/amoc_and_contacts",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_source_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def load_source_text(path: Path | None, ids: set[str]) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    frame = pd.read_parquet(path, columns=["file_instance_id", "text"])
    frame["file_instance_id"] = frame["file_instance_id"].astype(str)
    frame = frame[frame["file_instance_id"].isin(ids)]
    return {
        str(row["file_instance_id"]): normalize_source_text(str(row["text"]))
        for row in frame.to_dict(orient="records")
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--source-text-parquet",
        type=Path,
        default=DEFAULT_SOURCE_TEXT,
        help="Optional document-level text cache for evidence-quote containment checks.",
    )
    args = parser.parse_args()

    split = json.loads((CONTENT_DIR / "split_manifest.json").read_text(encoding="utf-8"))
    selected = [row for row in split if row["split"] == "development"]
    if len(selected) != 30:
        raise ValueError(f"expected 30 development records, found {len(selected)}")

    selected_ids = {str(row["file_instance_id"]) for row in selected}
    source_text_by_id = load_source_text(args.source_text_parquet, selected_ids)
    manifest = pd.read_csv(ANNOTATION_MANIFEST, dtype=str).fillna("")
    manifest_by_file = {
        str(row["file_name"]): row for row in manifest.to_dict(orient="records")
    }

    rows: list[dict[str, Any]] = []
    critical_total = 0
    warning_total = 0
    evidence_count = 0
    evidence_containment_checks = 0
    evidence_containment_passes = 0

    for item in selected:
        ad_number = str(item["ad_number"])
        file_id = str(item["file_instance_id"])
        annotation_name = str(item["source_gold_filename"])
        derived_name = str(item["derived_filename"])
        annotation_path = ANNOTATION_DIR / annotation_name
        derived_path = CONTENT_DIR / "records" / derived_name
        critical: list[str] = []
        warnings: list[str] = []

        if not annotation_path.exists():
            critical.append("missing immutable source annotation")
            rows.append(
                {
                    "ad_number": ad_number,
                    "file_instance_id": file_id,
                    "critical_issues": critical,
                    "warnings": warnings,
                }
            )
            critical_total += len(critical)
            continue
        if not derived_path.exists():
            critical.append("missing derived content reference")
            rows.append(
                {
                    "ad_number": ad_number,
                    "file_instance_id": file_id,
                    "critical_issues": critical,
                    "warnings": warnings,
                }
            )
            critical_total += len(critical)
            continue

        annotation = json.loads(annotation_path.read_text(encoding="utf-8"))
        derived = json.loads(derived_path.read_text(encoding="utf-8"))
        manifest_row = manifest_by_file.get(annotation_name)

        if manifest_row is None:
            critical.append("annotation missing from release manifest")
        else:
            if manifest_row.get("record_status") != "approved":
                critical.append(
                    f"release manifest status is {manifest_row.get('record_status')!r}, not approved"
                )
            if "human-reviewer" not in manifest_row.get("human_reviewer", ""):
                critical.append("release manifest has no independent human reviewer")
            if manifest_row.get("file_instance_id") != file_id:
                critical.append("release manifest file_instance_id disagrees with split")
            if manifest_row.get("sha256") != sha256(annotation_path):
                critical.append("annotation SHA-256 disagrees with release manifest")

        if sha256(annotation_path) != str(item["original_annotation_sha256"]):
            critical.append("annotation SHA-256 disagrees with frozen split lock")
        if sha256(derived_path) != str(item["derived_json_sha256"]):
            critical.append("derived JSON SHA-256 disagrees with frozen split lock")

        metadata = annotation.get("annotation_metadata") or {}
        if metadata.get("record_status") != "approved":
            critical.append("annotation metadata is not approved")
        human_reviewers = {
            str(entry.get("annotator_id"))
            for entry in metadata.get("annotators", [])
            if entry.get("role") == "reviewer"
            and str(entry.get("annotator_id", "")).startswith("human-reviewer")
        }
        if not human_reviewers:
            critical.append("annotation metadata has no human reviewer")
        approved_actors = {
            str(event.get("actor_id"))
            for event in metadata.get("events", [])
            if event.get("event_type") == "approved"
        }
        if human_reviewers and not (human_reviewers & approved_actors):
            critical.append("human reviewer did not record the approval event")
        if metadata.get("quality_flags"):
            warnings.append(f"quality_flags={metadata['quality_flags']}")
        if metadata.get("uncertainty_flags"):
            warnings.append(f"uncertainty_flags={metadata['uncertainty_flags']}")

        source = annotation.get("source_document") or {}
        if str(source.get("file_instance_id")) != file_id:
            critical.append("source_document file_instance_id disagrees with split")
        if not source.get("file_sha256"):
            critical.append("source_document has no PDF SHA-256")
        page_count = int(source.get("page_count") or 0)
        if page_count <= 0:
            critical.append("source_document has invalid page_count")
        if source.get("needs_ocr"):
            warnings.append("source_document is marked needs_ocr")
        if (
            metadata.get("source_text_sha256")
            and source.get("normalized_text_sha256")
            and metadata.get("source_text_sha256") != source.get("normalized_text_sha256")
        ):
            critical.append("annotation/source normalized-text hashes disagree")

        reprojection, _ = project_record(annotation, annotation_path)
        if reprojection != derived:
            critical.append("derived reference no longer matches deterministic projection")
        schema_errors = validate_record(derived, SCHEMA)
        if schema_errors:
            critical.append("derived reference fails content schema: " + "; ".join(schema_errors[:3]))

        assertions = annotation.get("field_assertions", []) or []
        assertion_by_path = {
            str(assertion.get("field_path")): assertion for assertion in assertions
        }
        missing_assertions = sorted(SUBSTANTIVE_ASSERTION_PATHS - set(assertion_by_path))
        if missing_assertions:
            critical.append("missing substantive field assertions: " + ", ".join(missing_assertions))
        rejected = [
            str(assertion.get("assertion_id"))
            for assertion in assertions
            if assertion.get("verification_status") != "accepted"
        ]
        if rejected:
            critical.append("non-accepted field assertions: " + ", ".join(rejected))

        source_text = source_text_by_id.get(file_id)
        evidence_failures: list[str] = []
        for evidence in annotation.get("evidence_spans", []) or []:
            evidence_count += 1
            evidence_id = str(evidence.get("evidence_id"))
            if str(evidence.get("source_file_instance_id")) != file_id:
                critical.append(f"{evidence_id}: source file id mismatch")
            page_number = int(evidence.get("page_number") or 0)
            if page_number < 1 or (page_count and page_number > page_count):
                critical.append(f"{evidence_id}: invalid page number {page_number}")
            quote = str(evidence.get("exact_quote") or "")
            if not quote.strip():
                critical.append(f"{evidence_id}: empty exact_quote")
            if evidence.get("quality") != "exact":
                warnings.append(f"{evidence_id}: evidence quality={evidence.get('quality')!r}")
            if not evidence.get("page_text_sha256"):
                critical.append(f"{evidence_id}: missing page_text_sha256")
            if source_text is not None and quote.strip():
                evidence_containment_checks += 1
                contained = normalize_source_text(quote) in source_text
                evidence_containment_passes += int(contained)
                if not contained:
                    evidence_failures.append(evidence_id)
        if evidence_failures:
            warnings.append(
                "document-text cache did not contain normalized evidence quotes: "
                + ", ".join(evidence_failures)
            )

        critical_total += len(critical)
        warning_total += len(warnings)
        rows.append(
            {
                "ad_number": ad_number,
                "file_instance_id": file_id,
                "source_gold_filename": annotation_name,
                "derived_filename": derived_name,
                "approved": metadata.get("record_status") == "approved",
                "human_reviewers": sorted(human_reviewers),
                "page_count": page_count,
                "evidence_span_count": len(annotation.get("evidence_spans", []) or []),
                "quality_flags": metadata.get("quality_flags", []),
                "uncertainty_flags": metadata.get("uncertainty_flags", []),
                "critical_issues": critical,
                "warnings": warnings,
            }
        )

    report = {
        "audit_version": "development-reference-audit-v1",
        "scope": "development only; locked test records were not opened",
        "record_count": len(selected),
        "critical_issue_count": critical_total,
        "warning_count": warning_total,
        "all_records_approved_and_projection_locked": critical_total == 0,
        "source_text_cache_available": bool(source_text_by_id),
        "evidence_span_count": evidence_count,
        "evidence_quote_containment": {
            "checked": evidence_containment_checks,
            "passed": evidence_containment_passes,
            "accuracy": (
                evidence_containment_passes / evidence_containment_checks
                if evidence_containment_checks
                else None
            ),
            "note": (
                "Document-level containment is an auxiliary consistency check; page-level "
                "hashes remain the stronger provenance anchor in the approved annotation."
            ),
        },
        "records": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "records"},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if critical_total == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
