# E5 Status

Last updated: 5 August 2026

## Current state

E0/E4 are closed/frozen historical experiments. E5 is the active improvement path and uses a fresh development/final benchmark.

Implemented in repository:

- `docs/E5_ENGINEERING_AWARE_RETRIEVAL.md` — E5 methodology;
- `full_corpus_pipeline/prepare_e5_benchmark_families.py` — deterministic 24-development/16-final family selector;
- `full_corpus_pipeline/prepare_e5_authoring_packets.py` — source-grounded development authoring packets;
- `full_corpus_pipeline/validate_e5_questions.py` — final count/family/leakage/human-review validator;
- `full_corpus_pipeline/validate_e5_draft_questions.py` — structural draft validator that does not grant human approval;
- `full_corpus_pipeline/e5_query_router.py` — deterministic AD/SB/intent router;
- `full_corpus_pipeline/e5_retrieval.py` — runnable E5-A exact-document/discovery lexical retriever;
- `full_corpus_pipeline/hosted_qa.py` — provider-configurable evidence-grounded hosted QA with deterministic citation resolution;
- unit tests for query routing, exact-document retrieval, and hosted-QA citation validation.

## Frozen E5 family split — COMPLETE

The E5 family split was generated locally from the verified page-text v1.1 retrieval manifest and independently checked before question authoring.

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

## Development questions — DRAFT COMPLETE / HUMAN REVIEW REQUIRED

A source-grounded **60-question development draft** has been prepared from the 24 development packets.

Target distribution is satisfied exactly:

- identity/lifecycle: **8**;
- applicability: **10**;
- required action/compliance: **20**;
- referenced publication: **8**;
- conditional/multi-passage: **8**;
- insufficient/conflict/abstention: **6**.

Query-mode distribution is also satisfied exactly:

- known-document: **36**;
- identifier-free discovery: **18**;
- abstention/conflict: **6**.

All 24 development families are represented. Mechanical checks confirm no discovery question contains its exact or base target AD identifier and all cited pages exist in the corresponding development packet.

The draft must remain `needs_human_review` until the question wording, reference answer, page(s) and section(s) are checked against the source packet. Do not label AI-authored questions `human_verified` automatically.

Draft structural validation command:

```bash
.venv/bin/python -m full_corpus_pipeline.validate_e5_draft_questions \
  --questions evaluation_sets/easa_airbus_ad_e5_benchmark_v1/development_questions.draft.jsonl
```

After actual human review and promotion to `development_questions.jsonl` with `review_status=human_verified`, the canonical gate is:

```bash
.venv/bin/python -m full_corpus_pipeline.validate_e5_questions \
  --split development
```

Only after that canonical validation passes may E5-A/B/C/D development scoring begin.

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
2. Place the prepared `development_questions.draft.jsonl` under the E5 benchmark directory.
3. Run the draft structural validator.
4. Human-review all 60 questions against the development authoring packets.
5. Promote only reviewed records to `development_questions.jsonl` with `review_status=human_verified`.
6. Run the canonical development-question validator.
7. Evaluate E5-A on the 60-question development set.
8. Add/evaluate E5-B, then E5-C/D according to the predeclared development progression.
9. Freeze one retrieval configuration and hosted-QA settings.
10. Only then generate/open the 16 final-test family packets and 40-question final benchmark.
