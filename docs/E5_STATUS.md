# E5 Status

Last updated: 6 August 2026

## Current state

E0/E4 are closed/frozen historical experiments. E5 is the active improvement path and uses a fresh development/final benchmark. The 16 E5 final-test families remain sealed.

Frozen E5 development benchmark:

- 24 development families / 16 final-test families;
- 60 human-reviewed development questions;
- 54 answerable retrieval questions + 6 abstention/conflict questions reserved for QA;
- 36 known-document + 18 identifier-free discovery + 6 abstention/conflict;
- benchmark SHA-256: `d43f08611d7d2f77eb37052a03f3deabf335b004ead9528e798e12fb8dad677b`.

Frozen retrieval source remains `rag-index-build-v1.2`: **1,786 documents / 12,634 E4 section chunks**.

## E5-A — COMPLETE

Engineering-aware lexical retrieval:

- deterministic AD-aware routing;
- within-document BM25 for known-document queries;
- corpus-wide sparse discovery otherwise;
- no dense retrieval or reranker.

Development result:

- overall Recall@5: **0.8889**;
- known-document Recall@5: **1.0000**;
- discovery Recall@5: **0.6667**;
- candidate source+page recall@20: **0.9444**.

## E5-B — COMPLETE / RETAINED LEXICAL BASE

E5-B preserves the successful known-document route and improves discovery with signal-preserving BM25, wider sparse retrieval, document aggregation, within-document re-retrieval, and evidence assembly.

Development result:

| Metric | E5-A | E5-B |
|---|---:|---:|
| Recall@1 | 0.6296 | 0.6111 |
| Recall@3 | 0.8519 | **0.8889** |
| Recall@5 | 0.8889 | **0.9444** |
| MRR@5 | 0.7407 | **0.7537** |
| nDCG@5 | 0.7785 | **0.8022** |
| Correct source@5 | 0.9259 | **0.9630** |
| Candidate source+page recall@20 | 0.9444 | **0.9630** |

Discovery Recall@5 improves from **0.6667 → 0.8333** while known-document Recall@5 remains **1.0000**. Paired E5-A/E5-B top-5 gains/losses: **3 / 0**.

Remaining E5-B top-5 failures were `E5D-030`, `E5D-041`, and `E5D-045`.

## E5-C — COMPLETE / USEFUL CANDIDATE GENERATOR, NOT CURRENT TOP-5 WINNER

E5-C adds pinned `Qwen/Qwen3-Embedding-0.6B@97b0c61` dense retrieval to E5-B discovery, with BM25/Qwen document-level and passage-level reciprocal-rank fusion. Known-document behavior remains unchanged.

A pre-score MPS normalization validation issue was corrected before any E5-C score was opened. The accepted dense artifact is `e5c-dense-build-v1.1`, which explicitly re-normalizes float32 document/query vectors before cosine-via-inner-product scoring.

Development result:

| Metric | E5-B | E5-C |
|---|---:|---:|
| Recall@1 | 0.6111 | **0.6481** |
| Recall@3 | **0.8889** | 0.8519 |
| Recall@5 | **0.9444** | 0.9259 |
| MRR@5 | 0.7537 | **0.7645** |
| nDCG@5 | 0.8022 | **0.8053** |
| Correct source@5 | **0.9630** | **0.9630** |
| Candidate source+page recall@20 | 0.9630 | **0.9815** |

Discovery result:

- E5-B Recall@5: **0.8333**;
- E5-C Recall@5: **0.7778**;
- E5-B candidate source+page recall@20: **0.8889**;
- E5-C candidate source+page recall@20: **0.9444**.

Paired E5-B/E5-C result:

- E5-C better rank: **4**;
- E5-B better rank: **2**;
- ties: **48**;
- top-5 gains: **0**;
- top-5 losses: **1**.

Changed questions:

- `E5D-006`: 2 → 1 (E5-C better);
- `E5D-010`: 3 → 4 (E5-B better);
- `E5D-024`: 3 → 1 (E5-C better);
- `E5D-027`: 2 → 1 (E5-C better);
- `E5D-037`: 1 → 6 (E5-B better; one top-5 loss);
- `E5D-045`: missing@20 → 19 (E5-C recovers the correct page into the candidate pool).

Remaining E5-C top-5 misses:

1. `E5D-030` — target `2016-0222` page 2 — target source/page still absent at 20;
2. `E5D-037` — target `2025-0067` — correct source/page rank 6;
3. `E5D-041` — target `2011-0024R1` page 3 — correct source rank 1, correct page rank 15;
4. `E5D-045` — target `2022-0040` page 3 — correct source rank 2, correct page rank 19.

Interpretation: E5-C does not replace E5-B as the current top-5 development winner, but it raises candidate source+page recall@20 to **53/54 = 0.9815**. This creates a useful high-recall candidate pool for the predeclared reranker experiment. `E5D-030` is the only remaining candidate-generation miss and therefore cannot be fixed by reranking.

## E5-D — IMPLEMENTED / DEVELOPMENT EVALUATION NEXT

E5-D keeps **E5-C top-20 candidate membership fixed** and applies only a learned passage reranker:

- reranker: `Qwen/Qwen3-Reranker-0.6B`;
- pinned revision: `e61197e`;
- execution: isolated SentenceTransformers `CrossEncoder` worker;
- score: raw reranker logit difference;
- candidate depth: **20**;
- candidate generation: unchanged E5-C;
- no final-test access.

Frozen aviation reranker instruction before E5-D scoring:

> Given an aviation airworthiness-directive maintenance query, rank passages by how directly and completely they answer the query. Preserve exact applicability, compliance thresholds, timing, exceptions, identifiers, lifecycle statements, and referenced publications.

Relevant files:

- `full_corpus_pipeline/e5d_retrieval.py`;
- `full_corpus_pipeline/e5d_rerank_worker.py`;
- `full_corpus_pipeline/evaluate_e5d_development.py`;
- `full_corpus_pipeline/tests/test_e5d_retrieval.py`.

Run:

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_e5d_development \
  --questions evaluation_sets/easa_airbus_ad_e5_benchmark_v1/development_questions.jsonl \
  --index data_processed/indexes/rag_v1_2/e4_section_hybrid \
  --dense-dir data_processed/indexes/e5c_qwen3_embedding_0_6b \
  --e5b-report data_processed/evaluations/e5/e5b_development_evaluation.json \
  --e5c-report data_processed/evaluations/e5/e5c_development_evaluation.json \
  --output data_processed/evaluations/e5/e5d_development_evaluation.json
```

The evaluator reports E5-D vs E5-C and E5-D vs E5-B paired rank/top-5 comparisons.

## Selection rule after E5-D

Use only the 60-question development set to choose the retrieval configuration. The primary selection objective is correct source+page Recall@5, with MRR/nDCG and discovery performance as secondary evidence. Candidate recall@20 is diagnostic, not a substitute for top-5 evidence quality.

After E5-D:

1. select one development-best E5 retrieval configuration;
2. freeze retrieval configuration completely;
3. freeze hosted-QA provider/model/prompt/evidence-pack settings;
4. only then author/review/open the 40-question final benchmark;
5. run the final retrieval/QA evaluation once without tuning.
