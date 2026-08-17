# Agent Guide: Airbus EASA AD Capstone

Read this before changing code, data rules, experiments, or documentation.

Last updated: 17 August 2026

## Project boundary

- Frozen snapshot: **1,809 physical EASA AD PDFs / 1,808 base AD families**.
- Five PDFs remain isolated as unseen ingestion/generalization cases.
- Nominal development extraction: **1,804 physical PDFs**.
- Strict Airbus-only operational retrieval scope: **1,786 PDFs / 6,002 verified pages**.
- Scope filtering never deletes physical/source records.
- Authoritative project methodology: `airbus_easa_ad_project_exact_plan.md`.

## Architecture

```text
Layer A: deterministic section-complete content records
→ metadata lookup, filtering, browsing, raw difficult AD sections

Layer B: verified original-PDF page text + frozen E5-D retrieval
→ applicability/compliance evidence, lifecycle-aware routing, page/source support

Layer C: frozen hosted evidence-grounded QA
→ answer | insufficient_evidence | conflicting_evidence
```

Detailed compliance interpretation must use original PDF passages. Do not claim structured content JSON fully normalizes complex compliance logic.

## Current benchmark state

Completed/frozen:

- parser v2.1.6 extraction development + clean locked test;
- page-text v1.1 source layer;
- historical E0/E4 retrieval evaluation;
- E5-A/B/C/D retrieval development;
- E5-D retrieval freeze;
- Layer C development + development oracle comparison;
- hosted-QA freeze;
- 40-question human-reviewed final benchmark lock;
- one-time primary final benchmark;
- human semantic final review;
- final oracle/reference-evidence diagnostic;
- exact audited transport retry for oracle `E5F-035`.

Authoritative primary final semantic result:

```text
38/40 = 95.0%
```

Active remaining phase: **five frozen unseen PDFs**.

Current unseen checkpoint:

- U0 source/selection validation: **complete**;
- U1 non-destructive preparation: **complete**;
- source hashes matched: **5/5**;
- source pages: **21**;
- frozen-parser extraction: **5/5 successful**;
- schema validity: **5/5**;
- U2 draft questions: **15 authored, exactly 3 per PDF**;
- human verification: **0/15**;
- needs human review: **15/15**;
- U3 temporary hosted QA: **not started**;
- permanent ingestion: **not started**.

Draft unseen question SHA-256:

```text
1d9600dd4379f501d0878adf6ae434076ef47ae0a299ef8be5bdc12cb55fc43b
```

Do not infer that the unseen questions are approved merely because they were source-grounded or assistant-authored. Explicit human review and lock are still required.

## Non-negotiable rules

1. Source PDFs and immutable gold are read-only.
2. Keep one generated content record per nominal physical PDF; operational scope is a separate filter.
3. Never merge passages or requirements from different PDF versions.
4. Keep lifecycle/latest-selection state outside content JSON.
5. Preserve Applicability, Definitions, Reason, Requirements/Compliance, Ref. Publications wording, and Remarks when printed.
6. Do not normalize difficult compliance conditions, intervals, exceptions, or terminating logic across the full corpus.
7. RAG/QA outputs must preserve source/page/section provenance through stable evidence metadata.
8. Abstain when supplied evidence is incomplete or conflicting.
9. Temporary upload and permanent ingestion do not retrain models.
10. Confirmed external/mixed-holder records remain physically preserved but are excluded from the strict Airbus-only operational view.
11. Missing/malformed/unclassified holders are `unknown`, never automatic exclusions.
12. **Parser v2.1.6 is frozen. Do not modify it from locked extraction-test outcomes.**
13. The disclosed `2024-0038` extraction-test leak remains excluded from clean extraction scoring.
14. The five unseen PDFs remain outside frozen development/final indexes and benchmark construction.
15. Retrieval experiments consume verified **page-text v1.1** only; unresolved weak pages or page-text hash failures block indexing.
16. E0/E4 are frozen historical experiments. Do not retune them from QA-v2 or E5 outcomes.
17. On macOS ARM, keep PyTorch/SentenceTransformers and FAISS process isolation where the frozen evaluator requires it.
18. Hosted LLMs are allowed only at QA time.
19. Distinguish retrieval failures from generation/reasoning failures. Do not blame or credit Layer C when the authoritative evidence was absent from supplied context.
20. E5 is a separate benchmark from QA-v2. Development and final families are disjoint, and unseen families remain separate.
21. E5 known-document routing is deterministic. A supplied AD identifier is a routing key, not a learned ranking feature.
22. E5 discovery questions remain identifier-free and test corpus-wide discovery.
23. E5-A/B/C/D development results are exposed, closed, and immutable historical ablations.
24. **E5-D is the selected/frozen retrieval configuration. Do not tune it from development, final, or unseen failures.**
25. Frozen E5-D candidate generation uses E5-C BM25 + `Qwen/Qwen3-Embedding-0.6B@97b0c61` over frozen E4 chunks.
26. Frozen E5-D reranking uses `Qwen/Qwen3-Reranker-0.6B@e61197e`, candidate limit 20, final evidence depth 5, and the instruction stored in `retrieval_freeze.json`.
27. The retrieval lock `evaluation_sets/easa_airbus_ad_e5_benchmark_v1/retrieval_freeze.json` is authoritative.
28. Development misses `E5D-030` and `E5D-045` are analysis findings, not tuning targets.
29. Hosted-QA settings are frozen in `evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json`.
30. Final questions are human reviewed and locked. Do not change them after the one-time final run.
31. The strict primary final result is **38/40 = 95.0%**. Never replace it with ambiguity-adjusted, oracle, transport-recovered, unseen, or other post-hoc values.
32. Primary final failures are `E5F-011` and `E5F-021`; preserve their attribution history.
33. `E5F-021` is confirmed Layer B retrieval/candidate-generation failure because oracle evidence makes the same frozen model answer correctly.
34. `E5F-011` remains a Layer C primary failure, more precisely evidence-selection/completeness sensitivity because focused oracle evidence makes the same model answer correctly.
35. `E5F-040` is a status-calibration/run-to-run variability diagnostic under unchanged negative-control evidence; do not label it a factual hallucination.
36. The original final oracle batch remains **39 successes / 1 technical failure**. The exact retry of `E5F-035` is a separate audit recovery artifact and must not rewrite the first-pass batch.
37. Semantic retries are prohibited. Exact transport retry is allowed only for genuine technical/provider failure with identical question/evidence/prompt/config and separate audit records.
38. Oracle/reference-evidence results are diagnostic only and cannot replace the primary final score.
39. Do not use the five unseen PDFs to tune extraction, retrieval, Layer C, or benchmark/system configuration.
40. Unseen evaluation must be reported separately as generalization/ingestion performance.
41. Unseen source preparation is non-destructive; preparation outputs do not imply benchmark approval.
42. **Do not run unseen hosted inference until all 15 unseen question/reference records have explicit human review and are locked.**
43. Human review may correct question/reference records for source fidelity, but may not change parser, retrieval, Layer C, or frozen generation settings.
44. **Do not permanently ingest any held-out unseen PDF before its temporary-document QA result is preserved.**
45. Permanent unseen ingestion must use an isolated evaluation store/index first; frozen E5 benchmark indexes remain immutable.
46. Repeat-ingestion/duplicate rejection, lifecycle handling, index append behavior, and post-ingestion citations are part of the unseen evaluation and must be recorded rather than silently repaired.

## Frozen/active versions

- Content schema: **2.1.0**.
- Frozen parser: **`content-local-v2.1.6`**.
- Extraction evaluator: **`content-eval-v3.1.5`**.
- Corpus scope audit: **`corpus-scope-audit-v1.3`**.
- Verified page source: **`page-text-v1.1`**.
- Frozen E0/E4 retrieval build: **`rag-index-build-v1.2`**.
- Frozen E0/E4 retrieval evaluator: **`retrieval-eval-v1.3`**.
- E5-A evaluator: **`e5-a-eval-v1.0`**.
- E5-B evaluator: **`e5-b-eval-v1.0`**.
- Accepted E5-C dense build: **`e5c-dense-build-v1.1`**.
- E5-C evaluator: **`e5-c-eval-v1.0`**.
- E5-D evaluator: **`e5-d-eval-v1.0`**.
- Frozen E5 retrieval lock: **`e5-retrieval-freeze-v1.0`**.
- Hosted-QA adapter: **`deepseek-direct-v1.1`**.
- Hosted-QA runner: **`e5-hosted-qa-runner-v1.1`**.
- Hosted-QA prompt: **`e5-hosted-qa-prompt-v1.0-dev`**.
- Hosted-QA response contract: **`e5-hosted-qa-contract-v1.0`**.
- Hosted-QA freeze: **`e5-hosted-qa-freeze-v1.0`**.
- Final oracle runner: **`e5-layer-c-final-oracle-runner-v1.0`**.
- Final oracle evaluator: **`e5-layer-c-final-oracle-eval-v1.0`**.
- Final oracle exact transport retry runner: **`e5-layer-c-final-oracle-transport-retry-v1.0`**.
- Unseen preparation: **`unseen-5-preparation-v1.0`**.

## Key frozen results

### Extraction

Development primary count 28:

- stable metadata macro F1: **0.9948**;
- applicability-model F1: **0.9929**;
- reference-number F1: **0.8065**;
- superseded-AD-number F1: **1.0000**;
- source containment: **130/130**.

Clean locked extraction primary count 17:

- stable metadata macro F1: **0.9831**;
- applicability-model F1: **0.9222**;
- reference-number F1: **0.9000**;
- superseded-AD-number F1: **0.6667**;
- source containment: **74/74**.

### Page source

- 1,786 successful documents;
- 6,002 pages;
- one reviewed visual override: AD 2011-0006 page 3;
- zero unresolved weak/OCR pages.

### E5-D development retrieval

- Recall@1: **0.7963**;
- Recall@3: **0.9259**;
- Recall@5: **0.9630**;
- MRR@5: **0.8633**;
- nDCG@5: **0.8884**;
- known-document Recall@5: **1.0000**;
- discovery Recall@5: **0.8889**.

### Primary final benchmark

- 40/40 hosted requests successful;
- retrieval Recall@5: **35/36 = 97.22%**;
- known-document Recall@5: **24/24 = 100%**;
- discovery Recall@5: **11/12 = 91.67%**;
- human semantic accuracy: **38/40 = 95.0%**.

### Final oracle diagnostic

- original batch: **39/40 requests successful**;
- reference-page citation hit: **100%**;
- target-AD citation hit: **100%**;
- `E5F-035` exact retry: **recovered**.

### Unseen preparation checkpoint

- documents: **5/5 prepared**;
- source hash matches: **5/5**;
- pages: **21**;
- deterministic extraction: **5/5 successful**;
- schema validity: **5/5**;
- question draft: **15 questions**;
- human verified: **0/15**;
- inference/permanent ingestion: **not started**.

## Immediate priority

1. Keep all extraction/E5/Layer-C freezes unchanged.
2. Preserve the primary final and oracle/transport-retry audit artifacts.
3. Complete human review of the 15 unseen question/reference records.
4. Incorporate only source-fidelity benchmark edits and create a locked unseen question artifact.
5. Run temporary unseen-document QA with the frozen Layer C configuration.
6. Preserve and human-review the temporary-QA result.
7. Only then run isolated permanent-ingestion/duplicate/lifecycle/index-update/post-ingestion QA evaluation.
8. Report unseen results separately from the 40-question final benchmark.
9. After material work, update `docs/PROJECT_STATUS.md`, `docs/UNSEEN_DOCUMENT_EVALUATION.md`, and relevant experiment-specific documentation.

## Working protocol

Authority order:

1. current user request;
2. this file;
3. machine-readable retrieval/hosted-QA/final benchmark locks;
4. `docs/UNSEEN_DOCUMENT_EVALUATION.md` while unseen evaluation is active;
5. `docs/E5_STATUS.md`;
6. `docs/LAYER_C_FINAL_EVALUATION.md`;
7. `docs/PROJECT_STATUS.md`;
8. `airbus_easa_ad_project_exact_plan.md`;
9. `docs/DECISIONS.md`;
10. `docs/BENCHMARK_DESIGN.md`.

Preserve unrelated artifacts, run relevant tests, keep first-pass failures in the audit trail, and never reopen frozen development or primary-final tuning from locked outcomes.