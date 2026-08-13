#!/usr/bin/env python3
"""Build the Layer C hosted-QA freeze from completed development artifacts.

This command is development-only. It validates the selected DeepSeek configuration,
retrieved-evidence development run, oracle-evidence run, frozen benchmark and code
artifacts, then writes a machine-readable freeze. It never reads the sealed final
benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from full_corpus_pipeline.layer_c.hosted_qa import HOSTED_QA_RUNNER_VERSION, PROMPT_VERSION
from full_corpus_pipeline.layer_c.providers.deepseek import (
    DEEPSEEK_MODEL,
    DEEPSEEK_PROVIDER_VERSION,
)


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_ROOT = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1"
DEVELOPMENT_ROOT = ROOT / "data_processed/evaluations/e5/layer_c/development"

DEFAULT_RETRIEVAL_FREEZE = BENCHMARK_ROOT / "retrieval_freeze.json"
DEFAULT_QUESTIONS = BENCHMARK_ROOT / "development_questions.jsonl"
DEFAULT_RETRIEVED_PACKS = DEVELOPMENT_ROOT / "evidence_packs.jsonl"
DEFAULT_ORACLE_PACKS = DEVELOPMENT_ROOT / "oracle_evidence_packs.jsonl"
DEFAULT_DEVELOPMENT_RUN = DEVELOPMENT_ROOT / "runs/deepseek-v4-pro-high-development-60/run_summary.json"
DEFAULT_TRANSPORT_RETRY_RUN = DEVELOPMENT_ROOT / "runs/deepseek-v4-pro-high-e5d034-transport-retry/run_summary.json"
DEFAULT_ORACLE_RUN = DEVELOPMENT_ROOT / "oracle_runs/deepseek-v4-pro-high-oracle-60/run_summary.json"
DEFAULT_OUTPUT = BENCHMARK_ROOT / "hosted_qa_freeze.json"

FREEZE_VERSION = "e5-hosted-qa-freeze-v1.0"
FREEZE_DATE = "2026-08-13"
CONTRACT_VERSION = "e5-hosted-qa-contract-v1.0"
EVIDENCE_PACK_VERSION = "e5-evidence-pack-v1.0"
ORACLE_EVIDENCE_PACK_VERSION = "e5-oracle-evidence-pack-v1.0"
EVIDENCE_DEPTH = 5

CODE_ARTIFACTS = {
    "hosted_qa": ROOT / "full_corpus_pipeline/layer_c/hosted_qa.py",
    "response_contract": ROOT / "full_corpus_pipeline/layer_c/hosted_qa_contract.schema.json",
    "provider_adapter": ROOT / "full_corpus_pipeline/layer_c/providers/deepseek.py",
    "retrieved_evidence_builder": ROOT / "full_corpus_pipeline/layer_c/build_evidence_packs.py",
    "development_runner": ROOT / "full_corpus_pipeline/layer_c/run_development.py",
    "development_evaluator": ROOT / "full_corpus_pipeline/layer_c/evaluate_development.py",
    "oracle_evidence_builder": ROOT / "full_corpus_pipeline/layer_c/build_oracle_evidence_packs.py",
    "oracle_runner": ROOT / "full_corpus_pipeline/layer_c/run_oracle_development.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)


def validate_selected_run(
    summary: dict[str, Any],
    *,
    expected_condition: str,
    expected_count: int,
) -> None:
    if summary.get("model") != DEEPSEEK_MODEL:
        raise ValueError("development artifact model does not match selected DeepSeek model")
    if summary.get("provider") != "deepseek":
        raise ValueError("development artifact provider is not DeepSeek")
    if summary.get("provider_version") != DEEPSEEK_PROVIDER_VERSION:
        raise ValueError("development artifact provider adapter version differs from current adapter")
    if summary.get("hosted_qa_runner_version") != HOSTED_QA_RUNNER_VERSION:
        raise ValueError("development artifact hosted-QA runner version differs from current runner")
    if summary.get("prompt_version") != PROMPT_VERSION:
        raise ValueError("development artifact prompt version differs from current prompt")
    if summary.get("thinking") != "enabled":
        raise ValueError("selected Layer C freeze requires DeepSeek thinking mode enabled")
    if summary.get("reasoning_effort") != "high":
        raise ValueError("selected Layer C freeze requires reasoning_effort=high")
    if int(summary.get("max_tokens", -1)) != 4096:
        raise ValueError("selected Layer C freeze requires max_tokens=4096")
    if summary.get("temperature") is not None:
        raise ValueError("selected Layer C freeze requires no temperature setting in thinking mode")
    if int(summary.get("selected_question_count", -1)) != expected_count:
        raise ValueError("development artifact question count is not the expected frozen count")

    actual_condition = str(summary.get("evidence_condition") or "retrieved_e5d_top5")
    if actual_condition != expected_condition:
        raise ValueError(
            f"unexpected evidence condition: expected {expected_condition!r}, got {actual_condition!r}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retrieval-freeze", type=Path, default=DEFAULT_RETRIEVAL_FREEZE)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--retrieved-packs", type=Path, default=DEFAULT_RETRIEVED_PACKS)
    parser.add_argument("--oracle-packs", type=Path, default=DEFAULT_ORACLE_PACKS)
    parser.add_argument("--development-run", type=Path, default=DEFAULT_DEVELOPMENT_RUN)
    parser.add_argument("--transport-retry-run", type=Path, default=DEFAULT_TRANSPORT_RETRY_RUN)
    parser.add_argument("--oracle-run", type=Path, default=DEFAULT_ORACLE_RUN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    required_paths = [
        args.retrieval_freeze,
        args.questions,
        args.retrieved_packs,
        args.oracle_packs,
        args.development_run,
        args.transport_retry_run,
        args.oracle_run,
        *CODE_ARTIFACTS.values(),
    ]
    for path in required_paths:
        require_file(path)

    retrieval_freeze = load_json(args.retrieval_freeze)
    if retrieval_freeze.get("freeze_version") != "e5-retrieval-freeze-v1.0":
        raise ValueError("unexpected retrieval freeze version")

    benchmark_sha = sha256(args.questions)
    expected_benchmark = retrieval_freeze.get("development_benchmark", {})
    if benchmark_sha != expected_benchmark.get("sha256"):
        raise ValueError("development benchmark hash differs from retrieval freeze")
    if int(expected_benchmark.get("question_count", -1)) != 60:
        raise ValueError("retrieval freeze does not declare the 60-question development benchmark")

    development_run = load_json(args.development_run)
    validate_selected_run(
        development_run,
        expected_condition="retrieved_e5d_top5",
        expected_count=60,
    )
    if sha256(args.retrieved_packs) != development_run.get("evidence_pack_sha256"):
        raise ValueError("retrieved evidence-pack hash differs from the selected development run")
    if int(development_run.get("success_count", -1)) != 59 or int(
        development_run.get("failure_count", -1)
    ) != 1:
        raise ValueError("selected first-pass development run is not the audited 59/60 artifact")

    retry_run = load_json(args.transport_retry_run)
    validate_selected_run(
        retry_run,
        expected_condition="retrieved_e5d_top5",
        expected_count=1,
    )
    if int(retry_run.get("success_count", -1)) != 1 or int(retry_run.get("failure_count", -1)) != 0:
        raise ValueError("audited E5D-034 transport retry is not 1/1 successful")
    if retry_run.get("evidence_pack_sha256") != development_run.get("evidence_pack_sha256"):
        raise ValueError("transport retry did not use the exact retrieved evidence-pack artifact")

    oracle_run = load_json(args.oracle_run)
    validate_selected_run(
        oracle_run,
        expected_condition="oracle_reference_evidence",
        expected_count=60,
    )
    if sha256(args.oracle_packs) != oracle_run.get("evidence_pack_sha256"):
        raise ValueError("oracle evidence-pack hash differs from the selected oracle run")
    if int(oracle_run.get("success_count", -1)) != 60 or int(oracle_run.get("failure_count", -1)) != 0:
        raise ValueError("selected oracle development run is not the audited 60/60 artifact")

    contract = load_json(CODE_ARTIFACTS["response_contract"])
    if contract.get("$id") != CONTRACT_VERSION:
        raise ValueError("response contract ID differs from selected freeze contract")

    code_hashes = {
        name: {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256(path),
        }
        for name, path in CODE_ARTIFACTS.items()
    }

    freeze: dict[str, Any] = {
        "freeze_version": FREEZE_VERSION,
        "freeze_date": FREEZE_DATE,
        "status": "frozen",
        "scope": "Layer C hosted evidence-grounded QA",
        "selection_basis": "E5 development retrieved-evidence and oracle-evidence comparison only",
        "provider": {
            "name": "deepseek",
            "adapter_version": DEEPSEEK_PROVIDER_VERSION,
            "model": DEEPSEEK_MODEL,
            "thinking": "enabled",
            "reasoning_effort": "high",
            "max_tokens": 4096,
            "temperature": None,
            "json_output": True,
            "model_alias_note": (
                "deepseek-v4-pro is a provider model alias rather than a repository-pinned weight snapshot; "
                "runtime returned_model/system_fingerprint/request IDs are preserved when supplied by the API."
            ),
        },
        "prompt": {
            "version": PROMPT_VERSION,
            "runner_version": HOSTED_QA_RUNNER_VERSION,
            "source_path": code_hashes["hosted_qa"]["path"],
            "source_sha256": code_hashes["hosted_qa"]["sha256"],
        },
        "response_contract": {
            "version": CONTRACT_VERSION,
            "path": code_hashes["response_contract"]["path"],
            "sha256": code_hashes["response_contract"]["sha256"],
        },
        "evidence": {
            "production_condition": "frozen_e5d_top5",
            "retrieved_pack_version": EVIDENCE_PACK_VERSION,
            "retrieved_pack_path": str(args.retrieved_packs.relative_to(ROOT)),
            "retrieved_pack_sha256": sha256(args.retrieved_packs),
            "evidence_depth": EVIDENCE_DEPTH,
            "oracle_pack_version": ORACLE_EVIDENCE_PACK_VERSION,
            "oracle_pack_path": str(args.oracle_packs.relative_to(ROOT)),
            "oracle_pack_sha256": sha256(args.oracle_packs),
            "oracle_is_diagnostic_only": True,
        },
        "benchmark": {
            "development_questions_path": str(args.questions.relative_to(ROOT)),
            "development_questions_sha256": benchmark_sha,
            "development_question_count": 60,
            "retrieval_freeze_path": str(args.retrieval_freeze.relative_to(ROOT)),
            "retrieval_freeze_sha256": sha256(args.retrieval_freeze),
            "retrieval_freeze_version": retrieval_freeze.get("freeze_version"),
            "final_benchmark_status": "sealed_until_this_freeze_is_committed_and_validated",
        },
        "development_evidence": {
            "retrieved_first_pass": {
                "run_id": development_run.get("run_id"),
                "run_summary_path": str(args.development_run.relative_to(ROOT)),
                "run_summary_sha256": sha256(args.development_run),
                "success_count": 59,
                "failure_count": 1,
                "responses_sha256": development_run.get("responses_sha256"),
                "failures_sha256": development_run.get("failures_sha256"),
            },
            "transport_retry": {
                "run_id": retry_run.get("run_id"),
                "run_summary_path": str(args.transport_retry_run.relative_to(ROOT)),
                "run_summary_sha256": sha256(args.transport_retry_run),
                "success_count": 1,
                "failure_count": 0,
                "policy": "exact same request/config only; no semantic retry",
            },
            "oracle": {
                "run_id": oracle_run.get("run_id"),
                "run_summary_path": str(args.oracle_run.relative_to(ROOT)),
                "run_summary_sha256": sha256(args.oracle_run),
                "success_count": 60,
                "failure_count": 0,
                "responses_sha256": oracle_run.get("responses_sha256"),
                "failures_sha256": oracle_run.get("failures_sha256"),
            },
        },
        "code_artifacts": code_hashes,
        "policies": {
            "retrieval_retuning_after_freeze": False,
            "semantic_retry": False,
            "transport_retry": "exact same request/config only",
            "reasoning_content_persisted": False,
            "benchmark_reference_answer_exposed_to_model": False,
            "final_test_configuration_changes": False,
        },
        "documented_development_findings": {
            "retrieval_misses": ["E5D-030", "E5D-045"],
            "benchmark_ambiguities": ["E5D-027", "E5D-034"],
            "retrieved_condition_layer_c_errors": ["E5D-017", "E5D-056"],
            "stability_note": (
                "E5D-056 returned the correct insufficient_evidence state in the evidence-equivalent negative-control "
                "oracle run after returning answered in the original retrieved-evidence run; hosted output therefore "
                "has observable run-to-run variability."
            ),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(freeze, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[progress] Hosted-QA freeze written: {args.output}", flush=True)
    print(json.dumps(freeze, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
