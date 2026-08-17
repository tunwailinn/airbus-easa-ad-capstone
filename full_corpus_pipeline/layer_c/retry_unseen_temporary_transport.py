#!/usr/bin/env python3
"""Perform one audited exact transport retry for a failed unseen temporary-QA request.

The original five-PDF temporary primary run is immutable. A retry is allowed only
for a preserved technical/provider failure that is absent from the original
responses and whose prompt-payload SHA-256 exactly matches the preserved evidence
pack. Retrieval is not rerun and no semantic setting may change.
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
UNSEEN_ROOT = ROOT / "evaluation_sets/unseen_incoming_5_v1"
DEFAULT_PRIMARY = ROOT / "data_processed/evaluations/unseen_5/temporary_primary"
DEFAULT_PACKS = DEFAULT_PRIMARY / "evidence_packs.jsonl"
DEFAULT_RETRY_ROOT = ROOT / "data_processed/evaluations/unseen_5/temporary_transport_retry"
DEFAULT_HOSTED_FREEZE = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json"
RETRY_RUNNER_VERSION = "unseen-5-temporary-transport-retry-v1.0"


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
        [sys.executable, "-m", "full_corpus_pipeline.layer_c.validate_unseen_question_lock"],
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
    parser.add_argument("--primary-run-dir", type=Path, default=DEFAULT_PRIMARY)
    parser.add_argument("--evidence-packs", type=Path, default=DEFAULT_PACKS)
    parser.add_argument("--hosted-freeze", type=Path, default=DEFAULT_HOSTED_FREEZE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_RETRY_ROOT)
    args = parser.parse_args()

    validate_locks(args.hosted_freeze)
    qid = str(args.question_id)

    summary_path = args.primary_run_dir / "run_summary.json"
    responses_path = args.primary_run_dir / "responses.jsonl"
    failures_path = args.primary_run_dir / "failures.jsonl"
    for path in (summary_path, responses_path, failures_path, args.evidence_packs, args.hosted_freeze):
        if not path.is_file():
            raise FileNotFoundError(path)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("scope") != "five frozen unseen PDFs — temporary-document primary":
        raise ValueError("original run is not the frozen unseen temporary primary run")
    if summary.get("permanent_ingestion_started") is not False:
        raise ValueError("unexpected permanent-ingestion state in original unseen run")
    if summary.get("model") != "deepseek-v4-pro":
        raise ValueError("original unseen model differs from frozen deepseek-v4-pro")
    if summary.get("reasoning_effort") != "high" or summary.get("thinking") != "enabled":
        raise ValueError("original unseen reasoning configuration differs from the freeze")
    if int(summary.get("max_tokens", -1)) != 4096:
        raise ValueError("original unseen max_tokens differs from frozen 4096")
    if summary.get("prompt_version") != PROMPT_VERSION:
        raise ValueError("original unseen prompt version mismatch")
    if summary.get("hosted_qa_runner_version") != HOSTED_QA_RUNNER_VERSION:
        raise ValueError("original unseen hosted-QA runner version mismatch")

    responses = unique_map(load_jsonl(responses_path), "question_id")
    failures = unique_map(load_jsonl(failures_path), "question_id")
    if qid in responses:
        raise ValueError(f"{qid} already succeeded in the original unseen run; semantic retry is prohibited")
    if qid not in failures:
        raise ValueError(f"{qid} is not a preserved original unseen transport/provider failure")

    packs = unique_map(load_jsonl(args.evidence_packs), "question_id")
    if qid not in packs:
        raise ValueError(f"no preserved unseen evidence pack for {qid}")
    pack = packs[qid]
    question, evidence, payload_sha = evidence_from_pack(pack)
    original_failure = failures[qid]
    if payload_sha != original_failure.get("prompt_payload_sha256"):
        raise ValueError("retry prompt-payload hash differs from the preserved failed request")

    if summary.get("evidence_packs_sha256") != sha256(args.evidence_packs):
        raise ValueError("unseen evidence-pack file hash differs from the primary run")
    if summary.get("hosted_qa_freeze_sha256") != sha256(args.hosted_freeze):
        raise ValueError("hosted-QA freeze hash differs from the primary unseen run")
    if DEEPSEEK_MODEL != "deepseek-v4-pro":
        raise ValueError("exact unseen retry requires frozen deepseek-v4-pro")

    retry_dir = args.output_root / qid
    if retry_dir.exists() and any(retry_dir.iterdir()):
        raise ValueError(f"refusing to overwrite existing unseen retry directory: {retry_dir}")
    retry_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "runner_version": RETRY_RUNNER_VERSION,
        "scope": "five frozen unseen PDFs — exact temporary transport retry",
        "question_id": qid,
        "retry_type": "exact_transport_only",
        "original_primary_summary_sha256": sha256(summary_path),
        "original_failure": original_failure,
        "evidence_packs_sha256": sha256(args.evidence_packs),
        "prompt_payload_sha256": payload_sha,
        "hosted_qa_freeze_sha256": sha256(args.hosted_freeze),
        "provider": "deepseek",
        "provider_version": DEEPSEEK_PROVIDER_VERSION,
        "model": DEEPSEEK_MODEL,
        "hosted_qa_runner_version": HOSTED_QA_RUNNER_VERSION,
        "prompt_version": PROMPT_VERSION,
        "thinking": "enabled",
        "reasoning_effort": "high",
        "max_tokens": 4096,
        "permanent_ingestion": False,
        "policy": (
            "One exact retry of a preserved technical/provider failure. The original primary run remains "
            "unchanged. Question, evidence, prompt payload hash, provider/model, prompt, response contract, "
            "thinking mode, reasoning effort and max-token limit are identical; retrieval is not rerun."
        ),
    }
    (retry_dir / "retry_manifest.json").write_text(
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
                "unseen_temporary_exact_transport_retry": True,
                "question_id": qid,
                "prompt_payload_sha256": payload_sha,
                "original_primary_summary_sha256": sha256(summary_path),
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
        failure_path = retry_dir / "failure.json"
        failure_path.write_text(json.dumps(failure, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        retry_summary = {
            **manifest,
            "status": "failed",
            "success_count": 0,
            "failure_count": 1,
            "failure_sha256": sha256(failure_path),
        }
        (retry_dir / "retry_summary.json").write_text(
            json.dumps(retry_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(json.dumps(retry_summary, indent=2, ensure_ascii=False))
        return 2

    response = {
        "question_id": qid,
        "prompt_payload_sha256": payload_sha,
        "answer": result,
        "elapsed_seconds": time.monotonic() - started,
    }
    response_path = retry_dir / "response.json"
    response_path.write_text(json.dumps(response, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    retry_summary = {
        **manifest,
        "status": "recovered",
        "success_count": 1,
        "failure_count": 0,
        "response_sha256": sha256(response_path),
    }
    (retry_dir / "retry_summary.json").write_text(
        json.dumps(retry_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(retry_summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
