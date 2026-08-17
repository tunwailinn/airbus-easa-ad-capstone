# Frozen Five-PDF Unseen-Document Evaluation

## Status

This is the post-final generalization experiment performed after the frozen E5-D retrieval configuration, frozen hosted-QA configuration, one-time 40-question final benchmark, human semantic review, and final oracle diagnostic.

The E5 primary result remains authoritative and unchanged:

- 40 final questions;
- 38 semantic passes / 2 semantic failures;
- strict end-to-end semantic accuracy: **95.0%**;
- E5-D final Recall@5: **35/36 = 97.22%**.

Unseen outcomes are reported separately and may not be used to retune the frozen parser, retrieval stack, prompt, DeepSeek model/settings, response contract, or evidence depth.

## Current checkpoint — 17 August 2026

### U0/U1 — source validation + non-destructive preparation — COMPLETE

- preparation version: `unseen-5-preparation-v1.0`;
- frozen documents: **5/5**;
- exact source SHA-256 matches: **5/5**;
- source pages: **21**;
- deterministic extraction successes: **5/5**;
- schema-valid extracted records: **5/5**;
- parser: `content-local-v2.1.6`;
- permanent ingestion during preparation: **false**.

Preparation manifest SHA-256:

```text
e3a60433348003b8e238a6704d40ddcd6e389e4f7804df92057f4eec9bbadc05
```

### U2 — human-reviewed unseen QA authoring + lock — COMPLETE

The unseen QA set contains **15 questions, exactly three per held-out PDF**.

- human verified: **15/15**;
- rejected: **0**;
- answerable from AD: **14**;
- abstention/insufficient-evidence: **1**.

Locked question SHA-256:

```text
603d3385f5d083aeabf071d8d0c9be88896d31eb3f6530e881efeb3c03baeb2d
```

### U3 — temporary-document retrieval + frozen Layer C QA — COMPLETE / PRESERVED

The immutable first-pass temporary run is preserved at:

```text
data_processed/evaluations/unseen_5/temporary_primary/
```

Configuration:

- retrieval restricted to the selected held-out PDF;
- all prepared section chunks from that PDF considered, maximum 14;
- pinned `Qwen/Qwen3-Reranker-0.6B@e61197e` reranker;
- final evidence depth: **5**;
- frozen DeepSeek V4 Pro Layer C configuration;
- no permanent ingestion;
- no semantic retry.

First-pass automatic results:

- questions: **15**;
- hosted successes: **14**;
- hosted failures: **1**;
- request success rate: **14/15 = 93.33%**;
- answerability/status accuracy on successful requests: **13/14 = 92.86%**;
- reference-page any-overlap Recall@5: **14/14 = 100%**;
- reference-page full-coverage@5: **14/14 = 100%**;
- reference-page citation hit rate on applicable successful answers: **100%**;
- target-AD citation hit rate on applicable successful answers: **100%**.

The page-level retrieval metric is retained as the frozen first-pass metric, but it is not interpreted as proof that the exact answer-bearing passage was present.

### Reference-quote containment diagnostic — COMPLETE / DIAGNOSTIC ONLY

Answerable-question diagnostic:

- any approved reference quote contained at top 5: **12/14 = 85.71%**;
- all approved reference quotes contained at top 5: **8/14 = 57.14%**.

These values do not replace the frozen page-level retrieval metrics. Exact quote containment can fail even when a supplied passage semantically supports a correct answer.

Important attribution finding:

- `U5Q-010`: page 1 overlapped top-5, but **neither** approved answer-bearing `Supersedure` nor `Applicability` quote was contained in top-5. The hosted model returned `insufficient_evidence`; this is therefore a **Layer B temporary passage-selection failure**, not a Layer C reasoning failure.

### U5Q-011 exact transport retry — FAILED / CLOSED

The first-pass request for `U5Q-011` failed with:

```text
DeepSeek JSON Output returned empty final content
```

One exact transport retry was performed with the identical question, evidence, prompt payload, provider/model, hosted-QA prompt/contract, thinking mode, reasoning effort, and max-token limit.

Prompt payload SHA-256:

```text
b17e0b69d1a7a28071cb9fc219272e4dc6e755223426cc39e08bd98ca66e5f33
```

The retry also failed with the same empty-final-content error. No further retry is permitted. `U5Q-011` is a **persistent provider/transport failure** and has no semantic score.

### U4 — human semantic review — COMPLETE / HUMAN-APPROVED / LOCKED

Final human-approved outcome:

- human semantic PASS: **13**;
- human semantic FAIL: **1**;
- persistent technical/provider failure: **1**;
- semantic accuracy among successful hosted responses: **13/14 = 92.86%**;
- strict first-pass end-to-end success: **13/15 = 86.67%**.

Final decisions:

- `U5Q-001`: **PASS**. The earlier AI-assisted proposal was too strict. The question asks for the correction identified, which directive is superseded, and why the AD was republished; it does not ask for either date. The hosted answer supplied all requested elements.
- `U5Q-010`: **FAIL — Layer B temporary passage selection**.
- `U5Q-011`: **persistent provider/transport failure**; no semantic result and no further retry.
- remaining 12 questions: **PASS**.

Committed human-review records:

```text
evaluation_sets/unseen_incoming_5_v1/unseen_temporary_human_review.csv
evaluation_sets/unseen_incoming_5_v1/unseen_temporary_human_review_summary.json
evaluation_sets/unseen_incoming_5_v1/unseen_temporary_human_review_final.md
evaluation_sets/unseen_incoming_5_v1/unseen_temporary_human_review_lock.json
evaluation_sets/unseen_incoming_5_v1/unseen_temporary_result_lock.json
```

The complete U3/U4 result is bound by SHA-256 in `unseen_temporary_result_lock.json`. Permanent ingestion is allowed only after `validate_unseen_temporary_result_lock` passes.

## Frozen unseen set

| Stratum | AD | Pages |
|---|---|---:|
| corrected | 2008-0008 | 2 |
| revised | 2011-0041R1 | 4 |
| supersedure | 2011-0142 | 3 |
| long document | 2026-0084 | 10 |
| simple original | 2007-0173 | 2 |

## Evaluation sequence

```text
U0 source/selection validation                         COMPLETE
→ U1 non-destructive unseen preparation               COMPLETE
→ U2 human-reviewed unseen QA authoring + lock         COMPLETE
→ U3 temporary-document retrieval + frozen Layer C QA  COMPLETE
→ U4 offline/human temporary-QA evaluation             COMPLETE / LOCKED
→ U5 permanent ingestion into isolated evaluation      NEXT / ALLOWED
→ U6 duplicate/lifecycle/index-update safeguards       NEXT
→ U7 post-ingestion QA/citation verification           NOT STARTED
→ U8 final unseen-generalization report                NOT STARTED
```

## U5/U6 — permanent ingestion — NEXT

Permanent ingestion must use an **isolated unseen-evaluation store/index first**. It must not modify frozen E5 benchmark indexes.

Required checks:

- validate `unseen_temporary_result_lock.json` before ingestion;
- exact SHA-256 duplicate rejection;
- frozen deterministic extraction;
- no model retraining;
- lifecycle/revision/correction/supersedure decisions;
- source provenance preservation;
- isolated index append behavior;
- repeat-ingestion rejection;
- post-ingestion QA and citations.

Frozen E5 benchmark indexes remain immutable audit artifacts.

## Interpretation boundary

Unseen failures must be attributed to the stage that caused them: source preparation, deterministic extraction, temporary passage selection, Layer C generation/status, provider/transport, duplicate handling, lifecycle handling, index update, or post-ingestion retrieval/QA.

Do not silently fix a held-out failure and report the fixed output as the original unseen result. Any later fix is post-hoc engineering work and must be labelled separately.
