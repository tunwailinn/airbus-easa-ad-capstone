# E5 Status

Last updated: 17 August 2026

## Current state

E5 retrieval development, hosted-QA freeze, the one-time 40-question final benchmark, human semantic review, and the final oracle/reference-evidence diagnostic are complete and frozen.

Authoritative E5 primary final result:

```text
38/40 = 95.0% strict end-to-end semantic accuracy
35/36 = 97.22% frozen E5-D Recall@5
24/24 = 100% known-document Recall@5
11/12 = 91.67% discovery Recall@5
```

No retrieval, prompt, provider/model, reasoning-effort, response-contract, evidence-depth or final-question changes are allowed from final or unseen outcomes. Oracle and unseen results are separate diagnostics/generalization results and cannot replace the primary score.

## Frozen E5 retrieval

Development result:

- Recall@1: **0.7963**;
- Recall@3: **0.9259**;
- Recall@5: **0.9630**;
- MRR@5: **0.8633**;
- nDCG@5: **0.8884**;
- correct source+page@5: **0.9630**;
- candidate source+page recall@20: **0.9815**;
- known-document Recall@5: **1.0000**;
- discovery Recall@5: **0.8889**.

Frozen retrieval stack:

- E5-C BM25 + `Qwen/Qwen3-Embedding-0.6B@97b0c61`;
- candidate depth 20;
- `Qwen/Qwen3-Reranker-0.6B@e61197e`;
- final evidence depth 5;
- deterministic known-document routing.

## Frozen Layer C

```text
provider: DeepSeek official API
adapter: deepseek-direct-v1.1
model: deepseek-v4-pro
thinking: enabled
reasoning_effort: high
max_tokens: 4096
prompt: e5-hosted-qa-prompt-v1.0-dev
response contract: e5-hosted-qa-contract-v1.0
semantic retry: prohibited
```

## One-time E5 final benchmark — COMPLETE

- 40 human-reviewed final questions;
- hosted success: **40/40**;
- answerability/status accuracy: **1.0000**;
- Recall@5: **35/36 = 97.22%**;
- human semantic result: **38/40 = 95.0%**.

Primary failures:

1. `E5F-011` — Layer C answer-selection/completeness under retrieved evidence.
2. `E5F-021` — Layer B retrieval/candidate-generation failure.

## Final oracle diagnostic — COMPLETE

Original oracle batch:

- selected: **40**;
- successes: **39**;
- one technical/provider failure: `E5F-035`;
- reference-page citation hit rate: **1.0000**;
- target-AD citation hit rate: **1.0000**.

Findings:

- `E5F-021` becomes correct → Layer B retrieval failure confirmed;
- `E5F-011` becomes correct with focused evidence → Layer C evidence-selection/completeness sensitivity;
- `E5F-040` demonstrates status-calibration/run-to-run variability;
- `E5F-035` exact transport retry recovered successfully.

The original oracle batch remains preserved as 39 successes / 1 failure.

## Post-final unseen-document evaluation — ACTIVE

The five unseen families were excluded from E5 development/final construction.

Frozen cases:

- corrected — `2008-0008`;
- revised — `2011-0041R1`;
- supersedure — `2011-0142`;
- long document — `2026-0084`;
- simple original — `2007-0173`.

### U0/U1 — COMPLETE

- exact source hashes: **5/5**;
- pages: **21**;
- deterministic extraction: **5/5**;
- schema valid: **5/5**.

### U2 — COMPLETE / HUMAN-LOCKED

- questions: **15**;
- exactly 3 per PDF;
- human verified: **15/15**;
- answerable: **14**;
- abstention: **1**;
- locked question SHA-256: `603d3385f5d083aeabf071d8d0c9be88896d31eb3f6530e881efeb3c03baeb2d`.

### U3 — TEMPORARY PRIMARY COMPLETE / PRESERVED

- hosted success: **14/15 = 93.33%**;
- answerability/status accuracy on successful requests: **13/14 = 92.86%**;
- page-overlap Recall@5: **14/14 = 100%**;
- reference-page citation hit: **100%**;
- target-AD citation hit: **100%**.

Post-hoc exact reference-quote containment diagnostic:

- any approved quote contained in top 5: **12/14 = 85.71%**;
- all approved quotes contained in top 5: **8/14 = 57.14%**.

Diagnostic only; it does not replace the frozen page-level retrieval metrics.

### U4 — HUMAN SEMANTIC REVIEW COMPLETE / LOCKED

Human-approved final temporary result:

- semantic PASS: **13**;
- semantic FAIL: **1**;
- persistent provider/transport failure: **1**;
- semantic accuracy on successful responses: **13/14 = 92.86%**;
- strict first-pass end-to-end success: **13/15 = 86.67%**.

Final decisions:

- `U5Q-001`: **PASS** — omission of dates is not material because the question did not request them;
- `U5Q-010`: **FAIL — Layer B temporary passage selection**;
- `U5Q-011`: **persistent provider/transport failure** — both the primary call and the one permitted exact retry returned empty final content;
- remaining 12: **PASS**.

Result lock:

```text
evaluation_sets/unseen_incoming_5_v1/unseen_temporary_result_lock.json
```

Validator before permanent ingestion:

```text
full_corpus_pipeline/layer_c/validate_unseen_temporary_result_lock.py
```

### U5/U6 permanent ingestion — NEXT / ALLOWED

Permanent ingestion may proceed only after the temporary result validator passes and only in an isolated evaluation store/index. Frozen E5 indexes remain immutable.

Detailed protocol:

```text
docs/UNSEEN_DOCUMENT_EVALUATION.md
```
