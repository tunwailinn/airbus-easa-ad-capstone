# Layer C Final Benchmark — One-Time Frozen Evaluation

Last updated: 14 August 2026

## Status

**COMPLETE / FROZEN.**

The one-time 40-question primary final benchmark has been executed and preserved. The hosted-QA configuration, retrieval configuration, final questions, and primary outputs are immutable.

Hosted-QA freeze:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json
```

Final benchmark lock:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/final_lock.json
```

Final questions:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/final_questions.jsonl
```

Final questions SHA-256:

```text
f6b008c1b5d24160cb5718e2d4e91a7e0d323277a531654e4b5c3a33995c9a85
```

Do not rerun the benchmark as a new primary experiment and do not tune retrieval, prompt, model, reasoning effort, evidence depth, response contract, or provider adapter from final-test observations.

## Frozen primary configuration

```text
retrieval: E5-D
candidate generation: frozen E5-C top 20
reranker: Qwen/Qwen3-Reranker-0.6B @ e61197e
final evidence depth: 5
provider: DeepSeek official API
adapter: deepseek-direct-v1.1
model: deepseek-v4-pro
thinking: enabled
reasoning_effort: high
max_tokens: 4096
prompt: e5-hosted-qa-prompt-v1.0-dev
runner: e5-hosted-qa-runner-v1.1
response contract: e5-hosted-qa-contract-v1.0
semantic retry: prohibited
transport retry: exact same request/config only, separately audited
```

The model-visible payload contains only question ID/text and supplied evidence. Private target ADs, reference pages, reference answers, category/query-mode labels, answerability labels, and required conditions/exceptions are not exposed to the hosted model.

## Completed primary workflow

The guarded one-time workflow was:

```text
validate final benchmark lock
→ validate hosted-QA freeze
→ open/validate 40 human-reviewed final questions
→ frozen E5-C candidate generation
→ frozen E5-D reranking
→ assemble top-5 source evidence
→ frozen DeepSeek Layer C QA
→ preserve primary retrieval + QA artifacts
→ offline automatic evaluation
→ human semantic review
```

Primary output directory:

```text
data_processed/evaluations/e5/layer_c/final/primary/
```

The original primary output remains authoritative and must not be deleted or overwritten to manufacture a second primary result.

## Final benchmark composition

- final questions: **40**;
- answerable: **36**;
- abstention/conflict: **4**;
- known-document: **24**;
- identifier-free discovery: **12**;
- abstention/conflict query mode: **4**.

## Primary automatic result

- hosted requests: **40/40 successful**;
- answerability/status accuracy: **1.0000**;
- retrieval Recall@1: **0.8333**;
- Recall@3: **0.9722**;
- Recall@5: **35/36 = 0.9722**;
- MRR@5: **0.8981**;
- nDCG@5: **0.9173**;
- correct source@5: **0.9722**;
- correct source+page@5: **0.9722**;
- known-document Recall@5: **24/24 = 1.0000**;
- discovery Recall@5: **11/12 = 0.9167**;
- reference-page citation hit rate: **0.9722**;
- target-AD citation hit rate: **0.9722**.

## Human semantic primary result

- passes: **38/40**;
- failures: **2/40**;
- strict end-to-end semantic accuracy: **95.0%**.

**38/40 = 95.0% is the authoritative final semantic result.**

Primary failures:

- `E5F-011` — correct target evidence was available, but Layer C selected incomplete/wrong applicability detail;
- `E5F-021` — target `2018-0289R1` evidence was absent from frozen retrieval support, causing a Layer B retrieval/candidate-generation failure.

Primary PASS diagnostics:

- `E5F-015` — retained with post-hoc lifecycle/benchmark ambiguity note;
- `E5F-030` — retained with canonical reference-page citation diagnostic.

## Oracle/reference-evidence diagnostic

A final oracle condition was executed only after the primary result was preserved. It kept the exact same frozen Layer C configuration and changed only the evidence condition.

Original oracle batch:

- selected: **40**;
- successes: **39**;
- technical/provider failures: **1** (`E5F-035`);
- request success rate: **97.5%**;
- reference-page citation hit rate: **100%**;
- target-AD citation hit rate: **100%**.

Key attribution:

- `E5F-021` becomes correct with oracle evidence → **Layer B failure confirmed**;
- `E5F-011` becomes correct with focused oracle evidence → retain as a Layer C primary failure, more precisely **evidence-selection/completeness sensitivity**;
- `E5F-040` used unchanged negative-control evidence but changed status between runs → **Layer C status-calibration/run-to-run variability**.

## Exact oracle transport retry

The original `E5F-035` oracle call failed because DeepSeek returned empty JSON final content. Under the predeclared policy, one exact transport retry was performed.

The retry preserved the exact prompt payload hash:

```text
74ad9826c35d14082c13f15d94a639d017462b0515092c17e0fa4fd42b28892c
```

and unchanged question, evidence, model, prompt, response contract, thinking mode, reasoning effort, and max-token limit.

Retry result: **recovered successfully**.

The original oracle batch remains preserved as 39 successes / 1 failure. The retry is a separate diagnostic audit artifact and does not alter the strict primary score.

## Reporting policy

Always report the strict primary result first and unchanged:

```text
Primary end-to-end semantic accuracy: 38/40 = 95.0%
Primary retrieval Recall@5: 35/36 = 97.22%
Known-document Recall@5: 24/24 = 100%
Discovery Recall@5: 11/12 = 91.67%
```

Oracle, ambiguity, stability, and transport-retry analyses are post-hoc diagnostics only. They may explain failure mechanisms but may not replace or adjust the primary final score.

## Next evaluation

The next and final major benchmark phase is the five frozen unseen-PDF generalization evaluation under:

```text
evaluation_sets/unseen_incoming_5_v1/
```

Evaluate temporary unseen-document QA first, then permanent ingestion without retraining. Keep those results separate from this 40-question final benchmark.