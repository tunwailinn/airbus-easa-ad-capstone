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
- hosted inference during preparation: **false**;
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

Committed lock/audit records:

```text
evaluation_sets/unseen_incoming_5_v1/unseen_lock.json
evaluation_sets/unseen_incoming_5_v1/unseen_question_verification_audit.json
evaluation_sets/unseen_incoming_5_v1/unseen_question_final_review.md
```

### U3 — temporary-document retrieval + frozen Layer C QA — FIRST PASS COMPLETE

The primary temporary run is preserved at:

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
- target-AD citation hit rate on applicable successful answers: **100%**;
- permanent ingestion started: **false**.

The page-level retrieval metric is retained as the frozen first-pass metric, but it is not interpreted as proof that the exact answer-bearing passage was present.

### Post-hoc reference-quote containment diagnostic

Diagnostic implementation:

```text
full_corpus_pipeline/layer_c/diagnose_unseen_reference_quote_containment.py
```

This check asks whether the human-approved evidence quotations themselves are contained in the top-5 prompt evidence.

Answerable-question diagnostic:

- any approved reference quote contained at top 5: **12/14 = 85.71%**;
- all approved reference quotes contained at top 5: **8/14 = 57.14%**.

These are **diagnostic-only** values and do not replace the frozen page-level retrieval metrics. Exact normalized quote containment can fail even when a supplied passage is sufficient for a semantically correct answer.

Important attribution finding:

- `U5Q-010`: page 1 overlapped top-5, but **neither** approved answer-bearing `Supersedure` nor `Applicability` quote was contained in top-5. The hosted model returned `insufficient_evidence`. This is therefore a temporary passage-selection failure, not a Layer C reasoning failure.

Other diagnostic examples show why exact quote containment is not itself the primary retrieval score: some successful correct answers were produced even where the full approved quote string was not literally contained in top-5.

### U5Q-011 exact transport retry — FAILED / CLOSED

The first-pass request for `U5Q-011` failed with:

```text
DeepSeek JSON Output returned empty final content
```

One exact transport retry was performed under the predeclared retry policy. The retry preserved the identical:

- question;
- evidence pack;
- prompt payload SHA-256;
- provider/model;
- hosted-QA prompt/contract;
- thinking mode;
- reasoning effort;
- max-token limit.

Prompt payload SHA-256:

```text
b17e0b69d1a7a28071cb9fc219272e4dc6e755223426cc39e08bd98ca66e5f33
```

The retry also failed with the same empty-final-content error. No further retry is permitted. Record `U5Q-011` as a **persistent provider/transport failure**, not a semantic failure.

### U4 — human semantic review — PENDING FINAL HUMAN APPROVAL

An AI-assisted semantic audit has produced the following **provisional** classifications:

- `U5Q-001`: proposed **FAIL — Layer C completeness**. The response omitted the human-approved correction date `[Corrected: 10 September 2009]`, even though that date was supplied in top-5 evidence.
- `U5Q-010`: proposed **FAIL — Layer B temporary passage selection**. The approved answer-bearing passages were absent from top-5.
- `U5Q-011`: **persistent technical/provider failure** after the single permitted exact retry.
- remaining 12 questions: proposed **PASS**.

If the reviewer approves those semantic decisions, the reported unseen temporary-QA results will be:

- semantic accuracy among successful first-pass responses: **12/14 = 85.71%**;
- strict first-pass end-to-end success: **12/15 = 80.0%**;
- semantic failures: **2**;
- persistent provider/transport failures: **1**.

These values are **not human-finalized until explicit reviewer approval is recorded**.

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
→ U4 offline/human temporary-QA evaluation             PENDING HUMAN APPROVAL
→ U5 permanent ingestion into isolated evaluation      BLOCKED UNTIL U4 LOCKED
→ U6 duplicate/lifecycle/index-update safeguards       NOT STARTED
→ U7 post-ingestion QA/citation verification           NOT STARTED
→ U8 final unseen-generalization report                NOT STARTED
```

Do not permanently ingest a held-out PDF until the temporary-document result and human semantic decisions are preserved.

## U5/U6 — permanent ingestion — NOT STARTED

Permanent ingestion will use an isolated unseen-evaluation store/index first and test:

- exact SHA-256 duplicate rejection;
- frozen deterministic extraction;
- no model retraining;
- lifecycle/revision/correction/supersedure decisions;
- source provenance preservation;
- index append behavior;
- repeat-ingestion rejection;
- post-ingestion QA and citations.

Frozen E5 benchmark indexes remain immutable audit artifacts.

## Interpretation boundary

Unseen failures must be attributed to the stage that caused them: source preparation, deterministic extraction, temporary passage selection, Layer C generation/status, provider/transport, duplicate handling, lifecycle handling, index update, or post-ingestion retrieval/QA.

Do not silently fix a held-out failure and report the fixed output as the original unseen result. Any later fix is post-hoc engineering work and must be labelled separately.
