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

_COMMON_HOLDER_LABEL = r"Design\s+Approval\s+Holder(?:[’']s)?\s+Name"
_COMMON_MODEL_LABEL = r"Type/Model\s+designation(?:\(s\))?"


def _normalize_header_layout(text: str) -> str:
    """Normalize equivalent printed header spellings without rewriting AD prose."""
    value = text.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(
        r"(?i)((?:Design|Design\s+Change|Design\s+Organisation)\s+Approval\s+Holder(?:[’']s)?\s+Name)\s*::+",
        r"\1:",
        value,
    )
    value = re.sub(
        r"(?i)\b(?:Type|Modification)\s+Approval\s+Holder(?:s)?(?:[’']s)?\s+(?:Name|names)\s*:+",
        "Design Approval Holder’s Name:",
        value,
    )
    value = re.sub(
        r"(?i)\bType/Model\s+designations?\s*:+",
        "Type/Model designation(s):",
        value,
    )
    value = re.sub(r"(?im)^\s*Manufacturers\s*:", "Manufacturer(s):", value)
    return value


def _header_holder(text: str) -> str | None:
    """Read the normalized approval-holder field across legacy/modern layouts."""
    cleaned = _v215._clean_layout_text(text)
    lines = cleaned[:16000].splitlines()
    holder_re = re.compile(rf"{_COMMON_HOLDER_LABEL}\s*:", re.IGNORECASE)
    model_re = re.compile(rf"{_COMMON_MODEL_LABEL}\s*:", re.IGNORECASE)
    stop_re = re.compile(
        r"^(?:Effective\s+Date|TCDS\s+Number|Foreign\s+AD|Revision|Supersedure|ATA\s+\d{2})\s*:",
        re.IGNORECASE,
    )

    for index, raw_line in enumerate(lines):
        line = raw_line.strip()
        match = holder_re.search(line)
        if not match:
            continue

        same_model = model_re.search(line, match.end())
        inline = line[match.end() : same_model.start() if same_model else len(line)].strip(" :")
        parts: list[str] = [inline] if inline else []
        model_label_precedes_holder = bool(index > 0 and model_re.search(lines[index - 1]))

        for candidate in lines[index + 1 : index + 10]:
            candidate = candidate.strip()
            if not candidate:
                continue
            model_label = model_re.search(candidate)
            if model_label:
                prefix = candidate[: model_label.start()].strip(" :")
                if prefix:
                    parts.append(prefix)
                break
            if stop_re.match(candidate):
                break

            # Normal two-column extraction preserves a wide whitespace gap:
            # `AIRBUS S.A.S.        Airbus aeroplanes (see Applicability)`.
            columns = re.split(r"\s{2,}", candidate, maxsplit=1)
            if len(columns) == 2 and columns[0].strip():
                parts.append(columns[0].strip())
                break

            model_token = _v215.MODEL_PATTERN.search(candidate)
            if model_token:
                prefix = candidate[: model_token.start()].strip(" :")
                if prefix:
                    parts.append(prefix)
                    break
                # A few 2013 two-column PDFs extract the model label/value first,
                # then the holder value on the next line. Skip the model row and
                # continue until that holder cell is reached.
                if model_label_precedes_holder:
                    continue
                break

            if model_label_precedes_holder:
                if candidate.casefold() in {"aeroplane", "aeroplanes", "aircraft"}:
                    continue
                parts.append(candidate)
                break

            # Sequential multi-holder forms intentionally keep all organization
            # lines until the Type/Model label so scope policy can classify them
            # as mixed rather than silently choosing Airbus.
            parts.append(candidate)

        value = _v215.compact(" ".join(parts))
        return value if _v215._looks_like_holder(value) else None
    return None


def _flexible_a300_models(text: str | None) -> list[str]:
    """Recover canonical A300 variants printed with optional extra hyphens."""
    if not text:
        return []
    values: list[str] = []
    patterns = (
        re.compile(r"\bA300\s*-?\s*([BCF]\d)\s*-?\s*(\d{3}[A-Z]*)\b", re.IGNORECASE),
        re.compile(r"\bA300\s*-\s*(600ST)\b", re.IGNORECASE),
    )
    for pattern_index, pattern in enumerate(patterns):
        for match in pattern.finditer(text):
            if pattern_index == 0:
                value = f"A300{match.group(1).upper()}-{match.group(2).upper()}"
            else:
                value = f"A300-{match.group(1).upper()}"
            if value not in values:
                values.append(value)
    return values


def _legacy_subject_prefix(header: str, first_ata_start: int) -> str | None:
    """Return contiguous legacy subject text printed immediately before ATA.

    Early Form 110 layouts often print the first half of the subject before an
    isolated `ATA xx` line and the rest immediately after it. The prefix begins
    only after the last recognized metadata field, so holder/model/date/TCDS
    values cannot be pulled into the subject.
    """
    prefix_region = header[:first_ata_start]
    field_re = re.compile(
        r"(?im)^\s*(?:Design\s+Approval\s+Holder(?:[’']s)?\s+Name|Type/Model\s+designation(?:\(s\))?|"
        r"Effective\s+Date|TCDS\s+Number(?:\(s\))?|Foreign\s+AD|Revision|Supersedure|Cancellation)\s*:.*$"
    )
    matches = list(field_re.finditer(prefix_region))
    if not matches:
        return None

    candidate = prefix_region[matches[-1].end() :]
    lines = [line.strip() for line in candidate.splitlines() if line.strip()]
    lines = [
        line
        for line in lines
        if not re.match(
            r"^(?:Airworthiness\s+Directive|AD\s+No\.?|Issued|Date|Note)\s*:?"," 
            " line,
            re.IGNORECASE,
        )
    ]
    return _v215.compact(" ".join(lines)) if lines else None


def _header_subject_and_ata(text: str) -> tuple[str | None, list[dict[str, str]]]:
    """Recover the printed header subject, including legacy split/consecutive ATA blocks."""
    cleaned = _v215._clean_layout_text(text)
    header = cleaned[:20000]
    ata_re = re.compile(
        r"(?m)^[ \t]*ATA\s+(\d{2}(?:\s*(?:,|/|&|and)\s*\d{2})*)\b",
        re.IGNORECASE,
    )
    all_matches = list(ata_re.finditer(header))
    if not all_matches:
        return None, []

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

    legacy_prefix = _legacy_subject_prefix(header, first.start())
    parts: list[str] = []
    chapters: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else boundary
        body = re.sub(r"\s+", " ", header[match.end() : end]).strip(" \t\n-–—:;")
        if not body:
            continue
        codes = re.findall(r"\d{2}", match.group(1))
        if not parts:
            first_body = _v215.compact(" ".join(part for part in (legacy_prefix, body) if part))
            if first_body:
                parts.append(first_body)
        else:
            parts.append(f"ATA {', '.join(codes)} – {body}")
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

    holder = _header_holder(str(patched_row["text"]))
    if holder:
        record.setdefault("ad_identity", {})["design_approval_holder"] = holder

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
