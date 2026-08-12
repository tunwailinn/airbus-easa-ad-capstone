# Layer C — Hosted Evidence-Grounded QA

## Status

Frozen E5-D retrieval remains unchanged.

**Phase C1 is complete. Phase C2 direct-provider integration is implemented. Phase C3 development smoke/evaluation is next.** The 16 final-test families and 40 final questions remain sealed until the hosted-QA configuration is frozen.

The active Layer C implementation is under:

```text
full_corpus_pipeline/layer_c/
```

Legacy root module names remain only as compatibility entry points.

## Boundary

```text
Question
→ frozen E5-D retrieval
→ frozen top-5 original-PDF evidence
→ DeepSeek V4 Pro
→ local response-contract validation
→ local EV citation resolution
→ cited answer or evidence-based abstention
```

Layer C may not retune routing, candidate generation, embedding/reranker models, RRF settings, candidate depth, reranker instruction, chunking, or evidence depth.

## Declared development configuration

The development provider/model is now declared as:

```text
provider: DeepSeek official API
provider adapter: deepseek-direct-v1.0
model: deepseek-v4-pro
thinking: enabled
reasoning_effort: high for the initial development configuration
max_tokens: 4096
temperature: not used in thinking mode
API key environment variable: DEEPSEEK_API_KEY
```

The model/provider is declared for development but **not yet frozen**. A change from `high` to `max`, a prompt change, or any other generation-setting change creates a new development configuration and must use a new run ID.

DeepSeek `reasoning_content` is deliberately ignored and never stored in evaluation artifacts. Only final JSON output, usage metadata, request ID, and locally resolved citations are persisted.

## Implemented response contract

Machine-readable response schema:

```text
full_corpus_pipeline/layer_c/hosted_qa_contract.schema.json
```

Contract version:

```text
e5-hosted-qa-contract-v1.0
```

Allowed answer states:

- `answered`
- `insufficient_evidence`
- `conflicting_evidence`

An `answered` result must cite at least one supplied evidence ID. Abstention states must include a non-empty `reason_for_abstention`.

DeepSeek JSON Output is used only as the transport-level JSON constraint. The local JSON Schema remains authoritative: every model response is validated after parsing. The model returns stable evidence IDs (`EV1`, `EV2`, ...); the application resolves those IDs back to original AD/PDF/page/section metadata locally.

## Evidence-pack contract

Canonical builder:

```text
full_corpus_pipeline/layer_c/build_evidence_packs.py
```

Compatibility entry point:

```text
full_corpus_pipeline/build_layer_c_evidence_packs.py
```

Version:

```text
e5-evidence-pack-v1.0
```

Development input sources:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/retrieval_freeze.json
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/development_questions.jsonl
data_processed/evaluations/e5/e5d_development_evaluation.json
data_processed/indexes/rag_v1_2/e4_section_hybrid/chunks.jsonl
```

The builder does **not** run retrieval. It joins frozen E5-D top-five chunk IDs back to the frozen E4 chunk store to restore original passage text and source metadata.

### No benchmark leakage

The model-visible evidence-pack prompt payload contains only:

```text
question_id
question
evidence
```

The following stay outside the hosted-model prompt and are retained only for later evaluation:

- category;
- query mode;
- `answerable_from_ad`;
- target AD;
- reference pages;
- retrieval relevance ranks; and
- gold/reference answers.

## Hosted QA runner

Canonical single-request runner:

```text
full_corpus_pipeline/layer_c/hosted_qa.py
```

Runner version:

```text
e5-hosted-qa-runner-v1.1
```

Current prompt version:

```text
e5-hosted-qa-prompt-v1.0-dev
```

Direct DeepSeek adapter:

```text
full_corpus_pipeline/layer_c/providers/deepseek.py
```

The current prompt requires the model to:

- use only supplied evidence;
- preserve thresholds, units, timing, conditions, branches, exceptions, repetitive requirements, previous-action credit, terminating actions, applicability restrictions, lifecycle statements, and publication identifiers when material;
- avoid aircraft-specific legal-compliance determinations without complete aircraft history;
- abstain on insufficient evidence;
- flag irreconcilable supplied evidence as conflicting;
- cite material claims using supplied evidence IDs only; and
- output no chain-of-thought.

## Development batch runner

Canonical batch runner:

```text
full_corpus_pipeline/layer_c/run_development.py
```

Version:

```text
e5-layer-c-development-runner-v1.1
```

The batch runner:

- consumes the 60 frozen development evidence packs;
- is currently locked to `deepseek-v4-pro`;
- records thinking mode, reasoning effort and max tokens explicitly;
- never runs retrieval;
- never accesses the final benchmark;
- writes a new run directory instead of overwriting a previous run;
- records evidence-pack hash, provider/model settings, prompt/runner versions, request IDs, usage, per-question elapsed time, successes, and failures;
- does not persist `reasoning_content`; and
- performs no automatic semantic retry.

## Development commands

Set the DeepSeek API key for the current shell:

```bash
export DEEPSEEK_API_KEY="<your-api-key>"
```

Run the Layer C tests:

```bash
.venv/bin/python -m unittest \
  full_corpus_pipeline.tests.test_hosted_qa \
  full_corpus_pipeline.tests.test_layer_c_evidence_packs \
  full_corpus_pipeline.tests.test_deepseek_provider \
  -v
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

Only if that run is technically and semantically clean, run all 60 development questions with the exact same settings:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.run_development \
  --model deepseek-v4-pro \
  --reasoning-effort high \
  --max-tokens 4096 \
  --run-id deepseek-v4-pro-high-dev60
```

## Next gate

Before the final benchmark can be opened:

1. run the declared 3-question DeepSeek V4 Pro smoke test;
2. inspect the three outputs for contract validity, citation behavior, evidence grounding, timing/condition/exception preservation, and inappropriate abstention;
3. if clean, run all 60 development questions with the exact same configuration;
4. implement/run the oracle-reference-evidence condition with the same QA settings;
5. produce human-review/evaluation outputs for correctness, material-condition completeness, citation correctness/support, abstention, conflict handling, and unsupported claims;
6. select/finalize the development configuration;
7. write and validate `hosted_qa_freeze.json`; and
8. only then open/finalize the sealed 40-question final benchmark.

Do not create the hosted-QA freeze until the development configuration has been evaluated. Do not open the final benchmark during smoke or development work.
