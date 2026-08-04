# Cloud and Data Workflow

The active v3.1 project keeps versioned code and compact reference artifacts in GitHub while large/generated data remains local or in Google Drive.

## GitHub contains

- `full_corpus_pipeline/` implementation and tests;
- `gold_releases/easa_airbus_ad_gold_v2/` immutable 50-record audit source;
- the frozen corpus manifest and document-level extracted-text cache under `step3_pilot/source_metadata/`;
- project methodology, benchmark, decisions, status, and QA gateway documentation; and
- dependency configuration.

## Local / Google Drive data

Do not commit raw source PDFs, page-preserving text derivatives, `data_processed/`, `data_incoming/`, `indexes/`, generated evaluation projections/locks, credentials, tokens, or temporary renders/scratch outputs.

## Active extraction generations

Preserve every material parser generation separately.

Historical/development outputs:

```text
data_processed/canonical_content_v2.1.3/
data_processed/runs/local-content-development-1804-v2.1.4/
data_processed/runs/local-content-development-1804-v2.1.5/
```

The v2.1.5 run is valuable development evidence because it demonstrated complete raw difficult-section preservation, but it is not the final promotion target.

Active regeneration target:

```text
data_processed/runs/local-content-development-1804-v2.1.6/
```

After development/reference/scope audits, clean test evaluation, and source spot checks pass, promote to:

```text
data_processed/canonical_content_v2.1.6/
```

Never overwrite, relabel, or copy an older generation into the v2.1.6 path.

## v2.1.6 validation outputs

Keep these with the local run:

```text
data_processed/runs/local-content-development-1804-v2.1.6/
├── records/
├── run_config.json
├── extraction_failures.csv
├── development_reference_audit.json
├── corpus_scope_audit.json
├── evaluation_development_v3.1.5.json
└── evaluation_test_clean_v3.1.5.json   # only after development freeze
```

Earlier scope reports are diagnostics only. In particular:

- v2.1.4: `1729 eligible / 59 excluded / 16 unknown`;
- v2.1.5: `1765 eligible / 17 excluded / 22 unknown`.

Neither is the final Airbus-only operational count because later source review showed parser-format misses among the apparent scope discrepancies.

## Scope-approved operational view

Extraction preserves one generated content record per nominal physical PDF for provenance.

`scope_policy.py` / corpus-scope audit v1.2 classify each generated holder as:

- eligible Airbus S.A.S./legacy Airbus;
- confirmed external or mixed holder, excluded from the strict Airbus-only operational view; or
- unknown pending review.

Confirmed exclusions remain in the physical inventory/content store. Do not delete PDFs or generated records to make the nominal physical count match the strict operational scope count. Resolve/document unknowns before freezing the operational subset.

## Required external data for RAG

The page-aware RAG build needs page-preserving text for the scope-approved development PDFs. Supply it through a local or mounted directory and pass that directory explicitly to the retrieval builder.

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
