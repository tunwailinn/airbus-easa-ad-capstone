"""Lifecycle decisions stored separately from sparse AD content records."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any


AD_RE = re.compile(r"^((?:19|20)\d{2}-\d{4})(?:R(\d+))?$", re.I)


@dataclass(frozen=True)
class LifecycleDecision:
    base_ad_number: str
    revision_number: int
    operational_selection: bool
    relationship_status: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_ad_number(ad_number: str) -> tuple[str, int]:
    match = AD_RE.fullmatch(ad_number.strip())
    if not match:
        raise ValueError(f"unsupported AD number: {ad_number}")
    return match.group(1).upper(), int(match.group(2) or 0)


def decide_lifecycle(ad_number: str, existing_rows: list[dict[str, Any]]) -> LifecycleDecision:
    base, revision = parse_ad_number(ad_number)
    family = [row for row in existing_rows if str(row.get("base_ad_number", "")).upper() == base]
    if not family:
        return LifecycleDecision(base, revision, True, "new_family", "No existing family record exists in the frozen corpus.")
    exact = [row for row in family if str(row.get("ad_number", "")).upper() == ad_number.upper()]
    if exact:
        return LifecycleDecision(
            base, revision, False, "ambiguous_same_version",
            "The same AD/version label already exists with a different file hash; human lifecycle review is required.",
        )
    known_revisions = [int(row.get("revision_number") or 0) for row in family]
    if revision > max(known_revisions):
        return LifecycleDecision(
            base, revision, True, "higher_revision",
            "The uploaded revision number is higher than every stored family member.",
        )
    return LifecycleDecision(
        base, revision, False, "ambiguous_version_order",
        "The uploaded version does not have an unambiguous higher revision number; operational selection is unchanged.",
    )
