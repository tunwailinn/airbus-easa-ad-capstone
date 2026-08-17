# Five-PDF Unseen Temporary QA — First-Pass Record

Date: 17 August 2026

## Status

This document records the immutable first-pass temporary-document QA result for the five frozen unseen PDFs. It is a post-final generalization experiment and does not alter the frozen E5 primary result of **38/40 = 95.0%**.

Permanent ingestion has **not** started.

## Frozen inputs

- unseen questions: 15 human-reviewed/locked questions;
- unseen questions SHA-256: `603d3385f5d083aeabf071d8d0c9be88896d31eb3f6530e881efeb3c03baeb2d`;
- 14 answerable + 1 insufficient-evidence/abstention;
- five held-out PDFs / 21 pages;
- document-scoped temporary retrieval only;
- all prepared section chunks from each selected PDF passed to the pinned E5-D Qwen reranker;
- final evidence depth: 5;
- DeepSeek `deepseek-v4-pro`, thinking enabled, reasoning effort high, max tokens 4096;
- prompt/contract unchanged from the hosted-QA freeze;
- semantic retry prohibited.

## First-pass automatic result

- hosted successes: **14/15**;
- hosted failures: **1/15**;
- request success rate: **93.33%**;
- answerability/status accuracy over successful requests: **92.86%**;
- page-overlap any-reference-page Recall@5: **100%**;
- page-overlap full-reference-page coverage@5: **100%**;
- reference-page citation hit rate on applicable successful answers: **100%**;
- target-AD citation hit rate on applicable successful answers: **100%**;
- permanent ingestion started: **false**.

The single request failure was `U5Q-011`: DeepSeek returned empty final JSON content. This is a technical/provider failure and is eligible for one exact transport retry using the identical preserved prompt/evidence/configuration. The original failure remains part of the first-pass record.

## Important passage-level diagnostic

The 100% reference-page metrics above measure **page overlap**, not literal answer-bearing passage support.

`U5Q-010` demonstrates this distinction. Its human reference answer is on page 1 of AD `2026-0084`, so the page-level metric counted the top-5 evidence as a hit. However, the top-5 passages contained only the generic page-1 `Document` chunk (`Type/Model designation(s): A340 aeroplanes`) and did **not** contain the separate page-1 `Supersedure` and `Applicability` chunks with:

- `This AD supersedes EASA AD 2019-0243 dated 30 September 2019.`
- `Airbus A340-211, A340-212, A340-213, A340-311, A340-312 and A340-313 ...`

The model therefore returned `insufficient_evidence`. This is best attributed to **temporary passage selection/reranking (Layer B)**, not to an inability of Layer C to answer from evidence it actually received.

A separate diagnostic utility now checks exact normalized containment of the human-approved source quotations in the preserved top-5 evidence:

```text
full_corpus_pipeline/layer_c/diagnose_unseen_reference_quote_containment.py
```

This diagnostic does not modify the frozen first-pass retrieval report.

## AI-assisted semantic audit — pending human confirmation

The assistant audit of the 14 successful requests proposes:

- `U5Q-001` — **FAIL / Layer C completeness**: the answer identifies the typographical Service Bulletin-reference correction and the superseded AD number, but omits the approved lifecycle details `[Corrected: 10 September 2009]` and the superseded directive date `21 March 2001`. The additional statement that the AD requires a new inspection programme is source-supported.
- `U5Q-010` — **FAIL / Layer B temporary passage selection**: answer-bearing Supersedure/Applicability chunks were not in top 5 even though page 1 was represented.
- `U5Q-011` — **TECHNICAL FAILURE / provider transport-output issue**: eligible for exact retry; no semantic conclusion until recovery is inspected.
- all other successful requests (`U5Q-002`–`009`, `U5Q-012`–`015`) — **proposed PASS** against the human-reviewed references.

Until the reviewer explicitly confirms these semantic decisions, do **not** label the assistant audit as human-reviewed.

## Exact transport retry

Guarded retry utility:

```text
full_corpus_pipeline/layer_c/retry_unseen_temporary_transport.py
```

For `U5Q-011`:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.retry_unseen_temporary_transport \
  --question-id U5Q-011
```

The retry refuses to run unless the question is a preserved primary failure, is absent from primary successes, and the prompt-payload/evidence-pack/freeze hashes match the original run. It does not rerun retrieval and cannot overwrite the original first-pass outputs.

## Gate before permanent ingestion

Do not start permanent ingestion until all of the following are preserved:

1. first-pass automatic artifacts;
2. reference-quote containment diagnostic;
3. exact transport retry result for `U5Q-011`;
4. human-confirmed semantic review of the temporary QA outputs.

Any later engineering improvement must be reported post-hoc and must not replace this first-pass result.
