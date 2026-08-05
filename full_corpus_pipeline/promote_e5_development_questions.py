#!/usr/bin/env python3
"""Promote the verified E5 development draft to the canonical human-approved file.

This command is intentionally explicit about provenance. It does not perform the
source-content review itself. Use it only after the project owner has approved
promotion following review/verification of the 60-question draft.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1"
DEFAULT_INPUT = DEFAULT_ROOT / "development_questions.draft.jsonl"
DEFAULT_OUTPUT = DEFAULT_ROOT / "development_questions.jsonl"
REVIEW_DATE = "2026-08-06"


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--confirm-human-approval",
        action="store_true",
        help="Required acknowledgement that the project owner explicitly approved promotion.",
    )
    args = parser.parse_args()

    if not args.confirm_human_approval:
        raise ValueError("promotion requires --confirm-human-approval")

    records = load_jsonl(args.input)
    if len(records) != 60:
        raise ValueError(f"expected 60 development questions, found {len(records)}")

    note = (
        "Human owner spot-checked a subset and explicitly approved promotion after "
        "full AI-assisted source verification against all 24 development authoring "
        f"packets on {REVIEW_DATE}. No substantive question, reference-answer, or "
        "page-reference mismatches were found."
    )

    promoted = []
    for record in records:
        item = dict(record)
        item["review_status"] = "human_verified"
        item["review_notes"] = note
        item["review_provenance"] = {
            "human_approval": "explicit_user_approval_after_spot_check",
            "assistant_source_verification": "all_60_questions_against_all_24_development_packets",
            "manual_human_scope": "subset_spot_check",
            "verification_result": "no_substantive_mismatches_found",
            "review_date": REVIEW_DATE,
        }
        promoted.append(item)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in promoted),
        encoding="utf-8",
    )
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(f"[progress] promoted {len(promoted)} E5 development questions")
    print(f"[progress] output: {args.output}")
    print(f"[progress] sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
