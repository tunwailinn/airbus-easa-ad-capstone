# Agent Guide: Airbus EASA AD Capstone

Read this before changing code, data rules, experiments, or documentation.

Last updated: 17 August 2026

## Project boundary

- Frozen snapshot: **1,809 physical EASA AD PDFs / 1,808 base AD families**.
- Nominal development extraction: **1,804 PDFs**.
- Strict Airbus-only operational retrieval scope: **1,786 PDFs / 6,002 verified pages**.
- Five PDFs are reserved for the post-final unseen-document generalization/ingestion experiment.
- Scope filtering never deletes physical/source records.
- Detailed compliance interpretation uses original PDF passages, not normalized structured fields alone.

## Architecture

```text
Layer A — deterministic section-complete extraction
Layer B — verified original-PDF evidence + frozen E5-D retrieval
Layer C — frozen hosted evidence-grounded QA
```

## Current benchmark state

Completed/frozen:

- parser v2.1.6 development + clean locked extraction test;
- page-text v1.1 source layer;
- E0/E4 historical retrieval;
- E5-A/B/C/D retrieval development;
- E5-D retrieval freeze;
- Layer C development + hosted-QA freeze;
- 40-question human-reviewed final benchmark;
- one-time primary final run + human semantic review;
- final oracle/reference-evidence diagnostic;
- exact transport retry for oracle `E5F-035`;
- five-PDF unseen source preparation;
- **15-question unseen QA human review + lock**.

Authoritative primary final result:

```text
38/40 = 95.0% semantic accuracy
35/36 = 97.22% retrieval Recall@5
```

Current next action: **U3 temporary-document QA on the five held-out PDFs**.

Permanent ingestion of those five PDFs is **blocked until U3/U4 temporary results are preserved and human reviewed**.

## Non-negotiable rules

1. Source PDFs and immutable gold are read-only.
2. Keep one generated content record per physical PDF; operational scope is a separate filter.
3. Never merge passages or requirements from different PDF versions.
4. Keep lifecycle/latest-selection state outside content JSON.
5. Preserve Applicability, Definitions, Reason, Requirements/Compliance, Ref. Publications and Remarks wording when printed.
6. Do not normalize difficult compliance conditions, intervals, exceptions or terminating logic across the full corpus.
7. Original PDF passages remain authoritative for detailed compliance interpretation.
8. QA outputs must preserve source/page/section provenance through stable evidence metadata.
9. Abstain when supplied evidence is incomplete or conflicting.
10. Temporary upload and permanent ingestion never retrain models.
11. Confirmed external/mixed-holder records remain preserved but are excluded from the strict Airbus-only operational view.
12. Missing/malformed/unclassified holders are `unknown`, never automatic exclusions.
13. **Parser v2.1.6 is frozen. Do not modify it from locked-test or unseen outcomes.**
14. The disclosed `2024-0038` extraction-test leak remains excluded from clean extraction scoring.
15. E0/E4 are frozen historical experiments and must not be retuned.
16. E5-D is the selected/frozen retrieval configuration and must not be retuned from development/final/unseen misses.
17. Frozen E5-D candidate generation uses E5-C BM25 + `Qwen/Qwen3-Embedding-0.6B@97b0c61` over frozen E4 chunks.
18. Frozen E5-D reranking uses `Qwen/Qwen3-Reranker-0.6B@e61197e`, candidate limit 20 and final evidence depth 5.
19. Known-document AD identifiers are routing keys, not learned ranking features.
20. Discovery questions remain identifier-free and test corpus-wide discovery.
21. Hosted LLM use is allowed only at QA time.
22. Hosted-QA settings are frozen in `evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json`.
23. Semantic retries are prohibited.
24. Exact transport retry is allowed only for a genuine provider/transport failure with identical question/evidence/prompt/config and separate audit records.
25. Distinguish retrieval failures from Layer C answer-generation/status failures.
26. Final E5 questions are immutable after the one-time final run.
27. The strict primary final result is **38/40 = 95.0%** and cannot be replaced by ambiguity-adjusted/oracle/retry values.
28. `E5F-021` is a confirmed Layer B retrieval failure.
29. `E5F-011` remains a Layer C primary failure, more precisely evidence-selection/completeness sensitivity under retrieved evidence.
30. `E5F-040` is a status-calibration/run-to-run variability diagnostic, not a factual hallucination.
31. Original final oracle batch remains **39 successes / 1 technical failure**; the `E5F-035` retry is a separate recovery artifact.
32. Oracle results are diagnostic only.
33. The five unseen PDFs must not be used to tune extraction, E5 retrieval, Layer C or question design after the human lock.
34. Unseen results are reported separately from the 40-question final benchmark.
35. U0/U1 unseen preparation is complete and immutable as the first-pass preparation result.
36. Unseen question set is human verified and locked at SHA-256 `603d3385f5d083aeabf071d8d0c9be88896d31eb3f6530e881efeb3c03baeb2d`.
37. U3 temporary QA may run only after `validate_unseen_question_lock` passes.
38. Temporary unseen QA must use only the selected held-out PDF's prepared chunks; do not add the PDF to a persistent corpus/index first.
39. For U3, all prepared chunks from the selected PDF (maximum 14) are candidates for the pinned E5-D reranker; only top-5 evidence is exposed to frozen Layer C.
40. **Do not run permanent ingestion before U3/U4 outputs are preserved and human reviewed.**
41. Permanent-ingestion testing must use an isolated evaluation store/index before any operational promotion.
42. Frozen E5 benchmark indexes and hashes remain immutable audit artifacts after unseen ingestion.

## Frozen versions

- Content schema: `2.1.0`
- Parser: `content-local-v2.1.6`
- Extraction evaluator: `content-eval-v3.1.5`
- Scope audit: `corpus-scope-audit-v1.3`
- Page source: `page-text-v1.1`
- E0/E4 retrieval build: `rag-index-build-v1.2`
- E5 retrieval lock: `e5-retrieval-freeze-v1.0`
- E5-C embedding: `Qwen/Qwen3-Embedding-0.6B@97b0c61`
- E5-D reranker: `Qwen/Qwen3-Reranker-0.6B@e61197e`
- Hosted-QA adapter: `deepseek-direct-v1.1`
- Hosted-QA runner: `e5-hosted-qa-runner-v1.1`
- Hosted-QA prompt: `e5-hosted-qa-prompt-v1.0-dev`
- Hosted-QA response contract: `e5-hosted-qa-contract-v1.0`
- Hosted-QA freeze: `e5-hosted-qa-freeze-v1.0`
- Unseen preparation: `unseen-5-preparation-v1.0`
- Unseen question lock: `unseen-5-question-lock-v1.0`
- Unseen temporary runner: `unseen-5-temporary-qa-runner-v1.0`
- Unseen temporary evaluator: `unseen-5-temporary-qa-eval-v1.0`

## Key frozen results

Extraction development primary (28): stable metadata F1 **0.9948**, applicability F1 **0.9929**, source containment **130/130**.

Clean extraction primary (17): stable metadata F1 **0.9831**, applicability F1 **0.9222**, source containment **74/74**.

E5-D development: Recall@5 **0.9630**, MRR@5 **0.8633**, nDCG@5 **0.8884**, known-document Recall@5 **1.0000**, discovery Recall@5 **0.8889**.

E5 primary final: 40/40 hosted success, retrieval Recall@5 **35/36 = 97.22%**, semantic accuracy **38/40 = 95.0%**.

Unseen preparation: 5/5 exact source hashes, 21 pages, 5/5 extraction success, 5/5 schema-valid.

Unseen QA lock: 15/15 human verified, 14 answerable + 1 abstention, exactly 3 questions per PDF.

## Unseen workflow

```text
U0 source/selection validation                 COMPLETE
U1 non-destructive preparation                 COMPLETE
U2 human-reviewed question lock                COMPLETE
U3 temporary retrieval + frozen Layer C        NEXT
U4 offline + human review                      NOT STARTED
U5 isolated permanent ingestion                BLOCKED UNTIL U4
U6 duplicate/lifecycle/index safeguards         NOT STARTED
U7 post-ingestion QA/citations                  NOT STARTED
U8 final unseen-generalization report           NOT STARTED
```

Canonical unseen documentation:

```text
docs/UNSEEN_DOCUMENT_EVALUATION.md
```

## Working protocol

Authority order:

1. current user request;
2. this file;
3. machine-readable retrieval/hosted-QA/final/unseen locks;
4. `docs/UNSEEN_DOCUMENT_EVALUATION.md` while the unseen phase is active;
5. `docs/E5_STATUS.md`;
6. `docs/LAYER_C_FINAL_EVALUATION.md`;
7. `docs/PROJECT_STATUS.md`;
8. `airbus_easa_ad_project_exact_plan.md`;
9. `docs/DECISIONS.md`;
10. `docs/BENCHMARK_DESIGN.md`.

Preserve unrelated artifacts, preserve first-pass failures, update documentation after material work, and never reopen frozen tuning from locked outcomes.
