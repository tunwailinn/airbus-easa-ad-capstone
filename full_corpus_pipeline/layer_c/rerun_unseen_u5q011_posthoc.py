#!/usr/bin/env python3
"""Run one explicitly post-hoc exploratory rerun of unseen U5Q-011.

This command is OUTSIDE the frozen unseen temporary evaluation protocol. The
human-approved U3/U4 result remains immutable: U5Q-011 is a persistent technical
failure in the official first-pass record, and the one permitted exact transport
retry has already been consumed and failed.

This utility exists only to test provider/run-to-run variability at the user's
explicit request. It uses the exact preserved question/evidence/prompt payload,
provider/model, prompt, response contract, thinking mode, reasoning effort and
max-token limit. Retrieval is not rerun. Any success is diagnostic only and MUST
NOT change the official unseen score or locked U5Q-011 classification.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from full_corpus_pipeline.layer_c.hosted_qa import (
    HOSTED_QA_RUNNER_VERSION,
    PROMPT_VERSION,
    call_hosted_qa,
    evidence_from_pack,
)
from full_corpus_pipeline.layer_c.providers.deepseek import (
    DEEPSEEK_MODEL,
    DEEPSEEK_PROVIDER_VERSION,
    DeepSeekProvider,
)

ROOT = Path(__file__).resolve().parents[2]
UNSEEN_ROOT = ROOT / "evaluation_sets/unseen_incoming_5_v1"
PRIMARY_DIR = ROOT / "data_processed/evaluations/unseen_5/temporary_primary"
PACKS_PATH = PRIMARY_DIR / "evidence_packs.jsonl"
OFFICIAL_RETRY_DIR = ROOT / "data_processed/evaluations/unseen_5/temporary_transport_retry/U5Q-011"
OFFICIAL_RESULT_LOCK = UNSEEN_ROOT / "unseen_temporary_result_lock.json"
OUTPUT_DIR = ROOT / "data_processed/evaluations/unseen_5/temporary_posthoc_extra_retry/U5Q-011"
QUESTION_ID = "U5Q-011"
RUNNER_VERSION = "unseen-5-u5q011-posthoc-extra-rerun-v1.0"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def unique_map(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = str(row[key])
        if value in out:
            raise ValueError(f"duplicate {key}: {value}")
        out[value] = row
    return out


def main() -> int:
    # First prove the official U3/U4 result is still intact and locked.
    subprocess.run(
        [sys.executable, "-m", "full_corpus_pipeline.layer_c.validate_unseen_temporary_result_lock"],
        cwd=ROOT,
        check=True,
    )

    for path in (
        PRIMARY_DIR / "run_summary.json",
        PRIMARY_DIR / "failures.jsonl",
        PRIMARY_DIR / "responses.jsonl",
        PACKS_PATH,
        OFFICIAL_RETRY_DIR / "retry_summary.json",
        OFFICIAL_RETRY_DIR / "failure.json",
        OFFICIAL_RESULT_LOCK,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    official_lock = json.loads(OFFICIAL_RESULT_LOCK.read_text(encoding="utf-8"))
    retry_lock = official_lock.get("transport_retry") or {}
    if retry_lock.get("question_id") != QUESTION_ID:
        raise ValueError("official result lock does not bind U5Q-011 transport retry")
    if retry_lock.get("status") != "failed":
        raise ValueError("official U5Q-011 retry is not recorded as failed")
    if retry_lock.get("further_retry_permitted") is not False:
        raise ValueError("official result lock must prohibit further official retries")

    retry_summary_path = OFFICIAL_RETRY_DIR / "retry_summary.json"
    retry_failure_path = OFFICIAL_RETRY_DIR / "failure.json"
    if sha256(retry_summary_path) != str(retry_lock.get("retry_summary_sha256")):
        raise ValueError("official U5Q-011 retry summary hash mismatch")
    if sha256(retry_failure_path) != str(retry_lock.get("failure_sha256")):
        raise ValueError("official U5Q-011 retry failure hash mismatch")

    primary_summary_path = PRIMARY_DIR / "run_summary.json"
    primary_summary = json.loads(primary_summary_path.read_text(encoding="utf-8"))
    if primary_summary.get("scope") != "five frozen unseen PDFs — temporary-document primary":
        raise ValueError("unexpected primary unseen run scope")
    if primary_summary.get("model") != "deepseek-v4-pro":
        raise ValueError("primary unseen model mismatch")
    if primary_summary.get("thinking") != "enabled" or primary_summary.get("reasoning_effort") != "high":
        raise ValueError("primary unseen reasoning settings mismatch")
    if int(primary_summary.get("max_tokens", -1)) != 4096:
        raise ValueError("primary unseen max_tokens mismatch")
    if primary_summary.get("prompt_version") != PROMPT_VERSION:
        raise ValueError("primary unseen prompt version mismatch")
    if primary_summary.get("hosted_qa_runner_version") != HOSTED_QA_RUNNER_VERSION:
        raise ValueError("primary unseen hosted QA runner mismatch")
    if primary_summary.get("evidence_packs_sha256") != sha256(PACKS_PATH):
        raise ValueError("preserved evidence-packs hash differs from primary run")

    responses = unique_map(load_jsonl(PRIMARY_DIR / "responses.jsonl"), "question_id")
    failures = unique_map(load_jsonl(PRIMARY_DIR / "failures.jsonl"), "question_id")
    if QUESTION_ID in responses:
        raise ValueError("U5Q-011 unexpectedly succeeded in the official primary run")
    if QUESTION_ID not in failures:
        raise ValueError("U5Q-011 is not a preserved official primary failure")

    packs = unique_map(load_jsonl(PACKS_PATH), "question_id")
    if QUESTION_ID not in packs:
        raise ValueError("preserved U5Q-011 evidence pack not found")
    pack = packs[QUESTION_ID]
    question, evidence, payload_sha = evidence_from_pack(pack)

    primary_failure = failures[QUESTION_ID]
    official_retry_summary = json.loads(retry_summary_path.read_text(encoding="utf-8"))
    if payload_sha != primary_failure.get("prompt_payload_sha256"):
        raise ValueError("post-hoc payload differs from official primary failure")
    if payload_sha != official_retry_summary.get("prompt_payload_sha256"):
        raise ValueError("post-hoc payload differs from official exact retry")
    if payload_sha != "b17e0b69d1a7a28071cb9fc219272e4dc6e755223426cc39e08bd98ca66e5f33":
        raise ValueError("unexpected U5Q-011 frozen prompt-payload SHA")
    if DEEPSEEK_MODEL != "deepseek-v4-pro":
        raise ValueError("post-hoc rerun requires frozen deepseek-v4-pro")

    if OUTPUT_DIR.exists() and any(OUTPUT_DIR.iterdir()):
        raise ValueError(f"refusing to overwrite existing post-hoc directory: {OUTPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)

    manifest = {
        "runner_version": RUNNER_VERSION,
        "scope": "U5Q-011 post-hoc exploratory provider-variability rerun",
        "question_id": QUESTION_ID,
        "diagnostic_only": True,
        "official_score_change_permitted": False,
        "official_u5q011_classification_remains": "persistent_provider_transport_failure",
        "official_primary_summary_sha256": sha256(primary_summary_path),
        "official_result_lock_sha256": sha256(OFFICIAL_RESULT_LOCK),
        "official_retry_summary_sha256": sha256(retry_summary_path),
        "official_retry_failure_sha256": sha256(retry_failure_path),
        "evidence_packs_sha256": sha256(PACKS_PATH),
        "prompt_payload_sha256": payload_sha,
        "provider": "deepseek",
        "provider_version": DEEPSEEK_PROVIDER_VERSION,
        "model": DEEPSEEK_MODEL,
        "hosted_qa_runner_version": HOSTED_QA_RUNNER_VERSION,
        "prompt_version": PROMPT_VERSION,
        "thinking": "enabled",
        "reasoning_effort": "high",
        "max_tokens": 4096,
        "retrieval_rerun": False,
        "permanent_ingestion": False,
        "policy": (
            "Explicitly post-hoc exploratory rerun requested by the user after the official primary request and the single permitted exact transport retry both failed. "
            "This run uses the same preserved question/evidence/prompt payload and frozen Layer C configuration. Any success demonstrates provider/run-to-run variability only and cannot replace, recover, rescore, or modify the locked official unseen temporary result."
        ),
    }
    (OUTPUT_DIR / "posthoc_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    provider = DeepSeekProvider(reasoning_effort="high", thinking_enabled=True, max_tokens=4096)
    started = time.monotonic()
    try:
        result = call_hosted_qa(
            question,
            evidence,
            model=DEEPSEEK_MODEL,
            provider=provider,
            reasoning_effort="high",
            max_tokens=4096,
            request_metadata={
                "unseen_u5q011_posthoc_extra_rerun": True,
                "diagnostic_only": True,
                "official_score_change_permitted": False,
                "question_id": QUESTION_ID,
                "prompt_payload_sha256": payload_sha,
                "official_result_lock_sha256": sha256(OFFICIAL_RESULT_LOCK),
            },
        )
    except Exception as exc:
        failure = {
            "question_id": QUESTION_ID,
            "prompt_payload_sha256": payload_sha,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "elapsed_seconds": time.monotonic() - started,
        }
        failure_path = OUTPUT_DIR / "failure.json"
        failure_path.write_text(json.dumps(failure, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        summary = {
            **manifest,
            "status": "failed",
            "success_count": 0,
            "failure_count": 1,
            "failure_sha256": sha256(failure_path),
        }
        (OUTPUT_DIR / "posthoc_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 2

    response = {
        "question_id": QUESTION_ID,
        "prompt_payload_sha256": payload_sha,
        "answer": result,
        "elapsed_seconds": time.monotonic() - started,
    }
    response_path = OUTPUT_DIR / "response.json"
    response_path.write_text(json.dumps(response, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = {
        **manifest,
        "status": "succeeded_posthoc_diagnostic_only",
        "success_count": 1,
        "failure_count": 0,
        "response_sha256": sha256(response_path),
    }
    (OUTPUT_DIR / "posthoc_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
