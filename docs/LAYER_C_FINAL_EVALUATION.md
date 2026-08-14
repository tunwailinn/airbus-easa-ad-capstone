# Layer C Final Evaluation

Last updated: 14 August 2026

## Status

**COMPLETE / FROZEN.**

The strict one-time E5 final benchmark, human semantic review, post-hoc oracle/reference-evidence diagnostic, and the single allowed exact transport retry are complete.

The strict primary result is immutable. No retrieval, prompt, model, reasoning-effort, evidence-depth, response-contract, provider-adapter, or benchmark-question tuning is permitted from final-test observations.

## Final benchmark

- 40 human-reviewed final questions;
- 36 answerable + 4 abstention/conflict;
- 24 known-document + 12 identifier-free discovery + 4 abstention/conflict;
- final questions SHA-256: `f6b008c1b5d24160cb5718e2d4e91a7e0d323277a531654e4b5c3a33995c9a85`.

## Strict primary automatic result

- hosted requests: **40/40 successful**;
- answerability/status accuracy: **1.0000**;
- frozen E5-D Recall@1: **0.8333**;
- Recall@3: **0.9722**;
- Recall@5: **0.9722 (35/36)**;
- MRR@5: **0.8981**;
- nDCG@5: **0.9173**;
- correct source@5: **0.9722**;
- correct source+page@5: **0.9722**;
- reference-page citation hit rate: **0.9722**;
- target-AD citation hit rate: **0.9722**.

Query-mode retrieval:

- known-document Recall@5: **1.0000 (24/24)**;
- discovery Recall@5: **0.9167 (11/12)**.

## Human semantic review — authoritative result

- semantic passes: **38/40**;
- semantic failures: **2/40**;
- strict end-to-end semantic accuracy: **95.0%**.

**The authoritative primary final semantic result is 38/40 = 95.0%.**

It must not be replaced by any oracle-evidence, ambiguity-adjusted, transport-recovered, or other post-hoc score.

### E5F-011 — primary FAIL

Question: applicability of EASA AD `2023-0117`.

The correct target AD/reference evidence was present in the frozen top-5, but the primary answer shifted to lower-deck cargo-door/frame-fork part numbers instead of giving the approved applicability:

- Airbus `A300F4-605R`;
- Airbus `A300F4-622R`;
- all manufacturer serial numbers on which Airbus modification 12046 was embodied in production.

Primary classification: **Layer C answer-selection/completeness failure under the retrieved-evidence condition**.

### E5F-021 — primary FAIL

The approved target is `2018-0289R1`. Its reference evidence was absent from the frozen retrieval support and the primary hosted answer selected `2025-0111`.

Primary classification: **Layer B retrieval/candidate-generation failure**.

### E5F-015 — primary PASS with ambiguity note

The frozen reference target is `2009-0075`, while superseded `2008-0101` originally imposed the same requirement. The primary answer correctly explains the lifecycle relationship. Retain the ambiguity as a post-hoc diagnostic only; do not remove the question from the 40-question denominator.

### E5F-030 — primary PASS with citation diagnostic

The primary answer correctly identifies Airbus SB `A320-53-1339` and `A320-53-1330`. The automatic canonical reference-page check missed the approved page. Preserve this as a citation-page diagnostic, not a semantic answer failure.

## Final oracle/reference-evidence diagnostic

The oracle experiment is **diagnostic only**. It changes only the evidence condition and keeps the generation system frozen.

Implemented files:

```text
full_corpus_pipeline/layer_c/build_final_oracle_evidence_packs.py
full_corpus_pipeline/layer_c/run_final_oracle.py
full_corpus_pipeline/layer_c/evaluate_final_oracle.py
full_corpus_pipeline/layer_c/retry_final_oracle_transport.py
full_corpus_pipeline/tests/test_layer_c_final_oracle.py
```

### Oracle evidence policy

- 36 answerable questions: source chunks from the human-reviewed target AD/reference pages;
- 4 abstention/conflict questions: exact primary frozen top-5 evidence retained as negative controls;
- maximum evidence depth: **5**;
- no retrieval rerun;
- no retrieval retuning;
- model-visible payload remains only question ID/text and evidence;
- reference answers and private scoring labels never enter the hosted prompt.

### Frozen generation configuration

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

## Oracle batch result

Original 40-question oracle run:

- selected questions: **40**;
- successful requests: **39**;
- technical/provider failures: **1**;
- request success rate: **0.9750**;
- answerability/status accuracy on successful requests: **0.9743589744**;
- reference-page citation hit rate: **1.0000**;
- target-AD citation hit rate: **1.0000**.

The one original technical failure was `E5F-035`, where DeepSeek returned empty JSON final content. The original batch remains preserved as 39 successes / 1 failure.

## Final attribution findings

### E5F-021 — Layer B confirmed

Primary:

- reference evidence in top-5: **no**;
- answer: wrong target (`2025-0111`).

Oracle:

- answer: correctly identifies `2018-0289R1`;
- correctly states the 16,800-flight-cycle repetitive inspection interval and Table 1 alternatives.

Conclusion: **Layer B retrieval/candidate generation caused the primary failure.**

### E5F-011 — Layer C evidence-selection/completeness sensitivity

Primary:

- correct target/reference evidence was available;
- answer selected the wrong applicability detail.

Oracle:

- same frozen DeepSeek configuration correctly gives `A300F4-605R`, `A300F4-622R`, all MSNs with mod 12046 embodied in production.

Conclusion: retain E5F-011 as a **Layer C primary failure**, but describe the mechanism more precisely as **evidence-selection/completeness sensitivity under the retrieved-evidence condition**, not inability to reason from the intended evidence.

### E5F-040 — status-calibration stability diagnostic

E5F-040 is one of the four negative controls. Its evidence was intentionally unchanged between primary and oracle conditions.

- primary status: `insufficient_evidence`;
- oracle status: `answered`;
- oracle prose still states that the exact corrective repair dimensions/procedures are not present in the AD and that Airbus-approved instructions are required.

Conclusion: **Layer C status-calibration/run-to-run variability**. This is not a factual hallucination, because the answer text remains appropriately cautious.

## E5F-035 exact transport retry

The original oracle failure was:

```text
DeepSeek JSON Output returned empty final content
```

Under the frozen policy, one exact transport retry was permitted because this was a technical/provider failure rather than a semantic failure.

The retry preserved:

- question ID `E5F-035`;
- question text;
- evidence pack;
- prompt payload SHA-256 `74ad9826c35d14082c13f15d94a639d017462b0515092c17e0fa4fd42b28892c`;
- provider/model;
- prompt and response contract;
- thinking mode;
- reasoning effort;
- max-token limit.

Retry result:

- status: **recovered**;
- success: **1/1**;
- failure: **0**;
- recovered response SHA-256: `86830dafabdde280a50ae80cf7fc907665ed344b3c1fb36b6075486345d9db8f`.

The recovered answer correctly states that modification in accordance with the modification SB, when accomplished at **6,100 FC since first flight or later**, terminates the applicable repetitive inspections and cancels the applicable ALI task 531103 inspection requirements.

The retry does **not** rewrite the original oracle batch as 40/40. It is retained as a separate audit artifact.

## Final reporting table

| Measure | Result | Status |
|---|---:|---|
| Primary hosted request success | 40/40 = 100% | authoritative primary |
| Primary retrieval Recall@5 | 35/36 = 97.22% | authoritative primary |
| Known-document Recall@5 | 24/24 = 100% | authoritative primary |
| Discovery Recall@5 | 11/12 = 91.67% | authoritative primary |
| Primary answerability/status accuracy | 40/40 = 100% | authoritative primary |
| Human semantic accuracy | **38/40 = 95.0%** | **authoritative primary** |
| Original oracle request success | 39/40 = 97.5% | diagnostic only |
| Oracle reference-page citation hit | 100% | diagnostic only |
| Oracle target-AD citation hit | 100% | diagnostic only |
| E5F-035 exact retry | recovered | diagnostic/audit only |

## Remaining project evaluation

Layer C final evaluation is complete.

The remaining major experiment is the five frozen unseen-PDF generalization/ingestion evaluation under:

```text
evaluation_sets/unseen_incoming_5_v1/
```

Run it without retraining in two stages:

1. temporary unseen-document QA without permanent corpus insertion;
2. permanent ingestion with duplicate rejection, deterministic extraction, lifecycle safeguards, index update, and page-cited QA.

The unseen results must be reported separately from the 40-question primary final benchmark and must not be used to tune the frozen E5 system.