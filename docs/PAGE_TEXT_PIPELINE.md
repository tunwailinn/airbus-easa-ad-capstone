# Page-Preserving PDF Text Pipeline

Status: **VERIFIED / INDEX-READY — page-text v1.1**

This stage is separate from deterministic content extraction. It creates the page-addressable original-PDF source layer used by retrieval and citation evaluation.

## Retrieval corpus

Frozen physical snapshot: **1,809 PDFs**.

For development RAG indexing:

- 5 frozen unseen PDFs remain excluded;
- 18 confirmed external/mixed-holder PDFs remain physically preserved but are excluded from the strict Airbus S.A.S. operational view;
- scope unknown: 0;
- verified retrieval corpus: **1,786 PDFs**.

The selection is reconstructed from the corpus manifest, scope audit v1.3, and unseen selection. Never delete PDFs to manufacture this count.

## Native page extraction result

The local page-preserving run completed with:

- selected documents: **1,786**;
- successful documents: **1,786**;
- failures: **0**;
- total pages: **6,002**;
- native weak-page documents: **1**;
- native weak pages: **1**.

The single weak page was **AD 2011-0006, page 3**. Visual review confirmed that it is a graphical Appendix comparing:

- old hydraulic accumulator design: **4 parts / 3 welds**;
- new hydraulic accumulator design: **2 parts / 1 weld**.

The native layer captured only minimal page text, so a narrow source-hash-bound visual-transcription override was applied. Original native text remains preserved in provenance/backups.

Final page-source gate:

- page-text version: **`page-text-v1.1`**;
- visual override count: **1**;
- unresolved weak/OCR documents: **0**;
- unresolved weak/OCR pages: **0**;
- failures: **0**;
- `ready_for_indexing`: **true**.

## Canonical local path

Use:

```text
data_processed/page_text_v1_1/operational_airbus/
```

The former ambiguous folder name:

```text
data_processed/page_text_v1/operational_airbus/
```

is deprecated.

For an existing verified local run, migrate it without re-extracting PDFs:

```bash
mv data_processed/page_text_v1 data_processed/page_text_v1_1
```

Then confirm:

```bash
cat data_processed/page_text_v1_1/operational_airbus/page_extraction_audit.json
```

The audit must say:

```text
page_text_version = page-text-v1.1
ready_for_indexing = true
needs_ocr_document_count = 0
needs_ocr_page_count = 0
failure_count = 0
```

## Files

`data_processed/page_text_v1_1/operational_airbus/` contains:

- `pages/*.pages.jsonl` — one file per scope-approved PDF;
- `retrieval_manifest.csv` — exact 1,786-row E0/E4 manifest;
- `page_manifest.csv` — page/review status by document;
- `failures.csv` — extraction failures;
- `page_extraction_audit.json` — source-layer gate;
- `.native-v1.0.bak` files for reviewed/modified provenance where applicable.

Each retrieval page record preserves source identity, page number, page-text hash, text source/provenance, and review state.

## Retrieval input gate

Do not build an index unless all are true:

- `selected_document_count == 1786`;
- `successful_document_count == 1786`;
- `failure_count == 0`;
- `needs_ocr_document_count == 0`;
- `needs_ocr_page_count == 0`;
- `page_text_version == "page-text-v1.1"`;
- `ready_for_indexing == true`.

The retrieval reader also rechecks page sequence and any stored page-text SHA-256 before accepting pages.

## E0 / E4 build

Use the strict experiment builder:

```bash
.venv/bin/python -m full_corpus_pipeline.build_retrieval_experiments \
  --page-text-root data_processed/page_text_v1_1/operational_airbus \
  --output-root data_processed/indexes/rag_v1 \
  --experiment all
```

The builder requires the real local retrieval dependencies. It does not permit the fallback backends for thesis measurements.

### E0 — flat dense baseline

- flat page chunks;
- 350-token nominal chunk size;
- `sentence-transformers/all-MiniLM-L6-v2`;
- FAISS inner-product index;
- evaluation through dense-only ranking.

### E4 — section-aware hybrid

- section-aware 250–450-token chunks;
- SQLite FTS5/BM25;
- same dense embedding model as E0;
- FAISS;
- reciprocal-rank fusion;
- local cross-encoder reranking;
- metadata/lifecycle filtering when applicable.

Expected outputs:

```text
data_processed/indexes/rag_v1/
├── e0_flat_dense/
│   ├── chunks.jsonl
│   ├── chunk_manifest.parquet
│   ├── dense_embeddings.npy
│   ├── dense.faiss
│   ├── sparse.sqlite
│   ├── index_config.json
│   └── build_report.json
├── e4_section_hybrid/
│   └── ...
└── build_summary.json
```

## After index build

Evaluate both systems on the same locked QA retrieval benchmark:

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_retrieval \
  data_processed/indexes/rag_v1/e0_flat_dense \
  --mode dense \
  --output data_processed/indexes/rag_v1/e0_retrieval_evaluation.json

.venv/bin/python -m full_corpus_pipeline.evaluate_retrieval \
  data_processed/indexes/rag_v1/e4_section_hybrid \
  --mode hybrid \
  --output data_processed/indexes/rag_v1/e4_retrieval_evaluation.json
```

Report Recall@1/3/5, MRR, nDCG@5, correct source retrieval, and correct source/page retrieval before moving to answer-generation evaluation.
