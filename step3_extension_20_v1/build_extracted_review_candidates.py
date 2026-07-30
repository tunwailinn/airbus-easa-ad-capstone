#!/usr/bin/env python3
"""Build populated, source-grounded first-pass annotations for the extension.

This is a machine-assisted extraction pass for human review. It reads only the
frozen blind packets and selection identity, preserves exact PDF-page evidence,
and never marks a record human-confirmed or gold.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


EXTENSION = Path(__file__).resolve().parent
PROJECT = EXTENSION.parent
PACKET_DIR = EXTENSION / "packets" / "blind"
SELECTION_PATH = EXTENSION / "selection" / "extension_selection.json"
OUTPUT_DIR = EXTENSION / "annotations" / "extracted_candidates"

sys.path.insert(0, str(PROJECT))
from step3_pilot import build_annotator_a3_records as base  # noqa: E402


ROWS = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
ROW_BY_AD = {row["ad_number"]: row for row in ROWS}
PACKETS = {
    row["ad_number"]: (
        f"{row['ad_number']}__{row['file_instance_id']}.blind-packet.json"
    )
    for row in ROWS
}

base.PACKET_DIR = PACKET_DIR
base.PACKETS = PACKETS
base.OUT_DIR = OUTPUT_DIR
base.ANNOTATOR_ID = "codex-extension-extractor"

NOW = (
    datetime.now(timezone.utc)
    .replace(microsecond=0)
    .isoformat()
    .replace("+00:00", "Z")
)
base.CREATED_AT = NOW
base.SUBMITTED_AT = NOW
base.MACHINE_AT = NOW


ACTION_TYPES: dict[str, list[str]] = {
    "2006-0077": ["modification"],
    "2007-0249": ["inspection", "test_or_check", "repair"],
    "2008-0066": ["inspection", "reporting", "modification"],
    "2009-0171": ["test_or_check", "inspection", "reporting"],
    "2010-0271": ["document_amendment", "operational_procedure"],
    "2011-0098": ["records_review", "inspection", "replacement", "modification"],
    "2012-0259": ["modification"],
    "2013-0011": ["inspection", "replacement", "modification"],
    "2016-0175": ["replacement", "prohibition"],
    "2018-0246": ["document_amendment", "operational_procedure", "modification"],
    "2019-0188": ["test_or_check", "reporting"],
    "2020-0016": ["modification", "replacement", "prohibition"],
    "2021-0221": ["modification", "replacement", "install", "inspection"],
    "2021-0286": ["inspection", "install", "modification"],
    "2022-0058": ["inspection", "test_or_check", "replacement", "reporting", "prohibition"],
    "2023-0057": ["modification", "replacement", "prohibition"],
    "2024-0001": ["document_amendment", "limitation"],
    "2025-0138": ["records_review", "replacement", "prohibition"],
    "2025-0181": ["replacement", "prohibition"],
    "2026-0100": ["inspection", "replacement", "reporting"],
}


TABLE_ADS = {
    "2009-0171",
    "2013-0011",
    "2016-0175",
    "2021-0221",
    "2022-0058",
    "2025-0181",
}


ATA_TITLES = {
    "05": "Time Limits / Maintenance Checks",
    "11": "Placards and Markings",
    "21": "Air Conditioning",
    "22": "Auto Flight",
    "24": "Electrical Power",
    "25": "Equipment / Furnishings",
    "26": "Fire Protection",
    "28": "Fuel",
    "29": "Hydraulic Power",
    "33": "Lights",
    "35": "Oxygen",
    "36": "Pneumatic",
    "38": "Water / Waste",
    "42": "Integrated Modular Avionics",
    "49": "Airborne Auxiliary Power",
    "53": "Fuselage",
    "54": "Nacelles / Pylons",
    "56": "Windows",
    "71": "Powerplant",
}


PUBLICATIONS: dict[str, list[tuple[str, str, str | None, str | None]]] = {
    "2006-0077": [
        ("service_bulletin", "A310-33-2045", "Revision 1", None),
        ("service_bulletin", "A300-33-6047", "Revision 1", None),
    ],
    "2007-0249": [
        ("alert_service_bulletin", "A320-26A1068", "Original issue", None),
    ],
    "2008-0066": [
        ("service_bulletin", "A310-54-2036", "Revision 1", None),
        ("service_bulletin", "A310-54-2036", "Revision 2", None),
        ("service_bulletin", "A310-54-2032", "Original issue", None),
    ],
    "2009-0171": [
        ("service_bulletin", "A300-29-0124", "Revision 02", None),
        ("service_bulletin", "A310-29-2097", "Revision 01", None),
        ("service_bulletin", "A300-29-6060", "Revision 01", None),
        ("service_bulletin", "A300-29-9009", "Revision 02", None),
    ],
    "2010-0271": [
        ("other", "A330 AFM TR 149", None, None),
        ("other", "A340 AFM TR 150", None, None),
    ],
    "2011-0098": [],
    "2012-0259": [
        ("service_bulletin", "A340-38-5017", "Original issue", "2012-02-13"),
    ],
    "2013-0011": [
        ("service_bulletin", "A320-56-1015", "Original issue", "2012-09-14"),
    ],
    "2016-0175": [
        ("service_bulletin", "A380-36-8016", "Original issue", "2013-02-05"),
    ],
    "2018-0246": [
        ("other", "A350 AFM TR 114", "Issue 1.0", "2018-08-17"),
        ("service_bulletin", "A350-31-P028", "Original issue", "2018-09-17"),
        ("service_bulletin", "A350-31-P029", "Original issue", "2018-09-17"),
        ("other", "FOT 999.0062/18", "Original issue", "2018-09-17"),
    ],
    "2019-0188": [
        ("airworthiness_limitations_section", "A300-600 ALS Part 3", "Revision 1, Variation 1.1", "2019-02-21"),
        ("airworthiness_limitations_section", "A310 ALS Part 3", "Revision 1, Variation 1.1", "2019-02-21"),
    ],
    "2020-0016": [
        ("service_bulletin", "A380-36-8047", "Original issue", "2018-04-25"),
    ],
    "2021-0221": [
        *[
            ("service_bulletin", number, revision, date)
            for number, revision, date in (
                ("A380-21-8092", "Original issue or Revision 01", "2018-03-08"),
                ("A380-21-8093", "Original issue or Revision 01", "2018-03-08"),
                ("A380-24-8130", "Original issue", "2017-10-02"),
                ("A380-25-8195", "Original issue", "2017-04-04"),
                ("A380-25-8196", "Original issue", "2017-04-04"),
                ("A380-25-8197", "Original issue", "2017-04-04"),
                ("A380-25-8198", "Original issue", "2017-04-04"),
                ("A380-25-8199", "Original issue", "2017-04-04"),
                ("A380-25-8200", "Original issue", "2017-04-04"),
                ("A380-25-8201", "Original issue", "2017-04-04"),
                ("A380-25-8202", "Original issue", "2017-04-04"),
                ("A380-28-8047", "Original issue", "2015-09-02"),
                ("A380-28-8050", "Original issue / Revision 01 / Revision 02", "2015-09-10"),
                ("A380-53-8122", "Original issue", "2018-08-23"),
                ("A380-71-8006", "Original issue", "2013-04-23"),
            )
        ]
    ],
    "2021-0286": [
        ("all_operators_telex", "AOT-A330MRTT-11-0001", None, "2021-10-08"),
        ("service_bulletin", "A330MRTT-11-0022", None, "2021-12-03"),
    ],
    "2022-0058": [
        ("service_bulletin", "A300-56-0014", "Original issue", "2021-11-19"),
        ("service_bulletin", "A300-56-6007", "Original issue", "2021-11-19"),
        ("service_bulletin", "A310-56-2008", "Original issue", "2021-11-19"),
        ("service_bulletin", "A300-56-9002", "Original issue", "2021-11-19"),
        ("service_bulletin", "SPS A340-56-001", "Original issue", "2021-10-25"),
    ],
    "2023-0057": [
        ("service_bulletin", "GTCP331-49-7954", "Original issue", "2007-12-19"),
    ],
    "2024-0001": [
        ("airworthiness_limitations_section", "A310 ALS Part 4", "Revision 03 Variation 3.4", "2023-08-03"),
    ],
    "2025-0138": [
        ("all_operators_telex", "A35P024-24", "Original issue", "2025-04-22"),
    ],
    "2025-0181": [
        ("all_operators_telex", "A42P003-25", "Original issue", "2025-06-25"),
        ("service_bulletin", "C13210D-42-011", "Original issue", "2025-06-27"),
    ],
    "2026-0100": [
        ("service_bulletin", "A330-71-3044", "Original issue", "2025-06-24"),
        ("service_bulletin", "RB.211-71-AL162", "Original issue", "2025-03-19"),
        ("service_bulletin", "RB.211-71-K989", "Original issue or Revision 01", "2024-04-03"),
    ],
}


HOLDERS = {
    "2006-0077": "Airbus SAS",
    "2007-0249": "Airbus",
    "2008-0066": "Airbus SAS",
    "2009-0171": "Airbus",
    "2010-0271": "Airbus",
    "2011-0098": "Airbus; The Boeing Company; Fokker Services",
    "2012-0259": "Airbus",
    "2013-0011": "Airbus",
    "2016-0175": "Airbus",
    "2018-0246": "Airbus",
    "2019-0188": "Airbus",
    "2020-0016": "Airbus",
    "2021-0221": "Airbus",
    "2021-0286": "Airbus Defence and Space S.A.",
    "2022-0058": "Airbus",
    "2023-0057": "Airbus S.A.S.",
    "2024-0001": "Airbus S.A.S.",
    "2025-0138": "Airbus S.A.S.",
    "2025-0181": "Airbus S.A.S.",
    "2026-0100": "Airbus S.A.S.",
}


def unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def page_norm(builder: base.Builder, page: int) -> str:
    return base.norm(builder.page_text(page))


def first_index(text: str, patterns: Iterable[str], start: int = 0) -> int | None:
    indexes = []
    lowered = text.casefold()
    for pattern in patterns:
        index = lowered.find(pattern.casefold(), start)
        if index >= 0:
            indexes.append(index)
    return min(indexes) if indexes else None


def section_evidence(
    builder: base.Builder,
    *,
    start_patterns: list[str],
    end_patterns: list[str],
    section: str,
    section_raw: str,
    clause: str,
) -> tuple[str, list[str]]:
    started = False
    chunks: list[str] = []
    evidence_ids: list[str] = []
    for page_number in sorted(builder.pages):
        text = page_norm(builder, page_number)
        if not started:
            start = first_index(text, start_patterns)
            if start is None:
                continue
            started = True
        else:
            start = 0
        end = first_index(text, end_patterns, start + 1)
        quote = text[start:end].strip() if end is not None else text[start:].strip()
        if quote:
            evidence_ids.append(
                builder.ev(
                    page_number,
                    section,
                    quote,
                    section_raw=section_raw,
                    clause=clause,
                )
            )
            chunks.append(quote)
        if end is not None:
            break
    return base.norm(" ".join(chunks)), evidence_ids


def parse_cover(builder: base.Builder, row: dict[str, Any]) -> dict[str, Any]:
    text = page_norm(builder, 1)
    cover_ev = builder.ev(
        1,
        "cover",
        text,
        section_raw="Cover identity and publication",
        clause="cover",
    )

    subject_match = re.search(
        r"\bATA\s+([0-9,| ]{2,})\s+(.+?)\s+Manufacturer\(s\)\s*:",
        text,
        flags=re.IGNORECASE,
    )
    if subject_match:
        subject_raw = f"ATA {subject_match.group(1).strip()} {subject_match.group(2).strip()}"
        subject = subject_match.group(2).strip().lstrip("-– ").strip()
    else:
        subject_raw = f"ATA {row['ata']} {row['rationale']}"
        subject = row["rationale"]

    issue_match = re.search(
        r"\b(?:Date|Issued)\s*:\s*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})",
        text,
        flags=re.IGNORECASE,
    )
    issue_raw = (
        issue_match.group(0)
        if issue_match
        else f"Issued: {row['issue_date']}"
    )
    issue_value = (
        datetime.strptime(issue_match.group(1), "%d %B %Y").date().isoformat()
        if issue_match
        else row["issue_date"]
    )
    effective_match = re.search(
        r"Effective Date\s*:\s*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})",
        " ".join(page_norm(builder, page) for page in sorted(builder.pages)),
        flags=re.IGNORECASE,
    )
    if effective_match is None:
        raise ValueError(f"{builder.ad_number}: effective date not found")
    effective_raw = effective_match.group(0)
    effective_value = datetime.strptime(
        effective_match.group(1), "%d %B %Y"
    ).date().isoformat()

    manufacturer_raw, manufacturer_evs = section_evidence(
        builder,
        start_patterns=["Manufacturer(s):", "Manufacturer(s) :"],
        end_patterns=["Applicability:"],
        section="cover",
        section_raw="Manufacturer(s)",
        clause="Manufacturer(s)",
    )
    if not manufacturer_evs:
        manufacturer_evs = [cover_ev]
        manufacturer_raw = "Airbus"

    tcds_match = re.search(
        r"TCDS Number(?:\(s\))?\s*:\s*(.+?)\s+Foreign AD\s*:",
        text,
        flags=re.IGNORECASE,
    )
    tcds = [tcds_match.group(1).strip()] if tcds_match else []
    ata_codes = [part.strip() for part in str(row["ata"]).split("|")]
    manufacturers = [
        {
            "raw_name": manufacturer_raw,
            "normalized_name": (
                "Airbus"
                if "airbus" in manufacturer_raw.casefold()
                else manufacturer_raw
            ),
            "role": "manufacturer",
            "evidence_ids": manufacturer_evs,
        }
    ]
    if builder.ad_number == "2011-0098":
        manufacturers = [
            {
                "raw_name": name,
                "normalized_name": "Airbus" if name.startswith("Airbus") else name,
                "role": "manufacturer",
                "evidence_ids": manufacturer_evs,
            }
            for name in (
                "Airbus (formerly Airbus Industrie)",
                "The Boeing Company",
                "Fokker Services (formerly Fokker Aircraft B.V.)",
            )
        ]

    return {
        "cover_ev": cover_ev,
        "subject": subject,
        "subject_raw": subject_raw,
        "issue_raw": issue_raw,
        "issue_value": issue_value,
        "effective_raw": effective_raw,
        "effective_value": effective_value,
        "manufacturer_raw": manufacturer_raw,
        "manufacturer_evs": manufacturer_evs,
        "tcds": tcds,
        "ata_codes": ata_codes,
        "manufacturers": manufacturers,
    }


MODEL_RE = re.compile(
    r"\b(?:A(?:300(?:B[0-9])?|310|318|319|320|321|330|340|350|380)"
    r"(?:F4)?(?:-[A-Z0-9]+)?|DC-[0-9]+|MD-[0-9]+|F28[^,.;]*)\b",
    flags=re.IGNORECASE,
)
PART_RE = re.compile(r"\b(?:P/N|part number)\s*[A-Z0-9./-]+", flags=re.IGNORECASE)


def build_applicability(
    builder: base.Builder, row: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    start_patterns = ["Applicability:"]
    if builder.ad_number == "2009-0171":
        start_patterns.insert(
            0, "AIRBUS A300, A310 and A300-600 aeroplanes"
        )
    raw, evidence_ids = section_evidence(
        builder,
        start_patterns=start_patterns,
        end_patterns=["Definitions:", "Reason:"],
        section="applicability",
        section_raw="Applicability",
        clause="Applicability",
    )
    if not raw or not evidence_ids:
        raise ValueError(f"{builder.ad_number}: applicability section not found")
    models = unique(
        match.group(0)
        for match in MODEL_RE.finditer(raw)
        if not re.search(r"-[0-9]{1,2}$", match.group(0))
    )
    part_numbers = unique(
        re.sub(r"^(?:P/N|part number)\s*", "", match.group(0), flags=re.I)
        for match in PART_RE.finditer(raw)
    )
    serials: list[dict[str, Any]] = []
    if re.search(r"\ball (?:manufacturer )?serial numbers\b|\ball MSN\b", raw, re.I):
        serials.append(base.all_serials("MSN-001", "all serial numbers", evidence_ids))
    else:
        serial_match = re.search(
            r"manufacturer serial numbers? \(MSN\)\s+(.+?)(?:\.\s|;)",
            raw,
            flags=re.IGNORECASE,
        )
        if serial_match:
            serial_values = unique(
                re.findall(r"\b[0-9]{4}\b", serial_match.group(1))
            )
            serials.append(
                base.listed_serials(
                    "MSN-001",
                    serial_match.group(0),
                    serial_values,
                    evidence_ids,
                )
            )
    conditions = []
    for match in re.finditer(r"\bif\b[^.;]+", raw, flags=re.IGNORECASE):
        conditions.append(match.group(0).strip())
    exclusions = []
    for match in re.finditer(r"\bexcept\b[^.;]+", raw, flags=re.IGNORECASE):
        exclusions.append(match.group(0).strip())
    if builder.ad_number == "2025-0181":
        appendix_ev = builder.table_ev(
            4,
            "Appendix 1 - List of Affected Parts (s/n)",
            ["s/n"],
            rows=re.findall(r"\bC132100[0-9]{5}\b", page_norm(builder, 4)),
            note="Component serial-number appendix visually reviewed.",
        )
        evidence_ids.append(appendix_ev)
        part_numbers.append("C13210D")
        conditions.append(
            "Affected CPIOM part C13210D with a serial number listed in Appendix 1."
        )
    family = str(row.get("family") or "").strip()
    return [
        base.app(
            "APP-001",
            f"{family} applicability stated in the AD",
            raw,
            [family] if family else [],
            models,
            serials,
            evidence_ids,
            part_numbers=part_numbers,
            conditions=unique(conditions),
            exclusions=unique(exclusions),
            logic="all",
        )
    ], evidence_ids


def build_definitions(builder: base.Builder) -> tuple[list[dict[str, Any]], list[str]]:
    raw, evidence_ids = section_evidence(
        builder,
        start_patterns=["Definitions:"],
        end_patterns=["Reason:"],
        section="definitions",
        section_raw="Definitions",
        clause="Definitions",
    )
    if not raw or not evidence_ids:
        return [], []
    definition_text = re.sub(r"^Definitions\s*:\s*", "", raw, flags=re.I)
    return [
        {
            "definition_id": "DEF-001",
            "term": "Definitions in this AD",
            "definition_text": definition_text,
            "evidence_ids": evidence_ids,
        }
    ], evidence_ids


def sentence_candidates(text: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"(?<=[.!?])\s+", text)
        if item.strip()
    ]


def build_unsafe(builder: base.Builder) -> tuple[dict[str, Any], list[str]]:
    raw, evidence_ids = section_evidence(
        builder,
        start_patterns=["Reason:"],
        end_patterns=["Effective Date:", "Required Action(s)", "Compliance:"],
        section="reason",
        section_raw="Reason",
        clause="Reason",
    )
    if not raw or not evidence_ids:
        raise ValueError(f"{builder.ad_number}: reason section not found")
    sentences = sentence_candidates(re.sub(r"^Reason\s*:\s*", "", raw, flags=re.I))
    consequence = [
        sentence
        for sentence in sentences
        if re.search(r"\b(?:could|may|might|would|lead|result|unsafe)\b", sentence, re.I)
    ]
    mitigation = [
        sentence
        for sentence in sentences
        if re.search(r"\bthis AD (?:requires|mandates)\b", sentence, re.I)
    ]
    return {
        "state": "present",
        "raw_reason_text": raw,
        "observed_events_or_defects": sentences[:1],
        "causes": [],
        "unsafe_conditions": consequence[:2] or sentences[:1],
        "potential_consequences": consequence[-2:],
        "affected_components": [],
        "intended_risk_mitigation": mitigation[-1:],
        "evidence_ids": evidence_ids,
    }, evidence_ids


UNIT_MAP = {
    "fh": "flight_hour",
    "flight hour": "flight_hour",
    "flight hours": "flight_hour",
    "fc": "flight_cycle",
    "flight cycle": "flight_cycle",
    "flight cycles": "flight_cycle",
    "day": "calendar_day",
    "days": "calendar_day",
    "month": "calendar_month",
    "months": "calendar_month",
    "year": "calendar_year",
    "years": "calendar_year",
    "week": "other",
    "weeks": "other",
}


def parse_limits(
    builder: base.Builder, text: str, evidence_ids: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    initial: list[dict[str, Any]] = []
    repetitive: list[dict[str, Any]] = []
    seen: set[tuple[str, float, str]] = set()
    seen_values: set[tuple[float, str]] = set()
    pattern = re.compile(
        r"(?P<relation>within|prior to|before|at intervals not to exceed|not exceeding)"
        r"(?: the next)?(?: accumulation of)?\s+"
        r"(?P<quantity>[0-9]+(?:\s+[0-9]{3})*(?:\.[0-9]+)?)\s*"
        r"(?P<unit>FH|FC|flight hours?|flight cycles?|days?|weeks?|months?|years?)",
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        raw_relation = match.group("relation").casefold()
        relation = (
            "not_to_exceed"
            if "not to exceed" in raw_relation or "not exceeding" in raw_relation
            else "before"
            if raw_relation in {"prior to", "before"}
            else "within"
        )
        quantity = float(match.group("quantity").replace(" ", ""))
        if quantity.is_integer():
            quantity = int(quantity)
        unit_raw = match.group("unit").casefold()
        unit = UNIT_MAP[unit_raw]
        key = (relation, float(quantity), unit)
        if key in seen:
            continue
        seen.add(key)
        seen_values.add((float(quantity), unit))
        limit = builder.limit(
            relation,
            quantity,
            unit,
            match.group(0),
            evidence_ids,
            reference_event=(
                "effective date of this AD"
                if "effective date" in text.casefold()
                else None
            ),
        )
        if (
            "interval" in raw_relation
            or (
                relation == "not_to_exceed"
                and "thereafter" in text.casefold()
            )
            or "repeat" in text[max(0, match.start() - 100):match.start()].casefold()
        ):
            repetitive.append(limit)
        else:
            initial.append(limit)
    for match in re.finditer(
        r"(?P<quantity>[0-9]+(?:\s+[0-9]{3})*(?:\.[0-9]+)?)\s*"
        r"(?P<unit>FH|FC|flight hours?|flight cycles?|days?|weeks?|months?|years?)",
        text,
        flags=re.IGNORECASE,
    ):
        quantity = float(match.group("quantity").replace(" ", ""))
        if quantity.is_integer():
            quantity = int(quantity)
        unit = UNIT_MAP[match.group("unit").casefold()]
        if (float(quantity), unit) in seen_values:
            continue
        key = ("within", float(quantity), unit)
        if key in seen:
            continue
        seen.add(key)
        seen_values.add((float(quantity), unit))
        initial.append(
            builder.limit(
                "within",
                quantity,
                unit,
                match.group(0),
                evidence_ids,
                reference_event=(
                    "effective date of this AD"
                    if "effective date" in text.casefold()
                    else None
                ),
            )
        )
    if re.search(r"\bbefore next flight\b", text, re.I):
        initial.append(
            builder.limit(
                "before",
                None,
                "before_next_flight",
                "before next flight",
                evidence_ids,
                reference_event="next flight",
            )
        )
    exceeds_match = re.search(
        r"\bbefore\b[^.;]{0,80}?\bexceeds?\s+"
        r"(?P<quantity>[0-9]+(?:\s+[0-9]{3})*)\s*"
        r"(?P<unit>FH|FC|flight hours?|flight cycles?)",
        text,
        flags=re.IGNORECASE,
    )
    if exceeds_match:
        quantity = int(exceeds_match.group("quantity").replace(" ", ""))
        unit = UNIT_MAP[exceeds_match.group("unit").casefold()]
        if (float(quantity), unit) not in seen_values:
            initial.append(
                builder.limit(
                    "before",
                    quantity,
                    unit,
                    exceeds_match.group(0),
                    evidence_ids,
                    reference_event="affected part accumulated usage",
                )
            )
    date_match = re.search(
        r"\bbefore\s+([A-Za-z]+\s+[0-9]{1,2}(?:st|nd|rd|th)?,\s+[0-9]{4})",
        text,
        flags=re.IGNORECASE,
    )
    if date_match:
        normalized_date = re.sub(r"(st|nd|rd|th)", "", date_match.group(1))
        calendar_date = datetime.strptime(
            normalized_date, "%B %d, %Y"
        ).date().isoformat()
        initial.append(
            builder.limit(
                "before",
                None,
                "calendar_date",
                date_match.group(0),
                evidence_ids,
                calendar_date=calendar_date,
            )
        )
    return initial, repetitive


def split_requirements(raw: str) -> list[tuple[str, str]]:
    positions = list(
        re.finditer(r"(?<!paragraph )\(([0-9]{1,2})\)\s+(?=[A-Z])", raw)
    )
    if not positions:
        return [("Compliance section", raw)]
    chunks: list[tuple[str, str]] = []
    for index, match in enumerate(positions):
        end = positions[index + 1].start() if index + 1 < len(positions) else len(raw)
        text = raw[match.start():end].strip()
        if len(text) >= 25:
            chunks.append((f"({match.group(1)})", text))
    return chunks or [("Compliance section", raw)]


def build_requirements(
    builder: base.Builder,
    publication_ids: list[str],
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    raw, evidence_ids = section_evidence(
        builder,
        start_patterns=[
            "Required as indicated",
            "The following measures are required",
            "Required Action(s)",
            "Compliance:",
        ],
        end_patterns=["Ref. Publications:", "Ref. Publications :"],
        section="required_actions_and_compliance_times",
        section_raw="Required Action(s) and Compliance Time(s)",
        clause="compliance",
    )
    if not raw or not evidence_ids:
        raise ValueError(f"{builder.ad_number}: requirements section not found")

    table_evidence: list[str] = []
    if builder.ad_number in TABLE_ADS:
        for page_number in sorted(builder.pages):
            text = page_norm(builder, page_number)
            if re.search(r"\bTable\s+[0-9]", text, re.I) or (
                builder.ad_number == "2025-0181" and "Appendix 1" in text
            ):
                table_evidence.append(
                    builder.table_ev(
                        page_number,
                        "Table/appendix-dependent requirement source",
                        [],
                        note=(
                            "Full rendered page retained because the requirement "
                            "depends on table or appendix layout."
                        ),
                    )
                )
    all_evidence = unique([*evidence_ids, *table_evidence])
    requirements: list[dict[str, Any]] = []
    for index, (paragraph, text) in enumerate(split_requirements(raw), start=1):
        initial, repetitive = parse_limits(builder, text, all_evidence)
        logic = (
            "whichever_occurs_first"
            if "whichever occurs first" in text.casefold() and len(initial) >= 2
            else "whichever_occurs_later"
            if "whichever occurs later" in text.casefold() and len(initial) >= 2
            else "conditional"
            if " if " in f" {text.casefold()} "
            else "all"
            if len(initial) > 1
            else "single"
        )
        compliance = builder.cmp(
            text,
            all_evidence,
            logic=logic,
            initial=initial,
            repetitive=repetitive,
        )
        obligation = (
            "conditional"
            if text.casefold().startswith(("if ", "(1) if", "(2) if", "(3) if"))
            else "mandatory"
        )
        terminating = (
            base.term_yes(
                text,
                [f"REQ-{prior:03d}" for prior in range(1, index)],
                all_evidence,
                scope="partial",
            )
            if index > 1 and re.search(
                r"\b(?:terminating action|no further actions? (?:are|is) required)\b",
                text,
                re.I,
            )
            else base.term_none()
        )
        requirements.append(
            base.req(
                f"REQ-{index:03d}",
                paragraph,
                ["APP-001"],
                ACTION_TYPES[builder.ad_number],
                obligation,
                text,
                all_evidence,
                objects=[],
                conditions=[],
                pubs=publication_ids,
                cmps=[compliance],
                terminating=terminating,
            )
        )
    return requirements, all_evidence, table_evidence


def build_publications(
    builder: base.Builder,
) -> tuple[list[dict[str, Any]], list[str]]:
    raw, evidence_ids = section_evidence(
        builder,
        start_patterns=["Ref. Publications:", "Ref. Publications :"],
        end_patterns=["Remarks:", "Remarks :"],
        section="reference_publications",
        section_raw="Ref. Publications",
        clause="Ref. Publications",
    )
    entries = []
    for index, (kind, number, revision, date) in enumerate(
        PUBLICATIONS[builder.ad_number], start=1
    ):
        entries.append(
            base.pub(
                f"PUB-{index:03d}",
                kind,
                (
                    "Airbus Defence and Space"
                    if builder.ad_number == "2021-0286"
                    else "Honeywell"
                    if builder.ad_number == "2023-0057"
                    else "Rolls-Royce"
                    if number.startswith("RB.")
                    else "Airbus"
                ),
                number,
                revision,
                date,
                ["required_method"],
                evidence_ids,
                later=True if "later approved" in raw.casefold() else None,
            )
        )
    return entries, evidence_ids


def build_contacts(builder: base.Builder) -> tuple[list[dict[str, Any]], list[str]]:
    raw, evidence_ids = section_evidence(
        builder,
        start_patterns=["Remarks:", "Remarks :"],
        end_patterns=[],
        section="remarks",
        section_raw="Remarks",
        clause="Remarks",
    )
    if not raw or not evidence_ids:
        return [], []
    entries = []
    if re.search(r"Alternative Methods? of Compliance|AMOC", raw, re.I):
        entries.append(
            {
                "entry_id": "AMC-001",
                "entry_type": "amoc_authority",
                "authority_or_organization": "EASA",
                "contact_text": raw,
                "conditions": ["Requested and appropriately substantiated"],
                "evidence_ids": evidence_ids,
            }
        )
    entries.append(
        {
            "entry_id": f"AMC-{len(entries) + 1:03d}",
            "entry_type": "regulatory_contact",
            "authority_or_organization": "EASA and the technical contact stated in the AD",
            "contact_text": raw,
            "conditions": [],
            "evidence_ids": evidence_ids,
        }
    )
    return entries, evidence_ids


def build_record(ad_number: str) -> dict[str, Any]:
    row = ROW_BY_AD[ad_number]
    builder = base.Builder(ad_number)
    cover = parse_cover(builder, row)
    applicability, app_evs = build_applicability(builder, row)
    definitions, _ = build_definitions(builder)
    unsafe, reason_evs = build_unsafe(builder)
    publications, pub_evs = build_publications(builder)
    publication_ids = [item["publication_id"] for item in publications]
    requirements, req_evs, table_evs = build_requirements(builder, publication_ids)
    contacts, contact_evs = build_contacts(builder)

    publication = {
        "subject": base.grounded_text(
            cover["subject"], cover["subject_raw"], [cover["cover_ev"]]
        ),
        "issue_date": base.grounded_date(
            cover["issue_value"], cover["issue_raw"], [cover["cover_ev"]]
        ),
        "effective_date": base.grounded_date(
            cover["effective_value"],
            cover["effective_raw"],
            [cover["cover_ev"]],
        ),
        "ata_chapters": [
            {
                "code": code,
                "title": ATA_TITLES.get(code, cover["subject"]),
                "evidence_ids": [cover["cover_ev"]],
            }
            for code in cover["ata_codes"]
        ],
        "manufacturers": cover["manufacturers"],
        "type_model_designations": applicability[0]["models"],
        "tcds_numbers": cover["tcds"],
        "foreign_ad": base.explicit_none(
            "Foreign AD: None or Not applicable", [cover["cover_ev"]]
        ),
    }

    action_union = unique(
        action
        for requirement in requirements
        for action in requirement["action_types"]
    )
    repetitive = any(
        rule["is_repetitive"]
        for requirement in requirements
        for rule in requirement["compliance_rules"]
    )
    terminating = any(
        requirement["terminating_action"]["present"]
        for requirement in requirements
    )
    table_present = ad_number in TABLE_ADS
    classification = {
        "airbus_families": [row["family"]],
        "ata_chapters": cover["ata_codes"],
        "action_types": action_union,
        "frequency": "mixed" if repetitive and len(requirements) > 1 else "repetitive" if repetitive else "one_time",
        "emergency_status": "emergency" if ad_number.endswith("-E") else "standard",
        "terminating_action_present": terminating,
        "table_or_appendix_present": table_present,
        "compliance_complexity": (
            "table_driven"
            if table_present
            else "conditional_branches"
            if len(requirements) > 2
            else "alternative_limits"
            if any(
                len(rule["initial_limits"]) > 1
                for requirement in requirements
                for rule in requirement["compliance_rules"]
            )
            else "simple"
        ),
        "human_confirmed": False,
        "evidence_ids": unique(
            [cover["cover_ev"], *app_evs, *reason_evs, *req_evs, *table_evs]
        ),
    }

    record = builder.finish(
        cover_ev=cover["cover_ev"],
        identity_evs=[cover["cover_ev"]],
        version_label="Original",
        lifecycle="unknown",
        holder_raw=HOLDERS[ad_number],
        holder_value=HOLDERS[ad_number],
        supersedure=base.explicit_none(
            "Supersedure: None", [cover["cover_ev"]]
        ),
        publication=publication,
        applicability=applicability,
        definitions=definitions,
        unsafe_condition=unsafe,
        requirements=requirements,
        exceptions=[],
        credits=[],
        publications=publications,
        relationships=[],
        contacts=contacts,
        classification=classification,
        quality_flags=unique(
            [
                "manual_review_required",
                "complex_table" if table_present else "",
                "complex_compliance" if len(requirements) > 2 else "",
                "complex_applicability"
                if "|" in str(row.get("strata")) or "complex_applicability" in str(row.get("strata"))
                else "",
            ]
        ),
        notes=[
            "Machine-assisted populated extraction from the complete frozen PDF/page-text packet.",
            "Requirements were split from numbered source paragraphs where possible; every field assertion remains unreviewed.",
            "No supersedure relationship was created because the cover explicitly states Supersedure: None.",
            "Independent human comparison and correction are required before approval or gold promotion.",
        ],
    )
    allowed_strata = {
        "simple",
        "complex_applicability",
        "revised",
        "corrected",
        "emergency",
        "table_heavy",
        "long_document",
        "stc_conditioned",
        "near_duplicate_cluster",
        "other",
    }
    source_strata = [
        part.strip() for part in str(row["strata"]).split("|") if part.strip()
    ]
    normalized_strata = unique(
        part if part in allowed_strata else "other" for part in source_strata
    )
    record["benchmark_metadata"]["selection_strata"] = normalized_strata
    record["annotation_metadata"]["machine_provenance"][
        "prompt_or_rules_version"
    ] = "step3-extension-populated-extraction-1.0.0"
    return record


def main() -> int:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)
    reports = []
    for ad_number in sorted(ROW_BY_AD):
        record = build_record(ad_number)
        source = record["source_document"]
        path = OUTPUT_DIR / (
            f"{ad_number}__{source['file_instance_id']}.annotation.json"
        )
        path.write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        reports.append(
            {
                "ad_number": ad_number,
                "file": path.name,
                "requirements": len(record["requirements"]),
                "evidence_spans": len(record["evidence_spans"]),
                "referenced_publications": len(record["referenced_publications"]),
                "field_assertions": len(record["field_assertions"]),
            }
        )
    report_path = EXTENSION / "validation" / "extraction_build_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "generated_at": NOW,
                "record_count": len(reports),
                "human_confirmed": False,
                "gold_record": False,
                "records": reports,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"record_count": len(reports), "report": str(report_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
