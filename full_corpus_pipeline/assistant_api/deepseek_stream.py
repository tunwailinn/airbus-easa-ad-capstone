from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from full_corpus_pipeline.layer_c.hosted_qa import (
    HOSTED_QA_RUNNER_VERSION,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    Evidence,
    build_user_prompt,
    load_contract,
    validate_and_resolve_answer,
)
from full_corpus_pipeline.layer_c.providers.deepseek import DEEPSEEK_MODEL, DeepSeekProvider


SERVING_PROVIDER_VERSION = "deepseek-live-stream-v1.0"


async def stream_hosted_qa(
    question: str,
    evidence: list[Evidence],
    *,
    request_metadata: dict[str, Any] | None = None,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """Stream provider progress but publish only a fully validated Layer C result.

    Raw JSON fragments are deliberately not emitted to the browser. This keeps the
    frozen response-contract and citation-validation boundary intact while allowing
    the UI to show genuine provider activity.
    """
    provider = DeepSeekProvider(reasoning_effort="high", thinking_enabled=True, max_tokens=4096)
    contract = load_contract()
    payload = provider.build_request_payload(
        model=DEEPSEEK_MODEL,
        system_prompt=SYSTEM_PROMPT,
        document_text=build_user_prompt(question, evidence),
        schema=contract,
    )
    payload["stream"] = True
    payload["stream_options"] = {"include_usage": True}

    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    content_parts: list[str] = []
    usage: dict[str, Any] = {}
    request_id: str | None = None
    received_chars = 0

    async with httpx.AsyncClient(timeout=httpx.Timeout(provider.timeout)) as client:
        async with client.stream(
            "POST",
            f"{provider.base_url}/chat/completions",
            headers=headers,
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                body = line[5:].strip()
                if not body or body == "[DONE]":
                    continue
                chunk = json.loads(body)
                if chunk.get("id") is not None:
                    request_id = str(chunk["id"])
                if isinstance(chunk.get("usage"), dict):
                    usage = chunk["usage"]
                choices = chunk.get("choices")
                if not isinstance(choices, list) or not choices:
                    continue
                delta = choices[0].get("delta") if isinstance(choices[0], dict) else None
                if not isinstance(delta, dict):
                    continue
                # reasoning_content is intentionally ignored and never persisted/emitted.
                part = delta.get("content")
                if isinstance(part, str) and part:
                    content_parts.append(part)
                    received_chars += len(part)
                    yield "generation.progress", {"received_chars": received_chars}

    content = "".join(content_parts).strip()
    if not content:
        raise ValueError("DeepSeek JSON Output returned empty final content")
    try:
        raw_answer = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("DeepSeek streamed final content is not valid JSON") from exc
    if not isinstance(raw_answer, dict):
        raise ValueError("DeepSeek streamed final JSON output is not an object")

    result = validate_and_resolve_answer(raw_answer, evidence, contract=contract)
    result["runtime"] = {
        "runner_version": HOSTED_QA_RUNNER_VERSION,
        "prompt_version": PROMPT_VERSION,
        "provider": "deepseek",
        "provider_version": SERVING_PROVIDER_VERSION,
        "model": DEEPSEEK_MODEL,
        "thinking": "enabled",
        "reasoning_effort": "high",
        "max_tokens": 4096,
        "usage": usage,
        "request_id": request_id,
        "request_metadata": request_metadata or {},
    }
    yield "answer.validated", result
