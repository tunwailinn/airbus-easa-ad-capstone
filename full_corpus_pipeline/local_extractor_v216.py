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
                if model_label_precedes_holder:
                    continue
                break

            if model_label_precedes_holder:
                if candidate.casefold() in {"aeroplane", "aeroplanes", "aircraft"}:
                    continue
                parts.append(candidate)
                break

            parts.append(candidate)

        value = _v215.compact(" ".join(parts))
        return value if _v215._looks_like_holder(value) else None
    return None


def _header_manufacturer(text: str) -> str | None:
    """Read the printed Manufacturer(s) cell without absorbing Applicability."""
    cleaned = _v215._clean_layout_text(text)
    lines = cleaned[:20000].splitlines()
    pattern = re.compile(r"Manufacturer(?:\(s\))?\s*:", re.IGNORECASE)
    stop = re.compile(
        r"^(?:Applic+ability|Definitions?|Reas\w*n|Required\s+Action|Compliance)\s*:",
        re.IGNORECASE,
    )
    for index, raw_line in enumerate(lines):
        match = pattern.search(raw_line)
        if not match:
            continue
        inline = raw_line[match.end() :].strip()
        if inline:
            return _v215.compact(re.split(r"\s{2,}", inline, maxsplit=1)[0])
        for candidate in lines[index + 1 : index + 4]:
            candidate = candidate.strip()
            if not candidate:
                continue
            if stop.match(candidate):
                return None
            return _v215.compact(re.split(r"\s{2,}", candidate, maxsplit=1)[0])
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


def _spaced_model_variants(text: str | None) -> list[str]:
    """Recover variants whose hyphen is separated by PDF-extraction whitespace."""
    if not text:
        return []
    values: list[str] = []
    pattern = re.compile(
        r"\b(A(?:310|318|319|320|321|330|340|350|380))\s*-\s*(\d{3,4}[A-Z]*)\b",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        value = f"{match.group(1).upper()}-{match.group(2).upper()}"
        if value not in values:
            values.append(value)
    return values


def _legacy_subject_prefix(header: str, first_ata_start: int) -> str | None:
    """Return contiguous legacy subject text printed immediately before ATA."""
    prefix_region = header[:first_ata_start]
    field_re = re.compile(
        r"(?im)^\s*(?:Design\s+Approval\s+Holder(?:[’']s)?\s+Name|"
        r"Type/Model\s+designation(?:\(s\))?|Effective\s+Date|"
        r"TCDS\s+Number(?:\(s\))?|Foreign\s+AD|Revision|Supersedure|"
        r"Cancellation)\s*:.*$"
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
            r"^(?:Airworthiness\s+Directive|AD\s+No\.?|Issued|Date|Note)\s*: ?",
            line,
            re.IGNORECASE,
        )
        and not re.match(
            r"^(?:EASA\s+)?AD\s+(?:19|20)\d{2}-\d{4}(?:R\d+)?\b",
            line,
            re.IGNORECASE,
        )
        and not re.match(
            r"^(?:19|20)\d{2}-\d{4}(?:R\d+)?\s+dated\b",
            line,
            re.IGNORECASE,
        )
    ]
    if not lines:
        return None

    joined = " ".join(lines)
    if re.search(
        r"\b(?:revis(?:es|ed)|supersed(?:e|ed|es)|correction\s+dated|DGAC\s+France)\b|"
        r"\b(?:EASA\s+)?AD\s+(?:19|20)\d{2}-\d{4}(?:R\d+)?\b|"
        r"\b(?:19|20)\d{2}-\d{4}(?:R\d+)?\s+dated\b",
        joined,
        re.IGNORECASE,
    ):
        return None
    return _v215.compact(joined)


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
        r"(?m)^\s*(?:Manufacturer(?:\(s\))?|Manufacturers?|Applic+ability|"
        r"Definitions?|Reas\w*n|Required\s+Action(?:s|\(s\))?|Compliance)\s*:",
        header[first.end() :],
        re.IGNORECASE,
    )
    boundary = first.end() + boundary_match.start() if boundary_match else min(
        len(header), first.start() + 2500
    )
    matches = [match for match in all_matches if match.start() < boundary]
    if not matches:
        return None, []

    legacy_prefix = _legacy_subject_prefix(header, first.start())
    parts: list[str] = []
    chapters: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else boundary
        body = re.sub(r"\s+", " ", header[match.end() : end]).strip(" \t\n:;")
        if not body:
            continue
        codes = re.findall(r"\d{2}", match.group(1))
        if not parts:
            if legacy_prefix:
                prefix = legacy_prefix.rstrip()
                first_body = body.lstrip()
                if prefix.endswith(("-", "–", "—")) and first_body.startswith(("-", "–", "—")):
                    first_body = first_body[1:].lstrip()
                combined = _v215.compact(f"{prefix} {first_body}")
            else:
                combined = _v215.compact(body.lstrip(" -–—"))
            if combined:
                parts.append(combined)
        else:
            parts.append(f"ATA {', '.join(codes)} – {body.lstrip(' -–—')}")
        for code in codes:
            chapters.append({"code": code, "title": body.lstrip(" -–—")})

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


def _repair_applicability(text: str, record: dict[str, Any]) -> None:
    """Repair legacy two-column Applicability order and model-token spacing."""
    cleaned = _v215._clean_layout_text(text)
    applicability = record.get("applicability") or []
    if not applicability:
        return

    label = re.search(r"(?im)^\s*Applic+ability\s*:", cleaned)
    if label:
        preceding = [line.strip() for line in cleaned[: label.start()].splitlines() if line.strip()]
        if preceding:
            prefix = preceding[-1]
            if _v215.MODEL_PATTERN.search(prefix) and not re.match(
                r"^(?:Manufacturer|TCDS|Foreign|Supersedure|ATA)\b", prefix, re.IGNORECASE
            ):
                current = str(applicability[0].get("text") or "")
                if not current.startswith(prefix):
                    applicability[0]["text"] = _v215.compact(f"{prefix} {current}")

    item = applicability[0]
    app_text = str(item.get("text") or "")
    models = _v215._models(app_text)
    for model in _flexible_a300_models(app_text) + _spaced_model_variants(app_text):
        if model not in models:
            models.append(model)

    models = [
        model
        for model in models
        if not (
            re.fullmatch(r"A300-\d{2}", str(model), re.IGNORECASE)
            and str(model).upper() != "A300-600"
        )
    ]

    # If a bare family token exists only because every occurrence belongs to a
    # printed detailed variant (e.g. `A320- 111` or `A300 B4-601`), remove the
    # artificial broad token while keeping genuinely printed broad families.
    for family in ("A300", "A310", "A318", "A319", "A320", "A321", "A330", "A340", "A350", "A380"):
        if family not in models:
            continue
        occurrences = list(re.finditer(rf"\b{re.escape(family)}\b", app_text, re.IGNORECASE))
        if not occurrences:
            continue

        def variant_occurrence(match: re.Match[str]) -> bool:
            tail = app_text[match.end() : match.end() + 12]
            if family == "A300":
                return bool(re.match(r"\s*(?:-\s*\d|[BCF]\d)", tail, re.IGNORECASE))
            return bool(re.match(r"\s*-\s*\d", tail, re.IGNORECASE))

        if all(variant_occurrence(match) for match in occurrences):
            models = [model for model in models if model != family]

    if models:
        item["models"] = models
        item["aircraft_families"] = _v215._families(models)


def extract_local_record(
    row: dict[str, Any], schema: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract one v2.1.6 content record using only deterministic local rules."""
    patched_row = copy.copy(row)
    patched_row["text"] = _normalize_header_layout(str(row["text"]))
    record, detail = _v215.extract_local_record(patched_row, schema)

    holder = _header_holder(str(patched_row["text"]))
    if holder:
        record.setdefault("ad_identity", {})["design_approval_holder"] = holder

    manufacturer = _header_manufacturer(str(patched_row["text"]))
    if manufacturer:
        record.setdefault("publication", {})["manufacturers"] = [manufacturer]

    subject, chapters = _header_subject_and_ata(str(patched_row["text"]))
    publication = record.setdefault("publication", {})
    if subject:
        publication["subject"] = subject
    if chapters:
        publication["ata_chapters"] = chapters

    _repair_applicability(str(patched_row["text"]), record)
    _postprocess_supersedure(record)

    errors = list(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(record)
    )
    if errors:
        raise ValueError("; ".join(error.message for error in errors[:5]))

    detail = dict(detail)
    detail["parser_version"] = PARSER_VERSION
    detail["method"] = "deterministic_local"
    return record, detail
