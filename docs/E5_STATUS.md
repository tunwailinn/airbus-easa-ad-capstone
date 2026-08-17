# E5 Status

Last updated: 17 August 2026

## Current state

E5 retrieval development, hosted-QA freeze, the one-time 40-question final benchmark, human semantic review, and the final oracle/reference-evidence diagnostic are complete and frozen.

Authoritative primary final result:

```text
38/40 = 95.0% strict end-to-end semantic accuracy
35/36 = 97.22% frozen E5-D Recall@5
24/24 = 100% known-document Recall@5
11/12 = 91.67% discovery Recall@5
```

No retrieval, prompt, provider/model, reasoning-effort, response-contract, evidence-depth or final-question changes are allowed from final or unseen outcomes. Oracle and unseen results are separate diagnostics/generalization results and cannot replace the primary score.

## Frozen E5 retrieval

Development benchmark:

- 24 development families / 16 final-test families;
- 60 human-reviewed development questions;
- 54 answerable retrieval questions + 6 abstention/conflict questions.

E5-D selected development result:

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

Retrieval freeze:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/retrieval_freeze.json
```

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

Hosted-QA freeze:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json
```

## One-time E5 final benchmark — COMPLETE

Final set:

- 40 human-reviewed questions;
- 36 answerable + 4 abstention/conflict;
- 24 known-document + 12 identifier-free discovery + 4 abstention/conflict.

Automatic primary result:

- hosted success: **40/40**;
- answerability/status accuracy: **1.0000**;
- Recall@1/3/5: **0.8333 / 0.9722 / 0.9722**;
- MRR@5: **0.8981**;
- nDCG@5: **0.9173**;
- known-document Recall@5: **1.0000**;
- discovery Recall@5: **0.9167**.

Human semantic result:

- passes: **38/40**;
- failures: **2/40**;
- strict accuracy: **95.0%**.

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
- `E5F-040` demonstrates status-calibration/run-to-run variability under unchanged negative-control evidence;
- `E5F-035` exact transport retry recovered successfully with unchanged prompt/evidence/config.

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
- schema valid: **5/5**;
- no hosted inference during preparation;
- no permanent ingestion during preparation.

### U2 — COMPLETE / HUMAN-LOCKED

- questions: **15**;
- exactly 3 per PDF;
- human verified: **15/15**;
- answerable: **14**;
- abstention: **1**;
- locked question SHA-256: `603d3385f5d083aeabf071d8d0c9be88896d31eb3f6530e881efeb3c03baeb2d`.

Committed lock/audit:

```text
evaluation_sets/unseen_incoming_5_v1/unseen_lock.json
evaluation_sets/unseen_incoming_5_v1/unseen_question_verification_audit.json
evaluation_sets/unseen_incoming_5_v1/unseen_question_final_review.md
```

U5Q-008's reviewer-requested phrase check was verified directly against the prepared `2011-0142` source packet; the question/reference answer was retained unchanged.

### U3 — NEXT

Temporary-document QA uses only the selected PDF's prepared section chunks, reranks all of them with the pinned E5-D Qwen reranker, supplies top-5 evidence to frozen Layer C, and writes an immutable first-pass temporary result.

Implementation:

```text
full_corpus_pipeline/layer_c/validate_unseen_question_lock.py
full_corpus_pipeline/layer_c/run_unseen_temporary_qa.py
full_corpus_pipeline/layer_c/evaluate_unseen_temporary_qa.py
```

### U5 permanent ingestion — BLOCKED

Do not permanently ingest any of the five PDFs until temporary-document QA and its human semantic review are preserved. Permanent ingestion will then be evaluated separately in an isolated evaluation store/index.

Detailed protocol:

```text
docs/UNSEEN_DOCUMENT_EVALUATION.md
```
