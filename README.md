# Airbus EASA AD Extraction and RAG Capstone

Intelligent engineering document automation for Airbus S.A.S. Airworthiness Directives issued by EASA.

## Architecture

```text
Layer A — deterministic structured extraction
→ metadata, lifecycle fields, exact source-derived difficult sections

Layer B — verified original-PDF retrieval
→ page-preserving evidence, engineering-aware retrieval, lifecycle-aware routing

Layer C — frozen hosted evidence-grounded QA
→ answer | insufficient_evidence | conflicting_evidence
→ source/page/section citations resolved locally from evidence metadata
```

Complex compliance semantics are interpreted from original-PDF evidence at question time. Full-corpus extraction and indexing do **not** use a hosted LLM. DeepSeek V4 Pro is used only in the frozen Layer C QA condition.

## Current status — 18 August 2026

The benchmark and five-document unseen-generalization evaluation are **complete and locked**.

Completed/frozen:

- Layer A deterministic extraction development + clean locked test;
- strict Airbus S.A.S. scope audit;
- verified original-PDF page-text layer;
- historical E0/E4 retrieval experiments;
- E5-A/B/C/D engineering-aware retrieval development;
- E5-D retrieval freeze;
- Layer C development + hosted-QA freeze;
- human-reviewed 40-question final benchmark;
- one-time final benchmark + human semantic review;
- final oracle/reference-evidence diagnostic;
- five-PDF unseen preparation and 15-question human-reviewed lock;
- U3/U4 temporary-document unseen evaluation;
- U5/U6 isolated permanent-ingestion and duplicate/index safeguards;
- frozen-chunk-policy compatibility gate;
- U7 post-ingestion E5-D + Layer C evaluation and human review;
- U8 final unseen-generalization report + completion lock.

Authoritative frozen E5 final result:

```text
38/40 = 95.0% strict end-to-end semantic accuracy
35/36 = 97.22% frozen E5-D Recall@5
24/24 = 100% known-document Recall@5
11/12 = 91.67% discovery Recall@5
```

Final unseen post-ingestion result:

```text
14/14 = 100% E5-D Recall@5 on answerable unseen questions
14/14 = 100% correct source@1
13/14 = 92.86% semantic accuracy on successful hosted responses
13/15 = 86.67% strict primary end-to-end success
U5Q-010 = Layer B answer-bearing passage-selection failure
U5Q-011 = provider/structured-output technical failure
```

The unseen result is **separate** from the frozen 40-question E5 final benchmark and does not replace the 95.0% primary score.

## Corpus

- frozen physical snapshot: **1,809 PDFs / 1,808 base AD families**;
- nominal development extraction: **1,804 PDFs**;
- strict Airbus-only operational retrieval view: **1,786 PDFs**;
- verified operational pages: **6,002**;
- retained external/mixed-holder records outside strict operational view: **18**;
- unresolved holder-scope unknowns: **0**;
- frozen unseen PDFs: **5**.

## Layer A — frozen extraction

Parser: `content-local-v2.1.6`  
Evaluator: `content-eval-v3.1.5`

Development primary (28 records):

- stable metadata macro F1: **0.9948**;
- applicability-model F1: **0.9929**;
- reference-number F1: **0.8065**;
- superseded-AD-number F1: **1.0000**;
- difficult raw-section presence F1: **1.0000** for all five sections;
- source containment: **130/130**;
- contamination detected: **0**.

Clean locked test primary (17 records):

- stable metadata macro F1: **0.9831**;
- applicability-model F1: **0.9222**;
- reference-number F1: **0.9000**;
- superseded-AD-number F1: **0.6667**;
- difficult raw-section presence F1: **1.0000** for all five sections;
- source containment: **74/74**;
- contamination detected: **0**.

## Layer B — verified source + frozen E5-D retrieval

Verified original-PDF page source:

```text
data_processed/page_text_v1_1/operational_airbus/
```

- **1,786/1,786** documents successful;
- **6,002** pages;
- zero unresolved weak/OCR pages;
- one reviewed visual override: AD `2011-0006`, page 3.

Selected E5-D development retrieval:

- Recall@1: **0.7963**;
- Recall@3: **0.9259**;
- Recall@5: **0.9630**;
- MRR@5: **0.8633**;
- nDCG@5: **0.8884**;
- candidate source+page recall@20: **0.9815**;
- known-document Recall@5: **1.0000**;
- discovery Recall@5: **0.8889**.

Frozen E5-D stack:

- E5-C BM25 + `Qwen/Qwen3-Embedding-0.6B@97b0c61` candidate generation;
- candidate depth 20;
- `Qwen/Qwen3-Reranker-0.6B@e61197e` reranker;
- final evidence depth 5;
- frozen E4 section chunks.

## Layer C — frozen hosted QA

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

## One-time E5 final benchmark

- 40 human-reviewed questions;
- 36 answerable + 4 abstention/conflict;
- hosted requests: **40/40 successful**;
- frozen retrieval Recall@5: **35/36 = 97.22%**;
- human semantic result: **38/40 = 95.0%**.

Primary failures:

- `E5F-011` — Layer C answer-selection/completeness under retrieved evidence;
- `E5F-021` — Layer B retrieval/candidate-generation failure.

The oracle diagnostic is explanatory only and never replaces the 95.0% primary result.

## Five-PDF unseen-document evaluation

Frozen cases:

| Stratum | AD | Pages |
|---|---|---:|
| corrected | 2008-0008 | 2 |
| revised | 2011-0041R1 | 4 |
| supersedure | 2011-0142 | 3 |
| long document | 2026-0084 | 10 |
| simple original | 2007-0173 | 2 |

Question lock:

- **15/15 human verified**;
- 14 answerable + 1 abstention;
- locked question SHA-256: `603d3385f5d083aeabf071d8d0c9be88896d31eb3f6530e881efeb3c03baeb2d`.

U5/U6 ingestion safeguards:

- ingestion success: **5/5**;
- deterministic record match: **5/5**;
- exact duplicate rejection without mutation: **5/5**;
- isolated E4/E5-C append/alignment: **5/5**;
- frozen source indexes unchanged: **true**;
- strict frozen-chunk-policy match: **5/5 exact**.

U7 post-ingestion retrieval:

- Recall@1: **13/14 = 92.86%**;
- Recall@3: **14/14 = 100%**;
- Recall@5: **14/14 = 100%**;
- correct source@1: **14/14 = 100%**;
- correct source+page@5: **14/14 = 100%**.

U7 human-approved primary result:

- semantic PASS: **13**;
- semantic FAIL: **1** (`U5Q-010`);
- technical failure: **1** (`U5Q-011`);
- semantic accuracy on successful hosted responses: **13/14 = 92.86%**;
- strict end-to-end success: **13/15 = 86.67%**.

Key unseen findings:

- `U5Q-010`: page-level retrieval hit the correct page but omitted the actual answer-bearing `Supersedure`/`Applicability` passages from top-5. **Correct source/page recall does not guarantee answer-bearing passage support.**
- `U5Q-011`: both approved answer-bearing passages were present in U7 top-5, but DeepSeek returned empty final JSON content on the primary request and the one exact retry. This is a **provider/structured-output reliability failure**, not retrieval.

Canonical unseen documentation:

```text
docs/UNSEEN_DOCUMENT_EVALUATION.md
docs/U8_FINAL_UNSEEN_GENERALIZATION_REPORT.md
```

Final unseen completion lock:

```text
evaluation_sets/unseen_incoming_5_v1/unseen_final_generalization_lock.json
```

Final validator:

```bash
.venv/bin/python -m \
  full_corpus_pipeline.layer_c.validate_unseen_final_generalization
```

## Next phase

The evaluation phase is complete. Remaining work is **post-evaluation engineering and capstone delivery**:

- user-facing aviation document assistant integration;
- final report/thesis and result tables;
- final system-flow/architecture diagrams;
- optional post-evaluation improvements to passage selection, lifecycle/correction normalization, and provider robustness.

Any changes after this point must be labelled post-evaluation and must not rewrite the locked benchmark results.

## Reporting boundaries

- The 1,809 PDFs are Airbus-related; not all are strict Airbus S.A.S.-holder operational records.
- Structured extraction does not fully normalize every complex compliance branch.
- Original PDF passages remain authoritative for detailed applicability/compliance interpretation.
- Correct source/page retrieval does not necessarily mean the answer-bearing passage reached Layer C.
- The system does not make aircraft-specific legal compliance determinations.
- Final oracle and transport-retry results are diagnostic/supplementary only.
- Unseen-document results are reported separately from the frozen 40-question E5 final result.
