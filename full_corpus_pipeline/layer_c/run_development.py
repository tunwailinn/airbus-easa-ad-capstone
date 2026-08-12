#!/usr/bin/env python3
"""Run Layer C hosted QA over frozen E5 development evidence packs.

This is a development-only runner. It never opens the final benchmark and never
runs retrieval. The model name and generation temperature must be explicit so
provider/model selection remains an auditable development decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from full_corpus_pipeline.layer_c.hosted_qa import (
    HOSTED_QA_RUNNER_VERSION,
    PROMPT_VERSION,
    call_hosted_qa,
    evidence_from_pack,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PACKS = ROOT / "data_processed/evaluations/e5/layer_c/development/evidence_packs.jsonl"
DEFAULT_OUTPUT_DIR = ROOT / "data_processed/evaluations/e5/layer_c/development/runs"
BATCH_RUNNER_VERSION = "e5-layer-c-development-runner-v1.0"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_packs(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 60:
        raise ValueError(f"expected 60 Layer C development evidence packs, found {len(rows)}")
    ids = [str(row["question_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate Layer C development question IDs")
    for row in rows:
        if row.get("evidence_pack_version") != "e5-evidence-pack-v1.0":
            raise ValueError("unexpected Layer C evidence pack version")
        if row.get("retrieval_freeze_version") != "e5-retrieval-freeze-v1.0":
            raise ValueError("development evidence pack is not tied to the frozen E5 retrieval")
        if int(row.get("evidence_depth", -1)) != 5:
            raise ValueError("development evidence depth must remain frozen at 5")
    return rows


def safe_run_name(value: str) -> str:
    rendered = "".join(char if char.isalnum() or char in "-_." else "-" for char in value)
    return rendered.strip("-.") or "model"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-packs", type=Path, default=DEFAULT_PACKS)
    parser.add_argument("--model", required=True)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--run-id")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--question-id", action="append", default=[])
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    if args.temperature < 0:
        raise ValueError("temperature must be non-negative")
    packs = load_packs(args.evidence_packs)
    selected_ids = set(args.question_id)
    if selected_ids:
        packs = [row for row in packs if str(row["question_id"]) in selected_ids]
        missing = selected_ids - {str(row["question_id"]) for row in packs}
        if missing:
            raise ValueError(f"unknown development question IDs: {sorted(missing)}")
    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError("--limit must be positive")
        packs = packs[: args.limit]

    run_id = args.run_id or f"dev-{safe_run_name(args.model)}-t{args.temperature:g}"
    run_dir = args.output_dir / run_id
    if run_dir.exists() and any(run_dir.iterdir()):
        raise ValueError(f"refusing to overwrite non-empty Layer C run directory: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    responses_path = run_dir / "responses.jsonl"
    failures_path = run_dir / "failures.jsonl"

    manifest: dict[str, Any] = {
        "batch_runner_version": BATCH_RUNNER_VERSION,
        "hosted_qa_runner_version": HOSTED_QA_RUNNER_VERSION,
        "prompt_version": PROMPT_VERSION,
        "run_id": run_id,
        "scope": "E5 development only",
        "model": args.model,
        "temperature": args.temperature,
        "evidence_pack_path": str(args.evidence_packs),
        "evidence_pack_sha256": file_sha256(args.evidence_packs),
        "selected_question_count": len(packs),
        "policy": (
            "No retrieval is run or retuned. Each request receives only the frozen Layer C "
            "prompt payload. Failed requests are logged; this runner does not perform semantic retries."
        ),
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    success_count = 0
    failure_count = 0
    started = time.monotonic()
    with responses_path.open("w", encoding="utf-8") as response_handle, failures_path.open(
        "w", encoding="utf-8"
    ) as failure_handle:
        for position, pack in enumerate(packs, 1):
            qid = str(pack["question_id"])
            print(f"[progress] Layer C development QA: {position}/{len(packs)} ({qid})", flush=True)
            question, evidence, payload_sha = evidence_from_pack(pack)
            request_started = time.monotonic()
            try:
                result = call_hosted_qa(
                    question,
                    evidence,
                    model=args.model,
                    temperature=args.temperature,
                    request_metadata={
                        "layer_c_run_id": run_id,
                        "question_id": qid,
                        "prompt_payload_sha256": payload_sha,
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
            row = {
                "question_id": qid,
                "prompt_payload_sha256": payload_sha,
                "answer": result,
                "elapsed_seconds": time.monotonic() - request_started,
            }
            response_handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            response_handle.flush()

    summary = {
        **manifest,
        "success_count": success_count,
        "failure_count": failure_count,
        "elapsed_seconds": time.monotonic() - started,
        "responses_path": str(responses_path),
        "responses_sha256": file_sha256(responses_path),
        "failures_path": str(failures_path),
        "failures_sha256": file_sha256(failures_path),
    }
    (run_dir / "run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("[progress] Layer C development QA run finished", flush=True)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if failure_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
