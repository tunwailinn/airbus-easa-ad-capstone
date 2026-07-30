#!/usr/bin/env python3
"""Verify annotation evidence quotes against the frozen per-page text cache."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_PAGE_DIR = ROOT / "page_text"


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).replace("\u00ad", "")
    return re.sub(r"\s+", " ", value).strip()


def token_subsequence(quote: str, page_text: str) -> bool:
    """Allow punctuation-normalized, ordered excerpts spanning layout gaps."""

    quote_tokens = re.findall(r"\w+", normalize(quote).casefold())
    page_tokens = re.findall(r"\w+", normalize(page_text).casefold())
    if not quote_tokens:
        return False
    position = 0
    for token in page_tokens:
        if token == quote_tokens[position]:
            position += 1
            if position == len(quote_tokens):
                return True
    return False


def collect_inputs(values: list[str]) -> list[Path]:
    paths: list[Path] = []
    for raw in values:
        path = Path(raw)
        if path.is_dir():
            paths.extend(sorted(path.glob("*.annotation.json")))
        elif path.is_file():
            paths.append(path)
        else:
            raise FileNotFoundError(path)
    return sorted(set(path.resolve() for path in paths))


def load_pages(page_dir: Path) -> dict[tuple[str, int], dict[str, Any]]:
    result: dict[tuple[str, int], dict[str, Any]] = {}
    for path in sorted(page_dir.glob("*.pages.jsonl")):
        for raw in path.read_text(encoding="utf-8").splitlines():
            page = json.loads(raw)
            key = (page["file_instance_id"], int(page["page_number"]))
            if key in result:
                raise ValueError(f"Duplicate page cache key {key}")
            result[key] = page
    return result


def evidence_errors(record: dict[str, Any], pages: dict[tuple[str, int], dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    source_id = record.get("source_document", {}).get("file_instance_id")
    for index, evidence in enumerate(record.get("evidence_spans") or []):
        prefix = f"/evidence_spans/{index} ({evidence.get('evidence_id', '?')})"
        if evidence.get("source_file_instance_id") != source_id:
            errors.append(f"{prefix}: source_file_instance_id differs from source document")
            continue
        page_number = evidence.get("page_number")
        page = pages.get((source_id, page_number))
        if page is None:
            errors.append(f"{prefix}: page {page_number!r} not found in frozen page cache")
            continue
        evidence_hash = evidence.get("page_text_sha256")
        if evidence_hash is None:
            errors.append(f"{prefix}: page_text_sha256 is missing")
        elif evidence_hash != page.get("page_text_sha256"):
            errors.append(f"{prefix}: page_text_sha256 differs from frozen page cache")

        quote = evidence.get("exact_quote") or ""
        page_text = page.get("text") or ""
        extraction = evidence.get("extraction_method")
        start, end = evidence.get("start_char"), evidence.get("end_char")
        if (start is None) != (end is None):
            errors.append(f"{prefix}: start_char and end_char must both be set or both be null")
        elif start is not None:
            if not (0 <= start < end <= len(page_text)):
                errors.append(f"{prefix}: character offsets are outside page text")
            elif normalize(page_text[start:end]) != normalize(quote):
                errors.append(f"{prefix}: character-offset text does not match exact_quote")

        if extraction == "visual_transcription":
            if not evidence.get("annotation_note"):
                errors.append(f"{prefix}: visual transcription requires an annotation note")
        elif (
            normalize(quote) not in normalize(page_text)
            and not token_subsequence(quote, page_text)
        ):
            errors.append(f"{prefix}: normalized exact_quote not found on cited page")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="annotation JSON file(s) or directories")
    parser.add_argument("--page-text-dir", type=Path, default=DEFAULT_PAGE_DIR)
    args = parser.parse_args(argv)

    try:
        files = collect_inputs(args.inputs)
        pages = load_pages(args.page_text_dir)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"CONFIGURATION ERROR: {exc}", file=sys.stderr)
        return 2
    if not files:
        print("CONFIGURATION ERROR: no annotation files found", file=sys.stderr)
        return 2

    failed = 0
    for path in files:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            errors = evidence_errors(record, pages)
        except (OSError, json.JSONDecodeError) as exc:
            errors = [f"could not load JSON: {exc}"]
        if errors:
            failed += 1
            print(f"FAIL {path}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
