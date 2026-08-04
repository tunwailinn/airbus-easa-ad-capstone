#!/usr/bin/env python3
"""Audit extracted records against the strict Airbus S.A.S. holder scope."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from full_corpus_pipeline.scope_policy import classify_holder, normalize_holder


DEFAULT_OVERRIDES = Path(__file__).with_name("scope_review_overrides.json")


def _load_overrides(path: Path | None) -> dict[tuple[str, str], dict]:
    if path is None or not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    result: dict[tuple[str, str], dict] = {}
    for item in payload.get("overrides", []):
        status = str(item.get("scope_status") or "")
        if status not in {"eligible", "excluded"}:
            raise ValueError(f"invalid reviewed scope status: {status!r}")
        key = (str(item.get("ad_number") or ""), str(item.get("file_instance_id") or ""))
        if not all(key):
            raise ValueError("scope review override requires ad_number and file_instance_id")
        if key in result:
            raise ValueError(f"duplicate scope review override: {key}")
        result[key] = item
    return result


def _file_instance_id(path: Path) -> str:
    match = re.search(r"__([0-9a-f]{16})\.json$", path.name, re.IGNORECASE)
    return match.group(1) if match else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path, help="Directory containing extracted JSON records")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--review-overrides",
        type=Path,
        default=DEFAULT_OVERRIDES,
        help="Versioned scope-review overrides; applied only when automatic status is unknown",
    )
    args = parser.parse_args()

    paths = sorted(args.records.glob("*.json"))
    if not paths:
        raise ValueError(f"no JSON records found in {args.records}")
    overrides = _load_overrides(args.review_overrides)

    counts = Counter()
    holder_counts = Counter()
    excluded = []
    unknown = []
    applied_overrides = []

    for path in paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        ad_number = str((record.get("ad_identity") or {}).get("ad_number") or path.stem)
        file_instance_id = _file_instance_id(path)
        raw_holder = (record.get("ad_identity") or {}).get("design_approval_holder")
        status, holder, reason = classify_holder(raw_holder)

        override = overrides.get((ad_number, file_instance_id))
        if override is not None and status == "unknown":
            status = str(override["scope_status"])
            holder = normalize_holder(override.get("design_approval_holder"))
            reason = f"reviewed scope override: {override.get('reason')}"
            applied_overrides.append(
                {
                    "ad_number": ad_number,
                    "file_instance_id": file_instance_id,
                    "scope_status": status,
                    "design_approval_holder": holder or None,
                    "source_page": override.get("source_page"),
                    "review_method": override.get("review_method"),
                    "reason": override.get("reason"),
                }
            )

        counts[status] += 1
        holder_counts[holder or "<missing>"] += 1
        row = {
            "ad_number": ad_number,
            "file": path.name,
            "file_instance_id": file_instance_id or None,
            "design_approval_holder": holder or None,
            "reason": reason,
        }
        if status == "excluded":
            excluded.append(row)
        elif status == "unknown":
            unknown.append(row)

    report = {
        "audit_version": "corpus-scope-audit-v1.3",
        "project_scope": (
            "EU-issued EASA ADs with Airbus S.A.S. approval holder; legacy "
            "Airbus/Airbus Industrie aliases accepted"
        ),
        "classification_policy": (
            "Accepted Airbus aliases are eligible. Confirmed external or mixed-holder "
            "records are excluded only from the strict Airbus-only operational view, "
            "while the physical source record remains preserved. Missing, malformed or "
            "unclassified holder text remains unknown. Versioned source-review overrides "
            "may resolve only an automatic unknown; they never rewrite extracted content."
        ),
        "record_count": len(paths),
        "eligible_count": counts["eligible"],
        "excluded_count": counts["excluded"],
        "unknown_count": counts["unknown"],
        "review_override_file": str(args.review_overrides) if args.review_overrides else None,
        "review_override_count": len(applied_overrides),
        "review_overrides_applied": applied_overrides,
        "excluded_records": excluded,
        "unknown_records": unknown,
        "holder_counts": [
            {"design_approval_holder": holder, "count": count}
            for holder, count in holder_counts.most_common()
        ],
        "decision_required": bool(unknown),
        "decision_note": (
            "Confirmed exclusions remain preserved in the immutable physical inventory. "
            "Resolve every remaining unknown before freezing the strict Airbus-only "
            "operational count; never silently treat unknowns as exclusions or delete PDFs."
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                key: value
                for key, value in report.items()
                if key not in {"excluded_records", "unknown_records", "holder_counts"}
            },
            indent=2,
        )
    )
    if excluded:
        print(f"Excluded from strict Airbus-only view: {len(excluded)}")
        for row in excluded[:20]:
            print(f"  {row['ad_number']}: {row['design_approval_holder']}")
    if unknown:
        print(f"Unknown-scope records: {len(unknown)}")
        for row in unknown[:20]:
            print(f"  {row['ad_number']}: {row['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
