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

## Required external data for the next stage

The page-aware RAG build needs page-preserving text for the 1,804 development PDFs. Supply it through a local or mounted directory and pass that directory explicitly to the retrieval builder.

Example:

```bash
.venv/bin/python -m full_corpus_pipeline.retrieval \
  --page-text-dir /approved/page_text \
  --manifest step3_pilot/source_metadata/corpus_manifest.parquet \
  --exclude-selection evaluation_sets/unseen_incoming_5_v1/selection.csv \
  --output-dir indexes/corpus_v1
```

## Generated extraction data

The completed deterministic development extraction is expected locally at:

```text
data_processed/canonical_content_v2.1.3/
```

The canonical generated directory is reproducible from the versioned parser and corpus reference Parquets, so it is intentionally not stored in GitHub.

## Safety boundaries

- Never edit source PDFs in place.
- Never commit credentials or API keys.
- Never overwrite a versioned extraction run or evaluation lock.
- Keep the five unseen PDFs outside development indexes until ingestion evaluation.
- Permanent ingestion requires explicit confirmation and never retrains the LLM or embedding model.
- Detailed compliance answers must be grounded in retrieved original-PDF page text.
