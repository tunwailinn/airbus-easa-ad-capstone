#!/usr/bin/env python3
"""Deterministic, content-only extraction for EASA AD records.

This parser structures stable header fields and preserves difficult sections as
raw source wording. Layout-only page furniture is removed before section
segmentation; compliance logic itself is intentionally not normalized.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


PARSER_VERSION = "content-local-v2.1.4"

DATE_FORMATS = (
    "%d %B %Y",
    "%d %b %Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%Y-%m-%d",
)

ACTION_HEADING = (
    r"required\s+action(?:s|\(s\))?"
    r"(?:\s+and\s+compliance\s+time(?:s|\(s\))?)?"
)

SECTION_ENDINGS = (
    "definitions?",
    "reason",
    r"effective\s+date",
    ACTION_HEADING,
    "compliance",
    r"ref\.?\s+publications?",
    r"referenced\s+publications?",
    "remarks?",
    "contacts?",
    "appendix",
    "annex",
)

MODEL_PATTERN = re.compile(
    r"\b(?:A300(?:B\d|F\d)?(?:-\d{2,4}[A-Z]*)?|A310(?:-\d{2,4}[A-Z]*)?|"
    r"A(?:318|319|320|321|330|340|350|380)(?:-\d{2,4}[A-Z]*)?)\b",
    re.IGNORECASE,
)

SB_PATTERN = re.compile(
    r"\b(A(?:300|310|318|319|320|321|330|340|350|380)[A-Z0-9]*-"
    r"\d{2}[A-Z]?\s*-?\s*\d{3,6})\b",
    re.IGNORECASE,
)

AD_PATTERN = re.compile(r"\b((?:19|20)\d{2}-\d{4}(?:R\d+)?)\b", re.IGNORECASE)

_PAGE_FURNITURE_PATTERNS = (
    re.compile(r"^\s*\[PAGE\s+\d+\]\s*$", re.IGNORECASE),
    re.compile(r"^\s*Page\s+\d+\s+of\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*TE\.CAP\.\d+(?:-\d+)?\b.*$", re.IGNORECASE),
    re.compile(
        r"^\s*©\s*European\s+Union\s+Aviation\s+Safety\s+Agency\b.*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*Proprietary\s+document\.\s*Copies\s+are\s+not\s+controlled\..*$",
        re.IGNORECASE,
    ),
    re.compile(r"^\s*An\s+agency\s+of\s+the\s+European\s+Union\s*$", re.IGNORECASE),
    re.compile(r"^\s*ISO9001\s+Certified\.?\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:SUPERSEDED|CANCELLED|CANCELED)\s*$", re.IGNORECASE),
)

_REPEATED_AD_HEADER = re.compile(
    r"^\s*(?:(?:SUPERSEDED|CANCELLED|CANCELED)\s*[.]?\s*)?"
    r"EASA\s+AD\s+No\.?\s*:\s*(?:19|20)\d{2}-\d{4}(?:R\d+)?\s*$",
    re.IGNORECASE,
)


def compact(value: Any) -> Any:
    """Recursively omit absent values and normalize layout whitespace."""
    if value is None:
        return None
    if isinstance(value, dict):
        return {
            key: item
            for key, raw in value.items()
            if (item := compact(raw)) not in (None, {}, [])
        }
    if isinstance(value, list):
        return [
            item for raw in value if (item := compact(raw)) not in (None, {}, [])
        ]
    if isinstance(value, str):
        value = re.sub(r"\s+", " ", value).strip(" \t\r\n:;,")
        return value or None
    return value


def _clean_layout_text(text: str) -> str:
    """Remove repeated page furniture without rewriting source prose."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(
        r"(?i)(?:SUPERSEDED|CANCELLED|CANCELED)\s*[.]?\s*"
        r"EASA\s+AD\s+No\.?\s*:\s*(?:19|20)\d{2}-\d{4}(?:R\d+)?",
        "\n",
        text,
    )
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue
        if _REPEATED_AD_HEADER.match(line):
            continue
        if any(pattern.match(line) for pattern in _PAGE_FURNITURE_PATTERNS):
            continue
        line = re.sub(
            r"\s*TE\.CAP\.\d+(?:-\d+)?\s+©\s*European\s+Union\s+Aviation\s+Safety\s+Agency.*$",
            "",
            line,
            flags=re.IGNORECASE,
        ).strip()
        if line:
            lines.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _parse_date(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.casefold() in {"nan", "nat", "none"}:
        return None
    text = re.sub(r"(?<=\d)(?:st|nd|rd|th)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" .")
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format).date().isoformat()
        except ValueError:
            continue
    return None


def _printed_date(text: str, labels: str) -> str | None:
    match = re.search(
        rf"(?:{labels})\s*:\s*(?:Revision\s+\d+\s*:\s*)?"
        r"([0-3]?\d\s+[A-Za-z]+\s+(?:19|20)\d{2})",
        text[:16000],
        re.IGNORECASE,
    )
    return _parse_date(match.group(1)) if match else None


def _section(
    text: str, heading: str, endings: tuple[str, ...] = SECTION_ENDINGS
) -> str | None:
    """Extract one labelled section without treating ordinary prose as a heading."""
    end_pattern = "|".join(endings)
    match = re.search(
        rf"(?:^|\n)\s*(?:{heading})\s*:\s*(.*?)"
        rf"(?=\n\s*(?:{end_pattern})\s*(?::[ \t]*|\n|$)|\Z)",
        text,
        re.IGNORECASE | re.DOTALL | re.MULTILINE,
    )
    return compact(match.group(1)) if match else None


def _header_field(text: str, heading: str, endings: tuple[str, ...]) -> str | None:
    return _section(text[:18000], heading, endings)


def _two_column_values(text: str) -> tuple[str | None, str | None]:
    """Read holder/model values from either two-column or sequential extraction."""
    lines = text[:12000].splitlines()
    holder_pattern = re.compile(
        r"(?:Type|Design|Design\s+Change)\s+Approval\s+Holder(?:[’']s)?\s+Name\s*:",
        re.IGNORECASE,
    )
    model_pattern = re.compile(
        r"Type/Model\s+designation(?:\(s\))?\s*:", re.IGNORECASE
    )
    for index, line in enumerate(lines):
        holder_match = holder_pattern.search(line)
        if not holder_match:
            continue
        model_match = model_pattern.search(line)
        if model_match:
            holder = line[holder_match.end() : model_match.start()].strip()
            model_value = line[model_match.end() :].strip()
            for candidate in lines[index + 1 : index + 6]:
                if not candidate.strip():
                    continue
                columns = re.split(r"\s{2,}", candidate.strip(), maxsplit=1)
                if not holder:
                    holder = columns[0]
                if not model_value and len(columns) == 2:
                    model_value = columns[1]
                break
            return compact(holder), compact(model_value)
        break

    holder = _header_field(
        text,
        r"(?:Type|Design|Design\s+Change)\s+Approval\s+Holder(?:[’']s)?\s+Name",
        (
            r"Type/Model\s+designation(?:\(s\))?",
            r"Effective\s+Date",
            r"TCDS\s+Number",
        ),
    )
    model_value = _header_field(
        text,
        r"Type/Model\s+designation(?:\(s\))?",
        (
            r"Effective\s+Date",
            r"TCDS\s+Number",
            r"Foreign\s+AD",
            "revision",
            "supersedure",
            r"ATA\s+\d{2}",
        ),
    )
    return holder, model_value


def _models(text: str | None) -> list[str]:
    if not text:
        return []
    values: list[str] = []
    seen: set[str] = set()
    for match in MODEL_PATTERN.finditer(text):
        following = text[match.end() : match.end() + 8]
        if re.match(r"(?:\d|-\s*\d)", following):
            continue
        value = match.group(0).upper()
        if value not in seen:
            seen.add(value)
            values.append(value)
    return values


def _families(models: list[str]) -> list[str]:
    values: list[str] = []
    for model in models:
        if model.startswith("A300"):
            family = "A300"
        elif model.startswith("A310"):
            family = "A310"
        elif model.startswith(("A318", "A319", "A320", "A321")):
            family = "A320 family"
        else:
            match = re.match(r"A\d{3}", model)
            if not match:
                continue
            family = match.group(0)
        if family not in values:
            values.append(family)
    return values


def _ata(text: str) -> list[dict[str, str]]:
    lines = text[:18000].splitlines()
    for index, line in enumerate(lines):
        match = re.search(
            r"\bATA\s+(\d{2}(?:\s*(?:,|&|and)\s*\d{2})*)\s*[-–—:]?\s*(.*)",
            line,
            re.IGNORECASE,
        )
        if not match:
            continue
        codes = re.findall(r"\d{2}", match.group(1))
        title_parts = [match.group(2).strip()] if match.group(2).strip() else []
        for continuation in lines[index + 1 : index + 4]:
            candidate = continuation.strip()
            if not candidate:
                continue
            if re.match(
                r"(?:Manufacturer(?:\(s\))?|Applicability|Definitions?|Reason|Effective\s+Date)\s*:",
                candidate,
                re.IGNORECASE,
            ):
                break
            title_parts.append(candidate)
        title = compact(" ".join(title_parts))
        return [compact({"code": code, "title": title}) for code in codes]
    return []


def _manufacturer(text: str) -> list[str]:
    value = _section(
        text,
        r"Manufacturer(?:\(s\))?",
        (
            "applicability",
            "definitions?",
            "reason",
            r"effective\s+date",
            ACTION_HEADING,
        ),
    )
    return [value] if value else []


def _tcds_numbers(text: str) -> list[str]:
    section = _section(
        text[:16000],
        r"TCDS\s+Number(?:\(s\))?",
        (
            r"foreign\s+ad",
            "revision",
            "correction",
            "supersedure",
            r"ata\s+\d{2}",
            "manufacturer",
            "applicability",
        ),
    )
    source = section or text[:16000]
    values: list[str] = []
    for match in re.finditer(
        r"\bEASA\s*\.?\s*A\s*\.\s*\d{3}\b", source, re.IGNORECASE
    ):
        value = re.sub(r"\s+", " ", match.group(0)).strip()
        value = re.sub(r"EASA\s*\.\s*A", "EASA.A", value, flags=re.IGNORECASE)
        if value not in values:
            values.append(value)
    return values


def _foreign_ad(text: str) -> str | None:
    return _section(
        text[:16000],
        r"Foreign\s+AD",
        (
            "revision",
            "correction",
            "cancellation",
            "supersedure",
            r"ata\s+\d{2}",
            "manufacturer",
            "applicability",
        ),
    )


def _revision_statement(text: str) -> str | None:
    return _section(
        text[:18000],
        r"Revision",
        (
            "correction",
            "supersedure",
            r"ata\s+\d{2}",
            "manufacturer",
            "applicability",
        ),
    )


def _correction_statement(text: str) -> str | None:
    match = re.search(
        r"\[(?:Corrected|Correction)\s*:\s*[^\]]+\]",
        text[:12000],
        re.IGNORECASE,
    )
    return compact(match.group(0)) if match else None


def _cancellation_statement(text: str) -> str | None:
    value = _section(
        text[:18000],
        r"Cancellation",
        (r"ata\s+\d{2}", "manufacturer", "applicability", "definitions?", "reason"),
    )
    if value:
        return value
    match = re.search(
        r"(?:^|\n)\s*Cancellation[ \t]+(This\s+Notice.*?)"
        r"(?=\n\s*ATA\s+\d{2}|\Z)",
        text[:18000],
        re.IGNORECASE | re.DOTALL,
    )
    return compact(match.group(1)) if match else None


def _cancellation_notice_number(text: str) -> str | None:
    match = re.search(
        r"\b((?:19|20)\d{2}\s*[-–—]\s*\d{4}(?:\s*R\d+)?\s*-\s*CN)\b",
        text[:1800],
        re.IGNORECASE,
    )
    if not match:
        return None
    value = re.sub(r"\s+", "", match.group(1)).upper()
    return value.replace("–", "-").replace("—", "-")


def _effective_date_statement(text: str) -> str | None:
    return _section(
        text[:16000],
        r"Effective\s+Date",
        (
            r"TCDS\s+Number(?:\(s\))?",
            r"Foreign\s+AD",
            "revision",
            "supersedure",
            r"ata\s+\d{2}",
        ),
    )


def _supersedure(text: str, current_ad: str) -> dict[str, Any] | None:
    statement = _section(
        text[:18000],
        r"(?:Revision\s*/\s*)?Supersedure",
        (r"ata\s+\d{2}", "manufacturer", "applicability", "definitions?", "reason"),
    )
    if not statement:
        return None
    numbers: list[str] = []
    for match in AD_PATTERN.finditer(statement):
        value = match.group(1).upper()
        if value != current_ad and value not in numbers:
            numbers.append(value)
    return compact({"statement": statement, "superseded_ad_numbers": numbers})


def _action_section(text: str) -> str | None:
    start = re.search(
        r"(?:^|\n)\s*Required\s+Action(?:\(s\))?\s+and\s+Compliance\s+Time(?:\(s\))?\s*:\s*",
        text,
        re.IGNORECASE,
    )
    if not start:
        start = re.search(
            r"(?:^|\n)\s*Required\s+Action(?:\(s\))?\s*:\s*",
            text,
            re.IGNORECASE,
        )
    if not start:
        start = re.search(
            r"(?:^|\n)\s*Compliance\s*:\s*", text, re.IGNORECASE
        )
    if not start:
        return None
    remainder = text[start.end() :]
    end = re.search(
        r"(?:^|\n)\s*(?:Ref\.?\s+Publications?|Referenced\s+Publications?|Remarks?|Contacts?)\s*:",
        remainder,
        re.IGNORECASE,
    )
    return compact(remainder[: end.start()] if end else remainder)


def _reference_section(text: str) -> str | None:
    return _section(
        text,
        r"(?:Ref\.?\s+Publications?|Referenced\s+Publications?)",
        ("remarks?", "contacts?", "appendix", "annex"),
    )


def _references(text: str, section: str | None = None) -> list[dict[str, str]]:
    section = section or _reference_section(text)
    source = section or text
    values: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in SB_PATTERN.finditer(source):
        number = re.sub(r"\s+", "", match.group(1)).upper()
        if number in seen:
            continue
        seen.add(number)
        prefix = source[max(0, match.start() - 80) : match.start()].casefold()
        publication_type = (
            "alert_service_bulletin" if "alert" in prefix else "service_bulletin"
        )
        values.append(
            {"type": publication_type, "issuer": "Airbus", "number": number}
        )
    if section and not values:
        values.append({"title": section})
    return values


def _reason_section(text: str) -> str | None:
    return _section(
        text,
        r"Reas\w*n",
        (r"effective\s+date", ACTION_HEADING, "compliance"),
    )


def _remarks_section(text: str) -> str | None:
    return _section(
        text,
        r"Remarks?",
        (
            "contacts",
            r"appendix(?:\s+[A-Z0-9]+)?",
            r"annex(?:\s+[A-Z0-9]+)?",
            r"attachment(?:\s+[A-Z0-9]+)?",
        ),
    )


def extract_local_record(
    row: dict[str, Any], schema: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract and validate one section-complete record without a model call."""
    raw_text = str(row["text"])
    header_match = re.search(
        r"(?:EASA\s+)?AD\s+N(?:o|r)\.?\s*:?\s*((?:19|20)\d{2}\s*[-–—]\s*\d{4}"
        r"(?:\s*-?\s*R\d+)?)",
        raw_text[:8000],
        re.IGNORECASE,
    )
    if not header_match:
        raise ValueError("AD number not found in document text")
    ad_number = re.sub(r"\s+", "", header_match.group(1)).upper()
    ad_number = re.sub(r"[-–—]R", "R", ad_number)
    ad_number = ad_number.replace("–", "-").replace("—", "-")
    manifest_ad = str(row.get("ad_number") or "").strip().upper()
    if manifest_ad and manifest_ad != ad_number:
        raise ValueError(
            f"PDF AD number {ad_number} disagrees with manifest {manifest_ad}"
        )

    text = _clean_layout_text(raw_text)
    holder, type_designation_text = _two_column_values(text)
    revision = re.search(r"R\d+$", ad_number)
    notice_number = _cancellation_notice_number(text)
    cancellation_notice = bool(notice_number) or bool(
        re.search(
            r"(?:EASA\s+(?:AD\s+)?Cancellation\s+Notice\s+No|"
            r"Airworthiness\s+Directive\s+Cancellation\s+Notice)",
            text[:1800],
            re.IGNORECASE,
        )
    )
    identity = {
        "ad_number": ad_number,
        "authority": "EASA" if re.search(r"\bEASA\b", raw_text[:4000]) else None,
        "document_type": (
            "Airworthiness Directive Cancellation Notice"
            if cancellation_notice
            else "Airworthiness Directive"
            if re.search(
                r"\bAirworthiness\s+Directive\b", text[:4000], re.IGNORECASE
            )
            else None
        ),
        "notice_number": notice_number,
        "revision": revision.group(0) if revision else None,
        "emergency": True if bool(row.get("is_emergency", False)) else None,
        "correction_date": _parse_date(row.get("correction_date")),
        "correction_statement": _correction_statement(text),
        "cancellation_statement": _cancellation_statement(text),
        "design_approval_holder": holder,
        "revision_statement": _revision_statement(text),
    }

    # Printed source wording is authoritative; manifest metadata is fallback only.
    issue_date = _printed_date(text, r"Issued|Issue\s+Date") or _parse_date(
        row.get("issue_date")
    )
    effective_date = _printed_date(text, r"Effective\s+Date")
    ata_chapters = _ata(text)
    publication = {
        "subject": ata_chapters[0].get("title") if ata_chapters else None,
        "issue_date": issue_date,
        "effective_date": effective_date,
        "effective_date_statement": _effective_date_statement(text),
        "ata_chapters": ata_chapters,
        "manufacturers": _manufacturer(text),
        "type_model_designations": _models(type_designation_text),
        "type_model_designation_text": type_designation_text,
        "tcds_numbers": _tcds_numbers(text),
        "foreign_ad": _foreign_ad(text),
    }

    applicability_text = _section(
        text,
        r"Applic+ability",
        (
            "definitions?",
            r"reas\w*n",
            r"effective\s+date",
            ACTION_HEADING,
            "compliance",
        ),
    )
    applicability_models = _models(applicability_text)
    applicability = []
    if applicability_text:
        applicability.append(
            {
                "text": applicability_text,
                "aircraft_families": _families(applicability_models),
                "models": applicability_models,
            }
        )

    action_text = _action_section(text)
    required_actions = [{"action": action_text}] if action_text else []
    reference_text = _reference_section(text)
    definitions_text = _section(
        text,
        r"Definitions?",
        (r"reas\w*n", r"effective\s+date", ACTION_HEADING, "compliance"),
    )
    reason_text = _reason_section(text)
    remarks_text = _remarks_section(text)

    record = compact(
        {
            "ad_identity": identity,
            "publication": publication,
            "applicability": applicability,
            "definitions": {"text": definitions_text} if definitions_text else None,
            "reason": {"text": reason_text} if reason_text else None,
            "required_actions": required_actions,
            "referenced_publications": _references(text, reference_text),
            "referenced_publications_text": (
                {"text": reference_text} if reference_text else None
            ),
            "supersedure": _supersedure(text, ad_number),
            "remarks": {"text": remarks_text} if remarks_text else None,
        }
    )
    errors = list(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(record)
    )
    if errors:
        raise ValueError("; ".join(error.message for error in errors[:5]))
    return record, {
        "attempts": 1,
        "parser_version": PARSER_VERSION,
        "method": "deterministic_local",
        "usage": {},
        "request_id": None,
    }
