#!/usr/bin/env python3
"""Deterministic, content-only extraction for EASA AD records.

The parser structures stable header fields and preserves difficult sections as
raw source wording. Layout-only page furniture is removed before section
segmentation; detailed compliance semantics remain intentionally unnormalized.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


PARSER_VERSION = "content-local-v2.1.5"

DATE_FORMATS = (
    "%d %B %Y",
    "%d %b %Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%Y-%m-%d",
)

# \s is intentional here: older EASA Form 110 PDFs often extract this heading
# over three separate lines (Required Action(s) / and Compliance / Time(s):).
ACTION_HEADING = (
    r"required\s+action(?:s|\(s\))?"
    r"(?:\s+and\s+compliance\s+time(?:s|\(s\))?)?"
)

SECTION_ENDINGS = (
    "definitions?",
    r"reas\w*n",
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
    r"\b(?:A300(?:[BCF]\d)?(?:-\d{2,4}[A-Z]*)?|A310(?:-\d{2,4}[A-Z]*)?|"
    r"A(?:318|319|320|321|330|340|350|380)(?:-\d{2,4}[A-Z]*)?)\b",
    re.IGNORECASE,
)

AD_PATTERN = re.compile(r"\b((?:19|20)\d{2}-\d{4}(?:R\d+)?)\b", re.IGNORECASE)

HOLDER_LABEL = (
    r"(?:(?:Type|Design|Design\s+Change)\s+Approval\s+Holder|"
    r"Design\s+Organisation\s+Approval\s+Holder)(?:[’']s)?\s+Name"
)
MODEL_LABEL = r"Type/Model\s+designation(?:\(s\))?"

_PAGE_LINE_PATTERNS = (
    re.compile(r"^\s*\[PAGE\s+\d+\]\s*$", re.IGNORECASE),
    re.compile(r"^\s*Page\s+\d+\s*(?:of|/)\s*\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*EASA\s+Form\s+\d+\s+Page\s+\d+\s*/\s*\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*TE\.CAP\.\d+(?:-\d+)?\b.*$", re.IGNORECASE),
    re.compile(r"^\s*©\s*European\s+Union\s+Aviation\s+Safety\s+Agency\b.*$", re.IGNORECASE),
    re.compile(r"^\s*Proprietary\s+document\.\s*Copies\s+are\s+not\s+controlled\..*$", re.IGNORECASE),
    re.compile(r"^\s*An\s+agency\s+of\s+the\s+European\s+Union\s*$", re.IGNORECASE),
    re.compile(r"^\s*ISO9001\s+Certified\.?\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:SUPERSEDED|CANCELLED|CANCELED)\s*$"),
)

_REPEATED_AD_HEADER = re.compile(
    r"^\s*(?:(?:SUPERSEDED|CANCELLED|CANCELED)\s*[.]?\s*)?"
    r"EASA\s+AD\s+No\.?\s*:?[ \t]*(?:19|20)\d{2}-\d{4}(?:R\d+)?\s*$",
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
        return [item for raw in value if (item := compact(raw)) not in (None, {}, [])]
    if isinstance(value, str):
        value = re.sub(r"\s+", " ", value).strip(" \t\r\n:;,")
        return value or None
    return value


def _clean_layout_text(text: str) -> str:
    """Remove repeated EASA page furniture without rewriting AD prose."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove headers/page counters even when a PDF extractor inserts them in the
    # middle of a semantic line rather than on their own line.
    inline_patterns = (
        r"(?i)(?:SUPERSEDED|CANCELLED|CANCELED)?\s*EASA\s+AD\s+No\.?\s*:?[ \t]*(?:19|20)\d{2}-\d{4}(?:R\d+)?",
        r"(?i)EASA\s+Form\s+\d+\s+Page\s+\d+\s*/\s*\d+",
        r"(?i)\bPage\s+\d+\s*(?:of|/)\s*\d+\b",
        r"(?i)TE\.CAP\.\d+(?:-\d+)?\s+©\s*European\s+Union\s+Aviation\s+Safety\s+Agency[^\n]*",
        r"(?i)©\s*European\s+Union\s+Aviation\s+Safety\s+Agency\.\s*All\s+rights\s+reserved\.?[^\n]*",
        r"(?i)Proprietary\s+document\.\s*Copies\s+are\s+not\s+controlled\.[^\n]*",
        r"(?i)An\s+agency\s+of\s+the\s+European\s+Union",
    )
    for pattern in inline_patterns:
        text = re.sub(pattern, "\n", text)

    # Watermarks are uppercase in extracted text. Keep ordinary regulatory prose
    # such as "which is superseded" intact.
    text = re.sub(r"\b(?:SUPERSEDED|CANCELLED|CANCELED)\b", "\n", text)

    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue
        if _REPEATED_AD_HEADER.match(line):
            continue
        if any(pattern.match(line) for pattern in _PAGE_LINE_PATTERNS):
            continue
        line = re.sub(r"\s*TE\.CAP\.\d+(?:-\d+)?\b.*$", "", line, flags=re.IGNORECASE).strip()
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
        rf"(?:{labels})\s*:\s*(?:Revision\s+\d+\s*:\s*)?([0-3]?\d\s+[A-Za-z]+\s+(?:19|20)\d{{2}})",
        text[:16000],
        re.IGNORECASE,
    )
    if not match and labels.casefold().startswith("issued"):
        # Legacy Form 110 used "Date:" rather than "Issued:".
        match = re.search(
            r"(?:^|\n)\s*Date\s*:\s*([0-3]?\d\s+[A-Za-z]+\s+(?:19|20)\d{2})",
            text[:8000],
            re.IGNORECASE,
        )
    return _parse_date(match.group(1)) if match else None


def _section(text: str, heading: str, endings: tuple[str, ...] = SECTION_ENDINGS) -> str | None:
    """Extract one labelled section while tolerating wrapped PDF headings."""
    end_pattern = "|".join(endings)
    match = re.search(
        rf"(?:^|\n)\s*(?:{heading})\s*:?[ \t]*(?:\n[ \t]*)?(.*?)"
        rf"(?=\n\s*(?:{end_pattern})\s*(?::[ \t]*|\n|$)|\Z)",
        text,
        re.IGNORECASE | re.DOTALL | re.MULTILINE,
    )
    return compact(match.group(1)) if match else None


def _header_field(text: str, heading: str, endings: tuple[str, ...]) -> str | None:
    return _section(text[:18000], heading, endings)


def _looks_like_holder(value: str | None) -> bool:
    if not value:
        return False
    normalized = re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
    if not normalized:
        return False
    bad_prefixes = ("type model", "type designation", "model designation", "applicability")
    if normalized.startswith(bad_prefixes):
        return False
    if len(normalized) > 180 or " reason " in f" {normalized} ":
        return False
    return True


def _split_holder_model_line(line: str) -> tuple[str | None, str | None]:
    """Split a collapsed two-column value line at the first aircraft model token."""
    model_match = MODEL_PATTERN.search(line)
    if not model_match:
        return compact(line), None
    holder = compact(line[: model_match.start()])
    model = compact(line[model_match.start() :])
    return holder, model


def _two_column_values(text: str) -> tuple[str | None, str | None]:
    """Read holder/model values from modern two-column or sequential headers."""
    lines = text[:12000].splitlines()
    holder_pattern = re.compile(rf"{HOLDER_LABEL}\s*:", re.IGNORECASE)
    model_pattern = re.compile(rf"{MODEL_LABEL}\s*:", re.IGNORECASE)

    for index, line in enumerate(lines):
        holder_match = holder_pattern.search(line)
        if not holder_match:
            continue
        model_match = model_pattern.search(line)
        if model_match:
            holder = line[holder_match.end() : model_match.start()].strip()
            model_value = line[model_match.end() :].strip()
            for candidate in lines[index + 1 : index + 6]:
                candidate = candidate.strip()
                if not candidate:
                    continue
                columns = re.split(r"\s{2,}", candidate, maxsplit=1)
                if len(columns) == 2:
                    holder = holder or columns[0]
                    model_value = model_value or columns[1]
                elif not holder or not model_value:
                    split_holder, split_model = _split_holder_model_line(candidate)
                    holder = holder or split_holder
                    model_value = model_value or split_model
                break
            holder = compact(holder)
            model_value = compact(model_value)
            return (holder if _looks_like_holder(holder) else None), model_value
        break

    holder = _header_field(
        text,
        HOLDER_LABEL,
        (MODEL_LABEL, r"Effective\s+Date", r"TCDS\s+Number", r"Foreign\s+AD"),
    )
    model_value = _header_field(
        text,
        MODEL_LABEL,
        (r"Effective\s+Date", r"TCDS\s+Number", r"Foreign\s+AD", "revision", "supersedure", r"ATA\s+\d{2}"),
    )
    return (holder if _looks_like_holder(holder) else None), model_value


def _models(text: str | None) -> list[str]:
    if not text:
        return []
    values: list[str] = []
    seen: set[str] = set()
    for match in MODEL_PATTERN.finditer(text):
        following = text[match.end() : match.end() + 10]
        # Do not misread a publication identifier such as A350-52-P012 as model A350-52.
        if re.match(r"\s*-[A-Z0-9]", following, re.IGNORECASE):
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


def _subject_and_ata(text: str) -> tuple[str | None, list[dict[str, str]]]:
    """Extract the complete subject around ATA, including continuation lines."""
    header = text[:20000]
    manufacturer_match = re.search(r"(?:^|\n)\s*Manufacturer(?:\(s\))?\s*:", header, re.IGNORECASE)
    end = manufacturer_match.start() if manufacturer_match else len(header)
    before_manufacturer = header[:end]

    ata_matches = list(re.finditer(r"\bATA\s+(\d{2}(?:\s*(?:,|/|&|and)\s*\d{2})*)\b", before_manufacturer, re.IGNORECASE))
    if not ata_matches:
        return None, []
    ata_match = ata_matches[-1]
    codes = re.findall(r"\d{2}", ata_match.group(1))

    line_start = before_manufacturer.rfind("\n", 0, ata_match.start()) + 1
    line_end = before_manufacturer.find("\n", ata_match.end())
    if line_end < 0:
        line_end = len(before_manufacturer)
    ata_line = before_manufacturer[line_start:line_end].strip()
    after = ata_line[ata_match.end() - line_start :].strip(" -–—:")
    before = ata_line[: ata_match.start() - line_start].strip(" -–—:")

    trailing = [
        candidate.strip()
        for candidate in before_manufacturer[line_end + 1 :].splitlines()
        if candidate.strip()
    ]

    # Legacy forms place the complete subject in one or two lines immediately before ATA.
    preceding: list[str] = []
    if not before:
        prior_lines = before_manufacturer[:line_start].splitlines()
        for candidate in reversed(prior_lines[-4:]):
            candidate = candidate.strip()
            if not candidate:
                if preceding:
                    break
                continue
            if re.match(
                r"(?:Foreign\s+AD|Revision|Supersedure|Cancellation|TCDS\s+Number|Effective\s+Date)\s*:",
                candidate,
                re.IGNORECASE,
            ):
                break
            preceding.append(candidate)
        preceding.reverse()

    if before:
        subject_parts = [before, after, *trailing]
    elif after and len(after.split()) >= 2:
        subject_parts = [after, *trailing]
    else:
        subject_parts = [*preceding, after, *trailing]
    subject = compact(" ".join(part for part in subject_parts if part))

    chapters = [compact({"code": code, "title": subject}) for code in codes]
    return subject, chapters


def _manufacturer(text: str) -> list[str]:
    value = _section(
        text,
        r"Manufacturer(?:\(s\))?",
        ("applicability", "definitions?", r"reas\w*n", r"effective\s+date", ACTION_HEADING),
    )
    if value:
        # Stop old-format field leakage if Applicability ended up on the same physical line.
        value = re.split(r"\bApplicability\s*:", value, maxsplit=1, flags=re.IGNORECASE)[0]
        value = compact(value)
    return [value] if value else []


def _holder_fallback(holder: str | None, manufacturers: list[str], text: str) -> str | None:
    if _looks_like_holder(holder):
        return holder
    # Legacy Airbus ADs often predate the DAH-name header and identify Airbus only
    # through Manufacturer(s). Do not use this fallback for STC/modification ADs.
    if re.search(r"(?:^|\n)\s*(?:Modification|Design\s+Change\s+Description)(?:\(s\))?\s*:", text[:16000], re.IGNORECASE):
        return None
    if manufacturers:
        candidate = manufacturers[0]
        if re.match(r"^Airbus\b", candidate, re.IGNORECASE):
            return candidate
    return None


def _tcds_numbers(text: str) -> list[str]:
    section = _section(
        text[:16000],
        r"TCDS\s+Number(?:\(s\))?",
        (r"foreign\s+ad", "revision", "correction", "supersedure", r"ata\s+\d{2}", "manufacturer", "applicability"),
    )
    source = section or text[:16000]
    values: list[str] = []
    patterns = (
        re.compile(r"\bEASA\s*\.?\s*A\s*\.\s*\d{3}\b", re.IGNORECASE),
        re.compile(r"\bFrance\s*(?:N[°ºo]\.?|No\.?)\s*\d+\b", re.IGNORECASE),
    )
    for pattern in patterns:
        for match in pattern.finditer(source):
            value = re.sub(r"\s+", " ", match.group(0)).strip()
            value = re.sub(r"EASA\s*\.\s*A", "EASA.A", value, flags=re.IGNORECASE)
            if value not in values:
                values.append(value)
    return values


def _foreign_ad(text: str) -> str | None:
    return _section(text[:16000], r"Foreign\s+AD", ("revision", "correction", "cancellation", "supersedure", r"ata\s+\d{2}", "manufacturer", "applicability"))


def _revision_statement(text: str) -> str | None:
    return _section(text[:18000], r"Revision", ("correction", "supersedure", r"ata\s+\d{2}", "manufacturer", "applicability"))


def _correction_statement(text: str) -> str | None:
    match = re.search(r"\[(?:Corrected|Correction)\s*:\s*[^\]]+\]", text[:12000], re.IGNORECASE)
    return compact(match.group(0)) if match else None


def _cancellation_statement(text: str) -> str | None:
    value = _section(text[:18000], r"Cancellation", (r"ata\s+\d{2}", "manufacturer", "applicability", "definitions?", r"reas\w*n"))
    if value:
        return value
    match = re.search(r"(?:^|\n)\s*Cancellation[ \t]+(This\s+Notice.*?)(?=\n\s*ATA\s+\d{2}|\Z)", text[:18000], re.IGNORECASE | re.DOTALL)
    return compact(match.group(1)) if match else None


def _cancellation_notice_number(text: str) -> str | None:
    match = re.search(r"\b((?:19|20)\d{2}\s*[-–—]\s*\d{4}(?:\s*R\d+)?\s*-\s*CN)\b", text[:1800], re.IGNORECASE)
    if not match:
        return None
    return re.sub(r"\s+", "", match.group(1)).upper().replace("–", "-").replace("—", "-")


def _effective_date_statement(text: str) -> str | None:
    return _section(text[:16000], r"Effective\s+Date", (r"TCDS\s+Number(?:\(s\))?", r"Foreign\s+AD", "revision", "supersedure", r"ata\s+\d{2}"))


def _supersedure(text: str, current_ad: str) -> dict[str, Any] | None:
    statement = _section(text[:18000], r"(?:Revision\s*/\s*)?Supersedure", (r"ata\s+\d{2}", "manufacturer", "applicability", "definitions?", r"reas\w*n"))
    numbers: list[str] = []
    if statement:
        for match in AD_PATTERN.finditer(statement):
            value = match.group(1).upper()
            if value != current_ad and value not in numbers:
                numbers.append(value)
        return compact({"statement": statement, "superseded_ad_numbers": numbers})

    revision = _revision_statement(text)
    if revision:
        direct = re.search(
            r"original\s+issue\s+of\s+this\s+AD\s+superseded\s+(.*?)(?=\.|$)",
            revision,
            re.IGNORECASE | re.DOTALL,
        )
        if direct:
            for match in AD_PATTERN.finditer(direct.group(1)):
                value = match.group(1).upper()
                if value != current_ad and value not in numbers:
                    numbers.append(value)
            if numbers:
                return {"statement": compact(direct.group(0)), "superseded_ad_numbers": numbers}
    return None


def _action_section(text: str) -> str | None:
    patterns = (
        rf"(?:^|\n)\s*{ACTION_HEADING}\s*:?[ \t]*(?:\n[ \t]*)?",
        r"(?:^|\n)\s*Compliance\s*:?[ \t]*(?:\n[ \t]*)?",
    )
    start = None
    for pattern in patterns:
        start = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if start:
            break
    if not start:
        return None
    remainder = text[start.end() :]
    end = re.search(
        r"(?:^|\n)\s*(?:Ref\.?\s+Publications?|Referenced\s+Publications?|Remarks?|Contacts?)\s*:?[ \t]*(?:\n|$)",
        remainder,
        re.IGNORECASE | re.MULTILINE,
    )
    return compact(remainder[: end.start()] if end else remainder)


def _reference_section(text: str) -> str | None:
    return _section(text, r"(?:Ref\.?\s+Publications?|Referenced\s+Publications?)", ("remarks?", "contacts?", "appendix", "annex"))


def _reference_type(context: str) -> str | None:
    value = context.casefold()
    if "alert service bulletin" in value:
        return "alert_service_bulletin"
    if "service bulletin" in value or re.search(r"\bsb\b", value):
        return "service_bulletin"
    if "alert operator transmission" in value or re.search(r"\baot\b", value):
        return "alert_operator_transmission"
    if re.search(r"\boit\b", value):
        return "operator_information_telex"
    if re.search(r"\bfot\b", value):
        return "flight_operations_transmission"
    if "mmel" in value:
        return "mmel"
    if "amm" in value:
        return "amm"
    if "cmm" in value:
        return "cmm"
    if "als" in value:
        return "als"
    return None


def _reference_candidates(section: str) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    # Publication identifiers are intentionally extracted only from the printed
    # reference section. This keeps recall broad without mining part numbers from
    # compliance prose.
    token_re = re.compile(r"\b[A-Z0-9][A-Z0-9./()_-]{2,}[A-Z0-9)]\b", re.IGNORECASE)
    for line in section.splitlines():
        line = line.strip()
        if not line:
            continue
        context = line
        for match in token_re.finditer(line):
            token = match.group(0).strip(".,;:")
            compact_token = re.sub(r"\s+", "", token).upper()
            if not re.search(r"\d", compact_token):
                continue
            if re.fullmatch(r"(?:19|20)\d{2}", compact_token):
                continue
            if AD_PATTERN.fullmatch(compact_token):
                # EASA AD lifecycle numbers are handled by revision/supersedure,
                # not counted as referenced technical publications.
                continue
            if re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-](?:19|20)?\d{2}", compact_token):
                continue
            if re.fullmatch(r"R(?:EV)?\.?\d+", compact_token):
                continue
            if MODEL_PATTERN.fullmatch(compact_token):
                continue
            candidates.append((compact_token, context))

        normalized = re.sub(r"[^A-Za-z0-9/-]+", "", line).upper()
        phrase_patterns = (
            (r"(?:A300(?:-600)?|A310|A320|A330|A340|A350|A380)ALSPART\d+", "als"),
            (r"AMMTASK[A-Z0-9/-]+", "amm"),
            (r"APPLICABLEAIRBUSAMM", "amm"),
            (r"APPLICABLEAIRBUSMAINTENANCEDOCUMENTATION", "amm"),
            (r"A(?:318/A319/A320/A321|320|330|340|350|380)MMEL[A-Z0-9]*", "mmel"),
        )
        for pattern, _ in phrase_patterns:
            for match in re.finditer(pattern, normalized):
                candidates.append((match.group(0), context))
    return candidates


def _references(text: str, section: str | None = None) -> list[dict[str, str]]:
    section = section or _reference_section(text)
    if not section:
        return []
    values: list[dict[str, str]] = []
    seen: set[str] = set()
    for number, context in _reference_candidates(section):
        if number in seen:
            continue
        seen.add(number)
        entry: dict[str, str] = {"number": number}
        ptype = _reference_type(context)
        if ptype:
            entry["type"] = ptype
        if re.search(r"\bAirbus\b", context, re.IGNORECASE):
            entry["issuer"] = "Airbus"
        values.append(entry)
    if not values:
        values.append({"title": section})
    return values


def _reason_section(text: str) -> str | None:
    return _section(text, r"Reas\w*n", (r"effective\s+date", ACTION_HEADING, "compliance"))


def _remarks_section(text: str) -> str | None:
    return _section(text, r"Remarks?", ("contacts", r"appendix(?:\s+[A-Z0-9]+)?", r"annex(?:\s+[A-Z0-9]+)?", r"attachment(?:\s+[A-Z0-9]+)?"))


def extract_local_record(row: dict[str, Any], schema: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract and validate one section-complete record without a model call."""
    raw_text = str(row["text"])
    header_match = re.search(
        r"(?:EASA\s+)?AD\s+N(?:o|r)\.?\s*:?\s*((?:19|20)\d{2}\s*[-–—]\s*\d{4}(?:\s*-?\s*R\d+)?)",
        raw_text[:8000],
        re.IGNORECASE,
    )
    if not header_match:
        raise ValueError("AD number not found in document text")
    ad_number = re.sub(r"\s+", "", header_match.group(1)).upper()
    ad_number = re.sub(r"[-–—]R", "R", ad_number).replace("–", "-").replace("—", "-")
    manifest_ad = str(row.get("ad_number") or "").strip().upper()
    if manifest_ad and manifest_ad != ad_number:
        raise ValueError(f"PDF AD number {ad_number} disagrees with manifest {manifest_ad}")

    text = _clean_layout_text(raw_text)
    explicit_holder, type_designation_text = _two_column_values(text)
    manufacturers = _manufacturer(text)
    holder = _holder_fallback(explicit_holder, manufacturers, text)
    revision = re.search(r"R\d+$", ad_number)
    notice_number = _cancellation_notice_number(text)
    cancellation_notice = bool(notice_number) or bool(
        re.search(r"(?:EASA\s+(?:AD\s+)?Cancellation\s+Notice\s+No|Airworthiness\s+Directive\s+Cancellation\s+Notice)", text[:1800], re.IGNORECASE)
    )
    identity = {
        "ad_number": ad_number,
        "authority": "EASA" if re.search(r"\bEASA\b", raw_text[:4000]) else None,
        "document_type": "Airworthiness Directive Cancellation Notice" if cancellation_notice else "Airworthiness Directive" if re.search(r"\bAirworthiness\s+Directive\b", text[:4000], re.IGNORECASE) else None,
        "notice_number": notice_number,
        "revision": revision.group(0) if revision else None,
        "emergency": True if bool(row.get("is_emergency", False)) else None,
        "correction_date": _parse_date(row.get("correction_date")),
        "correction_statement": _correction_statement(text),
        "cancellation_statement": _cancellation_statement(text),
        "design_approval_holder": holder,
        "revision_statement": _revision_statement(text),
    }

    issue_date = _printed_date(text, r"Issued|Issue\s+Date") or _parse_date(row.get("issue_date"))
    effective_date = _printed_date(text, r"Effective\s+Date")
    subject, ata_chapters = _subject_and_ata(text)
    publication = {
        "subject": subject,
        "issue_date": issue_date,
        "effective_date": effective_date,
        "effective_date_statement": _effective_date_statement(text),
        "ata_chapters": ata_chapters,
        "manufacturers": manufacturers,
        "type_model_designations": _models(type_designation_text),
        "type_model_designation_text": type_designation_text,
        "tcds_numbers": _tcds_numbers(text),
        "foreign_ad": _foreign_ad(text),
    }

    applicability_text = _section(text, r"Applic+ability", ("definitions?", r"reas\w*n", r"effective\s+date", ACTION_HEADING, "compliance"))
    applicability_models = _models(applicability_text)
    applicability = []
    if applicability_text:
        applicability.append({"text": applicability_text, "aircraft_families": _families(applicability_models), "models": applicability_models})

    action_text = _action_section(text)
    reference_text = _reference_section(text)
    definitions_text = _section(text, r"Definitions?", (r"reas\w*n", r"effective\s+date", ACTION_HEADING, "compliance"))
    reason_text = _reason_section(text)
    remarks_text = _remarks_section(text)

    record = compact(
        {
            "ad_identity": identity,
            "publication": publication,
            "applicability": applicability,
            "definitions": {"text": definitions_text} if definitions_text else None,
            "reason": {"text": reason_text} if reason_text else None,
            "required_actions": [{"action": action_text}] if action_text else [],
            "referenced_publications": _references(text, reference_text),
            "referenced_publications_text": {"text": reference_text} if reference_text else None,
            "supersedure": _supersedure(text, ad_number),
            "remarks": {"text": remarks_text} if remarks_text else None,
        }
    )
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(record))
    if errors:
        raise ValueError("; ".join(error.message for error in errors[:5]))
    return record, {"attempts": 1, "parser_version": PARSER_VERSION, "method": "deterministic_local", "usage": {}, "request_id": None}
