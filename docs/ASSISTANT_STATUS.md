# Aviation Document Assistant — Post-Evaluation Status

Last updated: 18 August 2026

## Current checkpoint

The first user-facing serving slice is **implemented** after the frozen evaluation phase.

Implemented:

- validated serving-snapshot preparation from the locked 1,791-document / 12,670-chunk post-ingestion derivative;
- reusable live E5-C/E5-D retrieval runtime;
- frozen Layer C evidence-grounded DeepSeek integration;
- locally resolved AD/PDF/page/section citations;
- graceful `technical_error` fallback that preserves retrieved evidence;
- retrieval-only mode with no hosted call;
- interactive and one-shot CLI;
- local browser UI and JSON query endpoint;
- assistant contract tests;
- explicit document-authority and aircraft-specific-decision safety boundary.

Canonical implementation:

```text
full_corpus_pipeline/assistant/
├── __init__.py
├── runtime.py
├── prepare_serving_snapshot.py
├── cli.py
└── web.py
```

Documentation:

```text
docs/ASSISTANT_INTEGRATION.md
```

## Evaluation boundary

This serving work is post-evaluation. It does not change:

- frozen E5 final result: **38/40 = 95.0%**;
- frozen E5-D final Recall@5: **35/36 = 97.22%**;
- locked unseen U7 result: **13 PASS / 1 semantic FAIL / 1 technical failure**;
- any parser/retrieval/hosted-QA freeze or benchmark lock.

The serving snapshot is a non-destructive copy of the already validated post-ingestion derivative. It is not a new benchmark condition.

## Local acceptance gate

The implementation is ready for a local smoke test on the project MacBook. The acceptance sequence is:

```bash
git pull

.venv/bin/python -m unittest discover \
  -s full_corpus_pipeline/tests \
  -p 'test_assistant_runtime.py'

.venv/bin/python -m \
  full_corpus_pipeline.assistant.prepare_serving_snapshot

.venv/bin/python -m full_corpus_pipeline.assistant.cli \
  --retrieval-only --show-evidence \
  "For EASA AD 2011-0041R1, what two actions had to be completed within 3 days after 14 March 2011?"

.venv/bin/python -m full_corpus_pipeline.assistant.web
```

Expected serving snapshot accounting:

```text
document_count: 1791
chunk_count: 12670
dense_row_count: 12670
status: ready
frozen_e5_results_modified: false
```

## Next step after the smoke test

After the local assistant smoke test passes, capture representative known-document, discovery, abstention and technical-error UI outputs for the capstone demonstration. Then move to final report/thesis integration and final system-flow/result slides.
