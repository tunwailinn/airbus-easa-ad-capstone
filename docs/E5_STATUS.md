# E5 Status

Last updated: 14 August 2026

## Current state

E5 development, retrieval selection, hosted-QA freeze, the one-time 40-question final benchmark, human semantic review, and the post-hoc oracle/reference-evidence diagnostic are complete.

**The authoritative primary final semantic result is 38/40 = 95.0%.**

The final result is frozen. No retrieval, prompt, provider/model, reasoning-effort, response-contract, evidence-depth, or question changes may be made from final-test observations. Oracle and error-attribution results are diagnostic only and must not replace the primary result.

The remaining major evaluation is the five frozen unseen-PDF temporary-upload and permanent-ingestion evaluation.

## Frozen E5 benchmark

- 24 development families / 16 final-test families;
- 60 human-reviewed development questions;
- 40 human-reviewed final questions;
- final questions SHA-256: `f6b008c1b5d24160cb5718e2d4e91a7e0d323277a531654e4b5c3a33995c9a85`;
- final composition: 36 answerable + 4 abstention/conflict;
- final query modes: 24 known-document + 12 identifier-free discovery + 4 abstention/conflict.

Frozen retrieval source remains `rag-index-build-v1.2`: **1,786 documents / 12,634 E4 section chunks**.

Machine-readable retrieval freeze:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/retrieval_freeze.json
```

Hosted-QA freeze:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json
```

Final benchmark lock:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/final_lock.json
```

## E5 retrieval development — COMPLETE / FROZEN

### E5-A

- overall Recall@5: **0.8889**;
- known-document Recall@5: **1.0000**;
- discovery Recall@5: **0.6667**;
- candidate source+page recall@20: **0.9444**.

### E5-B

- Recall@5: **0.9444**;
- discovery Recall@5: **0.8333**;
- candidate source+page recall@20: **0.9630**.

### E5-C

Pinned `Qwen/Qwen3-Embedding-0.6B@97b0c61` candidate generation raised candidate source+page recall@20 to **0.9815 (53/54)**.

### E5-D — selected retrieval configuration

Pinned reranker: `Qwen/Qwen3-Reranker-0.6B@e61197e`.

Frozen development result:

- Recall@1: **0.7963**;
- Recall@3: **0.9259**;
- Recall@5: **0.9630**;
- MRR@5: **0.8633**;
- nDCG@5: **0.8884**;
- correct source@5: **0.9815**;
- correct source+page@5: **0.9630**;
- candidate source+page recall@20: **0.9815**;
- known-document Recall@5: **1.0000 (36/36)**;
- discovery Recall@5: **0.8889 (16/18)**;
- routing accuracy: **1.0000**.

Development artifact:

```text
data_processed/evaluations/e5/e5d_development_evaluation.json
```

SHA-256:

```text
9241b5d777f47a95efd1a5afc9a4139d280be0a12c3b91b6eb2d44df31cbcb05
```

Do not retune against the remaining development misses `E5D-030` or `E5D-045`.

## Layer C hosted-QA configuration — FROZEN

Primary and oracle conditions use the same generation configuration:

```text
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
```

The model sees only the question and supplied evidence. Private benchmark labels, reference answers, target AD labels, reference pages, category/query-mode labels, and answerability labels are not exposed during generation.

## One-time final benchmark — COMPLETE

### Frozen retrieval / automatic result

- hosted requests: **40/40 successful**;
- answerability/status accuracy: **1.0000**;
- Recall@1: **0.8333**;
- Recall@3: **0.9722**;
- Recall@5: **0.9722 (35/36)**;
- MRR@5: **0.8981**;
- nDCG@5: **0.9173**;
- correct source@5: **0.9722**;
- correct source+page@5: **0.9722**;
- known-document Recall@5: **1.0000 (24/24)**;
- discovery Recall@5: **0.9167 (11/12)**;
- reference-page citation hit rate: **0.9722**;
- target-AD citation hit rate: **0.9722**.

### Human semantic result

- semantic passes: **38/40**;
- semantic failures: **2/40**;
- strict end-to-end semantic accuracy: **95.0%**.

This **38/40 = 95.0%** is the authoritative primary final semantic result.

Primary failure interpretation:

1. `E5F-011` — correct target evidence was available, but the answer selected the wrong applicability detail. Primary classification: **Layer C answer-selection/completeness failure under retrieved evidence**.
2. `E5F-021` — correct `2018-0289R1` evidence was absent from the frozen retrieval support and the answer selected `2025-0111`. Classification: **Layer B retrieval/candidate-generation failure**.

Approved diagnostics retained without changing the primary score:

- `E5F-015` — PASS, with a post-hoc lifecycle/benchmark ambiguity note;
- `E5F-030` — PASS, with a canonical reference-page citation diagnostic.

## Final oracle/reference-evidence diagnostic — COMPLETE

The oracle condition changed only the evidence source. The model/prompt/settings remained frozen.

Evidence construction:

- 36 answerable questions received source chunks from the human-reviewed target AD/reference pages;
- 4 abstention questions retained the exact primary frozen top-5 evidence as negative controls;
- maximum evidence depth: 5;
- no retrieval rerun or retuning.

Original oracle batch:

- selected: **40**;
- successful: **39**;
- technical/provider failures: **1** (`E5F-035`);
- request success rate: **0.9750**;
- answerability/status accuracy on successful requests: **0.9744**;
- reference-page citation hit rate: **1.0000**;
- target-AD citation hit rate: **1.0000**.

### Oracle error attribution

`E5F-021` becomes correct with oracle evidence. This confirms the primary failure as **Layer B retrieval/candidate generation**.

`E5F-011` also becomes correct with focused oracle evidence. The same frozen model correctly returns `A300F4-605R` and `A300F4-622R`, all MSNs with Airbus modification 12046 embodied in production. Therefore the primary failure is best described as **Layer C evidence-selection/completeness sensitivity under the retrieved-evidence condition**, rather than inability to reason from the intended evidence.

`E5F-040` is a negative-control stability diagnostic: the evidence was unchanged, but the oracle run returned `answered` instead of the primary `insufficient_evidence`. Its prose remained cautious and stated that the exact repair details were not provided. Record this as **Layer C status-calibration/run-to-run variability**, not a factual hallucination.

### E5F-035 exact transport retry

The original oracle request failed because DeepSeek returned empty JSON final content. One exact transport retry was allowed under the frozen policy.

The retry preserved:

- question text;
- evidence;
- prompt payload SHA-256 `74ad9826c35d14082c13f15d94a639d017462b0515092c17e0fa4fd42b28892c`;
- provider/model;
- prompt/response contract;
- thinking mode;
- reasoning effort;
- max-token limit.

Retry result: **recovered successfully**. The recovered answer correctly describes the 6,100-FC terminating-action condition and cancellation of the applicable ALI 531103 inspection requirements.

The original 39-success/1-failure oracle batch remains preserved. The retry is a separate diagnostic recovery artifact; do not rewrite the original run as 40/40.

## Reporting rule

Use these values in reports:

- **Primary final end-to-end semantic accuracy: 95.0% (38/40)**;
- **Primary final retrieval Recall@5: 97.22% (35/36)**;
- **Known-document final Recall@5: 100% (24/24)**;
- **Discovery final Recall@5: 91.67% (11/12)**.

Oracle results are explanatory only. They must not replace or adjust the strict primary score.

## Next gate — five frozen unseen PDFs

The final major evaluation is the frozen unseen-document set:

```text
evaluation_sets/unseen_incoming_5_v1/
```

Five distinct held-out cases were selected for:

- corrected AD;
- revised AD;
- supersedure case;
- long document;
- simple original.

Run the evaluation in two stages without retraining:

1. **temporary unseen-document QA** — process/query each held-out PDF without adding it to the permanent corpus;
2. **permanent ingestion** — duplicate rejection, deterministic extraction, lifecycle decision, index update, QA, and citations.

Do not use these five PDFs to tune the already-frozen E5 primary system.