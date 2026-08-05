#!/usr/bin/env python3
"""Evidence-grounded hosted QA for the aviation AD assistant.

The hosted model receives only retrieved evidence and stable evidence IDs. It is
never trusted to invent AD/page citations: returned evidence IDs are validated
and resolved to source metadata by this module.

Default provider settings target the official DeepSeek OpenAI-compatible API,
but base URL/model/key environment variable are configurable.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_API_KEY_ENV = "DEEPSEEK_API_KEY"


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    ad_number: str
    source_pdf: str
    page_start: int
    page_end: int
    section: str
    text: str

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
        )


@dataclass(frozen=True)
class HostedQAConfig:
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    api_key_env: str = DEFAULT_API_KEY_ENV
    thinking_enabled: bool = True
    reasoning_effort: str = "high"
    timeout_seconds: int = 180
    max_tokens: int = 4096


SYSTEM_PROMPT = """You are an aviation maintenance document assistant answering questions about EASA Airworthiness Directives.

Use ONLY the supplied evidence. Do not use outside knowledge to fill missing facts.
Preserve exact numeric thresholds, units, compliance timing, conditions, exceptions, alternatives, previous-action credit, terminating actions, and applicability restrictions.
If the evidence is incomplete, conflicting, or does not support the requested conclusion, abstain.
Do not make aircraft-specific legal-compliance determinations or calculate an operator-specific deadline unless the supplied evidence itself fully determines it.

Return one JSON object with exactly this semantic structure:
{
  "status": "answer" or "abstain",
  "answer": "concise evidence-grounded answer",
  "conditions": ["condition text"],
  "compliance_time": ["timing text"],
  "exceptions": ["exception text"],
  "evidence_ids": ["E1", "E2"]
}

The evidence_ids array may contain ONLY IDs provided in the evidence block. Never invent an AD number, PDF name, page number, section name, or evidence ID. The application will resolve citations from evidence IDs itself.
Do not output chain-of-thought or reasoning. Output JSON only.
"""


def build_user_prompt(question: str, evidence: list[Evidence]) -> str:
    if not evidence:
        evidence_block = "[NO RETRIEVED EVIDENCE]"
    else:
        parts = []
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
        f"RETRIEVED EVIDENCE:\n{evidence_block}\n\n"
        "Answer in JSON using only the retrieved evidence."
    )


def validate_and_resolve_answer(
    raw_answer: dict[str, Any], evidence: list[Evidence]
) -> dict[str, Any]:
    status = str(raw_answer.get("status", "")).strip().casefold()
    if status not in {"answer", "abstain"}:
        raise ValueError("hosted QA status must be 'answer' or 'abstain'")

    evidence_map = {item.evidence_id: item for item in evidence}
    raw_ids = raw_answer.get("evidence_ids", [])
    if not isinstance(raw_ids, list) or not all(isinstance(value, str) for value in raw_ids):
        raise ValueError("hosted QA evidence_ids must be a list of strings")
    unknown = [value for value in raw_ids if value not in evidence_map]
    if unknown:
        raise ValueError(f"hosted QA returned unknown evidence IDs: {unknown}")

    if status == "answer" and not raw_ids:
        raise ValueError("an answer must cite at least one supplied evidence ID")

    citations = []
    seen: set[str] = set()
    for evidence_id in raw_ids:
        if evidence_id in seen:
            continue
        seen.add(evidence_id)
        item = evidence_map[evidence_id]
        citations.append(
            {
                "evidence_id": evidence_id,
                "ad_number": item.ad_number,
                "source_pdf": item.source_pdf,
                "page_start": item.page_start,
                "page_end": item.page_end,
                "section": item.section,
            }
        )

    def _list_field(name: str) -> list[str]:
        value = raw_answer.get(name, [])
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError(f"hosted QA {name} must be a list")
        return [str(item) for item in value]

    return {
        "status": status,
        "answer": str(raw_answer.get("answer", "")).strip(),
        "conditions": _list_field("conditions"),
        "compliance_time": _list_field("compliance_time"),
        "exceptions": _list_field("exceptions"),
        "evidence_ids": list(dict.fromkeys(raw_ids)),
        "citations": citations,
    }


def call_hosted_qa(
    question: str,
    evidence: list[Evidence],
    *,
    config: HostedQAConfig = HostedQAConfig(),
) -> dict[str, Any]:
    api_key = os.environ.get(config.api_key_env)
    if not api_key:
        raise RuntimeError(
            f"missing hosted LLM API key environment variable: {config.api_key_env}"
        )

    body: dict[str, Any] = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(question, evidence)},
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": config.max_tokens,
    }
    # DeepSeek V4 supports explicit thinking controls on its OpenAI-compatible API.
    # Keep these configurable and never retain reasoning_content in project outputs.
    if config.thinking_enabled:
        body["thinking"] = {"type": "enabled"}
        body["reasoning_effort"] = config.reasoning_effort
    else:
        body["thinking"] = {"type": "disabled"}

    request = urllib.request.Request(
        config.base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"hosted LLM HTTP {exc.code}: {detail[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"hosted LLM request failed: {exc}") from exc

    try:
        message = payload["choices"][0]["message"]
        content = message["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("hosted LLM response missing choices[0].message.content") from exc

    # Intentionally ignore message.get('reasoning_content'). We do not persist CoT.
    raw_answer = json.loads(content)
    if not isinstance(raw_answer, dict):
        raise ValueError("hosted LLM JSON output must be an object")
    result = validate_and_resolve_answer(raw_answer, evidence)
    result["runtime"] = {
        "provider_base_url": config.base_url,
        "model": config.model,
        "thinking_enabled": config.thinking_enabled,
        "reasoning_effort": config.reasoning_effort if config.thinking_enabled else None,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--no-thinking", action="store_true")
    args = parser.parse_args()

    raw = json.loads(args.evidence.read_text(encoding="utf-8"))
    items = raw["evidence"] if isinstance(raw, dict) and "evidence" in raw else raw
    if not isinstance(items, list):
        raise ValueError("evidence file must contain a list or {'evidence': [...]} object")
    evidence = [Evidence.from_dict(item) for item in items]
    result = call_hosted_qa(
        args.question,
        evidence,
        config=HostedQAConfig(
            base_url=args.base_url,
            model=args.model,
            api_key_env=args.api_key_env,
            thinking_enabled=not args.no_thinking,
        ),
    )
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"[progress] hosted QA result written: {args.output}", flush=True)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
