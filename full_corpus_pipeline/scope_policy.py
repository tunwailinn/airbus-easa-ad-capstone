#!/usr/bin/env python3
"""Project-scope classification for Airbus S.A.S. approval holders.

The physical frozen corpus is preserved unchanged. This module only classifies
records for the strict Airbus S.A.S. operational/evaluation view. Ambiguous or
malformed holder text remains unknown; it is never silently treated as an
exclusion.
"""

from __future__ import annotations

import re
from typing import Any


AIRBUS_SCOPE_HOLDER_ALIASES = {
    "airbus",
    "airbus sas",
    "airbus s a s",
    "airbus industrie",
    "airbus industries",
    "airbus airbus industrie",
    "airbus airbus industries",
    "airbus sas airbus industrie",
    "airbus sas airbus industries",
    "airbus s a s airbus industrie",
    "airbus formerly airbus industrie",
    "airbus sas formerly airbus industrie",
    "airbus s a s formerly airbus industrie",
}

# These markers are only applied to the parsed approval-holder field, not to AD
# prose. They therefore represent a confirmed external or mixed approval-holder
# record rather than a mere reference to another organization elsewhere.
EXTERNAL_OR_MIXED_HOLDER_MARKERS = (
    "lufthansa technik",
    "airbus defence",
    "elbe flugzeugwerke",
    "fokker services",
    "short brothers",
    "jet aviation",
    "societe air france",
    "air france",
    "atr gie",
    "avions de transport regional",
    "bae systems",
)

MALFORMED_HOLDER_MARKERS = (
    "type model",
    "type designation",
    "model designation",
    "applicability",
    "aeroplanes tcds",
    "aircraft tcds",
    " aeroplanes ",
    " aircraft ",
    " serial ",
    " service bulletin ",
    " reason ",
)


def normalize_holder(value: Any) -> str:
    text = str(value or "").casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def holder_looks_malformed(holder: str) -> bool:
    if not holder:
        return True
    if len(holder) > 180:
        return True
    padded = f" {holder} "
    return any(marker in padded for marker in MALFORMED_HOLDER_MARKERS)


def classify_holder(value: Any) -> tuple[str, str, str]:
    """Return ``(status, normalized_holder, reason)``.

    Status is one of ``eligible``, ``excluded`` or ``unknown``. Mixed-holder
    documents are excluded from the strict Airbus-only operational view but the
    source PDF/record remains preserved in the frozen physical inventory.
    """
    holder = normalize_holder(value)
    if not holder:
        return "unknown", "", "approval holder is missing"
    if holder in AIRBUS_SCOPE_HOLDER_ALIASES:
        return "eligible", holder, "accepted Airbus S.A.S./legacy Airbus alias"
    if any(marker in holder for marker in EXTERNAL_OR_MIXED_HOLDER_MARKERS):
        return (
            "excluded",
            holder,
            "confirmed external or mixed approval holder; outside the strict Airbus S.A.S. operational view",
        )
    if holder_looks_malformed(holder):
        return "unknown", holder, "holder text appears malformed or contaminated by adjacent fields"
    return "unknown", holder, "holder is not yet an accepted Airbus alias or confirmed external holder"
