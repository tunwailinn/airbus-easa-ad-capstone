# Cloud and Data Workflow

The active v3.1 project keeps versioned code and compact reference artifacts in GitHub while large/generated data remains local or in Google Drive.

## GitHub contains

- `full_corpus_pipeline/` implementation and tests;
- `gold_releases/easa_airbus_ad_gold_v2/` immutable 50-record audit source;
- the frozen corpus manifest and document-level extracted-text cache under `step3_pilot/source_metadata/`;
- project methodology, benchmark, decisions, status, and QA gateway documentation; and
- dependency configuration.

## Local / Google Drive data

Do not commit:

- raw source PDFs;
- page-preserving text derivatives;
- `data_processed/` extraction runs and promoted corpora;
- `data_incoming/` permanent-ingestion storage;
- `indexes/` BM25/FAISS indexes;
- `evaluation_sets/` generated benchmark projections and locks;
- OAuth credentials or tokens; or
- temporary renders and scratch outputs.

These paths are covered by `.gitignore` where applicable.

## Active extraction generations

Preserve every material parser generation separately.

Stale/reference outputs:

```text
data_processed/canonical_content_v2.1.3/
data_processed/runs/local-content-development-1804-v2.1.4/
```

Do not overwrite, relabel, or promote those as v2.1.5.

Active regeneration target:

```text
data_processed/runs/local-content-development-1804-v2.1.5/
```

After the development/reference/scope audits, clean test evaluation, and source spot checks pass, promote to:

```text
data_processed/canonical_content_v2.1.5/
```

The generated corpus is reproducible from the versioned parser plus corpus reference Parquets and is intentionally not stored in GitHub.

## v2.1.5 validation outputs

Keep these with the local run:

```text
data_processed/runs/local-content-development-1804-v2.1.5/
├── records/
├── run_config.json
├── extraction_failures.csv
├── development_reference_audit.json
├── corpus_scope_audit.json
├── evaluation_development_v3.1.5.json
└── evaluation_test_clean_v3.1.5.json   # only after development freeze
```

The v2.1.4 scope report (`1729 eligible / 59 excluded / 16 unknown`) is a diagnostic artifact only. It is not a final scope count because many apparent exclusions were malformed DAH parses. Do not move those counts into thesis tables or Drive folder names as if they were final membership.

## Scope-approved operational view

Extraction keeps one generated content record per nominal physical development PDF for provenance. After the corrected v2.1.5 scope audit, a strict Airbus S.A.S.-only application view may be implemented with an explicit sidecar/filter containing eligible/excluded/unknown status.

Do not silently delete PDFs or generated records to make the nominal corpus count match the research scope. Keep source inventory accounting separate from the scope-approved operational view.

## Required external data for RAG

The page-aware RAG build needs page-preserving text for the scope-approved development PDFs. Supply it through a local or mounted directory and pass that directory explicitly to the retrieval builder.

Example:

```bash
.venv/bin/python -m full_corpus_pipeline.retrieval \
  --page-text-dir /approved/page_text \
  --manifest step3_pilot/source_metadata/corpus_manifest.parquet \
  --exclude-selection evaluation_sets/unseen_incoming_5_v1/selection.csv \
  --output-dir indexes/corpus_v1
```

The original PDF/page text remains authoritative for detailed compliance answers even after content extraction is promoted.

## Safety boundaries

- Never edit source PDFs in place.
- Never commit credentials or API keys.
- Never overwrite a versioned extraction run or evaluation lock.
- Never relabel outputs from one parser version as another; regenerate.
- Keep the five unseen PDFs outside development indexes until ingestion evaluation.
- Permanent ingestion requires explicit confirmation and never retrains the LLM or embedding model.
- Detailed compliance answers must be grounded in retrieved original-PDF page text.
