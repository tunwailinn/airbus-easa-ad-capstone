# E2 Status

Publication labels: E1 = legacy E4; E2-A–D = legacy E5-A–D. Artifact names, question IDs and code excerpts retain their original labels. See [experiment label mapping](EXPERIMENT_LABELS.md).

Last updated: 27 August 2026

## Current state

E2 retrieval development, hosted-QA freeze, the one-time 40-question final benchmark, human semantic review, and the final oracle/reference-evidence diagnostic are complete and frozen.

Authoritative E2 primary final result:

```text
38/40 = 95.0% strict end-to-end semantic accuracy
35/36 = 97.22% frozen E5-D Recall@5
24/24 = 100% known-document Recall@5
11/12 = 91.67% discovery Recall@5
```

No retrieval, prompt, provider/model, reasoning-effort, response-contract, evidence-depth or final-question changes are allowed from final or unseen outcomes. Oracle and unseen results are separate diagnostics/generalization results and cannot replace the primary score.

## Frozen E2 retrieval

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

- E2-C BM25 + `Qwen/Qwen3-Embedding-0.6B@97b0c61`;
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

## One-time E2 final benchmark — COMPLETE

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

The five unseen families were excluded from E2 development/final construction.

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

### U5/U6 — ISOLATED PERMANENT INGESTION COMPLETE / PASS

- Ingestion success: **5/5**;
- AD identity match: **5/5**;
- Parser version match (`content-local-v2.1.6`): **5/5**;
- Exact deterministic record match against U1 preparation: **5/5**;
- Copied source SHA match: **5/5**;
- Exact duplicate rejection without mutation: **5/5**;
- Isolated E1 chunk append match: **5/5**;
- Isolated E2-C dense row alignment: **5/5**;
- Frozen source indexes unchanged: **true**;
- Automatic safeguards pass: **true**.

The isolated evaluation derivative grew from 1,786 to 1,791 documents and 12,634 to 12,670 section chunks (+36 chunks).

Result lock:
```text
evaluation_sets/unseen_incoming_5_v1/unseen_permanent_ingestion_result_lock.json
```

### U7 — POST-INGESTION QA COMPLETE / HUMAN-APPROVED / LOCKED

Retrieval across 14 answerable questions:
- Recall@1: **13/14 = 92.86%**;
- Recall@3: **14/14 = 100%**;
- Recall@5: **14/14 = 100%**;
- Correct source@1: **14/14 = 100%**;
- Correct source+page@5: **14/14 = 100%**.

Human-approved semantic result:
- Semantic PASS: **13**;
- Semantic FAIL: **1** (`U5Q-010`, Layer B passage selection omission in top-5 evidence);
- Technical provider failure: **1** (`U5Q-011`, empty final JSON content from DeepSeek);
- Semantic accuracy among successful hosted responses: **13/14 = 92.86%**;
- Strict primary end-to-end success: **13/15 = 86.67%**.

Human review lock:
```text
evaluation_sets/unseen_incoming_5_v1/u7_post_ingestion_human_semantic_review_lock.json
```

### U8 — FINAL UNSEEN GENERALIZATION REPORT COMPLETE / LOCKED

- Authoritative report: [`docs/U8_FINAL_UNSEEN_GENERALIZATION_REPORT.md`](U8_FINAL_UNSEEN_GENERALIZATION_REPORT.md)
- Completion lock: `evaluation_sets/unseen_incoming_5_v1/unseen_final_generalization_lock.json`
- Validator: `full_corpus_pipeline/layer_c/validate_unseen_final_generalization.py`

## Post-Evaluation Assistant Integration & Demo Freeze

Downstream post-evaluation engineering:
- **FastAPI + Next.js Serving**: In-memory model warming on Apple MPS with 77.26% median retrieval latency reduction (26.87 s to 6.11 s) and 10/10 exact top-5 match against batch E2-D.
- **Reliability Hardening**: Single-AD follow-up context, strict SSE completion event checks, safe retrieval/generation cancellation.
- **Validation**: Live browser scenarios D1–D8 all passed on 26 August 2026.
- **Freeze Baseline Commit**: `88f96d5aca67fb0c98113f4f7b04410402a7e559`.
- **Launcher**: `make demo` / `bash scripts/start_demo.sh`.

See [`docs/ASSISTANT_STATUS.md`](ASSISTANT_STATUS.md) and [`docs/PROJECT_STATUS.md`](PROJECT_STATUS.md).
