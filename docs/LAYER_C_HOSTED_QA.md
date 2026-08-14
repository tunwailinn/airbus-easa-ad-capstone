# Layer C — Hosted Evidence-Grounded QA

Last updated: 14 August 2026

## Status

**FROZEN / FINAL EVALUATION COMPLETE.**

Frozen E5-D retrieval remains unchanged. Hosted-QA development, development oracle comparison, hosted-QA freeze, final benchmark, human semantic review, and final oracle diagnostic are all complete.

Authoritative primary final semantic accuracy: **38/40 = 95.0%**.

The next project phase is the five frozen unseen-PDF temporary-QA and permanent-ingestion evaluation. Do not tune hosted QA from final-test or unseen-test outcomes.

Detailed final record:

```text
docs/LAYER_C_FINAL_EVALUATION.md
```

## Production boundary

```text
Question
→ frozen E5-D retrieval
→ frozen top-5 original-PDF evidence
→ DeepSeek V4 Pro
→ local response-contract validation
→ local EV citation resolution
→ cited answer | insufficient_evidence | conflicting_evidence
```

Layer C may not retune routing, candidate generation, embedding/reranker models, RRF settings, candidate depth, reranker instruction, chunking, or evidence depth.

## Frozen hosted-QA configuration

```text
provider: DeepSeek official API
provider adapter: deepseek-direct-v1.1
model: deepseek-v4-pro
thinking: enabled
reasoning_effort: high
max_tokens: 4096
temperature: not used in thinking mode
prompt: e5-hosted-qa-prompt-v1.0-dev
hosted QA runner: e5-hosted-qa-runner-v1.1
response contract: e5-hosted-qa-contract-v1.0
production evidence: frozen E5-D top 5
evidence depth: 5
semantic retry: prohibited
```

Machine-readable freeze:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json
```

DeepSeek `reasoning_content` is ignored and never persisted. Only final JSON output, usage metadata, request ID, and locally resolved citations are stored.

## Response contract

Schema:

```text
full_corpus_pipeline/layer_c/hosted_qa_contract.schema.json
```

Allowed states:

- `answered`;
- `insufficient_evidence`;
- `conflicting_evidence`.

Answered results must cite supplied evidence IDs. Abstention states require a non-empty reason. EV identifiers are resolved locally to AD/PDF/page/section metadata.

## No benchmark leakage

Model-visible payload contains only question identity/text and supplied evidence.

Private scoring fields remain outside hosted inference:

- category;
- query mode;
- answerability label;
- target AD;
- reference pages;
- retrieval labels/ranks;
- human reference answers.

## Development retrieved-evidence result

Full development run:

- first-pass successes: **59/60**;
- first-pass technical failures: **1** (`E5D-034` empty final JSON content);
- exact same-request/config transport retry: **1/1 recovered**.

Important development diagnostics:

- `E5D-017` — retrieved-condition Layer C completeness miss;
- `E5D-030` — Layer B candidate-generation/retrieval miss;
- `E5D-045` — Layer B near-boundary page-ranking limitation;
- `E5D-056` — answer-state/abstention miss;
- `E5D-027` and `E5D-034` — benchmark ambiguity findings.

The 55/58 = 94.8% ambiguity-adjusted development statistic is post-hoc only and is not a final benchmark score.

## Development oracle/reference-evidence result

The 60-question development oracle condition kept the exact same generation configuration and changed only evidence for answerable questions.

- successes: **60/60**;
- request success: **100%**;
- answerability/status accuracy: **100%**;
- reference-page citation hit rate: **100%**;
- target-AD citation hit rate: **100%**.

Development oracle evidence-pack SHA-256:

```text
33beaf3b0f6b45be80cf2ef70fc9ac94e1fe593986915c180c3685f494939b32
```

Development oracle response SHA-256:

```text
c1757226df9d7793bdce47bba4dd9b68517951d361720c768b58d1665784be75
```

The assistant semantic audit of that oracle packet was AI-assisted and is not labelled human review.

## Hosted-QA freeze

Freeze tooling:

```text
full_corpus_pipeline/layer_c/build_hosted_qa_freeze.py
full_corpus_pipeline/layer_c/validate_hosted_qa_freeze.py
full_corpus_pipeline/tests/test_layer_c_hosted_qa_freeze.py
```

The generated freeze was validated and committed before the final benchmark was opened.

## Final benchmark result

Final set:

- 40 human-reviewed questions;
- 36 answerable + 4 abstention/conflict;
- 24 known-document + 12 identifier-free discovery + 4 abstention/conflict.

Primary final automatic result:

- hosted requests: **40/40 successful**;
- answerability/status accuracy: **100%**;
- retrieval Recall@5: **35/36 = 97.22%**;
- known-document Recall@5: **24/24 = 100%**;
- discovery Recall@5: **11/12 = 91.67%**.

Human semantic result:

- passes: **38/40**;
- failures: **2/40**;
- **strict end-to-end semantic accuracy: 95.0%**.

Primary failure attribution:

- `E5F-011` — Layer C answer-selection/completeness failure under retrieved evidence;
- `E5F-021` — Layer B retrieval/candidate-generation failure.

## Final oracle diagnostic

The final oracle condition was run after the primary result was preserved.

Original batch:

- selected: 40;
- successes: 39;
- technical/provider failures: 1 (`E5F-035`);
- reference-page citation hit rate: 100%;
- target-AD citation hit rate: 100%.

Key conclusions:

- `E5F-021` becomes correct with oracle evidence → Layer B failure confirmed;
- `E5F-011` becomes correct with focused oracle evidence → primary Layer C failure is more precisely evidence-selection/completeness sensitivity;
- `E5F-040` changes status under unchanged negative-control evidence while remaining semantically cautious → Layer C status-calibration/run-to-run variability.

One exact transport retry of `E5F-035` preserved prompt payload hash `74ad9826c35d14082c13f15d94a639d017462b0515092c17e0fa4fd42b28892c` and recovered successfully. The original 39-success/1-failure oracle batch remains preserved.

## Reporting rule

Never report oracle or retry-adjusted accuracy as the primary result.

Use:

```text
Primary final end-to-end semantic accuracy: 38/40 = 95.0%
```

## Next gate

Proceed to the five frozen unseen PDFs under:

```text
evaluation_sets/unseen_incoming_5_v1/
```

Evaluate temporary unseen-document QA first, then permanent ingestion without retraining. Keep those results separate from the 40-question final benchmark.