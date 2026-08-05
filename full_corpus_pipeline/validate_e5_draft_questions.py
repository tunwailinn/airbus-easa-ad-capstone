#!/usr/bin/env python3
"""Validate an E5 development draft without granting human-review status.

This wrapper runs the canonical E5 validator and ignores only the expected
`review_status must be human_verified` findings. Every other benchmark,
family-isolation, count, query-mode, page, answer and identifier-leakage check
remains enforced. The canonical validator must still pass without this wrapper
before a benchmark file is promoted to final use.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from full_corpus_pipeline.validate_e5_questions import DEFAULT_ROOT, validate_split


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--questions", type=Path, required=True)
    args = parser.parse_args()

    errors = validate_split(args.benchmark_root, "development", args.questions)
    substantive = [
        error for error in errors
        if "review_status must be human_verified" not in error
    ]
    review_only = len(errors) - len(substantive)

    result = {
        "structurally_valid": not substantive,
        "human_review_complete": review_only == 0,
        "review_status_findings": review_only,
        "substantive_error_count": len(substantive),
        "substantive_errors": substantive,
    }
    print(json.dumps(result, indent=2))
    return 0 if not substantive else 1


if __name__ == "__main__":
    raise SystemExit(main())
