# Layer C — Hosted Evidence-Grounded QA

## Status

Frozen E5-D retrieval remains unchanged.

**Phase C1 is complete. Phase C2 direct-provider integration is implemented. Phase C3 DeepSeek V4 Pro development evaluation is complete enough to proceed to the oracle-evidence condition.** The 16 final-test families and 40 final questions remain sealed until the hosted-QA configuration is frozen.

Detailed development findings, error attribution, ambiguity audit, and transport-retry accounting are recorded in:

```text
docs/LAYER_C_DEVELOPMENT_EVALUATION.md
```

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
provider adapter: deepseek-direct-v1.1
model: deepseek-v4-pro
thinking: enabled
reasoning_effort: high
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

## Development evaluation completed

The declared three-question smoke run completed successfully with 3/3 hosted responses, zero failures, and perfect automatic status/citation checks.

The full 60-question development run used the same model, prompt, reasoning effort, evidence packs, and output cap. First-pass hosted completion was 59/60 (98.3%). The single failed call, E5D-034, was an empty DeepSeek JSON-output response. It was repeated once using the exact same configuration under the predeclared transport-failure policy and completed successfully. The original failed run remains preserved for audit.

Development review identified:

- E5D-017: Layer C generation error — exact applicability population was incompletely reproduced even though supporting evidence was present;
- E5D-030: Layer B retrieval error — target/reference evidence was absent from frozen top-5 retrieval and the model answered from another retrieved AD;
- E5D-056: Layer C abstention/status error — prose correctly stated that requested repair details were absent, but the contract status was `answered` instead of `insufficient_evidence`;
- E5D-027: benchmark ambiguity — more than one retrieved AD genuinely satisfied the discovery wording;
- E5D-034: benchmark/lifecycle ambiguity — several retrieved RAT gearbox directives genuinely shared the same distinctive 6-month/4,000-FH interval;
- E5D-045: reference-page retrieval miss, but supplied evidence still supported a usable answer identifying the requested publications.

The original frozen benchmark is not modified after observing model outputs. E5D-027 and E5D-034 are retained unchanged and documented as post-hoc ambiguity findings.

Preliminary ambiguity-adjusted end-to-end correctness is 55/58 = 94.8% across the 58 unambiguous development questions. This is a development-analysis statistic, not a replacement benchmark score. It is reported alongside the strict frozen-benchmark results and the separate first-pass/recovered hosted completion rates.

No prompt, model, reasoning-effort, retrieval, or evidence-depth tuning is justified from these isolated development errors before the oracle-evidence condition is run.

## Development commands

Create local credentials from `.env.example` and place the real DeepSeek API key only in the gitignored project-root `.env` file.

Run the Layer C tests:

```bash
.venv/bin/python -m unittest \
  full_corpus_pipeline.tests.test_hosted_qa \
  full_corpus_pipeline.tests.test_layer_c_evidence_packs \
  full_corpus_pipeline.tests.test_deepseek_provider \
  full_corpus_pipeline.tests.test_layer_c_development_evaluator \
  -v
```

Run all 60 development questions with the declared configuration:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.run_development \
  --model deepseek-v4-pro \
  --reasoning-effort high \
  --max-tokens 4096 \
  --run-id deepseek-v4-pro-high-development-60
```

Evaluate a completed development run:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.evaluate_development \
  --run-dir data_processed/evaluations/e5/layer_c/development/runs/deepseek-v4-pro-high-development-60
```

## Next gate

Before the final benchmark can be opened:

1. build and validate the oracle/reference-evidence condition without changing the DeepSeek model, prompt, reasoning effort, response contract, or max-token limit;
2. run the oracle-evidence development condition;
3. compare retrieved-evidence QA against oracle-evidence QA to separate Layer B retrieval limitations from Layer C generation/reasoning limitations;
4. finalize the development configuration only after that comparison;
5. write and validate `hosted_qa_freeze.json`; and
6. only then open/finalize the sealed 40-question final benchmark.

Do not create the hosted-QA freeze until the oracle-evidence comparison is complete. Do not open the final benchmark during development work.
