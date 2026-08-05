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
- `full_corpus_pipeline/e5_retrieval.py` — runnable E5-A exact-document/discovery lexical retriever;
- `full_corpus_pipeline/evaluate_e5a_development.py` — strict E5-A development evaluator;
- `full_corpus_pipeline/hosted_qa.py` — provider-configurable evidence-grounded hosted QA with deterministic citation resolution;
- unit tests for query routing, exact-document retrieval, E5-A evaluation metrics, and hosted-QA citation validation.

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

## Development authoring packets — COMPLETE

All **24 development-family** authoring packets have been generated from page-text v1.1. Each packet provides the representative AD identity, source PDF, page text and reconstructed section blocks used for benchmark authoring.

No final-test authoring packets should be generated while E5 retrieval/model/prompt tuning remains active.

## Development questions — HUMAN REVIEWED

The complete **60-question E5 development benchmark** has been checked against all 24 development authoring packets and is marked `review_status=human_verified`.

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

Verification outcome:

- source packets checked: **24 / 24**;
- questions checked: **60 / 60**;
- substantive question errors: **0**;
- reference-answer errors: **0**;
- page-reference errors: **0**;
- discovery identifier leaks: **0**;
- duplicate question IDs: **0**.

Review status:

```text
Human reviewed.
```

Review audit:

```text
docs/E5_DEVELOPMENT_REVIEW_AUDIT.md
```

Verified promoted JSONL SHA-256:

```text
d43f08611d7d2f77eb37052a03f3deabf335b004ead9528e798e12fb8dad677b
```

Canonical local promotion/validation commands:

```bash
.venv/bin/python -m full_corpus_pipeline.promote_e5_development_questions \
  --confirm-human-approval

.venv/bin/python -m full_corpus_pipeline.validate_e5_questions \
  --split development
```

## E5-A — READY FOR DEVELOPMENT EVALUATION

E5-A remains the predeclared lexical/routing stage:

- deterministic AD-aware query routing;
- exact-document filtering for known-document questions;
- corpus-wide SQLite FTS5/BM25 for discovery questions;
- transparent preferred-section ordering;
- no dense retrieval;
- no learned reranker.

Two implementation-contract corrections were made before opening any E5-A development retrieval scores:

1. an explicit target AD identifier is removed from the BM25 passage-ranking query after it has been used for deterministic document routing, so header repetition cannot act as a ranking signal;
2. relational query routing distinguishes target-discovery wording such as `Which directive superseded AD X?` from known-target wording such as `What directive is superseded by AD Y?`, and preserves the primary target for questions that mention related ADs.

The E5-A evaluator uses the frozen `rag-index-build-v1.2` E4 section chunks and SQLite FTS5/BM25 index without rebuilding or changing the corpus. It evaluates the **54 answerable** development questions for retrieval and retains the 6 abstention questions for route diagnostics only.

Primary metrics:

- Recall@1/3/5;
- MRR@5;
- nDCG@5;
- correct source@1/@5;
- correct source+page@1/@5;
- candidate source recall@20;
- candidate source+page recall@20;
- per-category and per-query-mode breakdowns;
- deterministic route accuracy.

Run:

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_e5a_development \
  --questions evaluation_sets/easa_airbus_ad_e5_benchmark_v1/development_questions.jsonl \
  --index data_processed/indexes/rag_v1_2/e4_section_hybrid \
  --output data_processed/evaluations/e5/e5a_development_evaluation.json
```

The evaluator prints one progress line per question and writes the complete per-question retrieval trace to the output JSON.

## Predeclared development progression

- E5-A: deterministic document routing + within-document BM25 + section preference;
- E5-B: add multi-passage/adjacency evidence assembly;
- E5-C: add `Qwen/Qwen3-Embedding-0.6B` dense signal;
- E5-D: add `Qwen/Qwen3-Reranker-0.6B`; optional predeclared BGE reranker comparator if runtime permits.

Only the new 60-question E5 development set may select among these configurations. The 40-question E5 final set is opened once after retrieval and hosted-QA settings are frozen.

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
2. Run the canonical `validate_e5_questions --split development` gate.
3. Run **E5-A development evaluation** and preserve `e5a_development_evaluation.json`.
4. Review overall, known-document, discovery, and category-level failure patterns.
5. Add/evaluate E5-B, then E5-C/D according to the predeclared development progression.
6. Freeze one retrieval configuration and hosted-QA settings.
7. Only then generate/open the 16 final-test family packets and 40-question final benchmark.
