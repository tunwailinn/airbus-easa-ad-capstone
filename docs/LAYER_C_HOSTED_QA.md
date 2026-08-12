# Layer C — Hosted Evidence-Grounded QA

## Status

Layer C implementation has started. Frozen E5-D retrieval remains unchanged.

The current gate is **development-only hosted-QA preparation**. The 16 final-test families and 40 final questions must remain sealed until the hosted-QA configuration is frozen.

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
full_corpus_pipeline/hosted_qa_contract.schema.json
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

Builder:

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

Each evidence pack records hashes for the prompt payload and its frozen inputs.

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

Runner:

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

## Development commands

Build deterministic evidence packs after the local frozen artifacts are present:

```bash
.venv/bin/python -m full_corpus_pipeline.build_layer_c_evidence_packs
```

Run one evidence pack through a configured hosted gateway:

```bash
.venv/bin/python -m full_corpus_pipeline.hosted_qa \
  --evidence-pack path/to/one_evidence_pack.json \
  --model <development-model-name> \
  --output path/to/result.json
```

The batch development runner and QA evaluator are the next implementation step.

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

1. implement the batch development hosted-QA runner;
2. run all 60 development questions using frozen E5-D evidence;
3. implement/run the oracle-reference-evidence condition with the same QA settings;
4. score correctness, material-condition completeness, citation correctness, abstention, and unsupported claims;
5. compare a small declared provider/model/prompt/reasoning candidate set using development data only;
6. select one configuration;
7. write and validate `hosted_qa_freeze.json`; and
8. only then open/finalize the 40-question final benchmark.

Do not create the hosted-QA freeze until an actual provider/model/prompt/reasoning configuration has been selected from development results.
