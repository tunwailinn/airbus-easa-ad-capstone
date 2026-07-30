#!/usr/bin/env python3
"""Validate any versioned PDF-to-gold annotation release.

This is the reusable release gate. It deliberately does not contain the
30-record pilot's cohort or batch-size assumptions. A release passes only when:

1. annotation membership and source identity match the frozen selection;
2. the selected PDF files still match their frozen SHA-256 values;
3. every annotation passes the Step 2 schema and strict semantic checks;
4. every record passes the Step 3 human-review and approval checks; and
5. every evidence quote and page hash matches the frozen page-text cache.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STEP2_DIR = PROJECT_ROOT / "step2_ad_schema"
STEP3_DIR = PROJECT_ROOT / "step3_pilot"
DEFAULT_SCHEMA = STEP2_DIR / "easa_airbus_ad_annotation.schema.json"

for import_path in (PROJECT_ROOT, STEP2_DIR, STEP3_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from step2_ad_schema.validate_annotations import (  # noqa: E402
    batch_semantic_errors,
    load_schema,
    semantic_errors,
    structural_errors,
)
from step3_pilot.validate_evidence_quotes import (  # noqa: E402
    evidence_errors,
    load_pages,
)
from step3_pilot.validate_step3_pilot import (  # noqa: E402
    record_completion_errors,
)


IDENTITY_FIELDS = {
    "base_ad_number": ("ad_identity", "base_ad_number"),
    "logical_version_key": ("ad_identity", "logical_version_key"),
    "file_instance_id": ("source_document", "file_instance_id"),
    "content_id": ("source_document", "content_id"),
    "file_name": ("source_document", "file_name"),
    "relative_path": ("source_document", "relative_path"),
    "file_sha256": ("source_document", "file_sha256"),
    "normalized_text_sha256": ("source_document", "normalized_text_sha256"),
    "page_count": ("source_document", "page_count"),
}


def sha256_path(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normal_optional(value: Any) -> Any:
    return None if value in (None, "") else value


def collect_annotations(inputs: list[Path]) -> list[Path]:
    paths: list[Path] = []
    for value in inputs:
        if value.is_dir():
            paths.extend(sorted(value.glob("*.annotation.json")))
        elif value.is_file():
            paths.append(value)
        else:
            raise FileNotFoundError(value)
    return sorted(set(path.resolve() for path in paths))


def membership_errors(
    records: list[tuple[Path, dict[str, Any]]],
    selection_rows: list[dict[str, Any]],
    expected_count: int,
) -> list[str]:
    errors: list[str] = []
    if len(selection_rows) != expected_count:
        errors.append(
            f"selection contains {len(selection_rows)} rows; expected {expected_count}"
        )
    if len(records) != expected_count:
        errors.append(f"release contains {len(records)} records; expected {expected_count}")

    selection_by_ad: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(selection_rows):
        ad_number = str(row.get("ad_number") or "").strip()
        if not ad_number:
            errors.append(f"selection[{index}] is missing ad_number")
        elif ad_number in selection_by_ad:
            errors.append(f"selection contains duplicate ad_number {ad_number!r}")
        else:
            selection_by_ad[ad_number] = row

    records_by_ad: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    for path, record in records:
        ad_number = str((record.get("ad_identity") or {}).get("ad_number") or "")
        records_by_ad.setdefault(ad_number, []).append((path, record))
    for ad_number, values in records_by_ad.items():
        if len(values) > 1:
            errors.append(
                f"release contains duplicate ad_number {ad_number!r}: "
                + ", ".join(str(path) for path, _record in values)
            )

    selected = set(selection_by_ad)
    actual = set(records_by_ad)
    missing = sorted(selected - actual)
    unexpected = sorted(actual - selected)
    if missing:
        errors.append("release is missing selected ADs: " + ", ".join(missing))
    if unexpected:
        errors.append("release contains unselected ADs: " + ", ".join(unexpected))

    for ad_number in sorted(selected & actual):
        path, record = records_by_ad[ad_number][0]
        row = selection_by_ad[ad_number]
        for selection_key, (section, record_key) in IDENTITY_FIELDS.items():
            expected = normal_optional(row.get(selection_key))
            actual_value = (record.get(section) or {}).get(record_key)
            if selection_key == "page_count" and expected is not None:
                expected = int(expected)
            if actual_value != expected:
                errors.append(
                    f"{path}:{section}.{record_key} differs from frozen selection "
                    f"({actual_value!r} != {expected!r})"
                )
        canonical = (record.get("source_document") or {}).get(
            "canonical_file_instance_id"
        )
        if canonical != normal_optional(row.get("file_instance_id")):
            errors.append(
                f"{path}:source_document.canonical_file_instance_id differs "
                "from frozen file_instance_id"
            )
    return sorted(set(errors))


def source_errors(
    selection_rows: list[dict[str, Any]],
    source_pdf_dir: Path,
    pages: dict[tuple[str, int], dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    page_counts = Counter(file_id for file_id, _page_number in pages)
    for row in selection_rows:
        ad_number = str(row.get("ad_number") or "<missing>")
        file_name = str(row.get("file_name") or "")
        pdf_path = source_pdf_dir / file_name
        if not pdf_path.is_file():
            errors.append(f"{ad_number}: selected PDF is missing: {pdf_path}")
            continue
        actual_hash = sha256_path(pdf_path)
        expected_hash = str(row.get("file_sha256") or "").lower()
        if actual_hash != expected_hash:
            errors.append(
                f"{ad_number}: PDF SHA-256 differs from frozen selection "
                f"({actual_hash} != {expected_hash})"
            )
        file_instance_id = str(row.get("file_instance_id") or "")
        expected_pages = int(row.get("page_count") or 0)
        actual_pages = page_counts[file_instance_id]
        if actual_pages != expected_pages:
            errors.append(
                f"{ad_number}: page cache has {actual_pages} pages; "
                f"selection requires {expected_pages}"
            )
    return sorted(set(errors))


def validate_release(
    annotation_paths: list[Path],
    selection_rows: list[dict[str, Any]],
    schema: dict[str, Any],
    pages: dict[tuple[str, int], dict[str, Any]],
    source_pdf_dir: Path,
    expected_count: int,
) -> dict[str, list[str]]:
    gates: dict[str, list[str]] = {
        "selection_membership": [],
        "source_integrity": [],
        "schema_and_strict_semantics": [],
        "human_review_and_approval": [],
        "evidence_quotes": [],
    }
    records: list[tuple[Path, dict[str, Any]]] = []
    for path in annotation_paths:
        try:
            value = load_json(path)
            if not isinstance(value, dict):
                raise ValueError("annotation root must be a JSON object")
            records.append((path, value))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            gates["schema_and_strict_semantics"].append(f"{path}: {exc}")

    gates["selection_membership"].extend(
        membership_errors(records, selection_rows, expected_count)
    )
    gates["source_integrity"].extend(
        source_errors(selection_rows, source_pdf_dir, pages)
    )

    selection_by_ad = {
        str(row.get("ad_number")): row
        for row in selection_rows
        if row.get("ad_number")
    }
    structurally_valid: list[tuple[str, dict[str, Any]]] = []
    for path, record in records:
        structural = structural_errors(record, schema)
        if structural:
            gates["schema_and_strict_semantics"].extend(
                f"{path}: {error}" for error in structural
            )
            continue
        structurally_valid.append((str(path), record))
        gates["schema_and_strict_semantics"].extend(
            f"{path}: {error}" for error in semantic_errors(record, strict=True)
        )

        ad_number = str((record.get("ad_identity") or {}).get("ad_number") or "")
        selection_row = selection_by_ad.get(ad_number)
        if selection_row is not None:
            gates["human_review_and_approval"].extend(
                f"{path}: "
                + error.replace("final pilot", "final gold release").replace(
                    "gold pilot", "gold release"
                )
                for error in record_completion_errors(record, selection_row)
            )
        gates["evidence_quotes"].extend(
            f"{path}: {error}" for error in evidence_errors(record, pages)
        )

    gates["schema_and_strict_semantics"].extend(
        f"[batch] {error}"
        for error in batch_semantic_errors(structurally_valid)
    )
    return {name: sorted(set(errors)) for name, errors in gates.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--source-pdf-dir", type=Path, required=True)
    parser.add_argument("--page-text-dir", type=Path, required=True)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument(
        "--expected-count",
        type=int,
        help="expected release size; defaults to the frozen selection size",
    )
    parser.add_argument(
        "--max-console-errors",
        type=int,
        default=100,
        help="maximum detailed errors printed to the console; the report keeps all",
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)

    try:
        paths = collect_annotations(args.inputs)
        selection_value = load_json(args.selection)
        if not isinstance(selection_value, list) or not all(
            isinstance(row, dict) for row in selection_value
        ):
            raise ValueError("selection must be a JSON array of objects")
        expected_count = args.expected_count or len(selection_value)
        if expected_count < 1:
            raise ValueError("expected count must be positive")
        if args.max_console_errors < 0:
            raise ValueError("max console errors cannot be negative")
        schema = load_schema(args.schema)
        pages = load_pages(args.page_text_dir)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"CONFIGURATION ERROR: {exc}", file=sys.stderr)
        return 2

    gates = validate_release(
        paths,
        selection_value,
        schema,
        pages,
        args.source_pdf_dir,
        expected_count,
    )
    errors = [
        f"[{gate}] {error}"
        for gate, findings in gates.items()
        for error in findings
    ]
    passed = not errors
    report = {
        "passed": passed,
        "record_count": len(paths),
        "selection_count": len(selection_value),
        "expected_count": expected_count,
        "gates": {
            name: {"passed": not findings, "error_count": len(findings)}
            for name, findings in gates.items()
        },
        "errors": errors,
    }
    print(
        f"{'PASS' if passed else 'FAIL'} gold release: "
        f"{len(paths)} record(s), {len(errors)} error(s)"
    )
    for error in errors[: args.max_console_errors]:
        print(f"  - {error}")
    hidden = len(errors) - args.max_console_errors
    if hidden > 0:
        print(f"  ... {hidden} additional error(s) are retained in the JSON report")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
