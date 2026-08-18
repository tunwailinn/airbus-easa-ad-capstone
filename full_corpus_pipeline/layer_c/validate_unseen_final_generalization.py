#!/usr/bin/env python3
"""Validate the final locked five-PDF unseen generalization result (U7/U8)."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNSEEN_ROOT = ROOT / "evaluation_sets/unseen_incoming_5_v1"
DEFAULT_FINAL_LOCK = UNSEEN_ROOT / "unseen_final_generalization_lock.json"
DEFAULT_U7_LOCK = UNSEEN_ROOT / "u7_post_ingestion_human_semantic_review_lock.json"
VALIDATOR_VERSION = "unseen-5-final-generalization-validator-v1.0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rooted(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def require_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"{label} SHA-256 mismatch: expected {expected}, found {actual}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final-lock", type=Path, default=DEFAULT_FINAL_LOCK)
    parser.add_argument("--u7-lock", type=Path, default=DEFAULT_U7_LOCK)
    args = parser.parse_args()

    if not args.u7_lock.is_file():
        raise FileNotFoundError(args.u7_lock)
    u7 = json.loads(args.u7_lock.read_text(encoding="utf-8"))
    if u7.get("lock_version") != "unseen-5-u7-post-ingestion-human-review-lock-v1.0":
        raise ValueError("unexpected U7 human-review lock version")
    if u7.get("status") != "human_approved_and_locked":
        raise ValueError("U7 human review is not locked")

    require_hash(
        UNSEEN_ROOT / "u7_post_ingestion_human_semantic_review.csv",
        str(u7["human_review_csv_sha256"]),
        "U7 human review CSV",
    )
    require_hash(
        UNSEEN_ROOT / "u7_post_ingestion_human_semantic_review_summary.json",
        str(u7["human_review_summary_sha256"]),
        "U7 human review summary",
    )
    require_hash(
        UNSEEN_ROOT / "u7_post_ingestion_human_semantic_review_final.md",
        str(u7["human_review_final_md_sha256"]),
        "U7 human review Markdown",
    )

    if int(u7.get("semantic_pass_count", -1)) != 13:
        raise ValueError("unexpected U7 semantic PASS count")
    if int(u7.get("semantic_fail_count", -1)) != 1:
        raise ValueError("unexpected U7 semantic FAIL count")
    if int(u7.get("technical_failure_count", -1)) != 1:
        raise ValueError("unexpected U7 technical-failure count")
    if u7.get("semantic_failure_ids") != ["U5Q-010"]:
        raise ValueError("unexpected U7 semantic failure IDs")
    if u7.get("technical_failure_ids") != ["U5Q-011"]:
        raise ValueError("unexpected U7 technical failure IDs")

    if not args.final_lock.is_file():
        raise FileNotFoundError(args.final_lock)
    final = json.loads(args.final_lock.read_text(encoding="utf-8"))
    if final.get("lock_version") != "unseen-5-final-generalization-lock-v1.0":
        raise ValueError("unexpected final unseen lock version")
    if final.get("status") != "evaluation_complete_and_locked":
        raise ValueError("final unseen evaluation is not locked complete")

    require_hash(
        rooted(str(final["u7_human_review_lock_path"])),
        str(final["u7_human_review_lock_sha256"]),
        "U7 human-review lock",
    )
    require_hash(
        rooted(str(final["u8_final_report_path"])),
        str(final["u8_final_report_sha256"]),
        "U8 final report",
    )

    questions = UNSEEN_ROOT / "unseen_questions.jsonl"
    if questions.is_file():
        require_hash(questions, str(final["unseen_questions_sha256"]), "locked unseen questions")

    u5u6 = UNSEEN_ROOT / "unseen_permanent_ingestion_result_lock.json"
    require_hash(u5u6, str(final["u5_u6_result_lock_sha256"]), "U5/U6 result lock")

    unseen = final.get("final_unseen_post_ingestion_primary") or {}
    e5 = final.get("authoritative_frozen_e5_final") or {}
    if unseen != {
        "question_count": 15,
        "semantic_pass_count": 13,
        "semantic_fail_count": 1,
        "technical_failure_count": 1,
        "semantic_accuracy_on_successful_responses": 13 / 14,
        "strict_end_to_end_success_rate": 13 / 15,
        "retrieval_recall_at_5": 1.0,
        "correct_source_at_1": 1.0,
    }:
        raise ValueError("final unseen summary differs from locked result")
    if int(e5.get("question_count", -1)) != 40 or int(e5.get("semantic_pass_count", -1)) != 38:
        raise ValueError("authoritative E5 final summary differs from lock")
    if float(e5.get("strict_semantic_accuracy", -1)) != 0.95:
        raise ValueError("authoritative E5 final accuracy differs from 95.0%")

    output = {
        "validator_version": VALIDATOR_VERSION,
        "status": "valid",
        "evaluation_complete": True,
        "u7_human_approved": True,
        "u7_semantic_pass_count": 13,
        "u7_semantic_fail_count": 1,
        "u7_technical_failure_count": 1,
        "u7_semantic_accuracy_on_successful_responses": 13 / 14,
        "u7_strict_primary_end_to_end_success_rate": 13 / 15,
        "u7_retrieval_recall_at_5": 1.0,
        "authoritative_e5_final_semantic_accuracy": 0.95,
        "next_phase": "post-evaluation engineering, application integration, and final report/thesis writing",
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
