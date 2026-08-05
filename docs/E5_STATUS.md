# E5 Status

Last updated: 6 August 2026

## Current state

E0/E4 are closed/frozen historical experiments. E5 is the active improvement path and uses a fresh development/final benchmark.

Implemented in repository:

- `docs/E5_ENGINEERING_AWARE_RETRIEVAL.md` — E5 methodology;
- `full_corpus_pipeline/prepare_e5_benchmark_families.py` — deterministic 24-development/16-final family selector;
- `full_corpus_pipeline/prepare_e5_authoring_packets.py` — source-grounded development authoring packets;
- `full_corpus_pipeline/validate_e5_questions.py` — final count/family/leakage/human-review validator;
- `full_corpus_pipeline/e5_query_router.py` — deterministic AD/SB/intent router;
- `full_corpus_pipeline/e5_retrieval.py` — E5-A exact-document/discovery lexical retriever;
- `full_corpus_pipeline/evaluate_e5a_development.py` — strict E5-A development evaluator;
- `full_corpus_pipeline/e5b_retrieval.py` — E5-B two-stage sparse discovery and evidence assembler;
- `full_corpus_pipeline/evaluate_e5b_development.py` — E5-B evaluator with paired E5-A comparison;
- `full_corpus_pipeline/build_e5c_dense_embeddings.py` — separate Qwen3-Embedding-0.6B document-vector builder over frozen E4 chunks;
- `full_corpus_pipeline/e5c_encode_queries_worker.py` — isolated Qwen3 query encoder;
- `full_corpus_pipeline/e5c_retrieval.py` — E5-C BM25/Qwen document + passage RRF fusion for discovery;
- `full_corpus_pipeline/evaluate_e5c_development.py` — E5-C evaluator with paired E5-B comparison;
- `full_corpus_pipeline/hosted_qa.py` — provider-configurable evidence-grounded hosted QA with deterministic citation resolution.

## Frozen E5 family split — COMPLETE

- seed: **20260805**;
- development families: **24**;
- final-test families: **16**;
- total: **40**;
- each publication era contributes **6 development + 4 final-test families**;
- duplicate base families: **0**;
- overlap with the eight QA-v2 target families: **0**;
- `family_split.csv` SHA-256: **`86cdf72e020b1a6ae1d9a8eb1edd13f1a3f793e14d57dfb483a55783cfbbb1b3`**.

The 16 final-test families remain sealed from E5 development.

## Development questions — HUMAN REVIEWED

The **60-question E5 development benchmark** is human reviewed and marked `review_status=human_verified`.

Distribution:

- identity/lifecycle: **8**;
- applicability: **10**;
- required action/compliance: **20**;
- referenced publication: **8**;
- conditional/multi-passage: **8**;
- insufficient/conflict/abstention: **6**;
- known-document: **36**;
- identifier-free discovery: **18**;
- abstention/conflict: **6**.

Verified promoted JSONL SHA-256:

```text
d43f08611d7d2f77eb37052a03f3deabf335b004ead9528e798e12fb8dad677b
```

## E5-A — DEVELOPMENT EVALUATION COMPLETE

Artifact:

```text
data_processed/evaluations/e5/e5a_development_evaluation.json
```

Evaluation version: `e5-a-eval-v1.0`

Overall E5-A retrieval over 54 answerable questions:

| Metric | E5-A |
|---|---:|
| Recall@1 | 0.6296 |
| Recall@3 | 0.8519 |
| Recall@5 | **0.8889** |
| MRR@5 | 0.7407 |
| nDCG@5 | 0.7785 |
| Correct source@5 | **0.9259** |
| Correct source+page@5 | **0.8889** |
| Candidate source recall@20 | **0.9630** |
| Candidate source+page recall@20 | **0.9444** |

Query-mode split:

- known-document Recall@5: **1.0000**;
- discovery Recall@5: **0.6667**;
- route accuracy: **54/54 = 1.0000**.

All six E5-A top-5 failures were discovery questions: `E5D-024`, `E5D-027`, `E5D-030`, `E5D-037`, `E5D-041`, and `E5D-045`.

## E5-B — DEVELOPMENT EVALUATION COMPLETE / RETAINED

Artifact:

```text
data_processed/evaluations/e5/e5b_development_evaluation.json
```

Evaluation version: `e5-b-eval-v1.0`

E5-B preserves E5-A unchanged for known-document questions and changes only corpus-wide discovery via signal-preserving BM25, wider candidate retrieval, document aggregation, within-document re-retrieval, and evidence assembly.

Overall E5-B retrieval:

| Metric | E5-A | E5-B | Delta |
|---|---:|---:|---:|
| Recall@1 | 0.6296 | 0.6111 | -0.0185 |
| Recall@3 | 0.8519 | **0.8889** | +0.0370 |
| Recall@5 | 0.8889 | **0.9444** | **+0.0556** |
| MRR@5 | 0.7407 | **0.7537** | +0.0130 |
| nDCG@5 | 0.7785 | **0.8022** | +0.0237 |
| Correct source@5 | 0.9259 | **0.9630** | +0.0370 |
| Correct source+page@5 | 0.8889 | **0.9444** | **+0.0556** |
| Candidate source@20 | 0.9630 | **0.9815** | +0.0185 |
| Candidate source+page@20 | 0.9444 | **0.9630** | +0.0185 |

By query mode:

### Known-document — 36 questions

- Recall@5: **1.0000**;
- correct source@5: **1.0000**;
- candidate source+page@20: **1.0000**.

This branch is intentionally unchanged from E5-A.

### Discovery — 18 questions

| Metric | E5-A | E5-B |
|---|---:|---:|
| Recall@1 | 0.4444 | 0.3889 |
| Recall@3 | 0.6667 | **0.7778** |
| Recall@5 | 0.6667 | **0.8333** |
| MRR@5 | 0.5370 | **0.5759** |
| nDCG@5 | 0.5701 | **0.6412** |
| Correct source@5 | 0.7778 | **0.8889** |
| Candidate source@20 | 0.8889 | **0.9444** |
| Candidate source+page@20 | 0.8333 | **0.8889** |

Paired E5-A/E5-B result:

- E5-B better rank: **6**;
- E5-A better rank: **6**;
- ties: **42**;
- **top-5 gains: 3**;
- **top-5 losses: 0**.

The three top-5 gains are:

- `E5D-024`: rank **9 → 3**;
- `E5D-027`: rank **12 → 2**;
- `E5D-037`: **missing@20 → rank 1**.

Remaining E5-B top-5 failures:

1. `E5D-030` — required action/compliance — target `2016-0222`, page 2 — target source/page absent at 20;
2. `E5D-041` — referenced publication — target `2011-0024R1`, page 3 — correct source rank 1 but correct page rank 15;
3. `E5D-045` — referenced publication — target `2022-0040`, page 3 — correct source rank 7 but correct page absent at 20.

Interpretation: E5-B materially improves the primary top-5 objective without any top-5 regression, so it is retained as the lexical/evidence-assembly base for E5-C. Do not further hand-tune E5-B to these three individual development misses before evaluating the predeclared dense stage.

## E5-C — IMPLEMENTED / DEVELOPMENT EVALUATION NEXT

E5-C adds the predeclared `Qwen/Qwen3-Embedding-0.6B` dense signal to E5-B.

Design constraints:

- exact known-document routing remains unchanged;
- Qwen dense retrieval is used only as a supplemental signal for identifier-free discovery;
- documents use normalized embeddings with no prompt;
- queries use the model's stored `query` instruction prompt;
- global BM25 document ranks and Qwen document ranks are fused with RRF;
- BM25 and Qwen passage ranks are fused again inside shortlisted ADs;
- E5-B evidence assembly remains the final passage-pack strategy;
- no learned reranker yet;
- no FAISS is used by E5-C;
- PyTorch/SentenceTransformers run only in the dense-build/query-worker processes, while the evaluator uses NumPy similarity.

Frozen initial E5-C development configuration before scores are opened:

- lexical global pool: **80 chunks**;
- Qwen dense global pool: **80 chunks**;
- document fusion depth: **24 per branch**;
- selected documents: **12**;
- within-document lexical depth: **6**;
- within-document dense depth: **6**;
- final candidate/evidence pool: **20 passages**;
- RRF constant: **60**;
- embedding model: **`Qwen/Qwen3-Embedding-0.6B`**;
- query prompt: **`prompt_name=query`**;
- reranker: **none**.

Build the separate Qwen dense artifact once:

```bash
.venv/bin/python -m full_corpus_pipeline.build_e5c_dense_embeddings \
  --index data_processed/indexes/rag_v1_2/e4_section_hybrid \
  --output-dir data_processed/indexes/e5c_qwen3_embedding_0_6b
```

Then evaluate E5-C:

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_e5c_development \
  --questions evaluation_sets/easa_airbus_ad_e5_benchmark_v1/development_questions.jsonl \
  --index data_processed/indexes/rag_v1_2/e4_section_hybrid \
  --dense-dir data_processed/indexes/e5c_qwen3_embedding_0_6b \
  --e5b-report data_processed/evaluations/e5/e5b_development_evaluation.json \
  --output data_processed/evaluations/e5/e5c_development_evaluation.json
```

The evaluator produces a paired E5-B/E5-C rank comparison. The E5 final-test families remain sealed.

## Predeclared development progression

- E5-A: deterministic routing + within-document BM25 — **evaluated**;
- E5-B: two-stage lexical discovery + evidence assembly — **evaluated and retained**;
- E5-C: Qwen3-Embedding-0.6B supplemental dense retrieval — **implemented, evaluate next**;
- E5-D: Qwen3-Reranker-0.6B; optional predeclared BGE reranker comparator if runtime permits.

Only the 60-question E5 development set may select among these configurations. The 40-question E5 final set remains sealed until one retrieval configuration and hosted-QA settings are frozen.

## Hosted QA

The hosted model is used only after retrieval. Provider/model/prompt/settings are frozen only after the E5 retrieval configuration is selected. Generated answers must cite application-resolved evidence IDs and abstain when evidence is insufficient or conflicting.

## Immediate next gate

1. Pull current `main` and run the full unit-test suite.
2. Build the separate E5-C Qwen3 dense artifact over the frozen 12,634 E4 chunks.
3. Run E5-C development evaluation and preserve `e5c_development_evaluation.json`.
4. Compare E5-C against E5-B overall, on the 18 discovery questions, and on the three remaining E5-B top-5 misses.
5. Then implement/evaluate the predeclared E5-D reranker.
6. Select and freeze one development-best retrieval configuration.
7. Freeze hosted-QA provider/model/prompt/evidence-pack settings.
8. Only then open the 16 final-test families and construct/run the 40-question final benchmark once.
