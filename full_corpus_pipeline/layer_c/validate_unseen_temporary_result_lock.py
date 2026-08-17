#!/usr/bin/env python3
"""Validate the human-approved five-PDF temporary-document result lock.

This validator is the gate before permanent-ingestion evaluation. It binds the
preserved U3 first-pass run, passage-support diagnostic, the single failed exact
transport retry, and the U4 human semantic review by SHA-256. It never modifies
any evaluation artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
UNSEEN_ROOT = ROOT / "evaluation_sets/unseen_incoming_5_v1"
DEFAULT_LOCK = UNSEEN_ROOT / "unseen_temporary_result_lock.json"
DEFAULT_QUESTIONS = UNSEEN_ROOT / "unseen_questions.jsonl"
VALIDATOR_VERSION = "unseen-5-temporary-result-lock-validator-v1.0"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"{label} SHA-256 mismatch: expected {expected}, found {actual}")


def rooted(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    args = parser.parse_args()

    if not args.lock.is_file():
        raise FileNotFoundError(args.lock)
    lock: dict[str, Any] = json.loads(args.lock.read_text(encoding="utf-8"))

    if lock.get("lock_version") != "unseen-5-temporary-result-lock-v1.0":
        raise ValueError("unexpected unseen temporary result lock version")
    if lock.get("status") != "human_approved_and_locked":
        raise ValueError("unseen temporary result is not human approved and locked")
    if not args.questions.is_file():
        raise FileNotFoundError(args.questions)
    if sha256(args.questions) != lock.get("unseen_questions_sha256"):
        raise ValueError("locked unseen question SHA-256 mismatch")

    primary = lock.get("primary_run") or {}
    for key, hash_key, label in (
        ("run_summary_path", "run_summary_sha256", "primary run summary"),
        ("retrieval_report_path", "retrieval_report_sha256", "primary retrieval report"),
        ("automatic_evaluation_path", "automatic_evaluation_sha256", "primary automatic evaluation"),
    ):
        require_hash(rooted(str(primary[key])), str(primary[hash_key]), label)

    diagnostic = lock.get("passage_support_diagnostic") or {}
    require_hash(rooted(str(diagnostic["path"])), str(diagnostic["sha256"]), "reference-quote containment diagnostic")
    if diagnostic.get("diagnostic_only") is not True:
        raise ValueError("passage-support containment artifact must remain diagnostic-only")

    retry = lock.get("transport_retry") or {}
    require_hash(rooted(str(retry["retry_summary_path"])), str(retry["retry_summary_sha256"]), "transport retry summary")
    require_hash(rooted(str(retry["failure_path"])), str(retry["failure_sha256"]), "transport retry failure")
    if retry.get("question_id") != "U5Q-011" or retry.get("status") != "failed":
        raise ValueError("unexpected locked U5Q-011 retry state")
    if retry.get("further_retry_permitted") is not False:
        raise ValueError("locked retry policy must prohibit another U5Q-011 retry")

    review = lock.get("human_review") or {}
    for key, hash_key, label in (
        ("csv_path", "csv_sha256", "human review CSV"),
        ("summary_path", "summary_sha256", "human review summary"),
        ("final_review_path", "final_review_sha256", "human review markdown"),
    ):
        require_hash(rooted(str(review[key])), str(review[hash_key]), label)

    review_summary = json.loads(rooted(str(review["summary_path"])).read_text(encoding="utf-8"))
    expected = {
        "semantic_pass_count": 13,
        "semantic_fail_count": 1,
        "persistent_technical_failure_count": 1,
    }
    for key, value in expected.items():
        if int(review_summary.get(key, -1)) != value:
            raise ValueError(f"human review summary {key} differs from locked value")
    if review_summary.get("semantic_failure_ids") != ["U5Q-010"]:
        raise ValueError("locked semantic failure set must contain only U5Q-010")
    if review_summary.get("technical_failure_ids") != ["U5Q-011"]:
        raise ValueError("locked technical failure set must contain only U5Q-011")

    next_stage = lock.get("next_stage") or {}
    if next_stage.get("permanent_ingestion_allowed") is not True:
        raise ValueError("permanent ingestion has not been authorized by the temporary result lock")
    if next_stage.get("required_mode") != "isolated_evaluation_store_and_index":
        raise ValueError("permanent ingestion must use an isolated evaluation store/index")
    if next_stage.get("may_modify_frozen_e5_indexes") is not False:
        raise ValueError("temporary result lock must prohibit frozen E5 index modification")
    if next_stage.get("may_retune_from_unseen_results") is not False:
        raise ValueError("temporary result lock must prohibit unseen-result retuning")

    output = {
        "validator_version": VALIDATOR_VERSION,
        "status": "valid",
        "human_approved": True,
        "semantic_pass_count": 13,
        "semantic_fail_count": 1,
        "persistent_technical_failure_count": 1,
        "semantic_accuracy_on_successful_responses": 13 / 14,
        "strict_first_pass_end_to_end_success_rate": 13 / 15,
        "semantic_failure_ids": ["U5Q-010"],
        "technical_failure_ids": ["U5Q-011"],
        "permanent_ingestion_allowed": True,
        "required_mode": "isolated_evaluation_store_and_index",
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
