# Project Status

Last updated: 4 August 2026

This file records only the active v3.1 project state. Superseded annotation-workflow history remains available in Git history and is not part of the current execution path.

## Current position

- Frozen corpus: **1,809 physical PDF records / 1,808 base AD families**.
- Development corpus: **1,804 PDFs**.
- Held-out unseen set: **5 PDFs from 5 distinct families**.
- Methodology: **section-complete deterministic local extraction + original-PDF page-aware RAG**.
- Content schema: **2.1.0**.
- Local parser: **v2.1.4**.
- Hosted semantic extraction: **not used**.
- Immutable audit source: `gold_releases/easa_airbus_ad_gold_v2/` with 50 validated records.
- Content evaluation set: `evaluation_sets/easa_airbus_ad_content_gold_50_v2/`, split 30 development / 20 locked test.
- QA benchmark: `evaluation_sets/easa_airbus_ad_qa_50_v2/`, 50 locked questions.
- Previous generated corpus: `data_processed/canonical_content_v2.1.3/` with 1,804 development records; this output is now **stale and must not be promoted as final** after the v2.1.4 parser fix.
- Next corrected corpus target: `data_processed/canonical_content_v2.1.4/`.

## Completed

### Corpus and reference data

- Frozen 1,809-record corpus inventory established.
- Stable corpus manifest and extracted-text cache retained at:
  - `step3_pilot/source_metadata/corpus_manifest.parquet`
  - `step3_pilot/source_metadata/corpus_extracted_text.parquet`
- Five non-gold PDFs reserved for unseen-document evaluation.

### Human-validated audit source

- `gold_releases/easa_airbus_ad_gold_v2/` contains the preserved 50-record validated audit release.
- The audit release is immutable and is used only to derive/evaluate the active content benchmark and QA references.

### Local extraction

- Deterministic parser v2.1.3 completed a 1,804-record development run with zero schema failures and no hosted LLM/API calls.
- Representative PDF spot checks then found material extraction-boundary defects in v2.1.3.
- Parser v2.1.4 fixes those defects and has regression coverage for:
  - printed `Issued:` date taking precedence over stale manifest metadata;
  - `Foreign AD:` stopping before `Revision:` metadata;
  - repeated `EASA AD No.`, `TE.CAP`, page counters, copyright/footer text, and `SUPERSEDED`/cancellation watermarks being removed before section segmentation;
  - ordinary prose beginning with words such as `compliance` not being mistaken for a new section heading;
  - cross-page Definitions and Required Actions remaining continuous; and
  - Remark contact lines being retained while later appendices are excluded.
- The v2.1.4 logic was checked against source PDFs for AD 2024-0038, AD 2024-0097R2, and AD 2025-0058R1.

The active content contract retains, when printed:

- AD identity and publication metadata;
- applicability and model/family information;
- Definitions;
- Reason / unsafe-condition narrative;
- complete Required Action(s) and Compliance Time(s) wording;
- referenced-publication identifiers and reference wording;
- supersedure/correction/cancellation wording; and
- Remarks, including AMOC/contact text.

### RAG and application implementation

Implemented in `full_corpus_pipeline/`:

- page/section chunking;
- BM25/FTS5 sparse retrieval;
- local dense embeddings and FAISS support;
- reciprocal-rank fusion;
- local reranking;
- lifecycle filtering;
- corpus QA;
- temporary uploaded-document QA;
- permanent ingestion without retraining;
- duplicate and lifecycle safeguards;
- extraction, retrieval, and QA evaluators; and
- Streamlit prototype.

## Not yet complete

- Regeneration of all 1,804 development content records with parser v2.1.4.
- Representative PDF spot checks of the regenerated v2.1.4 corpus.
- Final locked 20-record extraction evaluation on v2.1.4.
- Promotion of `data_processed/canonical_content_v2.1.4/` after validation.
- Page-preserving text generation/mounting for all 1,804 development PDFs.
- Production E0 and E4 indexes.
- Locked retrieval metrics: Recall@1/3/5, MRR, nDCG@5, correct-source/page retrieval.
- Locked QA metrics: answer correctness, citation correctness, condition preservation, abstention, unsupported-claim rate.
- Temporary-document testing on all five unseen PDFs.
- Permanent ingestion of the five unseen PDFs.
- Final 1,809-record corpus after ingestion testing.

## Immediate next actions

1. Run the complete 1,804-record extraction with parser v2.1.4 into a new versioned run; do not overwrite v2.1.3.
2. Spot-check representative regenerated records against source PDFs, including normal, revision, multi-page, appendix-bearing, and older-format ADs.
3. Run the locked extraction evaluation and promote only if it passes.
4. Produce or mount page-preserving text for the 1,804 development PDFs.
5. Build **E0**: flat chunks + dense-only retrieval.
6. Build **E4**: section-aware BM25 + dense/FAISS + RRF + reranking + metadata/lifecycle filtering.
7. Run the locked retrieval and QA evaluation.
8. Test temporary QA on the five held-out PDFs.
9. Permanently ingest those five PDFs and verify the final corpus count is 1,809.

## Current blockers

- The corrected v2.1.4 development corpus must be regenerated and validated before the extraction layer is treated as frozen.
- Page-preserving text for the complete 1,804-document retrieval index must be available locally or mounted from the approved data store.
- Supervisor approval of the v3.1 research boundary should be documented before final thesis claims are frozen.

## Reporting boundary

Do not claim:

- that all 1,809 records contain normalized compliance logic;
- that successful schema validation proves semantic correctness;
- that the frozen snapshot is guaranteed to represent the legally current EASA state; or
- that the prototype determines aircraft-specific compliance.

The original PDF passage remains authoritative for complex compliance interpretation and QA citations.
