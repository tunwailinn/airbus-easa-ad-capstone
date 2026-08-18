# Frozen Five-PDF Unseen-Document Evaluation

## Status

This is the post-final generalization experiment performed after the frozen E5-D retrieval configuration, frozen hosted-QA configuration, one-time 40-question final benchmark, human semantic review, and final oracle diagnostic.

The E5 primary result remains authoritative and unchanged:

- 40 final questions;
- 38 semantic passes / 2 semantic failures;
- strict end-to-end semantic accuracy: **95.0%**;
- E5-D final Recall@5: **35/36 = 97.22%**.

Unseen outcomes are reported separately and may not be used to retune the frozen parser, retrieval stack, prompt, DeepSeek model/settings, response contract, or evidence depth.

## Current checkpoint — 18 August 2026

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

Post-hoc exact reference-quote containment diagnostic:

- any approved reference quote contained at top 5: **12/14 = 85.71%**;
- all approved reference quotes contained at top 5: **8/14 = 57.14%**.

Important attribution finding:

- `U5Q-010`: page 1 overlapped top-5, but neither approved answer-bearing `Supersedure` nor `Applicability` quote was contained in top-5. The hosted model returned `insufficient_evidence`; this is therefore a **Layer B temporary passage-selection failure**, not a Layer C reasoning failure.

### U4 — temporary human semantic review — COMPLETE / HUMAN-APPROVED / LOCKED

Final human-approved outcome:

- human semantic PASS: **13**;
- human semantic FAIL: **1**;
- persistent technical/provider failure: **1**;
- semantic accuracy among successful hosted responses: **13/14 = 92.86%**;
- strict first-pass end-to-end success: **13/15 = 86.67%**.

Final decisions:

- `U5Q-001`: **PASS**. The question does not require correction/supersedure dates; the hosted answer supplied the requested correction, directive identity, and republication reason.
- `U5Q-010`: **FAIL — Layer B temporary passage selection**.
- `U5Q-011`: **persistent provider/transport failure**; no semantic result.
- remaining 12 questions: **PASS**.

The original `U5Q-011` request, the one permitted exact transport retry, and a later post-hoc identical provider probe all returned `DeepSeek JSON Output returned empty final content`. Those extra attempts do not replace the locked U3/U4 result.

### U5/U6 — isolated permanent ingestion + safeguards — COMPLETE / PASS

The five held-out PDFs were admitted only to an isolated evaluation store/index after the U3/U4 result lock validated.

Technical-safeguard results:

- ingestion success: **5/5**;
- AD identity match: **5/5**;
- frozen parser match: **5/5**;
- deterministic record match against U1: **5/5**;
- copied source SHA match: **5/5**;
- isolated E4 append checks: **5/5**;
- isolated E5-C Qwen row-alignment checks: **5/5**;
- immediate exact duplicate rejection with no mutation: **5/5**;
- lifecycle decisions recorded: **5/5**;
- frozen E4 source artifact unchanged: **true**;
- frozen E5-C source artifact unchanged: **true**;
- normal `data_incoming/` unchanged: **true**.

The isolated derivative grew from **12,634 to 12,670 chunks** and from **1,786 to 1,791 documents**.

The U5/U6 result is a technical-safeguard pass. It does not claim that every structured Layer A field is semantically perfect. Some unseen `revision_statement` captures are over-broad but exactly reproduce the pre-ingestion U1 records, so they are recorded as pre-existing extraction limitations rather than ingestion regressions.

Committed U5/U6 lock:

```text
evaluation_sets/unseen_incoming_5_v1/unseen_permanent_ingestion_result_lock.json
```

### Pre-U7 frozen-chunk-policy compatibility gate — COMPLETE / PASS

Before post-ingestion E5-D retrieval, the five newly appended documents were reconstructed with the frozen E4 strict section chunking policy and compared against the isolated derivative.

- selected documents: **5**;
- exact match: **5/5**;
- chunk counts and chunk IDs matched exactly for every document;
- `all_exact`: **true**.

This confirms that U7 evaluates the same chunking policy used by the frozen E5 retrieval stack.

### U7 — post-ingestion E5-D + frozen Layer C primary — COMPLETE / PRESERVED

U7 reuses the same 15 locked unseen questions after the five PDFs have been admitted to the isolated E5-compatible derivative.

Frozen algorithm/configuration retained:

- E5-C BM25 + `Qwen/Qwen3-Embedding-0.6B@97b0c61` candidate generation;
- candidate depth: **20**;
- E5-D `Qwen/Qwen3-Reranker-0.6B@e61197e`;
- evidence depth: **5**;
- DeepSeek `deepseek-v4-pro`;
- thinking enabled, reasoning effort high, max tokens 4096;
- prompt `e5-hosted-qa-prompt-v1.0-dev`;
- no frozen E5 artifact mutation;
- no retrieval retuning.

Post-ingestion retrieval result on 14 answerable questions:

- Recall@1: **13/14 = 92.86%**;
- Recall@3: **14/14 = 100%**;
- Recall@5: **14/14 = 100%**;
- MRR@5: **96.43%**;
- nDCG@5: **97.36%**;
- correct source@1: **14/14 = 100%**;
- correct source+page@5: **14/14 = 100%**;
- candidate source+page recall@20: **14/14 = 100%**.

Primary hosted result:

- hosted successes: **14/15 = 93.33%**;
- hosted failures: **1/15** (`U5Q-011`);
- answerability/status accuracy among successful responses: **13/14 = 92.86%**;
- reference-page citation hit rate on answerable successful responses: **12/13 = 92.31%**;
- target-AD citation hit rate on answerable successful responses: **12/13 = 92.31%**.

Passage-support diagnostic:

- any approved reference quote contained@5: **12/14 = 85.71%**;
- all approved reference quotes contained@5: **8/14 = 57.14%**.

Important U7 attribution findings:

- `U5Q-010`: page-level E5-D reports a reference-page hit, but neither approved answer-bearing `Supersedure` nor `Applicability` quote is in the top-five prompt evidence. The hosted `insufficient_evidence` response is therefore attributed to **post-ingestion Layer B passage selection**. This demonstrates that page-level Recall@5 can overstate answer-bearing passage support.
- `U5Q-011`: **both approved reference quotations are present in the U7 top-five evidence**, but the hosted request still failed with `DeepSeek JSON Output returned empty final content`. This is a provider/structured-output failure, not a retrieval failure. Its U7 prompt-payload SHA-256 is `7a85360c8bfcb9bf9dff5f2932d6381e75b3bb740a8b271192501143c634ba5b`.
- `U5Q-014` and `U5Q-015`: exact normalized reference-quote containment is false, but the hosted answers are semantically correct and supported by the supplied passages. Exact quote containment remains a diagnostic, not a replacement retrieval score.

### U7 semantic review — AI-ASSISTED PROPOSAL / HUMAN APPROVAL PENDING

Current proposed classification:

- proposed semantic PASS: **13**;
- proposed semantic FAIL: **1** (`U5Q-010`);
- technical/provider failure: **1** (`U5Q-011`);
- proposed semantic accuracy among successful hosted responses: **13/14 = 92.86%**;
- proposed strict primary end-to-end success: **13/15 = 86.67%**.

These values must **not** be called human reviewed until the reviewer explicitly approves the U7 decisions.

A separate exact transport retry command has been added for the preserved U7 `U5Q-011` failure. It reuses the exact U7 question/evidence/prompt-payload hash and frozen Layer C configuration without rerunning retrieval. Any retry result is supplementary and cannot overwrite the preserved U7 primary.

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
→ U5 permanent ingestion into isolated evaluation      COMPLETE / PASS
→ U6 duplicate/lifecycle/index-update safeguards       COMPLETE / PASS
→ U7 post-ingestion QA/citation verification           COMPLETE / HUMAN REVIEW PENDING
→ U8 final unseen-generalization report                NEXT
```

## Interpretation boundary

Unseen failures must be attributed to the stage that caused them: source preparation, deterministic extraction, temporary or post-ingestion passage selection, Layer C generation/status, provider/transport, duplicate handling, lifecycle handling, index update, or post-ingestion retrieval/QA.

Do not silently fix a held-out failure and report the fixed output as the original unseen result. Any later fix or extra retry is post-hoc engineering/diagnostic work and must be labelled separately.
