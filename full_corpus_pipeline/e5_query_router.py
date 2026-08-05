#!/usr/bin/env python3
"""Deterministic query routing for E5 engineering-aware retrieval.

This module intentionally uses no LLM. It extracts explicit AD identifiers and
assigns a coarse engineering intent that is later used only as a retrieval hint.
Exact document identity supplied by the user is treated as routing metadata, not
as a semantic-ranking feature.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Iterable


AD_ID_PATTERN = r"(?:19|20)\d{2}-\d{4}(?:R\d+)?"
AD_RE = re.compile(
    rf"\b(?:EASA\s+AD\s+|AD\s+)?({AD_ID_PATTERN})\b",
    re.IGNORECASE,
)
SB_RE = re.compile(r"\b([A-Z]\d{3,4}-\d{2}-\d{4})\b", re.IGNORECASE)

# In target-discovery wording, an explicitly named AD can be contextual evidence
# rather than the document being requested. Example: "Which directive superseded
# EASA AD 2013-0250R1?". Such queries must remain corpus-wide discovery.
SUPERSEDER_DISCOVERY_RE = re.compile(
    rf"\b(?:which|what)\b.*\b(?:directive|ad)\b.*\bsupersed(?:e|ed|es|ing)\b"
    rf".*\b(?:EASA\s+AD\s+|AD\s+)?{AD_ID_PATTERN}\b",
    re.IGNORECASE,
)

# Some questions name one primary target first and then mention related ADs for
# context. In these forms the first AD remains the routed document rather than
# forcing a multi-document search.
PRIMARY_RELATION_RE = re.compile(
    rf"^\s*how\s+does\s+(?:EASA\s+AD\s+|AD\s+)?({AD_ID_PATTERN})\b.*\brelate\b",
    re.IGNORECASE,
)


SECTION_HINTS: dict[str, tuple[str, ...]] = {
    "identity_lifecycle": (
        "Document",
        "Effective Date",
        "Supersedure",
        "Reason",
        "Remarks",
    ),
    "applicability": (
        "Applicability",
        "Document",
        "Definitions",
    ),
    "required_action_compliance": (
        "Required Action(s) and Compliance Time(s)",
        "Required Action(s)",
        "Required action(s)",
        "Compliance",
        "Definitions",
        "Reason",
    ),
    "referenced_publication": (
        "Ref. Publications",
        "Ref. Publications ",
        "Required Action(s) and Compliance Time(s)",
        "Required Action(s)",
        "Remarks",
    ),
    "conditional_multi_passage": (
        "Required Action(s) and Compliance Time(s)",
        "Required Action(s)",
        "Compliance",
        "Definitions",
        "Applicability",
        "Reason",
    ),
    "general": (),
}


@dataclass(frozen=True)
class QueryRoute:
    mode: str
    ad_numbers: tuple[str, ...]
    publication_ids: tuple[str, ...]
    intent: str
    preferred_sections: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        normalized = value.upper()
        if normalized not in seen:
            seen.add(normalized)
            output.append(normalized)
    return tuple(output)


def extract_ad_numbers(question: str) -> tuple[str, ...]:
    return _dedupe(match.group(1) for match in AD_RE.finditer(question))


def extract_publication_ids(question: str) -> tuple[str, ...]:
    return _dedupe(match.group(1) for match in SB_RE.finditer(question))


def classify_intent(question: str) -> str:
    text = question.casefold()

    conditional_terms = (
        " unless ",
        " whichever ",
        " if ",
        " depending ",
        " provided that ",
        " terminating action",
        " repetitive ",
        " repeat ",
        " exception",
        " alternative ",
        "what happens after",
    )
    if any(term in f" {text} " for term in conditional_terms):
        return "conditional_multi_passage"

    reference_terms = (
        "service bulletin",
        "ref. publication",
        "reference publication",
        "referenced publication",
        "which sb",
        "what sb",
    )
    if any(term in text for term in reference_terms) or SB_RE.search(question):
        return "referenced_publication"

    applicability_terms = (
        "applicability",
        "applicable",
        "which aircraft",
        "what aircraft",
        "affected aircraft",
        "affected model",
        "which model",
        "what model",
        "serial number",
        "manufacturer serial",
        " msn ",
        "installed on",
    )
    if any(term in f" {text} " for term in applicability_terms):
        return "applicability"

    compliance_terms = (
        "compliance",
        "flight cycle",
        "flight hour",
        "within ",
        "before ",
        "no later than",
        "inspect",
        "inspection",
        "replace",
        "replacement",
        "modify",
        "modification",
        "accomplish",
        "required action",
        "must be done",
        "must be performed",
    )
    if any(term in text for term in compliance_terms):
        return "required_action_compliance"

    identity_terms = (
        "effective date",
        "issue date",
        "supersed",
        "revision",
        "revised",
        "correction",
        "cancelled",
        "canceled",
        "lifecycle",
        "latest version",
        "current version",
    )
    if any(term in text for term in identity_terms):
        return "identity_lifecycle"

    return "general"


def route_query(question: str) -> QueryRoute:
    all_ad_numbers = extract_ad_numbers(question)
    publication_ids = extract_publication_ids(question)
    intent = classify_intent(question)

    if SUPERSEDER_DISCOVERY_RE.search(question):
        mode = "discovery"
        ad_numbers: tuple[str, ...] = ()
    else:
        primary_match = PRIMARY_RELATION_RE.search(question)
        if primary_match:
            mode = "known_document"
            ad_numbers = (primary_match.group(1).upper(),)
        else:
            ad_numbers = all_ad_numbers
            if len(ad_numbers) == 1:
                mode = "known_document"
            elif len(ad_numbers) > 1:
                mode = "multi_document"
            else:
                mode = "discovery"

    return QueryRoute(
        mode=mode,
        ad_numbers=ad_numbers,
        publication_ids=publication_ids,
        intent=intent,
        preferred_sections=SECTION_HINTS[intent],
    )
