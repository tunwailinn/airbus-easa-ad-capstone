#!/usr/bin/env python3
"""Validate the human-reviewed five-PDF unseen QA lock before hosted inference."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
UNSEEN_ROOT = ROOT / "evaluation_sets/unseen_incoming_5_v1"
DEFAULT_QUESTIONS = UNSEEN_ROOT / "unseen_questions.jsonl"
DEFAULT_LOCK = UNSEEN_ROOT / "unseen_lock.json"
DEFAULT_SELECTION = UNSEEN_ROOT / "selection.csv"
DEFAULT_SELECTION_LOCK = UNSEEN_ROOT / "selection_lock.json"
DEFAULT_AUDIT = UNSEEN_ROOT / "unseen_question_verification_audit.json"
DEFAULT_REVIEW = UNSEEN_ROOT / "unseen_question_final_review.md"
DEFAULT_PREPARATION = ROOT / "data_processed/evaluations/unseen_5/preparation"
DEFAULT_HOSTED_FREEZE = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json"

EXPECTED_CATEGORY_COUNTS = {
    "identity_lifecycle": 4,
    "applicability": 3,
    "required_action_compliance": 3,
    "conditional_multi_passage": 3,
    "referenced_publication": 1,
    "insufficient_conflict_abstention": 1,
}
EXPECTED_STRATUM_COUNTS = {
    "corrected": 3,
    "revised": 3,
    "supersedure": 3,
    "long_document": 3,
    "simple_original": 3,
}
EXPECTED_TARGET_COUNTS = {
    "2008-0008": 3,
    "2011-0041R1": 3,
    "2011-0142": 3,
    "2026-0084": 3,
    "2007-0173": 3,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_questions(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 15:
        raise ValueError(f"expected 15 unseen questions, found {len(rows)}")
    expected_ids = [f"U5Q-{i:03d}" for i in range(1, 16)]
    ids = [str(row.get("question_id", "")) for row in rows]
    if ids != expected_ids:
        raise ValueError(f"unexpected unseen question IDs/order: {ids}")
    for row in rows:
        if row.get("split") != "unseen_post_final":
            raise ValueError(f"{row['question_id']}: unexpected split")
        if row.get("evaluation_role") != "temporary_document_generalization":
            raise ValueError(f"{row['question_id']}: unexpected evaluation role")
        if row.get("query_mode") != "temporary_document":
            raise ValueError(f"{row['question_id']}: unexpected query mode")
        if row.get("review_status") != "human_verified" or row.get("human_verified") is not True:
            raise ValueError(f"{row['question_id']}: question is not human verified")
        if not row.get("source_packet"):
            raise ValueError(f"{row['question_id']}: missing source_packet")
        if not row.get("reference_pages"):
            raise ValueError(f"{row['question_id']}: missing reference_pages")
    if Counter(str(r["category"]) for r in rows) != Counter(EXPECTED_CATEGORY_COUNTS):
        raise ValueError("unexpected unseen category distribution")
    if Counter(str(r["stratum"]) for r in rows) != Counter(EXPECTED_STRATUM_COUNTS):
        raise ValueError("unexpected unseen stratum distribution")
    if Counter(str(r["target_ad_number"]) for r in rows) != Counter(EXPECTED_TARGET_COUNTS):
        raise ValueError("unexpected questions-per-document distribution")
    if sum(bool(r.get("answerable_from_ad")) for r in rows) != 14:
        raise ValueError("expected 14 answerable unseen questions")
    return rows


def validate(
    questions_path: Path = DEFAULT_QUESTIONS,
    lock_path: Path = DEFAULT_LOCK,
    preparation_dir: Path = DEFAULT_PREPARATION,
) -> dict[str, Any]:
    required = [questions_path, lock_path, DEFAULT_SELECTION, DEFAULT_SELECTION_LOCK, DEFAULT_AUDIT, DEFAULT_REVIEW]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing unseen lock inputs: " + ", ".join(missing))

    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("status") != "human_verified_and_locked":
        raise ValueError("unseen question lock is not human_verified_and_locked")
    if int(lock.get("question_count", 0)) != 15 or int(lock.get("human_verified_count", 0)) != 15:
        raise ValueError("unseen question lock has unexpected counts")
    if lock.get("question_inference_started_before_lock") is not False:
        raise ValueError("lock does not prove inference was unstarted before lock")
    if lock.get("permanent_ingestion_started_before_lock") is not False:
        raise ValueError("lock does not prove ingestion was unstarted before lock")

    rows = load_questions(questions_path)
    bindings = {
        "selection_sha256": sha256(DEFAULT_SELECTION),
        "selection_lock_sha256": sha256(DEFAULT_SELECTION_LOCK),
        "unseen_questions_sha256": sha256(questions_path),
        "verification_audit_sha256": sha256(DEFAULT_AUDIT),
        "final_review_sha256": sha256(DEFAULT_REVIEW),
    }
    for field, actual in bindings.items():
        if str(lock.get(field, "")) != actual:
            raise ValueError(f"unseen lock hash mismatch for {field}: {actual}")

    prep_manifest = preparation_dir / "preparation_manifest.json"
    prep_summary = preparation_dir / "preparation_summary.json"
    if not prep_manifest.is_file() or not prep_summary.is_file():
        raise FileNotFoundError("unseen preparation outputs are missing")
    if sha256(prep_manifest) != str(lock.get("preparation_manifest_sha256", "")):
        raise ValueError("preparation manifest hash differs from unseen lock")
    summary = json.loads(prep_summary.read_text(encoding="utf-8"))
    if summary.get("document_count") != 5 or summary.get("source_hash_match_count") != 5:
        raise ValueError("unseen preparation source validation is incomplete")
    if summary.get("extraction_success_count") != 5 or summary.get("schema_valid_count") != 5:
        raise ValueError("unseen preparation extraction/schema validation is incomplete")
    if summary.get("question_inference_started") is not False or summary.get("permanent_ingestion_started") is not False:
        raise ValueError("preparation state is not pre-inference/pre-ingestion")

    # Revalidate the already-frozen hosted-QA configuration before any unseen hosted inference.
    subprocess.run(
        [sys.executable, "-m", "full_corpus_pipeline.layer_c.validate_hosted_qa_freeze", "--freeze", str(DEFAULT_HOSTED_FREEZE)],
        cwd=ROOT,
        check=True,
    )

    return {
        "status": "valid",
        "question_count": len(rows),
        "answerable_count": sum(bool(r.get("answerable_from_ad")) for r in rows),
        "abstention_count": sum(not bool(r.get("answerable_from_ad")) for r in rows),
        "unseen_questions_sha256": bindings["unseen_questions_sha256"],
        "preparation_manifest_sha256": sha256(prep_manifest),
        "hosted_qa_freeze_validated": True,
        "permanent_ingestion_started": False,
    }


def main() -> int:
    result = validate()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
