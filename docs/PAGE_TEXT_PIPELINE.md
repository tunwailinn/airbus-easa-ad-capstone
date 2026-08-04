# Page-Preserving PDF Text Pipeline

Status: **RAG source-layer implementation, page-text v1.0**

This stage begins only after canonical content parser v2.1.6 is frozen. It does not change or reinterpret the canonical JSON extraction. Its job is to create the page-addressable source layer used by retrieval and citation evaluation.

## Research corpus for this stage

The frozen physical snapshot contains 1,809 PDFs. For development RAG indexing:

- 5 frozen unseen incoming PDFs remain excluded;
- 18 confirmed external/mixed-holder records remain preserved physically but are excluded from the strict Airbus S.A.S. operational view;
- 0 scope-unknown records remain;
- target page-text/retrieval corpus: **1,786 PDFs**.

The operational selection is reconstructed from the frozen corpus manifest, scope audit v1.3, and unseen selection. Do not manually delete source PDFs to obtain this count.

## Inputs

- original frozen PDF directory supplied with `--pdf-root`;
- `step3_pilot/source_metadata/corpus_manifest.parquet`;
- `data_processed/runs/local-content-development-1804-v2.1.6/corpus_scope_audit.json`;
- `evaluation_sets/unseen_incoming_5_v1/selection.csv`.

## Run page extraction

Set `PDF_ROOT` to the local directory that contains the original frozen EASA PDF snapshot. The script searches recursively, so the PDFs may be inside subdirectories.

```bash
PDF_ROOT="/absolute/path/to/frozen/pdfs"

.venv/bin/python -m full_corpus_pipeline.extract_page_text \
  --pdf-root "$PDF_ROOT" \
  --output-dir data_processed/page_text_v1/operational_airbus \
  --expected-count 1786
```

The command validates each resolved PDF against the manifest SHA-256 when available and verifies page counts before accepting its page text.

OCR is never performed silently. By default, any page with fewer than 80 non-whitespace native-text characters is marked `needs_ocr` and the run is not approved for indexing. `--allow-needs-ocr` is diagnostic only and must not be used to bypass the thesis indexing gate.

## Outputs

`data_processed/page_text_v1/operational_airbus/` contains:

- `pages/*.pages.jsonl` — one file per scope-approved PDF;
- `retrieval_manifest.csv` — the exact 1,786-row manifest to feed E0/E4;
- `page_manifest.csv` — one row per source PDF with page/OCR status;
- `failures.csv` — source resolution/hash/page-count/extraction failures;
- `page_extraction_audit.json` — run-level gate summary.

Each page JSONL row includes:

- `schema_version` (`page-text-v1.0`);
- `file_instance_id`;
- `ad_number`;
- original source filename/path;
- source PDF SHA-256;
- 1-based PDF page number;
- page-text SHA-256;
- character counts;
- `needs_ocr`;
- native page text.

## Approval gate

Do not build retrieval indexes until all of the following are true:

- `selected_document_count == 1786`;
- `successful_document_count == 1786`;
- `failure_count == 0`;
- `needs_ocr_document_count == 0`;
- `needs_ocr_page_count == 0`;
- `ready_for_indexing == true`.

Useful checks:

```bash
cat data_processed/page_text_v1/operational_airbus/page_extraction_audit.json

find data_processed/page_text_v1/operational_airbus/pages \
  -name '*.pages.jsonl' | wc -l

wc -l data_processed/page_text_v1/operational_airbus/retrieval_manifest.csv

cat data_processed/page_text_v1/operational_airbus/failures.csv
```

Expected document-file count is 1,786. `retrieval_manifest.csv` should have 1,787 lines including the CSV header.

If the run reports OCR-required pages or failures, stop and review those pages/files. Do not silently substitute document-level extracted text, canonical JSON, or hosted OCR output.

## After the page-text gate passes

Build the two retrieval variants from the same page source and the generated `retrieval_manifest.csv`.

### E0 — flat dense-only baseline

```bash
.venv/bin/python -m full_corpus_pipeline.retrieval \
  --page-text-dir data_processed/page_text_v1/operational_airbus/pages \
  --manifest data_processed/page_text_v1/operational_airbus/retrieval_manifest.csv \
  --output-dir data_processed/indexes/e0_flat_dense \
  --chunking flat
```

E0 evaluation must query this index through the dense-only retrieval path. The index implementation may still contain auxiliary sparse files, but they are not used for E0 ranking.

### E4 — proposed section-aware hybrid system

```bash
.venv/bin/python -m full_corpus_pipeline.retrieval \
  --page-text-dir data_processed/page_text_v1/operational_airbus/pages \
  --manifest data_processed/page_text_v1/operational_airbus/retrieval_manifest.csv \
  --output-dir data_processed/indexes/e4_section_hybrid \
  --chunking section
```

E4 uses section-aware chunks, BM25/FTS5 plus local dense retrieval, reciprocal-rank fusion, and reranking as implemented in `full_corpus_pipeline/retrieval.py`.

Do not build E0/E4 until `page_extraction_audit.json` passes the gate above.
