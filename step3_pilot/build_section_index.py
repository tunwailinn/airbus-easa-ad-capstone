#!/usr/bin/env python3
"""Build the deterministic Step 3 annotation-navigation section index.

The index reports pages containing recognizable EASA AD section headings.  It
does not extract field values, decide that a missing heading means a section is
absent, or create gold annotations.  ``heading_not_found`` means only that this
deterministic heading matcher did not find a label in the cached page text.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
DEFAULT_SELECTION = ROOT / "selection" / "pilot_selection.json"
DEFAULT_PAGE_TEXT = ROOT / "page_text" / "pilot_pages.jsonl"
DEFAULT_OUTPUT_DIR = ROOT / "packets"
EXPECTED_DOCUMENTS = 30
DETECTOR_VERSION = "1.0.0"

SECTION_ORDER = (
    "cover",
    "applicability",
    "definitions",
    "reason",
    "required_actions_compliance",
    "credit",
    "reference_publications",
    "remarks",
    "appendix_table",
)


def _compile(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


# Patterns match normalized individual lines, not arbitrary mentions in body
# paragraphs.  For example, "as specified in Table 1" is deliberately not a
# table-heading match.
HEADING_PATTERNS: dict[str, tuple[tuple[str, re.Pattern[str]], ...]] = {
    "cover": (
        (
            "airworthiness_directive_title",
            _compile(r"^(?:EASA\s+)?AIRWORTHINESS\s+DIRECTIVE\s*$"),
        ),
    ),
    "applicability": (
        ("applicability", _compile(r"^Applicability\s*:")),
    ),
    "definitions": (
        ("definitions", _compile(r"^Definitions?\s*:")),
    ),
    "reason": (
        ("reason", _compile(r"^Reasons?\s*:")),
    ),
    "required_actions_compliance": (
        (
            "required_actions_and_compliance",
            _compile(
                r"^Required\s+Action(?:\(s\)|s)?"
                r"(?:\s+and\s+Compliance\s+Time(?:\(s\)|s)?)?\s*:"
            ),
        ),
        (
            "required_actions_required_as_indicated",
            _compile(
                r"^Required\s+Action(?:\(s\)|s)?\s+"
                r"(?:\d+\.\s*)?Required\s+as\s+indicated\b"
            ),
        ),
        ("compliance", _compile(r"^Compliance\s*:")),
    ),
    "credit": (
        (
            "credit",
            _compile(r"^(?:Conditional\s+)?Credit(?:\s+for\s+.+?)?\s*:"),
        ),
    ),
    "reference_publications": (
        (
            "reference_publications",
            _compile(
                r"^(?:Ref\.?|Reference)\s+Publication(?:\(s\)|s)?\s*:"
            ),
        ),
    ),
    "remarks": (
        ("remarks", _compile(r"^Remarks?\s*:")),
    ),
    "appendix_table": (
        (
            "appendix_heading",
            _compile(
                r"^(?:EASA\s+AD\s+No\.?\s*:?.*?\s+)?"
                r"Appendix\s+[A-Z0-9]+"
                r"(?:\s*(?:[-–—:]|page\b|continued\b|\d+\s*/\s*\d+|$).*)$"
            ),
        ),
        (
            "table_heading",
            _compile(r"^Table\s+[A-Z0-9]+\s*(?:[-–—:]|$).*$"),
        ),
    ),
}


class InputError(RuntimeError):
    """Raised when frozen inputs fail integrity checks."""


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_line(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def detect_page_headings(text: str) -> list[dict[str, Any]]:
    """Return ordered heading matches for one page of extracted text."""

    matches: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = normalize_line(raw_line)
        if not line:
            continue
        matched_section = False
        for section in SECTION_ORDER:
            for pattern_name, pattern in HEADING_PATTERNS[section]:
                if pattern.search(line):
                    matches.append(
                        {
                            "section": section,
                            "line_number": line_number,
                            "text": line,
                            "pattern": pattern_name,
                        }
                    )
                    matched_section = True
                    break
            if matched_section:
                break
    return matches


def load_selection(path: Path) -> list[dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"Cannot read selection {path}: {exc}") from exc
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise InputError("Selection JSON must be a list of objects")
    if len(value) != EXPECTED_DOCUMENTS:
        raise InputError(
            f"Selection must contain {EXPECTED_DOCUMENTS} rows; found {len(value)}"
        )
    ad_numbers = [row.get("ad_number") for row in value]
    if any(not number for number in ad_numbers):
        raise InputError("Every selection row must have ad_number")
    duplicates = sorted(number for number, count in Counter(ad_numbers).items() if count > 1)
    if duplicates:
        raise InputError("Duplicate selection AD numbers: " + ", ".join(duplicates))
    return value


def _reject_excluded_input(path: Path) -> None:
    resolved = path.resolve()
    if "excluded_after_selection_audit" in resolved.parts:
        raise InputError(
            "Refusing excluded_after_selection_audit page text; use the current "
            "step3_pilot/page_text/pilot_pages.jsonl"
        )


def load_and_verify_pages(
    path: Path, selection_rows: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    """Load the aggregate JSONL and verify exact selection/page provenance."""

    _reject_excluded_input(path)
    selection = {row["ad_number"]: row for row in selection_rows}
    by_ad: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_page_ids: set[str] = set()

    try:
        handle = path.open("r", encoding="utf-8")
    except OSError as exc:
        raise InputError(f"Cannot read page text {path}: {exc}") from exc

    with handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                raise InputError(f"{path}:{line_number}: blank JSONL line")
            try:
                page = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise InputError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(page, dict):
                raise InputError(f"{path}:{line_number}: page record is not an object")

            ad_number = page.get("ad_number")
            if ad_number not in selection:
                raise InputError(
                    f"{path}:{line_number}: unselected AD {ad_number!r}; aggregate may be stale"
                )
            page_id = page.get("page_id")
            if not page_id or page_id in seen_page_ids:
                raise InputError(f"{path}:{line_number}: missing or duplicate page_id {page_id!r}")
            seen_page_ids.add(page_id)

            row = selection[ad_number]
            expected_pairs = {
                "base_ad_number": row.get("base_ad_number"),
                "logical_version_key": row.get("logical_version_key"),
                "file_instance_id": row.get("file_instance_id"),
                "content_id": row.get("content_id"),
                "file_name": row.get("file_name"),
                "relative_path": row.get("relative_path"),
                "pdf_sha256": row.get("file_sha256"),
                "manifest_normalized_text_sha256": row.get(
                    "normalized_text_sha256"
                ),
            }
            for field, expected in expected_pairs.items():
                if page.get(field) != expected:
                    raise InputError(
                        f"{path}:{line_number}: {ad_number} {field} does not match "
                        f"selection ({page.get(field)!r} != {expected!r})"
                    )

            try:
                expected_page_count = int(row["page_count"])
            except (KeyError, TypeError, ValueError) as exc:
                raise InputError(f"Selection has invalid page_count for {ad_number}") from exc
            page_number = page.get("page_number")
            if page.get("page_count") != expected_page_count:
                raise InputError(
                    f"{path}:{line_number}: {ad_number} page_count does not match selection"
                )
            if not isinstance(page_number, int) or not 1 <= page_number <= expected_page_count:
                raise InputError(
                    f"{path}:{line_number}: {ad_number} page {page_number!r} is outside "
                    f"1..{expected_page_count}"
                )
            text = page.get("text")
            if not isinstance(text, str):
                raise InputError(f"{path}:{line_number}: page text must be a string")
            if page.get("page_text_sha256") != sha256_text(text):
                raise InputError(
                    f"{path}:{line_number}: {ad_number} page {page_number} text hash mismatch"
                )
            by_ad[ad_number].append(page)

    expected_ads = set(selection)
    actual_ads = set(by_ad)
    if actual_ads != expected_ads:
        missing = sorted(expected_ads - actual_ads)
        extra = sorted(actual_ads - expected_ads)
        raise InputError(f"Page-text AD mismatch; missing={missing}, extra={extra}")
    if len(by_ad) != EXPECTED_DOCUMENTS:
        raise InputError(f"Expected {EXPECTED_DOCUMENTS} AD groups; found {len(by_ad)}")

    for ad_number, pages in by_ad.items():
        pages.sort(key=lambda page: page["page_number"])
        expected_count = int(selection[ad_number]["page_count"])
        page_numbers = [page["page_number"] for page in pages]
        expected_numbers = list(range(1, expected_count + 1))
        if page_numbers != expected_numbers:
            raise InputError(
                f"{ad_number}: pages are not exactly contiguous 1..{expected_count}: "
                f"{page_numbers}"
            )
    return dict(by_ad)


def build_index(
    selection_rows: list[dict[str, Any]],
    pages_by_ad: dict[str, list[dict[str, Any]]],
    *,
    selection_sha256: str,
    page_text_sha256: str,
    page_text_source: str,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []

    for selection_position, row in enumerate(selection_rows, start=1):
        ad_number = row["ad_number"]
        pages = pages_by_ad[ad_number]
        found: dict[str, list[dict[str, Any]]] = {
            section: [] for section in SECTION_ORDER
        }
        for page in pages:
            for match in detect_page_headings(page["text"]):
                found[match["section"]].append(
                    {
                        "page_number": page["page_number"],
                        "line_number": match["line_number"],
                        "text": match["text"],
                        "pattern": match["pattern"],
                    }
                )

        sections: dict[str, dict[str, Any]] = {}
        headings_not_found: list[str] = []
        for section in SECTION_ORDER:
            matches = found[section]
            heading_pages = sorted({item["page_number"] for item in matches})
            # Page 1 remains the cover navigation page even if extraction did
            # not preserve its title; the separate flag reports that condition.
            navigation_pages = [1] if section == "cover" else heading_pages
            heading_not_found = not bool(matches)
            if heading_not_found:
                headings_not_found.append(section)
            sections[section] = {
                "pages": navigation_pages,
                "heading_pages": heading_pages,
                "heading_found": not heading_not_found,
                "heading_not_found": heading_not_found,
                "matches": matches,
            }

        record = {
            "selection_position": selection_position,
            "ad_number": ad_number,
            "base_ad_number": row["base_ad_number"],
            "logical_version_key": row["logical_version_key"],
            "file_instance_id": row["file_instance_id"],
            "file_name": row["file_name"],
            "page_count": int(row["page_count"]),
            "sections": sections,
            "headings_not_found": headings_not_found,
        }
        # Defensive postcondition: every referenced navigation/detection page
        # must be valid for the selected source PDF.
        for section in SECTION_ORDER:
            for key in ("pages", "heading_pages"):
                for page_number in record["sections"][section][key]:
                    if not 1 <= page_number <= record["page_count"]:
                        raise InputError(
                            f"{ad_number}: {section}.{key} page {page_number} is out of range"
                        )
        records.append(record)

    if len(records) != EXPECTED_DOCUMENTS:
        raise InputError(f"Index must contain {EXPECTED_DOCUMENTS} records")
    return {
        "schema_version": "1.0.0",
        "detector_version": DETECTOR_VERSION,
        "purpose": "annotation_navigation_only",
        "page_semantics": (
            "pages are pages containing detected headings; cover pages always contains "
            "page 1. They are navigation aids, not inferred section spans or gold values."
        ),
        "heading_not_found_semantics": (
            "true means no recognized heading was found in cached page text; it does "
            "not mean the source section or information is absent"
        ),
        "selection_source": "selection/pilot_selection.json",
        "selection_sha256": selection_sha256,
        "page_text_source": page_text_source,
        "page_text_sha256": page_text_sha256,
        "record_count": len(records),
        "page_record_count": sum(len(pages) for pages in pages_by_ad.values()),
        "section_order": list(SECTION_ORDER),
        "records": records,
    }


def render_json(index: dict[str, Any]) -> str:
    return json.dumps(index, indent=2, ensure_ascii=False) + "\n"


def _pages_cell(values: Iterable[int]) -> str:
    return "|".join(str(value) for value in values)


def render_csv(index: dict[str, Any]) -> str:
    base_columns = [
        "selection_position",
        "ad_number",
        "base_ad_number",
        "logical_version_key",
        "file_instance_id",
        "file_name",
        "page_count",
    ]
    section_columns = [
        value
        for section in SECTION_ORDER
        for value in (
            f"{section}_pages",
            f"{section}_heading_pages",
            f"{section}_heading_found",
            f"{section}_heading_not_found",
            f"{section}_matched_headings",
        )
    ]
    columns = base_columns + section_columns + ["headings_not_found"]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for record in index["records"]:
        row = {key: record[key] for key in base_columns}
        for section in SECTION_ORDER:
            section_value = record["sections"][section]
            row[f"{section}_pages"] = _pages_cell(section_value["pages"])
            row[f"{section}_heading_pages"] = _pages_cell(
                section_value["heading_pages"]
            )
            row[f"{section}_heading_found"] = str(
                section_value["heading_found"]
            ).lower()
            row[f"{section}_heading_not_found"] = str(
                section_value["heading_not_found"]
            ).lower()
            row[f"{section}_matched_headings"] = " || ".join(
                f"p{item['page_number']}:{item['text']}"
                for item in section_value["matches"]
            )
        row["headings_not_found"] = "|".join(record["headings_not_found"])
        writer.writerow(row)
    return output.getvalue()


def _check_or_write(path: Path, expected: str, check: bool) -> None:
    if check:
        try:
            actual = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise InputError(f"Cannot check output {path}: {exc}") from exc
        if actual != expected:
            raise InputError(f"Generated output is stale: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(expected, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--page-text", type=Path, default=DEFAULT_PAGE_TEXT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify committed outputs are byte-for-byte current instead of writing",
    )
    args = parser.parse_args(argv)

    try:
        selection_rows = load_selection(args.selection)
        pages_by_ad = load_and_verify_pages(args.page_text, selection_rows)
        try:
            page_text_source = str(args.page_text.resolve().relative_to(ROOT))
        except ValueError:
            page_text_source = str(args.page_text.resolve())
        index = build_index(
            selection_rows,
            pages_by_ad,
            selection_sha256=sha256_path(args.selection),
            page_text_sha256=sha256_path(args.page_text),
            page_text_source=page_text_source,
        )
        json_text = render_json(index)
        csv_text = render_csv(index)
        _check_or_write(args.output_dir / "section_index.json", json_text, args.check)
        _check_or_write(args.output_dir / "section_index.csv", csv_text, args.check)
    except InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    missing_counts = Counter(
        section
        for record in index["records"]
        for section in record["headings_not_found"]
    )
    print(
        f"{'Verified' if args.check else 'Built'} section index: "
        f"{index['record_count']} ADs, {index['page_record_count']} pages"
    )
    print(
        "Heading-not-found counts: "
        + ", ".join(
            f"{section}={missing_counts.get(section, 0)}"
            for section in SECTION_ORDER
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
