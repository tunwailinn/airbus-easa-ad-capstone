# Layer C — Hosted Evidence-Grounded QA

Layer C is the active answer-generation layer. Frozen Layer B / E5-D retrieval remains unchanged.

## Declared development provider

Layer C development now uses **DeepSeek V4 Pro** through the official OpenAI-compatible DeepSeek API.

Declared settings:

```text
provider: deepseek
model: deepseek-v4-pro
thinking: enabled
reasoning_effort: high for the first development run
max_tokens: 4096
temperature: not used in thinking mode
```

The API key is read only from `DEEPSEEK_API_KEY`. Do not commit credentials.

## Files

- `providers/deepseek.py` — direct DeepSeek V4 Pro API adapter
- `hosted_qa_contract.schema.json` — machine-readable answer/abstention contract
- `hosted_qa.py` — evidence-grounded prompt, output validation, and local citation resolution
- `build_evidence_packs.py` — deterministic frozen-E5-D top-5 evidence-pack builder
- `run_development.py` — development-only DeepSeek QA batch runner
- `hosted_gateway.py` — legacy provider-neutral gateway compatibility path

## Boundary

```text
Question
→ frozen Layer B / E5-D
→ frozen top-5 original-PDF evidence
→ DeepSeek V4 Pro
→ local schema validation
→ local EV citation resolution
→ cited answer | insufficient evidence | conflicting evidence
```

Layer C must not run or retune retrieval. DeepSeek `reasoning_content` is intentionally discarded and never stored in research outputs.

## Canonical commands

Build development evidence packs:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.build_evidence_packs
```

Set the credential for the current shell:

```bash
export DEEPSEEK_API_KEY="<your-api-key>"
```

Run the declared three-question smoke test:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.run_development \
  --model deepseek-v4-pro \
  --reasoning-effort high \
  --max-tokens 4096 \
  --limit 3 \
  --run-id deepseek-v4-pro-high-smoke
```

If the smoke test is technically and semantically clean, run all 60 development questions with the same configuration:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.run_development \
  --model deepseek-v4-pro \
  --reasoning-effort high \
  --max-tokens 4096 \
  --run-id deepseek-v4-pro-high-dev60
```

Do not change settings between the smoke and the 60-question run unless the smoke exposes a technical/configuration defect. Any changed configuration must use a new run ID.

## Output audit trail

Each development run writes:

```text
data_processed/evaluations/e5/layer_c/development/runs/<run-id>/
├── run_manifest.json
├── responses.jsonl
├── failures.jsonl
└── run_summary.json
```

The manifest records the provider, provider adapter version, model, thinking mode, reasoning effort, max tokens, frozen evidence-pack SHA-256, prompt/runner versions, and selected question count.

## Tests

Run the Layer C tests before a paid development run:

```bash
.venv/bin/python -m unittest \
  full_corpus_pipeline.tests.test_hosted_qa \
  full_corpus_pipeline.tests.test_layer_c_evidence_packs \
  full_corpus_pipeline.tests.test_deepseek_provider \
  -v
```

## Current gate

The provider/model is declared for development, but hosted QA is **not frozen yet**. First complete the 3-question smoke test, the 60-question development run, QA scoring, and the oracle-evidence condition. Only after the development configuration is selected and recorded should `hosted_qa_freeze.json` be created and the sealed 40-question final benchmark opened.
