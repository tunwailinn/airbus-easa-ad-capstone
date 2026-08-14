#!/usr/bin/env python3
"""Validate the human-reviewed E5 final benchmark lock before the primary run."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_ROOT = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1"
DEFAULT_LOCK = BENCHMARK_ROOT / "final_lock.json"
EXPECTED_LOCK_VERSION = "e5-final-benchmark-lock-v1.0"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def verify(path_text: str, expected_sha: str, label: str) -> None:
    path = ROOT / path_text
    if not path.is_file():
        raise FileNotFoundError(f"{label}: {path}")
    actual = sha256(path)
    if actual != expected_sha:
        raise ValueError(f"{label} hash mismatch: expected {expected_sha}, got {actual}")


def main() -> int:
    if not DEFAULT_LOCK.is_file():
        raise FileNotFoundError(DEFAULT_LOCK)
    lock = load_json(DEFAULT_LOCK)
    if lock.get("lock_version") != EXPECTED_LOCK_VERSION:
        raise ValueError("unexpected E5 final benchmark lock version")
    if lock.get("status") != "human_verified_and_locked":
        raise ValueError("E5 final benchmark is not human_verified_and_locked")
    if lock.get("split") != "final_test":
        raise ValueError("E5 final benchmark lock is not for final_test")

    questions = lock.get("questions", {})
    if int(questions.get("question_count", -1)) != 40:
        raise ValueError("final lock does not declare 40 questions")
    if int(questions.get("human_verified_count", -1)) != 40:
        raise ValueError("final lock does not declare 40 human-verified questions")
    verify(questions["path"], questions["sha256"], "final questions")

    family = lock.get("family_split", {})
    if int(family.get("final_family_count", -1)) != 16:
        raise ValueError("final lock does not declare 16 final-test families")
    verify(family["path"], family["sha256"], "family split")
    split_lock_path = BENCHMARK_ROOT / "split_lock.json"
    if not split_lock_path.is_file():
        raise FileNotFoundError(split_lock_path)
    if sha256(split_lock_path) != family.get("split_lock_sha256"):
        raise ValueError("split_lock.json hash differs from final lock")

    hosted = lock.get("hosted_qa_freeze", {})
    if hosted.get("freeze_version") != "e5-hosted-qa-freeze-v1.0":
        raise ValueError("unexpected hosted-QA freeze version in final lock")
    verify(hosted["path"], hosted["sha256"], "hosted-QA freeze")

    human = lock.get("human_review", {})
    if human.get("status") != "approved_all_40":
        raise ValueError("human review does not approve all 40 final questions")
    verify(human["path"], human["sha256"], "human review record")
    verify(
        human["verification_audit_path"],
        human["verification_audit_sha256"],
        "final-question verification audit",
    )

    policies = lock.get("policies", {})
    if policies.get("primary_final_run_count") != 1:
        raise ValueError("primary final run count must remain 1")
    for key in (
        "post_test_tuning_allowed",
        "retrieval_changes_allowed",
        "hosted_qa_configuration_changes_allowed",
        "semantic_retry_allowed",
    ):
        if policies.get(key) is not False:
            raise ValueError(f"final lock policy {key} must remain false")

    print(json.dumps({
        "lock_version": lock["lock_version"],
        "status": "valid",
        "question_count": questions["question_count"],
        "human_verified_count": questions["human_verified_count"],
        "final_family_count": family["final_family_count"],
        "questions_sha256": questions["sha256"],
        "hosted_qa_freeze_version": hosted["freeze_version"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
