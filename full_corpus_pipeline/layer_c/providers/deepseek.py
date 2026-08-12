"""Direct DeepSeek V4 Pro provider for Layer C hosted QA.

Credentials are read from ``DEEPSEEK_API_KEY`` and are never written to
repository artifacts. The provider uses DeepSeek's OpenAI-compatible
``/chat/completions`` endpoint with JSON Output, thinking mode, and explicit
reasoning effort. ``reasoning_content`` is intentionally discarded and never
persisted in Layer C evaluation artifacts.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from full_corpus_pipeline.layer_c.hosted_gateway import GatewayResult


DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-pro"
DEEPSEEK_PROVIDER_VERSION = "deepseek-direct-v1.0"
VALID_REASONING_EFFORTS = {"high", "max"}


class DeepSeekProvider:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        reasoning_effort: str = "high",
        thinking_enabled: bool = True,
        max_tokens: int = 4096,
        timeout: int = 300,
    ) -> None:
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.base_url = (base_url or os.environ.get("DEEPSEEK_BASE_URL") or DEEPSEEK_BASE_URL).rstrip("/")
        self.reasoning_effort = reasoning_effort
        self.thinking_enabled = bool(thinking_enabled)
        self.max_tokens = int(max_tokens)
        self.timeout = int(timeout)

        if not self.api_key:
            raise ValueError("set DEEPSEEK_API_KEY before running Layer C hosted QA")
        if self.reasoning_effort not in VALID_REASONING_EFFORTS:
            raise ValueError(
                f"DeepSeek reasoning_effort must be one of {sorted(VALID_REASONING_EFFORTS)}"
            )
        if not self.thinking_enabled:
            raise ValueError("Layer C DeepSeek development configuration requires thinking mode enabled")
        if self.max_tokens <= 0:
            raise ValueError("DeepSeek max_tokens must be positive")

    def build_request_payload(
        self,
        *,
        model: str,
        system_prompt: str,
        document_text: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        if model != DEEPSEEK_MODEL:
            raise ValueError(
                f"Layer C DeepSeek provider is locked to {DEEPSEEK_MODEL!r} during development; got {model!r}"
            )

        schema_instruction = (
            "\n\nReturn one JSON object matching this response contract exactly. "
            "Do not add keys outside the contract.\nJSON RESPONSE CONTRACT:\n"
            + json.dumps(schema, ensure_ascii=False, sort_keys=True)
        )
        return {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt + schema_instruction},
                {"role": "user", "content": document_text},
            ],
            "response_format": {"type": "json_object"},
            "thinking": {"type": "enabled"},
            "reasoning_effort": self.reasoning_effort,
            "max_tokens": self.max_tokens,
            "stream": False,
        }

    @staticmethod
    def parse_response(payload: dict[str, Any]) -> GatewayResult:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("DeepSeek response contains no choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(message, dict):
            raise ValueError("DeepSeek response is missing assistant message")

        # Deliberately ignore message['reasoning_content']; the research pipeline
        # stores only the final answer, usage, and provider request identifier.
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("DeepSeek JSON Output returned empty final content")
        try:
            output = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("DeepSeek final content is not valid JSON") from exc
        if not isinstance(output, dict):
            raise ValueError("DeepSeek final JSON output is not an object")

        usage = payload.get("usage")
        if not isinstance(usage, dict):
            usage = {}
        provider_metadata: dict[str, Any] = {
            "provider": "deepseek",
            "provider_version": DEEPSEEK_PROVIDER_VERSION,
        }
        if payload.get("model") is not None:
            provider_metadata["returned_model"] = payload.get("model")
        if payload.get("system_fingerprint") is not None:
            provider_metadata["system_fingerprint"] = payload.get("system_fingerprint")
        usage = {**usage, "_provider_metadata": provider_metadata}

        return GatewayResult(
            output=output,
            usage=usage,
            request_id=str(payload["id"]) if payload.get("id") is not None else None,
        )

    def generate(
        self,
        *,
        model: str,
        system_prompt: str,
        document_text: str,
        schema: dict[str, Any],
        request_metadata: dict[str, Any],
    ) -> GatewayResult:
        body = json.dumps(
            self.build_request_payload(
                model=model,
                system_prompt=system_prompt,
                document_text=document_text,
                schema=schema,
            ),
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "airbus-easa-ad-capstone-layer-c/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1500]
            raise RuntimeError(f"DeepSeek API HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"DeepSeek API transport error: {exc.reason}") from exc

        if not isinstance(payload, dict):
            raise ValueError("DeepSeek API response is not a JSON object")
        return self.parse_response(payload)
