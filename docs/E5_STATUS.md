# E5 Status

Last updated: 6 August 2026

## Current state

E0/E4 are closed/frozen historical experiments. E5 is the active improvement path and uses a fresh development/final benchmark.

Implemented in repository:

- `docs/E5_ENGINEERING_AWARE_RETRIEVAL.md` — E5 methodology;
- `full_corpus_pipeline/prepare_e5_benchmark_families.py` — deterministic 24-development/16-final family selector;
- `full_corpus_pipeline/prepare_e5_authoring_packets.py` — source-grounded development authoring packets;
- `full_corpus_pipeline/validate_e5_questions.py` — final count/family/leakage/human-review validator;
- `full_corpus_pipeline/validate_e5_draft_questions.py` — structural draft validator;
- `full_corpus_pipeline/promote_e5_development_questions.py` — human-review promotion step;
- `full_corpus_pipeline/e5_query_router.py` — deterministic AD/SB/intent router;
- `full_corpus_pipeline/e5_retrieval.py` — E5-A exact-document/discovery lexical retriever;
- `full_corpus_pipeline/evaluate_e5a_development.py` — strict E5-A development evaluator;
- `full_corpus_pipeline/e5b_retrieval.py` — E5-B two-stage sparse discovery and evidence assembler;
- `full_corpus_pipeline/evaluate_e5b_development.py` — E5-B evaluator with paired E5-A comparison;
- `full_corpus_pipeline/hosted_qa.py` — provider-configurable evidence-grounded hosted QA with deterministic citation resolution;
- unit tests for query routing, E5-A/E5-B retrieval, evaluation metrics, and hosted-QA citation validation.

## Frozen E5 family split — COMPLETE

The E5 family split was generated locally from the verified page-text v1.1 retrieval manifest and checked before question authoring.

Frozen split:

- seed: **20260805**;
- development families: **24**;
- final-test families: **16**;
- total: **40**;
- each of four publication eras contributes **6 development + 4 final-test families**;
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

Configuration:

- frozen `rag-index-build-v1.2` E4 section chunks;
- **1,786 documents / 12,634 chunks**;
- deterministic AD-aware routing;
- SQLite FTS5/BM25 only;
- explicit AD identifiers used for routing only;
- candidate depth 20;
- no dense retrieval;
- no learned reranker.

Question accounting:

- total development questions: **60**;
- answerable retrieval questions: **54**;
- abstention questions reserved for QA: **6**;
- route accuracy: **54 / 54 = 100%**.

Overall E5-A retrieval:

| Metric | E5-A |
|---|---:|
| Recall@1 | 0.6296 |
| Recall@3 | 0.8519 |
| Recall@5 | **0.8889** |
| MRR@5 | 0.7407 |
| nDCG@5 | 0.7785 |
| Correct source@1 | 0.8333 |
| Correct source@5 | **0.9259** |
| Correct source+page@1 | 0.6296 |
| Correct source+page@5 | **0.8889** |
| Candidate source recall@20 | **0.9630** |
| Candidate source+page recall@20 | **0.9444** |

By query mode:

### Known-document — 36 questions

- Recall@1: **0.7222**;
- Recall@3: **0.9444**;
- Recall@5: **1.0000**;
- MRR@5: **0.8426**;
- nDCG@5: **0.8827**;
- correct source@1/@5: **1.0000 / 1.0000**;
- candidate source+page recall@20: **1.0000**.

This validates deterministic AD routing plus within-document sparse retrieval. E5-B must preserve this branch unchanged.

### Discovery — 18 questions

- Recall@1: **0.4444**;
- Recall@3: **0.6667**;
- Recall@5: **0.6667**;
- MRR@5: **0.5370**;
- nDCG@5: **0.5701**;
- correct source@1/@5: **0.5000 / 0.7778**;
- candidate source recall@20: **0.8889**;
- candidate source+page recall@20: **0.8333**.

All six E5-A top-5 failures are discovery questions:

- `E5D-024` — required action/compliance — target `2008-0196` — relevant rank **9**;
- `E5D-027` — required action/compliance — target `2012-0274` — relevant rank **12**;
- `E5D-030` — required action/compliance — target `2016-0222` — **missing at 20**;
- `E5D-037` — required action/compliance — target `2025-0067` — **missing at 20**;
- `E5D-041` — referenced publication — target `2011-0024R1` — source appears at **4**, correct page missing at 20;
- `E5D-045` — referenced publication — target `2022-0040` — source appears at **1**, correct page rank **15**.

Error analysis found two systematic E5-A discovery weaknesses:

1. the inherited sparse query helper keeps only the first 20 lexical terms, which can drop late high-signal thresholds/identifiers from long engineering questions;
2. hard preferred-section partitioning can demote the strongest raw BM25 hit. For example, some correct target passages were found early by raw sparse search but moved below generic passages because the predicted preferred section differed.

## E5-B — IMPLEMENTED / DEVELOPMENT EVALUATION NEXT

E5-B preserves E5-A unchanged for known-document questions and changes only corpus-wide discovery.

Discovery stages:

1. **signal-preserving sparse query** — up to 48 de-duplicated terms, always retaining digit-bearing thresholds/identifiers;
2. **wider sparse candidate pool** — 80 global chunk hits;
3. **document aggregation** — sparse support is aggregated per AD using capped reciprocal-rank support;
4. **candidate-document selection** — top 12 ADs;
5. **within-document BM25** — top 6 passages per candidate AD;
6. **evidence assembly** — one primary passage per candidate document first, followed by adjacent/section-diverse secondary evidence;
7. final evidence pool — 20 passages.

E5-B remains fully local and lexical:

- dense retrieval: **none**;
- learned reranker: **none**;
- corpus/index rebuild: **none**.

Run:

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_e5b_development \
  --questions evaluation_sets/easa_airbus_ad_e5_benchmark_v1/development_questions.jsonl \
  --index data_processed/indexes/rag_v1_2/e4_section_hybrid \
  --e5a-report data_processed/evaluations/e5/e5a_development_evaluation.json \
  --output data_processed/evaluations/e5/e5b_development_evaluation.json
```

The evaluator reports the same overall/per-mode/per-category metrics and an exact paired E5-A/E5-B rank comparison.

## Predeclared development progression

- E5-A: deterministic document routing + within-document BM25 + section preference — **evaluated**;
- E5-B: two-stage lexical discovery + multi-passage/adjacency evidence assembly — **implemented, evaluate next**;
- E5-C: add `Qwen/Qwen3-Embedding-0.6B` dense signal;
- E5-D: add `Qwen/Qwen3-Reranker-0.6B`; optional predeclared BGE reranker comparator if runtime permits.

Only the 60-question E5 development set may select among these configurations. The 40-question E5 final set remains sealed until one retrieval configuration and hosted-QA settings are frozen.

## Hosted QA

Default configured provider/model:

```text
base URL: https://api.deepseek.com
model: deepseek-v4-pro
API key env: DEEPSEEK_API_KEY
thinking: enabled
reasoning effort: high
JSON output: required
```

The client never persists reasoning content. The model returns evidence IDs only; source/page/section citations are resolved and validated by application code.

## Immediate next gate

1. Pull current `main` and run the full unit-test suite.
2. Run **E5-B development evaluation** and preserve `e5b_development_evaluation.json`.
3. Compare E5-B against E5-A overall and specifically on the 18 discovery questions.
4. If E5-B improves lexical discovery without degrading known-document retrieval, retain it as the lexical base for E5-C.
5. Add/evaluate E5-C dense retrieval, then E5-D reranking.
6. Freeze one retrieval configuration and hosted-QA settings.
7. Only then open the 16 final-test families and construct/run the 40-question final benchmark.
