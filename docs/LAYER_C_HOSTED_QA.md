# Layer C — Hosted Evidence-Grounded QA

## Status

Layer C implementation has started. Frozen E5-D retrieval remains unchanged.

**Phase C1 is implemented and Phase C2 is in progress.** The 16 final-test families and 40 final questions remain sealed until the hosted-QA configuration is frozen.

The active Layer C implementation is now organized under:

```text
full_corpus_pipeline/layer_c/
```

Legacy root module names remain only as compatibility entry points for earlier commands/tests.

## Boundary

```text
Question
→ frozen E5-D retrieval
→ frozen top-5 original-PDF evidence
→ hosted QA
→ cited answer or evidence-based abstention
```

Layer C may not retune routing, candidate generation, embedding/reranker models, RRF settings, candidate depth, reranker instruction, chunking, or evidence depth.

## Implemented contract

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

The hosted model does not provide trusted source/page metadata. It returns stable evidence IDs (`EV1`, `EV2`, ...), and the application resolves those IDs back to the original AD/PDF/page/section metadata locally.

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

It validates the frozen development benchmark hash against `retrieval_freeze.json`, verifies the E5-D report was generated from the same benchmark, checks overlapping retrieval/chunk metadata, and records hashes for the prompt payload and frozen inputs.

### No benchmark leakage

The model-visible prompt payload contains only:

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

This is especially important for abstention/conflict questions: the model must infer insufficiency or conflict from the supplied evidence rather than being told the expected label.

## Hosted QA runner

Canonical single-request runner:

```text
full_corpus_pipeline/layer_c/hosted_qa.py
```

Compatibility entry point:

```text
full_corpus_pipeline/hosted_qa.py
```

Runner version:

```text
e5-hosted-qa-runner-v1.0
```

Current prompt version:

```text
e5-hosted-qa-prompt-v1.0-dev
```

The runner is provider-neutral and uses `HostedGateway`. It does not hard-code a provider or model before development selection.

A model must be supplied explicitly during development. The eventual provider/model/reasoning/generation settings will be recorded later in the hosted-QA freeze.

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

Compatibility entry point:

```text
full_corpus_pipeline/run_layer_c_development.py
```

Version:

```text
e5-layer-c-development-runner-v1.0
```

The batch runner:

- consumes the 60 frozen development evidence packs;
- requires the model name explicitly;
- never runs retrieval;
- never accesses the final benchmark;
- writes an immutable-style run directory instead of overwriting a previous run;
- records the evidence-pack hash, model, temperature, prompt/runner versions, request IDs, usage, per-question elapsed time, successes, and failures; and
- performs no semantic retry.

## Development commands

Build deterministic evidence packs after the local frozen artifacts are present:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.build_evidence_packs
```

Run a small development smoke test first:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.run_development \
  --model <development-model-name> \
  --limit 3 \
  --run-id <model>-smoke
```

Run all 60 development questions only after the gateway/provider configuration is ready:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.run_development \
  --model <development-model-name> \
  --run-id <declared-development-run-id>
```

Hosted gateway credentials remain outside repository artifacts and are supplied through the configured gateway environment.

## Tests

Layer C contract tests:

```text
full_corpus_pipeline/tests/test_hosted_qa.py
full_corpus_pipeline/tests/test_layer_c_evidence_packs.py
```

They cover:

- stable evidence IDs;
- local citation resolution;
- rejection of unknown evidence IDs;
- answer-without-evidence rejection;
- insufficient/conflicting evidence states;
- deterministic prompt-payload hashes;
- evidence text/source restoration from the frozen chunk store;
- no evaluation-label leakage into the prompt payload; and
- frozen metadata drift rejection.

## Next gate

Before the final benchmark can be opened:

1. configure a small declared hosted-model candidate set through the gateway;
2. run development smoke tests, then all 60 development questions;
3. implement/run the oracle-reference-evidence condition with the same QA settings;
4. implement human-review/evaluation outputs for correctness, material-condition completeness, citation correctness, abstention, and unsupported claims;
5. compare the declared provider/model/prompt/reasoning candidates using development data only;
6. select one configuration;
7. write and validate `hosted_qa_freeze.json`; and
8. only then open/finalize the 40-question final benchmark.

Do not create the hosted-QA freeze until an actual provider/model/prompt/reasoning configuration has been selected from development results.
