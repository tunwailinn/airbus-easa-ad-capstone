#!/usr/bin/env python3
"""Evidence-grounded DeepSeek V4 Pro hosted QA for Layer C.

The model receives only the question and frozen retrieved evidence with stable
evidence IDs. It never supplies trusted AD/page citations itself: returned
evidence IDs are validated and resolved to source metadata locally.

DeepSeek thinking content is never persisted. The final answer must satisfy the
local machine-readable Layer C response contract before it is accepted.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from full_corpus_pipeline.layer_c.hosted_gateway import HostedGateway
from full_corpus_pipeline.layer_c.providers.deepseek import (
    DEEPSEEK_MODEL,
    DeepSeekProvider,
)


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = Path(__file__).with_name("hosted_qa_contract.schema.json")
HOSTED_QA_RUNNER_VERSION = "e5-hosted-qa-runner-v1.1"
PROMPT_VERSION = "e5-hosted-qa-prompt-v1.0-dev"


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    ad_number: str
    source_pdf: str
    page_start: int
    page_end: int
    section: str
    text: str
    chunk_id: str | None = None
    rank: int | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Evidence":
        return cls(
            evidence_id=str(value["evidence_id"]),
            ad_number=str(value["ad_number"]),
            source_pdf=str(value["source_pdf"]),
            page_start=int(value["page_start"]),
            page_end=int(value["page_end"]),
            section=str(value["section"]),
            text=str(value["text"]),
            chunk_id=str(value["chunk_id"]) if value.get("chunk_id") is not None else None,
            rank=int(value["rank"]) if value.get("rank") is not None else None,
        )


SYSTEM_PROMPT = """You are an aviation maintenance document assistant answering questions about EASA Airworthiness Directives.

Use ONLY the supplied evidence. Do not use outside knowledge to fill missing facts.
Preserve exact numeric thresholds, units, compliance timing, logical branches, conditions, exceptions, alternatives, previous-action credit, repetitive requirements, terminating actions, applicability restrictions, lifecycle statements, and referenced-publication identifiers when they are material to the answer.

Do not make an aircraft-specific legal-compliance determination or calculate an operator-specific deadline unless the supplied evidence itself contains all aircraft-specific history needed to determine it.

If the supplied evidence does not establish the requested conclusion, use status "insufficient_evidence". If supplied passages materially conflict such that the question cannot be resolved from them, use status "conflicting_evidence". Otherwise use status "answered".

For status "answered", cite every material conclusion using one or more supplied evidence IDs. For an abstention, explain what is missing or conflicting in reason_for_abstention. Never invent an evidence ID, AD number, PDF name, page number, section, procedure, threshold, exception, or maintenance requirement.

Return JSON only and obey the supplied response schema. Do not output chain-of-thought or hidden reasoning.
"""


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(value)
    return value


def build_user_prompt(question: str, evidence: list[Evidence]) -> str:
    if not evidence:
        evidence_block = "[NO RETRIEVED EVIDENCE]"
    else:
        parts: list[str] = []
        for item in evidence:
            parts.append(
                "\n".join(
                    [
                        f"[{item.evidence_id}]",
                        f"AD: {item.ad_number}",
                        f"Source PDF: {item.source_pdf}",
                        f"Page range: {item.page_start}-{item.page_end}",
                        f"Section: {item.section}",
                        "Text:",
                        item.text,
                    ]
                )
            )
        evidence_block = "\n\n---\n\n".join(parts)

    return (
        f"QUESTION:\n{question}\n\n"
        f"EVIDENCE:\n{evidence_block}\n\n"
        "Answer using only the evidence above."
    )


def validate_and_resolve_answer(
    raw_answer: dict[str, Any],
    evidence: list[Evidence],
    *,
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = contract or load_contract()
    errors = sorted(
        Draft202012Validator(contract).iter_errors(raw_answer),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        rendered = "; ".join(error.message for error in errors[:5])
        raise ValueError(f"hosted QA output violates response contract: {rendered}")

    evidence_map = {item.evidence_id: item for item in evidence}
    if len(evidence_map) != len(evidence):
        raise ValueError("duplicate evidence IDs supplied to hosted QA")

    raw_ids = list(raw_answer["evidence_ids"])
    unknown = [value for value in raw_ids if value not in evidence_map]
    if unknown:
        raise ValueError(f"hosted QA returned unknown evidence IDs: {unknown}")

    citations: list[dict[str, Any]] = []
    for evidence_id in raw_ids:
        item = evidence_map[evidence_id]
        citations.append(
            {
                "evidence_id": evidence_id,
                "chunk_id": item.chunk_id,
                "ad_number": item.ad_number,
                "source_pdf": item.source_pdf,
                "page_start": item.page_start,
                "page_end": item.page_end,
                "section": item.section,
            }
        )

    result = dict(raw_answer)
    result["citations"] = citations
    return result


def evidence_from_pack(pack: dict[str, Any]) -> tuple[str, list[Evidence], str | None]:
    payload = pack.get("prompt_payload")
    if not isinstance(payload, dict):
        raise ValueError("Layer C evidence pack is missing prompt_payload")
    question = str(payload["question"])
    raw_evidence = payload.get("evidence", [])
    if not isinstance(raw_evidence, list):
        raise ValueError("Layer C prompt_payload.evidence must be a list")
    evidence = [Evidence.from_dict(item) for item in raw_evidence]
    return question, evidence, pack.get("prompt_payload_sha256")


def call_hosted_qa(
    question: str,
    evidence: list[Evidence],
    *,
    model: str = DEEPSEEK_MODEL,
    provider: DeepSeekProvider | None = None,
    gateway: HostedGateway | None = None,
    reasoning_effort: str = "high",
    max_tokens: int = 4096,
    temperature: float = 0.0,
    request_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one Layer C QA request.

    Direct DeepSeek is the canonical development path. ``gateway`` and
    ``temperature`` remain only for backward compatibility with the earlier
    provider-neutral prototype; direct DeepSeek thinking mode does not use
    temperature.
    """

    if not model.strip():
        raise ValueError("hosted QA model must be explicitly configured during development")
    contract = load_contract()
    metadata = {
        "operation": "layer_c_qa",
        "runner_version": HOSTED_QA_RUNNER_VERSION,
        "prompt_version": PROMPT_VERSION,
        "evidence_ids": [item.evidence_id for item in evidence],
        "chunk_ids": [item.chunk_id for item in evidence if item.chunk_id],
        **(request_metadata or {}),
    }

    if gateway is not None:
        response = gateway.generate(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            document_text=build_user_prompt(question, evidence),
            schema=contract,
            temperature=temperature,
            request_metadata=metadata,
        )
        runtime_provider = {
            "provider": "gateway",
            "temperature": temperature,
        }
    else:
        direct = provider or DeepSeekProvider(
            reasoning_effort=reasoning_effort,
            thinking_enabled=True,
            max_tokens=max_tokens,
        )
        response = direct.generate(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            document_text=build_user_prompt(question, evidence),
            schema=contract,
            request_metadata=metadata,
        )
        runtime_provider = {
            "provider": "deepseek",
            "thinking": "enabled",
            "reasoning_effort": reasoning_effort,
            "max_tokens": max_tokens,
        }

    result = validate_and_resolve_answer(response.output, evidence, contract=contract)
    result["runtime"] = {
        "runner_version": HOSTED_QA_RUNNER_VERSION,
        "prompt_version": PROMPT_VERSION,
        "model": model,
        **runtime_provider,
        "usage": response.usage,
        "request_id": response.request_id,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-pack", type=Path, required=True)
    parser.add_argument("--model", default=DEEPSEEK_MODEL)
    parser.add_argument("--reasoning-effort", choices=["high", "max"], default="high")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    pack = json.loads(args.evidence_pack.read_text(encoding="utf-8"))
    question, evidence, pack_sha = evidence_from_pack(pack)
    result = call_hosted_qa(
        question,
        evidence,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        max_tokens=args.max_tokens,
        request_metadata={
            "question_id": pack.get("question_id"),
            "prompt_payload_sha256": pack_sha,
        },
    )
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"[progress] Layer C hosted QA result written: {args.output}", flush=True)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
