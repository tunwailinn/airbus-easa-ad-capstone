# Optional hosted QA answer-generation gateway contract

Full-corpus extraction and permanent-ingestion extraction are deterministic and
local. They do not use this gateway. The optional QA answer generator can use a
small provider-neutral HTTPS gateway so API credentials, provider SDK versions,
and spending controls stay outside the research repository.

Set `AD_LLM_GATEWAY_URL` and, if required, `AD_LLM_GATEWAY_API_KEY`. The gateway
receives a JSON request containing `model`, `system_prompt`, `document_text`, a
JSON Schema under `response_format.json_schema`, `temperature`, and request
metadata. It must return either the schema-valid JSON object directly or:

```json
{
  "output": {"ad_identity": {"ad_number": "2026-0001"}},
  "usage": {"input_tokens": 1000, "output_tokens": 200},
  "request_id": "provider-request-id"
}
```

The QA request supplies retrieved original-PDF passages and requires a cited
answer or abstention. The gateway must enforce authentication, provider-specific
structured output, request logging, rate limits, and budget limits. Do not place
API keys in this repository. No extraction command accepts a hosted-execution
flag.
