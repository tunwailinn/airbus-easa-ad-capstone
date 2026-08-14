#!/usr/bin/env python3
"""Run frozen DeepSeek Layer C QA over the final oracle/reference-evidence condition.

This is a post-hoc diagnostic executed only after the strict one-time primary final
result has been preserved. It keeps provider, model, prompt, thinking mode,
reasoning effort, max tokens, response contract and evidence depth policy frozen.
Only the evidence source changes from retrieved E5-D top-5 evidence to the
prebuilt final oracle/reference-evidence packs.

The oracle result must never replace the primary final benchmark score.
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

from full_corpus_pipeline.layer_c.build_final_oracle_evidence_packs import (
    FINAL_ORACLE_EVIDENCE_PACK_VERSION,
)
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
DEFAULT_OUTPUT_DIR = ROOT / "data_processed/evaluations/e5/layer_c/final/oracle/run"
DEFAULT_QUESTIONS = BENCHMARK_ROOT / "final_questions.jsonl"
DEFAULT_HOSTED_FREEZE = BENCHMARK_ROOT / "hosted_qa_freeze.json"
FINAL_ORACLE_RUNNER_VERSION = "e5-layer-c-final-oracle-runner-v1.0"
FINAL_QUESTION_COUNT = 40


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def load_packs(path: Path, final_questions_sha256: str) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != FINAL_QUESTION_COUNT:
        raise ValueError(f"expected 40 final oracle evidence packs, found {len(rows)}")
    ids = [str(row["question_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate final oracle question IDs")
    for row in rows:
        if row.get("evidence_pack_version") != FINAL_ORACLE_EVIDENCE_PACK_VERSION:
            raise ValueError("unexpected final oracle evidence-pack version")
        if row.get("evidence_condition") != "oracle_reference_evidence":
            raise ValueError("final oracle pack has unexpected evidence condition")
        if row.get("final_questions_sha256") != final_questions_sha256:
            raise ValueError("final oracle pack is tied to a different final benchmark")
        depth = int(row.get("evidence_depth", -1))
        max_depth = int(row.get("evidence_max_depth", -1))
        if depth < 0 or depth > 5 or max_depth != 5:
            raise ValueError("final oracle evidence depth is invalid")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-packs", type=Path, default=DEFAULT_PACKS)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--hosted-freeze", type=Path, default=DEFAULT_HOSTED_FREEZE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    validate_locks(args.hosted_freeze)
    for path in (args.evidence_packs, args.questions, args.hosted_freeze):
        if not path.is_file():
            raise FileNotFoundError(path)

    if DEEPSEEK_MODEL != "deepseek-v4-pro":
        raise ValueError("frozen final oracle requires deepseek-v4-pro")

    final_questions_sha = sha256(args.questions)
    packs = load_packs(args.evidence_packs, final_questions_sha)

    # Exact frozen Layer C generation configuration.
    provider = DeepSeekProvider(
        reasoning_effort="high",
        thinking_enabled=True,
        max_tokens=4096,
    )

    run_dir = args.output_dir
    if run_dir.exists() and any(run_dir.iterdir()):
        raise ValueError(f"refusing to overwrite non-empty final oracle run directory: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    responses_path = run_dir / "responses.jsonl"
    failures_path = run_dir / "failures.jsonl"

    manifest: dict[str, Any] = {
        "runner_version": FINAL_ORACLE_RUNNER_VERSION,
        "hosted_qa_runner_version": HOSTED_QA_RUNNER_VERSION,
        "prompt_version": PROMPT_VERSION,
        "scope": "E5 final oracle diagnostic",
        "diagnostic_only": True,
        "evidence_condition": "oracle_reference_evidence",
        "provider": "deepseek",
        "provider_version": DEEPSEEK_PROVIDER_VERSION,
        "model": DEEPSEEK_MODEL,
        "thinking": "enabled",
        "reasoning_effort": "high",
        "max_tokens": 4096,
        "temperature": None,
        "temperature_policy": "not used: DeepSeek thinking mode ignores sampling temperature",
        "final_questions_path": str(args.questions),
        "final_questions_sha256": final_questions_sha,
        "hosted_qa_freeze_path": str(args.hosted_freeze),
        "hosted_qa_freeze_sha256": sha256(args.hosted_freeze),
        "evidence_pack_path": str(args.evidence_packs),
        "evidence_pack_sha256": sha256(args.evidence_packs),
        "selected_question_count": len(packs),
        "policy": (
            "Post-hoc final oracle diagnostic only. The DeepSeek provider/model, prompt, response contract, "
            "thinking mode, reasoning effort and max-token limit remain identical to the strict primary final "
            "condition. Only evidence changes. No retrieval is rerun or retuned, no semantic retry is allowed, "
            "and this result cannot replace the strict primary final score."
        ),
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    success_count = 0
    failure_count = 0
    started = time.monotonic()
    with responses_path.open("w", encoding="utf-8") as response_handle, failures_path.open(
        "w", encoding="utf-8"
    ) as failure_handle:
        for position, pack in enumerate(packs, 1):
            qid = str(pack["question_id"])
            print(f"[progress] final oracle QA: {position}/{len(packs)} ({qid})", flush=True)
            question, evidence, payload_sha = evidence_from_pack(pack)
            request_started = time.monotonic()
            try:
                result = call_hosted_qa(
                    question,
                    evidence,
                    model=DEEPSEEK_MODEL,
                    provider=provider,
                    reasoning_effort="high",
                    max_tokens=4096,
                    request_metadata={
                        "layer_c_run_id": "e5-final-oracle",
                        "question_id": qid,
                        "prompt_payload_sha256": payload_sha,
                        "evidence_condition": "oracle_reference_evidence",
                        "diagnostic_only": True,
                    },
                )
            except Exception as exc:
                failure_count += 1
                failure = {
                    "question_id": qid,
                    "prompt_payload_sha256": payload_sha,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "elapsed_seconds": time.monotonic() - request_started,
                }
                failure_handle.write(json.dumps(failure, ensure_ascii=False) + "\n")
                failure_handle.flush()
                continue

            success_count += 1
            response_handle.write(
                json.dumps(
                    {
                        "question_id": qid,
                        "prompt_payload_sha256": payload_sha,
                        "answer": result,
                        "elapsed_seconds": time.monotonic() - request_started,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            response_handle.flush()

    summary = {
        **manifest,
        "status": "completed" if failure_count == 0 else "completed_with_failures",
        "success_count": success_count,
        "failure_count": failure_count,
        "elapsed_seconds": time.monotonic() - started,
        "responses_path": str(responses_path),
        "responses_sha256": sha256(responses_path),
        "failures_path": str(failures_path),
        "failures_sha256": sha256(failures_path),
    }
    (run_dir / "run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("[progress] final oracle QA run finished", flush=True)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if failure_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
