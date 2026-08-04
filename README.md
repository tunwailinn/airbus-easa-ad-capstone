# Airbus EASA AD Extraction and RAG Capstone

Current methodology: **v3.1**.

This project processes a frozen snapshot of **1,809 Airbus-related EASA Airworthiness Directive PDFs**. Five PDFs are held out during development, so the nominal development extraction contains **1,804 records**. Primary evaluation additionally enforces the stated Airbus S.A.S. Design/Type Approval Holder scope from reviewed gold metadata.

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
│   ├── evaluate_extraction.py
│   ├── audit_development_reference.py
│   ├── audit_corpus_scope.py
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
- Local parser: `v2.1.4`
- Extraction evaluator: `content-eval-v3.1.4`
- Previous generated corpus: `data_processed/canonical_content_v2.1.3/` — stale after the v2.1.4 boundary fix
- Corrected run: `data_processed/runs/local-content-development-1804-v2.1.4/`
- Canonical target after validation: `data_processed/canonical_content_v2.1.4/`
- Content evaluation set: `easa_airbus_ad_content_gold_50_v2`
- Nominal split: 30 development / 20 test, with scope/leakage exclusions reported separately by the evaluator
- QA benchmark: `easa_airbus_ad_qa_50_v2`, 50 questions
- Unseen ingestion set: 5 PDFs

Parser v2.1.4 fixes material spot-check defects found in v2.1.3: printed issue dates take precedence over stale manifest dates, `Foreign AD` stops before revision metadata, repeated EASA page furniture/status watermarks are removed before section segmentation, ordinary prose beginning with words such as `compliance` no longer terminates a section, cross-page sections are preserved, and Remark contact lines are retained.

## Run tests

```bash
.venv/bin/python -m unittest discover -s full_corpus_pipeline/tests -v
```

## Audit the development references

```bash
.venv/bin/python -m full_corpus_pipeline.audit_development_reference \
  --output data_processed/runs/local-content-development-1804-v2.1.4/development_reference_audit.json
```

The nominal development set contains 30 frozen references. The audit checks approval/provenance, deterministic projection, evidence integrity, source-text containment, and holder-scope eligibility. AD `2026-0079` is a known Lufthansa Technik Design Change Approval Holder case and is excluded from primary Airbus S.A.S. development scoring while remaining in the immutable release.

## Audit the full development extraction scope

Before canonical promotion, scan all 1,804 generated records:

```bash
.venv/bin/python -m full_corpus_pipeline.audit_corpus_scope \
  data_processed/runs/local-content-development-1804-v2.1.4/records \
  --output data_processed/runs/local-content-development-1804-v2.1.4/corpus_scope_audit.json
```

This reports the number of holder-scope-eligible, excluded, and unknown records plus the holder distribution. If any excluded or unknown records exist, resolve the corpus-governance policy before promoting a canonical corpus. Do not silently delete records or broaden the research scope.

## Run development extraction evaluation

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_extraction \
  data_processed/runs/local-content-development-1804-v2.1.4/records \
  --output data_processed/runs/local-content-development-1804-v2.1.4/evaluation_development_v3.1.4.json \
  --split development
```

Primary metrics now separate stable metadata, secondary family taxonomy, reference/lifecycle identifiers, and raw-section integrity. The old projection-overlap score remains diagnostic only.

Do not use the test split to tune the parser.

## Final clean extraction evaluation

After development rules and corpus scope are frozen:

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_extraction \
  data_processed/runs/local-content-development-1804-v2.1.4/records \
  --output data_processed/runs/local-content-development-1804-v2.1.4/evaluation_test_clean_v3.1.4.json \
  --split test
```

The evaluator derives out-of-scope holder exclusions from reviewed gold metadata and separately excludes known test leakage. Two test exclusions are already known: AD `2021-0286` is Airbus Defence and Space rather than Airbus S.A.S., and AD `2024-0038` was used during parser-v2.1.4 diagnosis. Use the generated report's `record_count` for the final clean sample size.

## Promote the corrected corpus

Only after the revised audits, development evaluation, clean test evaluation, source-PDF spot checks, and corpus-scope decision are satisfactory:

```bash
.venv/bin/python -m full_corpus_pipeline.promote_extraction_run \
  data_processed/runs/local-content-development-1804-v2.1.4 \
  data_processed/canonical_content_v2.1.4 \
  --expected-count 1804
```

That command still promotes all 1,804 successfully extracted physical development PDFs. If the strict Airbus S.A.S. research scope requires an operational subset rather than all 1,804 generated records, record that decision explicitly in a sidecar/filter or revise the canonical-corpus policy before promotion; do not silently change the expected count.

## Build RAG index

```bash
.venv/bin/python -m full_corpus_pipeline.retrieval \
  --page-text-dir /approved/page_text \
  --manifest step3_pilot/source_metadata/corpus_manifest.parquet \
  --exclude-selection evaluation_sets/unseen_incoming_5_v1/selection.csv \
  --output-dir indexes/corpus_v1
```

## Current next step

Run the development-reference audit, full-corpus holder-scope audit, and evaluator v3.1.4 on the regenerated v2.1.4 run. Inspect genuine per-field mismatches and raw-section integrity, resolve the corpus-scope policy, freeze extraction behavior, then run the clean test once. After that, promote the corrected corpus, generate page-preserving text, build E0/E4 retrieval indexes, and run retrieval/QA evaluation before ingesting the five unseen PDFs.
