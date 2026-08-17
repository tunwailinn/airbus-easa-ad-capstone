#!/usr/bin/env python3
"""Run one post-hoc exploratory recovery attempt for unseen U5Q-011.

This command exists only to study provider/run-to-run variability after the
human-approved unseen temporary result has already been locked. It MUST NOT
replace or modify the preserved primary run, the permitted exact retry, the
human-review lock, or the official unseen scores.

The question, evidence, prompt-payload SHA-256, provider/model, prompt, response
contract, thinking mode, reasoning effort and max-token limit are identical to
the preserved U5Q-011 request. Retrieval is not rerun.
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
PRIMARY = ROOT / "data_processed/evaluations/unseen_5/temporary_primary"
EVIDENCE_PACKS = PRIMARY / "evidence_packs.jsonl"
OFFICIAL_RETRY = ROOT / "data_processed/evaluations/unseen_5/temporary_transport_retry/U5Q-011"
OUTPUT_DIR = ROOT / "data_processed/evaluations/unseen_5/posthoc_extra_retry/U5Q-011"
HOSTED_FREEZE = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json"
RESULT_LOCK = UNSEEN_ROOT / "unseen_temporary_result_lock.json"
QUESTION_ID = "U5Q-011"
EXPECTED_PAYLOAD_SHA = "b17e0b69d1a7a28071cb9fc219272e4dc6e755223426cc39e08bd98ca66e5f33"
RUNNER_VERSION = "unseen-5-u5q011-posthoc-extra-retry-v1.0"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def unique_map(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = str(row[key])
        if value in output:
            raise ValueError(f"duplicate {key}: {value}")
        output[value] = row
    return output


def validate_frozen_state() -> None:
    subprocess.run(
        [sys.executable, "-m", "full_corpus_pipeline.layer_c.validate_unseen_temporary_result_lock"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "full_corpus_pipeline.layer_c.validate_hosted_qa_freeze",
            "--freeze",
            str(HOSTED_FREEZE),
        ],
        cwd=ROOT,
        check=True,
    )


def main() -> int:
    validate_frozen_state()

    for path in (
        RESULT_LOCK,
        PRIMARY / "run_summary.json",
        PRIMARY / "failures.jsonl",
        EVIDENCE_PACKS,
        OFFICIAL_RETRY / "retry_summary.json",
        OFFICIAL_RETRY / "failure.json",
        HOSTED_FREEZE,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    result_lock = json.loads(RESULT_LOCK.read_text(encoding="utf-8"))
    if result_lock.get("status") != "human_approved_and_locked":
        raise ValueError("official unseen temporary result is not locked")
    human_review = result_lock.get("human_review") or {}
    if human_review.get("technical_failure_ids") != [QUESTION_ID]:
        raise ValueError("official lock no longer records U5Q-011 as the sole technical failure")
    retry_lock = result_lock.get("transport_retry") or {}
    if retry_lock.get("question_id") != QUESTION_ID or retry_lock.get("status") != "failed":
        raise ValueError("official U5Q-011 retry is not preserved as failed")
    if retry_lock.get("further_retry_permitted") is not False:
        raise ValueError("official lock must prohibit any further official retry")

    primary_summary = json.loads((PRIMARY / "run_summary.json").read_text(encoding="utf-8"))
    if primary_summary.get("scope") != "five frozen unseen PDFs — temporary-document primary":
        raise ValueError("unexpected primary unseen run scope")
    if primary_summary.get("model") != "deepseek-v4-pro":
        raise ValueError("primary model differs from frozen DeepSeek V4 Pro")
    if primary_summary.get("thinking") != "enabled" or primary_summary.get("reasoning_effort") != "high":
        raise ValueError("primary reasoning configuration differs from freeze")
    if int(primary_summary.get("max_tokens", -1)) != 4096:
        raise ValueError("primary max_tokens differs from freeze")
    if primary_summary.get("prompt_version") != PROMPT_VERSION:
        raise ValueError("primary prompt version mismatch")
    if primary_summary.get("hosted_qa_runner_version") != HOSTED_QA_RUNNER_VERSION:
        raise ValueError("primary hosted-QA runner version mismatch")
    if primary_summary.get("evidence_packs_sha256") != sha256(EVIDENCE_PACKS):
        raise ValueError("preserved evidence-pack hash differs from primary run")
    if primary_summary.get("hosted_qa_freeze_sha256") != sha256(HOSTED_FREEZE):
        raise ValueError("hosted-QA freeze hash differs from primary run")

    primary_failures = unique_map(load_jsonl(PRIMARY / "failures.jsonl"), "question_id")
    if QUESTION_ID not in primary_failures:
        raise ValueError("U5Q-011 is not preserved as a primary technical failure")

    official_retry_summary = json.loads((OFFICIAL_RETRY / "retry_summary.json").read_text(encoding="utf-8"))
    if official_retry_summary.get("question_id") != QUESTION_ID or official_retry_summary.get("status") != "failed":
        raise ValueError("official retry state differs from the human-approved lock")

    packs = unique_map(load_jsonl(EVIDENCE_PACKS), "question_id")
    if QUESTION_ID not in packs:
        raise ValueError("preserved evidence pack for U5Q-011 is missing")
    pack = packs[QUESTION_ID]
    question, evidence, payload_sha = evidence_from_pack(pack)
    if payload_sha != EXPECTED_PAYLOAD_SHA:
        raise ValueError(f"unexpected U5Q-011 prompt-payload SHA: {payload_sha}")
    if payload_sha != primary_failures[QUESTION_ID].get("prompt_payload_sha256"):
        raise ValueError("post-hoc payload differs from preserved primary failure")
    if payload_sha != official_retry_summary.get("prompt_payload_sha256"):
        raise ValueError("post-hoc payload differs from preserved official retry")

    if DEEPSEEK_MODEL != "deepseek-v4-pro":
        raise ValueError("post-hoc recovery requires frozen deepseek-v4-pro")
    if OUTPUT_DIR.exists() and any(OUTPUT_DIR.iterdir()):
        raise ValueError(f"refusing to overwrite existing post-hoc recovery directory: {OUTPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)

    manifest = {
        "runner_version": RUNNER_VERSION,
        "scope": "U5Q-011 post-hoc exploratory recovery",
        "question_id": QUESTION_ID,
        "status": "started",
        "posthoc_only": True,
        "may_replace_official_result": False,
        "official_result_remains": {
            "semantic_pass_count": 13,
            "semantic_fail_count": 1,
            "persistent_technical_failure_count": 1,
            "strict_first_pass_end_to_end_success_rate": 13 / 15,
        },
        "official_result_lock_sha256": sha256(RESULT_LOCK),
        "primary_run_summary_sha256": sha256(PRIMARY / "run_summary.json"),
        "official_retry_summary_sha256": sha256(OFFICIAL_RETRY / "retry_summary.json"),
        "evidence_packs_sha256": sha256(EVIDENCE_PACKS),
        "prompt_payload_sha256": payload_sha,
        "hosted_qa_freeze_sha256": sha256(HOSTED_FREEZE),
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
            "Exploratory post-hoc provider-variability probe only. It reuses the exact preserved U5Q-011 "
            "question and evidence payload under the frozen Layer C configuration. Success or failure may be "
            "reported as a supplementary recovery observation but cannot replace the human-approved primary "
            "unseen result or its official failed retry."
        ),
    }
    (OUTPUT_DIR / "posthoc_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    provider = DeepSeekProvider(reasoning_effort="high", thinking_enabled=True, max_tokens=4096)
    started = time.monotonic()
    try:
        answer = call_hosted_qa(
            question,
            evidence,
            model=DEEPSEEK_MODEL,
            provider=provider,
            reasoning_effort="high",
            max_tokens=4096,
            request_metadata={
                "unseen_u5q011_posthoc_extra_retry": True,
                "posthoc_only": True,
                "question_id": QUESTION_ID,
                "prompt_payload_sha256": payload_sha,
                "official_result_lock_sha256": manifest["official_result_lock_sha256"],
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
        "answer": answer,
        "elapsed_seconds": time.monotonic() - started,
    }
    response_path = OUTPUT_DIR / "response.json"
    response_path.write_text(json.dumps(response, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = {
        **manifest,
        "status": "recovered_posthoc",
        "success_count": 1,
        "failure_count": 0,
        "response_sha256": sha256(response_path),
        "interpretation": (
            "Post-hoc recovery under identical preserved evidence/config indicates provider or run-to-run "
            "variability. The official locked U5Q-011 technical-failure classification remains unchanged."
        ),
    }
    (OUTPUT_DIR / "posthoc_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
