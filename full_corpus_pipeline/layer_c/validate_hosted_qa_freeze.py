#!/usr/bin/env python3
"""Validate the committed Layer C hosted-QA freeze against local artifacts.

The validator recomputes every recorded file hash it can resolve locally and checks
the frozen provider/model/prompt/schema/evidence policy. It never opens the sealed
final benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FREEZE = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json"
EXPECTED_VERSION = "e5-hosted-qa-freeze-v1.0"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def verify_hash(path_text: str, expected_sha: str, *, label: str) -> None:
    path = ROOT / path_text
    if not path.is_file():
        raise FileNotFoundError(f"{label}: {path}")
    actual = sha256(path)
    if actual != expected_sha:
        raise ValueError(f"{label} hash mismatch: expected {expected_sha}, got {actual}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    args = parser.parse_args()

    if not args.freeze.is_file():
        raise FileNotFoundError(args.freeze)
    freeze = load_json(args.freeze)

    if freeze.get("freeze_version") != EXPECTED_VERSION:
        raise ValueError("unexpected hosted-QA freeze version")
    if freeze.get("status") != "frozen":
        raise ValueError("hosted-QA freeze status is not frozen")

    provider = freeze.get("provider", {})
    expected_provider = {
        "name": "deepseek",
        "adapter_version": "deepseek-direct-v1.1",
        "model": "deepseek-v4-pro",
        "thinking": "enabled",
        "reasoning_effort": "high",
        "max_tokens": 4096,
        "temperature": None,
        "json_output": True,
    }
    for key, expected in expected_provider.items():
        if provider.get(key) != expected:
            raise ValueError(f"frozen provider field {key!r} differs: {provider.get(key)!r}")

    prompt = freeze.get("prompt", {})
    if prompt.get("version") != "e5-hosted-qa-prompt-v1.0-dev":
        raise ValueError("unexpected frozen prompt version")
    if prompt.get("runner_version") != "e5-hosted-qa-runner-v1.1":
        raise ValueError("unexpected frozen hosted-QA runner version")
    verify_hash(prompt["source_path"], prompt["source_sha256"], label="hosted_qa prompt/runner source")

    contract = freeze.get("response_contract", {})
    if contract.get("version") != "e5-hosted-qa-contract-v1.0":
        raise ValueError("unexpected frozen response-contract version")
    verify_hash(contract["path"], contract["sha256"], label="response contract")

    evidence = freeze.get("evidence", {})
    if evidence.get("production_condition") != "frozen_e5d_top5":
        raise ValueError("production evidence condition is not frozen E5-D top five")
    if evidence.get("retrieved_pack_version") != "e5-evidence-pack-v1.0":
        raise ValueError("unexpected retrieved evidence-pack version")
    if int(evidence.get("evidence_depth", -1)) != 5:
        raise ValueError("frozen evidence depth is not 5")
    verify_hash(
        evidence["retrieved_pack_path"], evidence["retrieved_pack_sha256"], label="retrieved evidence packs"
    )
    verify_hash(evidence["oracle_pack_path"], evidence["oracle_pack_sha256"], label="oracle evidence packs")

    benchmark = freeze.get("benchmark", {})
    if benchmark.get("retrieval_freeze_version") != "e5-retrieval-freeze-v1.0":
        raise ValueError("unexpected linked retrieval-freeze version")
    if int(benchmark.get("development_question_count", -1)) != 60:
        raise ValueError("unexpected development question count")
    verify_hash(
        benchmark["development_questions_path"],
        benchmark["development_questions_sha256"],
        label="development benchmark",
    )
    verify_hash(
        benchmark["retrieval_freeze_path"], benchmark["retrieval_freeze_sha256"], label="retrieval freeze"
    )

    for name, artifact in freeze.get("code_artifacts", {}).items():
        verify_hash(artifact["path"], artifact["sha256"], label=f"code artifact {name}")

    development = freeze.get("development_evidence", {})
    for condition in ("retrieved_first_pass", "transport_retry", "oracle"):
        row = development.get(condition, {})
        verify_hash(row["run_summary_path"], row["run_summary_sha256"], label=f"{condition} run summary")

    policies = freeze.get("policies", {})
    if policies.get("semantic_retry") is not False:
        raise ValueError("semantic retry must remain prohibited")
    if policies.get("retrieval_retuning_after_freeze") is not False:
        raise ValueError("retrieval retuning must remain prohibited")
    if policies.get("benchmark_reference_answer_exposed_to_model") is not False:
        raise ValueError("benchmark reference answers must not be exposed to the model")
    if policies.get("final_test_configuration_changes") is not False:
        raise ValueError("final-test configuration changes must remain prohibited")

    print(
        json.dumps(
            {
                "freeze_version": freeze["freeze_version"],
                "status": "valid",
                "provider": provider["name"],
                "model": provider["model"],
                "reasoning_effort": provider["reasoning_effort"],
                "evidence_depth": evidence["evidence_depth"],
                "final_benchmark_status": benchmark.get("final_benchmark_status"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
