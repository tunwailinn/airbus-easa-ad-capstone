#!/usr/bin/env python3
"""Generate a deliberately simple, leakage-safe regex baseline for the pilot.

The output is partial JSON. It uses only the frozen source identifier plus the
page text; it does not read Annotator A/B or gold annotations. Missing fields
are left missing and therefore count against the method during evaluation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


AD_RE = re.compile(r"\b(?:19|20)\d{2}-\d{4}(?:R[1-9]\d*)?(?:-E)?\b", re.I)
MODEL_RE = re.compile(
    r"\bA(?:300(?:F)?|310|318|319|320|321|330|340|350|380)"
    r"(?:-[A-Z0-9][A-Z0-9-]{0,12})?\b",
    re.I,
)
DATE_RE = r"([0-3]?\d\s+[A-Za-z]+\s+(?:19|20)\d{2})"
MONTHS = {
    name.casefold(): index
    for index, name in enumerate(
        (
            "January February March April May June July August September "
            "October November December"
        ).split(),
        1,
    )
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--selection",
        type=Path,
        default=Path("step3_pilot/selection/pilot_selection.json"),
    )
    parser.add_argument(
        "--page-text-dir",
        type=Path,
        default=Path("step3_pilot/page_text"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("step3_pilot/baselines/regex"),
    )
    return parser.parse_args()


def parse_date(raw: str | None) -> str | None:
    if not raw:
        return None
    match = re.fullmatch(r"\s*([0-3]?\d)\s+([A-Za-z]+)\s+((?:19|20)\d{2})\s*", raw)
    if not match:
        return None
    month = MONTHS.get(match.group(2).casefold())
    if not month:
        return None
    try:
        return datetime(int(match.group(3)), month, int(match.group(1))).date().isoformat()
    except ValueError:
        return None


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_date(text: str, label: str) -> str | None:
    match = re.search(rf"\b{label}\s*:\s*{DATE_RE}", text, re.I)
    return parse_date(match.group(1)) if match else None


def extract_between(text: str, start: str, ends: tuple[str, ...]) -> str | None:
    end_pattern = "|".join(re.escape(item) for item in ends)
    match = re.search(
        rf"\b{start}\s*:\s*(.+?)(?=\s+(?:{end_pattern})\s*:|$)",
        text,
        re.I,
    )
    return clean_text(match.group(1)) if match else None


def read_pages(path: Path) -> list[dict[str, Any]]:
    pages = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                pages.append(json.loads(line))
    return pages


def parse_ad_number(text: str) -> str | None:
    spaced = re.search(
        r"(?:EASA\s+)?AD\s+No\.?\s*:\s*"
        r"((?:19|20)\d{2}\s*-\s*\d{4}(?:\s*R[1-9]\d*)?(?:\s*-E)?)",
        text,
        re.I,
    )
    if spaced:
        return re.sub(r"\s+", "", spaced.group(1)).upper()
    patterns = (
        r"(?:EASA\s+)?AD\s+No\.?\s*:\s*(%s)" % AD_RE.pattern,
        r"AIRWORTHINESS\s+DIRECTIVE\s*(%s)" % AD_RE.pattern,
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).upper()
    match = AD_RE.search(text[:1800])
    return match.group(0).upper() if match else None


def identity_parts(ad_number: str | None) -> tuple[str | None, int | None, bool]:
    if not ad_number:
        return None, None, False
    match = re.fullmatch(
        r"((?:19|20)\d{2}-\d{4})(?:R([1-9]\d*))?(-E)?", ad_number, re.I
    )
    if not match:
        return None, None, False
    return match.group(1), int(match.group(2)) if match.group(2) else None, bool(match.group(3))


def manufacturer(text: str) -> tuple[str, str] | None:
    match = re.search(
        r"\bManufacturer(?:\(s\))?\s*:\s*"
        r"(Airbus(?:\s*,\s*formerly\s+Airbus\s+Industrie|\s+Industrie|\s+S\.A\.S\.)?)",
        text,
        re.I,
    )
    if not match:
        return None
    return clean_text(match.group(1)), "Airbus"


def explicit_supersedure(text: str, current_ad: str | None) -> tuple[str, str | None, list[dict[str, Any]]]:
    structured = re.search(r"\bSupersedure\s*:\s*(.{1,120}?)(?=\s+(?:ATA|Subject|Manufacturer|Applicability)\b|$)", text, re.I)
    relationships = []
    if structured:
        raw = clean_text(structured.group(1))
        if re.match(r"^(?:None|Not applicable)\b", raw, re.I):
            return "explicit_none", None, relationships
        targets = [item.upper() for item in AD_RE.findall(raw)]
        for target in targets:
            if target != current_ad:
                relationships.append(
                    {"relationship_type": "supersedes", "target_ad_number": target}
                )
        if relationships:
            return "present", raw, relationships
    sentence = re.search(
        r"\bThis\s+AD\s+supersedes\s+(?:EASA\s+AD\s+)?(%s)" % AD_RE.pattern,
        text,
        re.I,
    )
    if sentence:
        target = sentence.group(1).upper()
        return "present", target, [
            {"relationship_type": "supersedes", "target_ad_number": target}
        ]
    return "not_stated", None, relationships


def action_types(text: str) -> list[str]:
    rules = {
        "inspection": r"\binspect(?:ion|ions|ed|ing)?\b|\bcheck(?:s|ed|ing)?\b",
        "replacement": r"\breplac(?:e|ed|ement|ements|ing)\b",
        "modification": r"\bmodif(?:y|ied|ication|ications)\b",
        "repair": r"\brepair(?:ed|s|ing)?\b",
        "operational_limitation": r"\blimitation(?:s)?\b",
        "flight_manual_revision": r"\b(?:AFM|flight manual)\b.*\b(?:amend|revise|insert)\b",
        "reporting": r"\breport(?:ing|ed|s)?\b",
        "functional_test": r"\b(?:functional|operational)\s+test\b",
        "lubrication": r"\blubricat(?:e|ed|ion|ing)\b",
    }
    return sorted(name for name, pattern in rules.items() if re.search(pattern, text, re.I))


def build_prediction(row: dict[str, Any], pages: list[dict[str, Any]]) -> dict[str, Any]:
    page_text = "\n".join(item.get("text") or "" for item in pages)
    text = clean_text(page_text)
    first = clean_text(pages[0].get("text") or "") if pages else ""
    ad_number = parse_ad_number(first)
    base, revision, emergency = identity_parts(ad_number)
    issue_date = extract_date(text, r"Issued?") or extract_date(text, r"Issue\s+Date")
    if not issue_date:
        issue_date = extract_date(text, "Date")
    effective_date = extract_date(text, r"Effective\s+Date")
    correction_match = re.search(rf"\bCorrected\s*:\s*{DATE_RE}", text, re.I)
    correction_date = parse_date(correction_match.group(1)) if correction_match else None
    is_correction = bool(correction_date or re.search(r"\bThis Correction is issued\b", text, re.I))
    approval_holder = extract_between(
        text,
        r"(?:Type Certificate|Design Approval|Design Change Approval) Holder(?:'s)? Name",
        ("Modification", "Manufacturer(s)", "Subject", "Effective Date", "Applicability"),
    )
    subject = extract_between(
        text,
        "Subject",
        ("Effective Date", "Supersedure", "Manufacturer(s)", "Applicability", "Reason"),
    )
    if not subject:
        heading = re.search(r"\bATA\s+\d{2}\s*[-–—]\s*(.{3,180}?)(?=\s+(?:Manufacturer|Applicability|Reason)\s*:)", text, re.I)
        subject = clean_text(heading.group(1)) if heading else None
    manufacturer_value = manufacturer(text)
    ata_codes = sorted(set(re.findall(r"\bATA\s+(\d{2})\b", text, re.I)))
    models = sorted({item.upper() for item in MODEL_RE.findall(text)})
    tcds = sorted(
        {
            re.sub(r"\s+", ".", item.upper())
            for item in re.findall(r"\bEASA(?:\.|\s+)A\.\d{3}\b", text, re.I)
        }
    )
    supersedure_state, supersedure_value, relationships = explicit_supersedure(text, ad_number)
    reason = extract_between(
        text,
        "Reason",
        ("Effective Date", "Required Action(s) and Compliance Time(s)", "Compliance", "Ref. Publications", "Remarks"),
    )
    requirements_text = extract_between(
        text,
        r"Required Action(?:\(s\))? and Compliance Time(?:\(s\))?",
        ("Ref. Publications", "Remarks", "Contacts"),
    )
    if not requirements_text:
        requirements_text = extract_between(
            text,
            "Compliance",
            ("Ref. Publications", "Remarks", "Contacts"),
        )
    detected_actions = action_types(requirements_text or "")

    prediction: dict[str, Any] = {
        "source_document": {
            "file_instance_id": row["file_instance_id"],
            "file_name": row["file_name"],
        },
        "ad_identity": {
            "ad_number": ad_number,
            "base_ad_number": base,
            "revision_number": revision,
            "is_emergency": emergency,
            "is_correction": is_correction,
            "correction_date": {"value": correction_date},
            "design_approval_holder": {"value": approval_holder},
            "supersedure_statement": {
                "state": supersedure_state,
                "value": supersedure_value,
            },
        },
        "publication": {
            "subject": {"value": subject},
            "issue_date": {"value": issue_date},
            "effective_date": {"value": effective_date},
            "ata_chapters": [{"code": item} for item in ata_codes],
            "manufacturers": (
                [
                    {
                        "raw_name": manufacturer_value[0],
                        "normalized_name": manufacturer_value[1],
                    }
                ]
                if manufacturer_value
                else []
            ),
            "type_model_designations": models,
            "tcds_numbers": tcds,
        },
        "unsafe_condition": {
            "state": "present" if reason else "not_stated",
            "raw_reason_text": reason,
        },
        "requirements": (
            [
                {
                    "raw_action_text": requirements_text,
                    "action_types": detected_actions,
                    "compliance_rules": [{"raw_text": requirements_text}],
                }
            ]
            if requirements_text
            else []
        ),
        "relationships": relationships,
        "classification": {
            "ata_chapters": ata_codes,
            "action_types": detected_actions,
        },
        "prediction_metadata": {
            "method": "regex_rules",
            "rules_version": "regex_v1",
            "input_page_count": len(pages),
        },
    }
    return prediction


def main() -> int:
    args = parse_args()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    if not isinstance(selection, list) or len(selection) != 30:
        raise ValueError("selection must contain exactly 30 rows")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    generated = 0
    for row in selection:
        page_path = args.page_text_dir / f"{row['ad_number']}__{row['file_instance_id']}.pages.jsonl"
        if not page_path.exists():
            raise ValueError(f"missing page text: {page_path}")
        pages = read_pages(page_path)
        prediction = build_prediction(row, pages)
        output = args.output_dir / f"{row['ad_number']}__{row['file_instance_id']}.prediction.json"
        output.write_text(
            json.dumps(prediction, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        generated += 1
    print(f"Generated {generated} regex predictions in {args.output_dir}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
