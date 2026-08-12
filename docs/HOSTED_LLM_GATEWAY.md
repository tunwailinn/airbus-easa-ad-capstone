# Optional / legacy hosted QA gateway

Layer C development now uses the direct DeepSeek V4 Pro adapter at:

```text
full_corpus_pipeline/layer_c/providers/deepseek.py
```

The current development credential is supplied through:

```bash
DEEPSEEK_API_KEY
```

A separate `AD_LLM_GATEWAY_URL` service is therefore **not required** for the declared DeepSeek V4 Pro development experiment.

The provider-neutral `HostedGateway` code remains only as a compatibility/extension path in case a future deployment needs centralized credential handling, provider SDK isolation, spending controls, or a different hosted provider. It is not part of the current primary Layer C development configuration.

Extraction, page-text processing, retrieval, and permanent ingestion remain deterministic/local and never use either the direct hosted provider or this optional gateway. Hosted execution is allowed only at Layer C answer-generation time over frozen retrieved original-PDF evidence.

If the optional gateway is ever reactivated, it accepts a JSON request containing `model`, `system_prompt`, `document_text`, a JSON Schema under `response_format.json_schema`, `temperature`, and request metadata, and returns either the structured record directly or an envelope containing `output`, `usage`, and `request_id`.

Do not place any hosted-provider API key in this repository.
