# Full Corpus Pipeline

The pipeline is organized by the three research layers while preserving frozen thesis artifact paths.

```text
full_corpus_pipeline/
├── layer_a/   # deterministic section-complete catalogue index
├── layer_b/   # verified page text + frozen retrieval index
├── layer_c/   # active hosted evidence-grounded QA implementation
├── tests/     # cross-layer and regression tests
└── *.py       # frozen Layer A/B implementations, shared integration code,
               # and small Layer C compatibility entry points
```

## Layer A

Purpose: deterministic extraction, section-complete content records, corpus scope, and lifecycle support.

Start here: [`layer_a/README.md`](layer_a/README.md)

The active parser/evaluator paths remain at the package root because these are frozen thesis artifacts. Do not move or rewrite them simply for cosmetic organization.

## Layer B

Purpose: verified original-PDF page text and frozen E5-D engineering-aware retrieval.

Start here: [`layer_b/README.md`](layer_b/README.md)

The frozen page-text/E0/E4/E5 implementation paths remain at the package root for reproducibility.

## Layer C

Purpose: hosted evidence-grounded answer generation from frozen Layer B evidence.

Start here: [`layer_c/README.md`](layer_c/README.md)

Active Layer C implementation now lives inside `layer_c/`. Root Layer C module names are compatibility shims only.

## Shared/integration modules

A few modules intentionally span layers and remain at the package root:

- `document_io.py` — PDF/page source I/O
- `qa.py` — application-facing QA integration
- `permanent_ingest.py` — permanent ingestion workflow
- `streamlit_app.py` — prototype UI
- `lifecycle.py` — lifecycle selection support

## Research boundary

```text
Layer A
section-complete deterministic content
        ↓
Layer B
verified original-PDF evidence retrieval
        ↓
Layer C
hosted evidence-grounded answer generation
```

A failure in a later layer must not be used to silently retune a frozen earlier layer.
