#!/usr/bin/env python3
"""Development-hardened local extractor v2.1.6.

v2.1.6 deliberately layers narrow, source-format fixes over the frozen v2.1.5
parser. It does not add semantic compliance normalization. The fixes are based
only on development-set/source-format evidence discovered before the locked
extraction test is run.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from full_corpus_pipeline import local_extractor as _v215


PARSER_VERSION = "content-local-v2.1.6"


def _normalize_header_layout(text: str) -> str:
    """Normalize equivalent printed header spellings without rewriting AD prose."""
    value = text.replace("\r\n", "\n").replace("\r", "\n")

    # Several 2019/2020 PDFs extract the DAH label with a doubled colon.
    value = re.sub(
        r"(?i)((?:Design|Design\s+Change|Design\s+Organisation)\s+Approval\s+Holder(?:[’']s)?\s+Name)\s*::+",
        r"\1:",
        value,
    )

    # Legacy Form 110 wording used Type Approval Holder and occasionally a
    # plural multi-holder heading. Normalize only the label, never its value.
    value = re.sub(
        r"(?i)\bType\s+Approval\s+Holder(?:s)?(?:[’']s)?\s+(?:Name|names)\s*:+",
        "Design Approval Holder’s Name:",
        value,
    )

    # Older forms use the plural word rather than the modern designation(s).
    value = re.sub(
        r"(?i)\bType/Model\s+designations?\s*:+",
        "Type/Model designation(s):",
        value,
    )

    # Some legacy forms print `Manufacturers:` rather than the later
    # `Manufacturer(s):` label. Normalize the label so v2.1.5 boundaries apply.
    value = re.sub(
        r"(?im)^\s*Manufacturers\s*:",
        "Manufacturer(s):",
        value,
    )
    return value


def _flexible_a300_models(text: str | None) -> list[str]:
    """Recover canonical A300 variants printed with optional extra hyphens."""
    if not text:
        return []
    values: list[str] = []
    patterns = (
        re.compile(r"\bA300\s*-?\s*([BCF]\d)\s*-?\s*(\d{3}[A-Z]*)\b", re.IGNORECASE),
        re.compile(r"\bA300\s*-\s*(600ST)\b", re.IGNORECASE),
    )
    for pattern in patterns:
        for match in pattern.finditer(text):
            if pattern is patterns[0]:
                value = f"A300{match.group(1).upper()}-{match.group(2).upper()}"
            else:
                value = f"A300-{match.group(1).upper()}"
            if value not in values:
                values.append(value)
    return values


def _header_subject_and_ata(text: str) -> tuple[str | None, list[dict[str, str]]]:
    """Recover the printed header subject, including consecutive ATA blocks."""
    cleaned = _v215._clean_layout_text(text)
    header = cleaned[:20000]
    ata_re = re.compile(
        r"(?m)^[ \t]*ATA\s+(\d{2}(?:\s*(?:,|/|&|and)\s*\d{2})*)\b",
        re.IGNORECASE,
    )
    all_matches = list(ata_re.finditer(header))
    if not all_matches:
        return None, []

    # The subject heading precedes Manufacturer/Applicability/Definitions/Reason
    # or the compliance section. Restricting to that header window prevents ATA
    # references later in compliance prose from being mistaken for the subject.
    first = all_matches[0]
    boundary_match = re.search(
        r"(?m)^\s*(?:Manufacturer(?:\(s\))?|Manufacturers?|Applic+ability|Definitions?|Reas\w*n|"
        r"Required\s+Action(?:s|\(s\))?|Compliance)\s*:",
        header[first.end() :],
        re.IGNORECASE,
    )
    boundary = first.end() + boundary_match.start() if boundary_match else min(len(header), first.start() + 2500)
    matches = [match for match in all_matches if match.start() < boundary]
    if not matches:
        return None, []

    parts: list[str] = []
    chapters: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else boundary
        body = re.sub(r"\s+", " ", header[match.end() : end]).strip(" \t\n-–—:;")
        if not body:
            continue
        codes = re.findall(r"\d{2}", match.group(1))
        if not parts:
            parts.append(body)
        else:
            printed_codes = ", ".join(codes)
            parts.append(f"ATA {printed_codes} – {body}")
        for code in codes:
            chapters.append({"code": code, "title": body})

    subject = "; ".join(parts).strip() if parts else None
    return subject, chapters


def _postprocess_supersedure(record: dict[str, Any]) -> None:
    """Do not convert a revision chain into a false direct supersedure edge."""
    supersedure = record.get("supersedure")
    if not isinstance(supersedure, dict):
        return
    statement = str(supersedure.get("statement") or "")
    normalized = re.sub(r"\s+", " ", statement).casefold()
    # Example: "This AD revises ... which superseded ...". The full statement is
    # retained, but neither earlier AD is directly superseded by this revision.
    if "this ad revises" in normalized and "which superseded" in normalized:
        supersedure.pop("superseded_ad_numbers", None)


def _augment_applicability_models(record: dict[str, Any]) -> None:
    for item in record.get("applicability", []) or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "")
        models = list(item.get("models") or [])
        for model in _flexible_a300_models(text):
            if model not in models:
                models.append(model)
        # A300-24/A300-28 style ATA/reference fragments are not aircraft models.
        models = [
            model
            for model in models
            if not (re.fullmatch(r"A300-\d{2}", str(model), re.IGNORECASE) and str(model).upper() != "A300-600")
        ]
        if models:
            item["models"] = models


def extract_local_record(row: dict[str, Any], schema: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract one v2.1.6 content record using only deterministic local rules."""
    patched_row = copy.copy(row)
    patched_row["text"] = _normalize_header_layout(str(row["text"]))
    record, detail = _v215.extract_local_record(patched_row, schema)

    subject, chapters = _header_subject_and_ata(str(patched_row["text"]))
    publication = record.setdefault("publication", {})
    if subject:
        publication["subject"] = subject
    if chapters:
        publication["ata_chapters"] = chapters

    _augment_applicability_models(record)
    _postprocess_supersedure(record)

    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(record))
    if errors:
        raise ValueError("; ".join(error.message for error in errors[:5]))

    detail = dict(detail)
    detail["parser_version"] = PARSER_VERSION
    detail["method"] = "deterministic_local"
    return record, detail
