# E5 Status

Last updated: 6 August 2026

## Current state

E0/E4 are closed/frozen historical experiments. E5 retrieval development is now complete. **E5-D is selected and frozen as the final E5 retrieval configuration.**

The 16 E5 final-test families and 40 final questions remain sealed. Hosted-QA provider/model/prompt/evidence-pack settings must be frozen before they are opened.

Frozen E5 development benchmark:

- 24 development families / 16 final-test families;
- 60 human-reviewed development questions;
- 54 answerable retrieval questions + 6 abstention/conflict questions reserved for QA;
- 36 known-document + 18 identifier-free discovery + 6 abstention/conflict;
- benchmark SHA-256: `d43f08611d7d2f77eb37052a03f3deabf335b004ead9528e798e12fb8dad677b`.

Frozen retrieval source remains `rag-index-build-v1.2`: **1,786 documents / 12,634 E4 section chunks**.

Machine-readable retrieval freeze:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/retrieval_freeze.json
```

Freeze version: `e5-retrieval-freeze-v1.0`.

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

## E5-B — COMPLETE / LEXICAL BASE

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

Discovery Recall@5 improved from **0.6667 → 0.8333** while known-document Recall@5 remained **1.0000**. Paired E5-A/E5-B top-5 gains/losses: **3 / 0**.

## E5-C — COMPLETE / HIGH-RECALL CANDIDATE GENERATOR

E5-C adds pinned `Qwen/Qwen3-Embedding-0.6B@97b0c61` dense retrieval to E5-B discovery, with BM25/Qwen document-level and passage-level reciprocal-rank fusion. Known-document behavior remains unchanged.

The accepted dense artifact is `e5c-dense-build-v1.1`, which explicitly re-normalizes float32 document/query vectors before cosine-via-inner-product scoring.

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

Discovery Recall@5 was **0.7778**. E5-C did not beat E5-B at top 5, but it raised candidate source+page recall@20 to **53/54 = 0.9815**, providing the high-recall fixed candidate pool used by E5-D.

## E5-D — COMPLETE / SELECTED AND FROZEN

E5-D keeps **E5-C top-20 candidate membership fixed** and applies the pinned learned passage reranker:

- embedding model: `Qwen/Qwen3-Embedding-0.6B@97b0c61`;
- reranker: `Qwen/Qwen3-Reranker-0.6B@e61197e`;
- reranker execution: isolated SentenceTransformers `CrossEncoder` worker without FAISS;
- reranker score: raw logit difference;
- candidate depth: **20**;
- primary final evidence depth: **5**;
- no hosted LLM in retrieval;
- final-test families/questions remained sealed during selection.

Frozen aviation reranker instruction:

> Given an aviation airworthiness-directive maintenance query, rank passages by how directly and completely they answer the query. Preserve exact applicability, compliance thresholds, timing, exceptions, identifiers, lifecycle statements, and referenced publications.

Development artifact:

```text
data_processed/evaluations/e5/e5d_development_evaluation.json
```

Artifact SHA-256:

```text
9241b5d777f47a95efd1a5afc9a4139d280be0a12c3b91b6eb2d44df31cbcb05
```

### Development result

| Metric | E5-B | E5-C | **E5-D** |
|---|---:|---:|---:|
| Recall@1 | 0.6111 | 0.6481 | **0.7963** |
| Recall@3 | 0.8889 | 0.8519 | **0.9259** |
| Recall@5 | 0.9444 | 0.9259 | **0.9630** |
| MRR@5 | 0.7537 | 0.7645 | **0.8633** |
| nDCG@5 | 0.8022 | 0.8053 | **0.8884** |
| Correct source@5 | 0.9630 | 0.9630 | **0.9815** |
| Correct source+page@5 | 0.9444 | 0.9259 | **0.9630** |
| Candidate source+page recall@20 | 0.9630 | **0.9815** | **0.9815** |

Query-mode result:

- known-document Recall@5: **1.0000 (36/36)**;
- discovery Recall@5: **0.8889 (16/18)**;
- routing accuracy: **1.0000 (54/54)**.

Category Recall@5:

- applicability: **1.0000**;
- conditional/multi-passage: **1.0000**;
- identity/lifecycle: **1.0000**;
- referenced publication: **0.8750**;
- required action/compliance: **0.9500**.

Paired E5-D vs E5-B:

- E5-D better rank: **18**;
- E5-B better rank: **7**;
- ties: **29**;
- top-5 gains: **1**;
- top-5 losses: **0**.

Paired E5-D vs E5-C:

- E5-D better rank: **16**;
- E5-C better rank: **6**;
- ties: **32**;
- top-5 gains: **2**;
- top-5 losses: **0**.

### Remaining development top-5 misses

Only two of the 54 answerable questions remain outside top 5:

1. `E5D-030` — required action/compliance — discovery — target `2016-0222`, page 2 — target source/page absent at 20. This is a candidate-generation miss and cannot be repaired by reranking the fixed pool.
2. `E5D-045` — referenced publication — discovery — target `2022-0040`, page 3 — correct source+page rank **6**, source rank **4**. This is a near-boundary ranking miss.

Do **not** tune retrieval against either miss after this freeze.

## Retrieval selection decision

The predeclared primary selection objective is correct source+page Recall@5. E5-D is therefore selected because it achieves the best development Recall@5 (**0.9630**) and also has the strongest MRR@5 (**0.8633**), nDCG@5 (**0.8884**), Recall@1 (**0.7963**), and discovery Recall@5 (**0.8889**). It improves top-5 coverage versus both E5-B and E5-C with **zero top-5 regressions** in the paired comparisons.

From this point onward, the following are frozen for the primary final evaluation:

- exact known-document routing behavior;
- E5-C BM25/Qwen candidate generation and all its fixed depths/RRF settings;
- embedding model and revision;
- dense artifact construction rules;
- E5-D reranker model and revision;
- reranker instruction and score type;
- candidate limit 20 and final evidence depth 5;
- frozen E4 chunk/index source.

Any later retrieval experiment is post-hoc only and must not replace the primary frozen E5-D final result.

## Immediate next gate — hosted QA freeze

Retrieval tuning is closed. Next:

1. define/freeze the hosted-QA provider, model revision/name, reasoning mode, generation parameters, evidence-pack format, citation contract, and abstention policy;
2. validate the hosted-QA runner on development data only, without changing frozen retrieval;
3. record a machine-readable hosted-QA freeze;
4. only after that freeze, author/review/open the 40-question final benchmark from the 16 sealed final families;
5. run frozen E5-D retrieval + frozen hosted QA on the final benchmark once;
6. separately run the oracle-reference-evidence hosted-QA condition to distinguish retrieval failures from generation failures;
7. after final evaluation, run the five frozen unseen-PDF ingestion/QA cases without retraining.
