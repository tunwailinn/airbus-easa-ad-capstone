# Agent Guide: Airbus EASA AD Capstone v3.3

Read this before changing code, data rules, experiments, or documentation.

## Project boundary

- Frozen snapshot: **1,809 physical EASA AD PDFs / 1,808 base AD families**.
- Five PDFs remain frozen as unseen ingestion cases.
- Nominal development extraction: **1,804 physical PDFs**.
- Strict operational scope: EU-issued EASA ADs whose Design/Type Approval Holder is Airbus S.A.S., accepting legacy Airbus/Airbus Industrie naming.
- Scope filtering never deletes physical/source records.
- Authoritative methodology: `airbus_easa_ad_project_exact_plan.md`.

## Architecture

```text
Layer A: deterministic section-complete content records
→ metadata lookup, filtering, browsing, raw difficult AD sections

Layer B: original-PDF page text + frozen E5-D RAG
→ applicability/compliance retrieval, interpretation, page-cited QA

Layer C: hosted evidence-grounded QA
→ final answer generation only after retrieval is frozen
```

Detailed compliance interpretation must use original PDF passages retrieved by RAG. Do not claim the structured content JSON fully normalizes compliance logic.

## Non-negotiable rules

1. Source PDFs and immutable gold are read-only.
2. Keep one generated content record per nominal physical PDF; operational scope is a separate filter.
3. Never merge passages or requirements from different PDF versions.
4. Keep lifecycle/latest-selection state outside content JSON.
5. Preserve Applicability, Definitions, Reason, Requirements/Compliance, Ref. Publications wording, and Remarks when printed.
6. Do not normalize difficult compliance conditions, intervals, exceptions, or terminating logic across the full corpus.
7. RAG answers must cite AD number, source PDF, page, and section when available.
8. Abstain when retrieved support is incomplete or conflicting.
9. Temporary upload and permanent ingestion do not retrain models.
10. Confirmed external/mixed-holder records remain physically preserved but are excluded from the strict Airbus-only operational view.
11. Missing/malformed/unclassified holders are `unknown`, never automatic exclusions.
12. **Parser v2.1.6 is frozen. Do not modify it from locked extraction-test outcomes.**
13. The disclosed `2024-0038` test leak remains excluded from clean extraction scoring.
14. The five unseen PDFs remain outside development retrieval indexes until unseen-document evaluation.
15. Retrieval experiments must consume verified **page-text v1.1** only; unresolved weak pages or page-text hash failures block indexing.
16. E0 and E4 use the same 1,786-document retrieval manifest and the same dense embedding model.
17. E0 ranking is dense-only over flat chunks. E4 is section-aware BM25 + dense + FAISS + RRF + local cross-encoder reranking.
18. Do not silently use hashing, numpy-only dense indexing, or lexical reranking fallback for the frozen thesis E0/E4 measurements.
19. **`rag-index-build-v1.2` and `retrieval-eval-v1.3` are final/frozen. Do not retune retrieval from locked QA-v2 results.**
20. Chunk-size construction/reporting uses `whitespace_split`: E0 <=350, E4 target 250–450 and hard max 450. These are deterministic chunk units, not transformer subword tokens.
21. Final E0/E4 retrieval artifacts live under `data_processed/indexes/rag_v1_2/`; `rag_v1/` and `rag_v1_1/` are audit history only.
22. On macOS ARM, **never import/use PyTorch/SentenceTransformers and FAISS in the same Python process** for the frozen evaluator. Process isolation is mandatory where those runtimes could coexist.
23. Hosted LLMs are allowed only at QA time. They must receive retrieved original-PDF evidence, preserve page/source citations, and abstain when evidence is insufficient.
24. Distinguish retrieval failures from LLM reasoning/generation failures. Do not credit or blame the LLM when the authoritative passage was absent from its supplied context.
25. E5 is a separate post-E0/E4 experiment using a fresh benchmark. The **60-question E5 development set** was used for E5-A/B/C/D selection; the **40-question E5 final set remains sealed** until hosted-QA settings are frozen.
26. Do not reopen or retune E0/E4 from E5 outcomes.
27. E5 known-document routing is deterministic. A supplied AD identifier is a routing key, not a learned ranking feature.
28. E5 discovery questions must remain identifier-free and use corpus-wide retrieval before candidate-AD passage retrieval.
29. E5-A/B/C/D development results are exposed and closed. Do not rewrite those ablations.
30. **E5-D is the selected/frozen primary retrieval configuration. Do not tune retrieval further from development misses.**
31. Frozen E5-D candidate generation is the accepted E5-C BM25 + `Qwen/Qwen3-Embedding-0.6B@97b0c61` fusion over the frozen E4 chunks.
32. Frozen E5-D reranking uses `Qwen/Qwen3-Reranker-0.6B@e61197e`, candidate limit 20, final evidence depth 5, and the exact instruction recorded in `retrieval_freeze.json`.
33. The machine-readable retrieval lock is `evaluation_sets/easa_airbus_ad_e5_benchmark_v1/retrieval_freeze.json`. Treat it as authoritative for the primary E5 final evaluation.
34. Do not alter embedding/reranker revisions, prompts/instructions, routing, RRF depths/settings, candidate limits, evidence assembly, chunking, or the frozen E4 index before the one-time final evaluation.
35. E5D-030 and E5D-045 are known development misses. Do not hand-tune the frozen retriever against them. Any later retrieval experiment is post-hoc only and cannot replace the frozen primary result.
36. Hosted-QA provider/model/prompt/reasoning settings/evidence-pack/citation/abstention rules must be frozen separately before opening the 40-question final benchmark.
37. After the hosted-QA freeze, the final retrieval/QA benchmark is opened and run once. Later analyses must be labeled post-hoc.

## Frozen/active versions

- Content schema: **2.1.0**.
- Frozen parser: **`content-local-v2.1.6`**.
- Extraction evaluator: **`content-eval-v3.1.5`**.
- Corpus scope audit: **`corpus-scope-audit-v1.3`**.
- Verified page source: **`page-text-v1.1`**.
- Page visual override file: `full_corpus_pipeline/page_text_visual_overrides.json`.
- Frozen E0/E4 retrieval build: **`rag-index-build-v1.2`**.
- Frozen E0/E4 retrieval evaluator: **`retrieval-eval-v1.3`**.
- Retrieval plumbing diagnostic: **`retrieval-plumbing-diagnostic-v1.0`**.
- E5-A evaluator: **`e5-a-eval-v1.0`**.
- E5-B evaluator: **`e5-b-eval-v1.0`**.
- Accepted E5-C dense build: **`e5c-dense-build-v1.1`**.
- E5-C evaluator: **`e5-c-eval-v1.0`**.
- E5-D evaluator: **`e5-d-eval-v1.0`**.
- Frozen E5 retrieval lock: **`e5-retrieval-freeze-v1.0`**.
- E5 methodology/status: `docs/E5_ENGINEERING_AWARE_RETRIEVAL.md`, `docs/E5_STATUS.md`.
- Immutable extraction audit source: `gold_releases/easa_airbus_ad_gold_v2/`.

## Frozen extraction results

Development primary count: **28** after holder-scope exclusions.

- 1,804/1,804 generated; zero failures.
- coverage/schema validity: 1.0000/1.0000.
- stable-metadata macro F1: **0.9948**.
- applicability-model F1: **0.9929**.
- reference-number F1: **0.8065**.
- superseded-AD-number F1: **1.0000**.
- all five difficult raw-section presence F1 values: **1.0000**.
- source containment: **130/130**; contamination: **0**.

Clean locked extraction test primary count: **17**.

- coverage/schema validity: 1.0000/1.0000.
- stable-metadata macro F1: **0.9831**.
- applicability-model F1: **0.9222**.
- reference-number F1: **0.9000**.
- superseded-AD-number F1: **0.6667**.
- all five raw-section presence F1 values: **1.0000**.
- source containment: **74/74**; contamination: **0**.

These are final extraction results, not tuning input.

## Final development scope

- Physical development records: **1,804**.
- Strict Airbus-only operational records: **1,786**.
- Retained external/mixed-holder records: **18**.
- Unknown: **0**.

The `2012-0088` source-review override affects scope classification only.

## Verified page-text source layer

The local original-PDF page extraction completed over the exact 1,786-record strict Airbus development view:

- selected documents: **1,786**;
- successful documents: **1,786**;
- failures: **0**;
- total PDF pages: **6,002**;
- native weak pages detected: **1 page in 1 document**;
- reviewed visual override: **AD 2011-0006, page 3**;
- unresolved weak/OCR pages after review: **0**;
- `ready_for_indexing`: **true**;
- verified source version: **`page-text-v1.1`**.

Canonical local path:

```text
data_processed/page_text_v1_1/operational_airbus/
```

## Frozen E0/E4 retrieval experiment

Accepted v1.2 E0:

- 9,394 chunks;
- 1,786 documents;
- max chunk size 350;
- `sentence_transformers` dense backend;
- `faiss_index_flat_ip` dense index;
- dense-only ranking.

Accepted v1.2 E4:

- 12,634 chunks;
- 1,786 documents;
- max chunk size 450;
- 2,924 multi-page chunks; max page span 5;
- SQLite FTS5/BM25 + same dense model + FAISS + RRF;
- reranker `cross-encoder/ms-marco-MiniLM-L-6-v2`;
- candidate depth 20 per sparse/dense path.

Frozen index root:

```text
data_processed/indexes/rag_v1_2/
```

## Final E0/E4 retrieval results

`retrieval-eval-v1.3` over the 44 answerable retrieval questions:

E0 flat dense-only:

- Recall@1/3/5: **0.0000 / 0.0000 / 0.0000**;
- MRR/nDCG@5: **0.0000 / 0.0000**;
- correct-source@1/@5: **0.0000 / 0.0000**.

E4 section-aware hybrid:

- Recall@1/3/5: **0.2500 / 0.3636 / 0.4091**;
- MRR: **0.3106**;
- nDCG@5: **0.3353**;
- correct-source@1/@5: **0.2727 / 0.5000**;
- correct-source+page@1/@5: **0.2500 / 0.4091**;
- paired: **E4 better 18 / E0 better 0 / ties 26**.

`retrieval-plumbing-diagnostic-v1.0` validated the result:

- E0 and E4 FAISS/chunk alignment passed 20/20 sampled self matches;
- fresh-vs-stored embedding cosine is approximately 1.0 for both indexes;
- all 8 target ADs are present in both indexes;
- E0 dense correct-source@20: **0/44**;
- E4 dense correct-source@20: **0/44**;
- E4 BM25 correct-source/page@20: **40/44 (90.9%)**.

Interpretation: the observed E4 gain is primarily from **lexical/section-aware hybrid retrieval**, especially BM25 exact-term retrieval. Do not claim the MiniLM dense branch drove the gain.

## Frozen E5 development results

The E5 development benchmark contains **60 human-reviewed questions**, of which **54 are answerable retrieval questions** and 6 are reserved for abstention/QA evaluation.

| Stage | Overall Recall@5 | Discovery Recall@5 | Notes |
|---|---:|---:|---|
| E5-A | 0.8889 | 0.6667 | deterministic routing + lexical retrieval |
| E5-B | 0.9444 | 0.8333 | retained lexical/evidence-assembly base |
| E5-C | 0.9259 | 0.7778 | higher candidate recall@20 = 0.9815 |
| **E5-D** | **0.9630** | **0.8889** | **selected/frozen** |

Frozen E5-D additional metrics:

- Recall@1: **0.7963**;
- Recall@3: **0.9259**;
- MRR@5: **0.8633**;
- nDCG@5: **0.8884**;
- correct source@5: **0.9815**;
- correct source+page@5: **0.9630**;
- candidate source+page recall@20: **0.9815**;
- known-document Recall@5: **1.0000**;
- routing accuracy: **1.0000**.

E5-D paired versus E5-B: **18 better / 7 worse / 29 ties; top-5 gains 1 / losses 0**.

E5-D paired versus E5-C: **16 better / 6 worse / 32 ties; top-5 gains 2 / losses 0**.

Remaining top-5 misses: `E5D-030` (missing from candidate pool) and `E5D-045` (rank 6). They are analysis findings, not tuning targets.

## Immediate priority

1. Keep `e5-retrieval-freeze-v1.0` unchanged.
2. Freeze hosted-QA provider/model/prompt/reasoning/evidence-pack/citation/abstention settings on development data only.
3. Record a machine-readable hosted-QA freeze.
4. Only then open/author/review the 40-question final benchmark from the 16 sealed final families.
5. Run frozen E5-D retrieval + frozen hosted QA on the final benchmark once.
6. Run the same hosted QA model against oracle reference evidence to separate retrieval and generation errors.
7. After final evaluation, evaluate temporary uploaded-PDF QA and permanently ingest the five frozen unseen PDFs without retraining.

## Working protocol

Authority order:

1. current user request;
2. this file;
3. `evaluation_sets/easa_airbus_ad_e5_benchmark_v1/retrieval_freeze.json` for frozen E5 retrieval;
4. `docs/E5_STATUS.md` while E5 is active;
5. `docs/RETRIEVAL_BUILD_STATUS.md` for frozen E0/E4;
6. `airbus_easa_ad_project_exact_plan.md`;
7. `docs/PROJECT_STATUS.md`;
8. `docs/DECISIONS.md`;
9. `docs/BENCHMARK_DESIGN.md`;
10. `docs/PAGE_TEXT_PIPELINE.md`.

After material work, preserve unrelated artifacts, run relevant tests, update project status, and record stable methodology changes. Never reopen frozen extraction, E0/E4 retrieval, or frozen E5-D retrieval tuning from locked outcomes.
