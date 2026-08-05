# E5 Status

Last updated: 6 August 2026

## Current state

E0/E4 are closed/frozen historical experiments. E5 is the active improvement path and uses a fresh development/final benchmark.

Implemented in repository:

- `docs/E5_ENGINEERING_AWARE_RETRIEVAL.md` — E5 methodology;
- `full_corpus_pipeline/prepare_e5_benchmark_families.py` — deterministic 24-development/16-final family selector;
- `full_corpus_pipeline/prepare_e5_authoring_packets.py` — source-grounded development authoring packets;
- `full_corpus_pipeline/validate_e5_questions.py` — final count/family/leakage/human-review validator;
- `full_corpus_pipeline/validate_e5_draft_questions.py` — structural draft validator that does not grant human approval;
- `full_corpus_pipeline/promote_e5_development_questions.py` — explicit human-approval promotion step with provenance;
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

## Development questions — SOURCE VERIFIED / HUMAN APPROVED

The complete **60-question E5 development benchmark** has been checked against all 24 development authoring packets.

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

Review provenance is intentionally explicit: the project owner manually spot-checked a subset and approved promotion after full AI-assisted source verification of all 60 questions. The canonical records use `review_status=human_verified`, with per-record provenance documenting the human spot-check scope and complete assistant source verification. This must not be described as independent manual human reading of every question.

Review audit:

```text
docs/E5_DEVELOPMENT_REVIEW_AUDIT.md
```

Verified promoted JSONL SHA-256:

```text
b5b71d98c1ac5c6c7dfbb3b3347b6e084e134fb719365f500b277df2cc2d6310
```

Canonical local promotion/validation commands:

```bash
.venv/bin/python -m full_corpus_pipeline.promote_e5_development_questions \
  --confirm-human-approval

.venv/bin/python -m full_corpus_pipeline.validate_e5_questions \
  --split development
```

After canonical validation passes, E5-A/B/C/D development scoring may begin.

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
2. Place the verified draft at `evaluation_sets/easa_airbus_ad_e5_benchmark_v1/development_questions.draft.jsonl` if not already present.
3. Run the explicit promotion command with `--confirm-human-approval`.
4. Run the canonical `validate_e5_questions --split development` gate.
5. Evaluate **E5-A** on all 60 development questions and record per-mode/per-category metrics.
6. Add/evaluate E5-B, then E5-C/D according to the predeclared development progression.
7. Freeze one retrieval configuration and hosted-QA settings.
8. Only then generate/open the 16 final-test family packets and 40-question final benchmark.
