#!/usr/bin/env python3
"""Audit extracted records against the Airbus S.A.S. approval-holder scope."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from full_corpus_pipeline.evaluate_extraction import benchmark_scope_status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path, help="Directory containing extracted JSON records")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    paths = sorted(args.records.glob("*.json"))
    if not paths:
        raise ValueError(f"no JSON records found in {args.records}")

    counts = Counter()
    holder_counts = Counter()
    excluded = []
    unknown = []

    for path in paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        ad_number = str((record.get("ad_identity") or {}).get("ad_number") or path.stem)
        status, holder = benchmark_scope_status(record)
        counts[status] += 1
        holder_counts[holder or "<missing>"] += 1
        row = {
            "ad_number": ad_number,
            "file": path.name,
            "design_approval_holder": holder or None,
        }
        if status == "excluded":
            excluded.append(row)
        elif status == "unknown":
            unknown.append(row)

    report = {
        "audit_version": "corpus-scope-audit-v1.1",
        "project_scope": (
            "EU-issued EASA ADs with Airbus S.A.S. approval holder; legacy "
            "Airbus/Airbus Industrie aliases accepted"
        ),
        "classification_policy": (
            "Confident external holders are excluded. Missing or malformed holder "
            "text is unknown, not excluded, so parser boundary errors cannot silently "
            "shrink the research corpus."
        ),
        "record_count": len(paths),
        "eligible_count": counts["eligible"],
        "excluded_count": counts["excluded"],
        "unknown_count": counts["unknown"],
        "excluded_records": excluded,
        "unknown_records": unknown,
        "holder_counts": [
            {"design_approval_holder": holder, "count": count}
            for holder, count in holder_counts.most_common()
        ],
        "decision_required": bool(excluded or unknown),
        "decision_note": (
            "Review excluded and unknown records before freezing the scope-approved "
            "operational view. Do not silently delete physical source records, treat "
            "unknowns as exclusions, or broaden the stated Airbus S.A.S. scope."
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
        print(f"Out-of-scope records: {len(excluded)}")
        for row in excluded[:20]:
            print(f"  {row['ad_number']}: {row['design_approval_holder']}")
    if unknown:
        print(f"Unknown-scope records: {len(unknown)}")
        for row in unknown[:20]:
            print(f"  {row['ad_number']}: missing/malformed holder")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
