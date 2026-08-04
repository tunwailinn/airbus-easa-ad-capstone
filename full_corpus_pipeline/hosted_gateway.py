"""Small provider-neutral client for hosted structured-output generation.

The configured gateway must accept the request documented in
``docs/HOSTED_LLM_GATEWAY.md`` and return either a JSON content record directly
or ``{"output": <record>}``. This keeps provider credentials and SDK churn out
of the research pipeline while preserving a fully auditable request contract.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GatewayResult:
    output: dict[str, Any]
    usage: dict[str, Any]
    request_id: str | None


class HostedGateway:
    def __init__(self, endpoint: str | None = None, api_key: str | None = None, timeout: int = 180):
        self.endpoint = endpoint or os.environ.get("AD_LLM_GATEWAY_URL")
        self.api_key = api_key or os.environ.get("AD_LLM_GATEWAY_API_KEY")
        self.timeout = timeout
        if not self.endpoint:
            raise ValueError("set AD_LLM_GATEWAY_URL or pass an endpoint")

    def generate(
        self,
        *,
        model: str,
        system_prompt: str,
        document_text: str,
        schema: dict[str, Any],
        temperature: float,
        request_metadata: dict[str, Any],
    ) -> GatewayResult:
        body = json.dumps(
            {
                "model": model,
                "system_prompt": system_prompt,
                "document_text": document_text,
                "response_format": {"type": "json_schema", "json_schema": schema},
                "temperature": temperature,
                "metadata": request_metadata,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"hosted gateway HTTP {exc.code}: {detail}") from exc
        output = payload.get("output", payload)
        if not isinstance(output, dict):
            raise ValueError("hosted gateway output is not a JSON object")
        return GatewayResult(
            output=output,
            usage=payload.get("usage", {}) if isinstance(payload, dict) else {},
            request_id=payload.get("request_id") if isinstance(payload, dict) else None,
        )
