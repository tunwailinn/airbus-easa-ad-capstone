#!/usr/bin/env python3
"""Perform one audited exact transport retry for a failed final-oracle request.

This utility is diagnostic-only. It never edits or replaces the original oracle run.
A retry is allowed only when the selected question is present in the original
`failures.jsonl`, absent from the original `responses.jsonl`, and the exact
prompt-payload hash in the evidence pack matches the preserved failure record.

The DeepSeek provider/model, prompt, response contract, thinking mode, reasoning
effort, max-token limit, question text, and evidence are unchanged. There is no
semantic retry and no retrieval rerun.
"""

from __future__ import annotations

import argparse
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
BENCHMARK_ROOT = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1"
DEFAULT_PACKS = ROOT / "data_processed/evaluations/e5/layer_c/final/oracle/evidence_packs.jsonl"
DEFAULT_ORIGINAL_RUN = ROOT / "data_processed/evaluations/e5/layer_c/final/oracle/run"
DEFAULT_RETRY_ROOT = ROOT / "data_processed/evaluations/e5/layer_c/final/oracle/transport_retry"
DEFAULT_HOSTED_FREEZE = BENCHMARK_ROOT / "hosted_qa_freeze.json"
RETRY_RUNNER_VERSION = "e5-layer-c-final-oracle-transport-retry-v1.0"


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


def validate_locks(hosted_freeze: Path) -> None:
    subprocess.run(
        [sys.executable, "-m", "full_corpus_pipeline.layer_c.validate_final_benchmark_lock"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "full_corpus_pipeline.layer_c.validate_hosted_qa_freeze",
            "--freeze",
            str(hosted_freeze),
        ],
        cwd=ROOT,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question-id", required=True)
    parser.add_argument("--evidence-packs", type=Path, default=DEFAULT_PACKS)
    parser.add_argument("--original-run-dir", type=Path, default=DEFAULT_ORIGINAL_RUN)
    parser.add_argument("--hosted-freeze", type=Path, default=DEFAULT_HOSTED_FREEZE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_RETRY_ROOT)
    args = parser.parse_args()

    validate_locks(args.hosted_freeze)
    qid = str(args.question_id)

    original_summary_path = args.original_run_dir / "run_summary.json"
    original_responses_path = args.original_run_dir / "responses.jsonl"
    original_failures_path = args.original_run_dir / "failures.jsonl"
    for path in (
        args.evidence_packs,
        args.hosted_freeze,
        original_summary_path,
        original_responses_path,
        original_failures_path,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    original_summary = json.loads(original_summary_path.read_text(encoding="utf-8"))
    if original_summary.get("scope") != "E5 final oracle diagnostic":
        raise ValueError("original run is not the E5 final oracle diagnostic")
    if original_summary.get("diagnostic_only") is not True:
        raise ValueError("original oracle run is not diagnostic-only")
    if original_summary.get("model") != "deepseek-v4-pro":
        raise ValueError("original oracle model differs from frozen deepseek-v4-pro")
    if original_summary.get("reasoning_effort") != "high":
        raise ValueError("original oracle reasoning effort differs from frozen high")
    if int(original_summary.get("max_tokens", -1)) != 4096:
        raise ValueError("original oracle max_tokens differs from frozen 4096")
    if original_summary.get("thinking") != "enabled":
        raise ValueError("original oracle thinking mode differs from frozen enabled")
    if original_summary.get("prompt_version") != PROMPT_VERSION:
        raise ValueError("original oracle prompt version differs from current frozen prompt")
    if original_summary.get("hosted_qa_runner_version") != HOSTED_QA_RUNNER_VERSION:
        raise ValueError("original oracle hosted-QA runner version mismatch")

    responses = unique_map(load_jsonl(original_responses_path), "question_id")
    failures = unique_map(load_jsonl(original_failures_path), "question_id")
    if qid in responses:
        raise ValueError(f"{qid} already succeeded in the original oracle run; semantic retry is prohibited")
    if qid not in failures:
        raise ValueError(f"{qid} is not a preserved original oracle failure")

    packs = unique_map(load_jsonl(args.evidence_packs), "question_id")
    if qid not in packs:
        raise ValueError(f"no oracle evidence pack for {qid}")
    pack = packs[qid]
    question, evidence, payload_sha = evidence_from_pack(pack)
    original_failure = failures[qid]
    if payload_sha != original_failure.get("prompt_payload_sha256"):
        raise ValueError("retry prompt-payload hash differs from preserved failed request")

    expected_pack_sha = original_summary.get("evidence_pack_sha256")
    if expected_pack_sha != sha256(args.evidence_packs):
        raise ValueError("oracle evidence-pack file hash differs from the original run")
    expected_freeze_sha = original_summary.get("hosted_qa_freeze_sha256")
    if expected_freeze_sha != sha256(args.hosted_freeze):
        raise ValueError("hosted-QA freeze hash differs from the original run")
    if DEEPSEEK_MODEL != "deepseek-v4-pro":
        raise ValueError("frozen final oracle transport retry requires deepseek-v4-pro")

    retry_dir = args.output_root / qid
    if retry_dir.exists() and any(retry_dir.iterdir()):
        raise ValueError(f"refusing to overwrite existing transport-retry directory: {retry_dir}")
    retry_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "runner_version": RETRY_RUNNER_VERSION,
        "scope": "E5 final oracle exact transport retry",
        "diagnostic_only": True,
        "question_id": qid,
        "retry_type": "exact_transport_only",
        "original_run_summary_path": str(original_summary_path),
        "original_run_summary_sha256": sha256(original_summary_path),
        "original_failures_sha256": sha256(original_failures_path),
        "original_failure": original_failure,
        "evidence_pack_path": str(args.evidence_packs),
        "evidence_pack_sha256": sha256(args.evidence_packs),
        "prompt_payload_sha256": payload_sha,
        "provider": "deepseek",
        "provider_version": DEEPSEEK_PROVIDER_VERSION,
        "model": DEEPSEEK_MODEL,
        "hosted_qa_runner_version": HOSTED_QA_RUNNER_VERSION,
        "prompt_version": PROMPT_VERSION,
        "thinking": "enabled",
        "reasoning_effort": "high",
        "max_tokens": 4096,
        "temperature": None,
        "policy": (
            "One exact transport retry of a preserved technical/provider failure. Question text, evidence, "
            "prompt payload hash, provider/model, prompt, response contract, thinking mode, reasoning effort "
            "and max-token limit are unchanged. The original failure remains authoritative audit evidence; "
            "this retry is diagnostic-only and cannot replace the strict primary final result."
        ),
    }
    (retry_dir / "retry_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    provider = DeepSeekProvider(
        reasoning_effort="high",
        thinking_enabled=True,
        max_tokens=4096,
    )
    started = time.monotonic()
    response_path = retry_dir / "response.json"
    failure_path = retry_dir / "failure.json"
    try:
        result = call_hosted_qa(
            question,
            evidence,
            model=DEEPSEEK_MODEL,
            provider=provider,
            reasoning_effort="high",
            max_tokens=4096,
            request_metadata={
                "layer_c_run_id": "e5-final-oracle-transport-retry",
                "question_id": qid,
                "prompt_payload_sha256": payload_sha,
                "evidence_condition": "oracle_reference_evidence",
                "diagnostic_only": True,
                "retry_type": "exact_transport_only",
                "original_run_summary_sha256": sha256(original_summary_path),
            },
        )
    except Exception as exc:
        failure = {
            "question_id": qid,
            "prompt_payload_sha256": payload_sha,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "elapsed_seconds": time.monotonic() - started,
        }
        failure_path.write_text(json.dumps(failure, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        summary = {
            **manifest,
            "status": "failed",
            "success_count": 0,
            "failure_count": 1,
            "elapsed_seconds": time.monotonic() - started,
            "failure_sha256": sha256(failure_path),
        }
        (retry_dir / "retry_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 2

    response = {
        "question_id": qid,
        "prompt_payload_sha256": payload_sha,
        "answer": result,
        "elapsed_seconds": time.monotonic() - started,
    }
    response_path.write_text(json.dumps(response, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = {
        **manifest,
        "status": "recovered",
        "success_count": 1,
        "failure_count": 0,
        "elapsed_seconds": time.monotonic() - started,
        "response_sha256": sha256(response_path),
    }
    (retry_dir / "retry_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
