# Airbus EASA AD Extraction and RAG Capstone

Current methodology: **v3.1**.

This project processes a frozen snapshot of **1,809 Airbus S.A.S. EASA Airworthiness Directive PDFs**. Five PDFs are held out during development, so the active development corpus contains **1,804 records**.

The system has two layers:

```text
Section-complete local content extraction
→ filtering, browsing, metadata lookup, raw AD-section access

Original-PDF page-aware RAG
→ complex compliance timing, conditions, exceptions, branches, and QA
```

Reliable fields are structured locally. Difficult sections are preserved as source text and interpreted from retrieved PDF passages at question time. Full-corpus extraction uses no hosted LLM.

## Active repository structure

```text
.
├── AGENTS.md
├── README.md
├── airbus_easa_ad_project_exact_plan.md
├── requirements-v3.txt
├── docs/
│   ├── BENCHMARK_DESIGN.md
│   ├── CLOUD_WORKFLOW.md
│   ├── DECISIONS.md
│   ├── HOSTED_LLM_GATEWAY.md
│   └── PROJECT_STATUS.md
├── full_corpus_pipeline/
│   ├── content_record.schema.json
│   ├── local_extractor.py
│   ├── extract_corpus.py
│   ├── retrieval.py
│   ├── qa.py
│   ├── permanent_ingest.py
│   ├── streamlit_app.py
│   └── tests/
├── gold_releases/
│   └── easa_airbus_ad_gold_v2/      # immutable 50-record audit source
└── step3_pilot/source_metadata/
    ├── corpus_manifest.parquet
    └── corpus_extracted_text.parquet
```

`evaluation_sets/`, `data_processed/`, `data_incoming/`, `indexes/`, raw PDFs, and page-text derivatives are generated or large local/Drive data and are intentionally ignored by Git.

## Active versions

- Content schema: `2.1.0`
- Local parser: `v2.1.3`
- Active generated corpus: `data_processed/canonical_content_v2.1.3/`
- Content evaluation set: `easa_airbus_ad_content_gold_50_v2`
- Split: 30 development / 20 locked test
- QA benchmark: `easa_airbus_ad_qa_50_v2`, 50 questions
- Unseen ingestion set: 5 PDFs

## Run tests

```bash
.venv/bin/python -m unittest discover -s full_corpus_pipeline/tests -v
```

## Run local extraction

```bash
.venv/bin/python -m full_corpus_pipeline.extract_corpus \
  --run-id local-content-development-1804-v2.1.3
```

## Build RAG index

```bash
.venv/bin/python -m full_corpus_pipeline.retrieval \
  --page-text-dir /approved/page_text \
  --manifest step3_pilot/source_metadata/corpus_manifest.parquet \
  --exclude-selection evaluation_sets/unseen_incoming_5_v1/selection.csv \
  --output-dir indexes/corpus_v1
```

## Current next step

Build page-preserving text for the 1,804 development PDFs, construct the E0 and E4 retrieval indexes, then run locked retrieval/QA evaluation before ingesting the five unseen PDFs.
