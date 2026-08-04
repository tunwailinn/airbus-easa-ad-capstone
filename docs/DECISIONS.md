# Project Decisions

This log contains stable methodological decisions. Add a dated entry when a decision changes; do not silently rewrite the project boundary.

## Active decisions

| ID | Decision | Reason |
|---|---|---|
| D01 | Project period is 13 July-30 September 2026. | Fixed capstone deadline. |
| D02 | Main corpus is final EU-issued EASA ADs whose approval holder is Airbus S.A.S. | Keeps the study coherent and feasible. |
| D03 | PADs, SIBs, foreign-issued ADs, Airbus Helicopters, Airbus Canada, engines, and other approval holders are excluded. | Prevents scope drift and mixed regulatory populations. |
| D04 | Service Bulletins are references, not primary indexed documents. | Full SB content is outside the available corpus and project boundary. |
| D05 | Raw PDFs are immutable. | Preserves auditability and reproducibility. |
| D06 | Revisions, corrections, emergency issues, and superseded versions are lifecycle states, not disposable duplicates. | They may contain materially different regulatory requirements. |
| D07 | Maintain separate historical and operational corpus views. | Supports traceability while defaulting current queries to the latest verified publication. |
| D08 | Corpus-manifest corrections live in `manual_overrides.csv`; Step 3 annotation corrections live only in the batch `human_review_working/` folder. | Keeps generated manifests reproducible and frozen review queues immutable. |
| D09 | Split by base AD family, never individual PDF. | Prevents revision leakage across train and test data. |
| D10 | The full-corpus extraction object is section-complete: reliable fields are structured and difficult standard sections are preserved as raw text. | Avoids content loss without distorting difficult compliance semantics. |
| D18 | `docs/PDF_TO_GOLD_FRAMEWORK.md` is authoritative for every Step 3 annotation batch and gold release. | Keeps selection, review, approval, validation, and publication gates consistent. |
| D19 | The combined 50-record evidence-bearing release is an immutable audit source; a separate content-only projection is used for v3.1 evaluation. | Preserves audit history without carrying evidence/review metadata into application records. |
| D20 | Frozen selections and review queues are read-only; annotation corrections are made only in `human_review_working/`. | Prevents source, membership, and review-history drift. |
| D21 | Automated extraction or validator success never grants human approval or gold status. | Gold requires explicit independent human review and approval provenance. |
| D22 | New Step 3 releases use `dataset_framework/validate_gold_release.py` and are complete only after Drive readback verifies exact files and the final report. | Makes release validation batch-size-independent and publication auditable. |
| D23 | GitHub versions implementation and audit artifacts; Google Drive retains `corpus_raw`, canonical batch PDFs, page-text derivatives, temporary renders, credentials, and generated handoff archives. | Keeps the repository reproducible and reviewable without duplicating immutable or large Drive-resident data or exposing secrets. |
| D12 | Primary comparison is generic dense-only flat RAG versus the full lifecycle-aware system. | Tests the integrated research contribution directly. |
| D13 | Retrieval uses structured metadata, BM25, dense search, rank fusion, reranking, and lifecycle filtering. | Exact identifiers and semantic questions require complementary retrieval signals. |
| D14 | Answers must cite AD number, source PDF, page, and section from retrieval metadata and must abstain when support is insufficient or conflicting. | QA remains auditable without placing evidence spans in extracted content JSON. |
| D15 | Planned thresholds are goals, not claims. | Academic reporting must include actual measured results, including failures. |
| D24 | Process all 1,809 frozen physical PDF records; hold out five during development, producing a 1,804-record development corpus and 1,809 final corpus after ingestion testing. | Fixes exact record accounting and supports unseen-document evaluation. |
| D25 | The v3.1 extraction benchmark is the content 50-record set with a family-level 30/20 split and seed 42. | Evaluates reliable fields and raw-section preservation intended for full-corpus extraction. |
| D26 | QA v2 contains 50 locked questions, including complex compliance cases; standalone classification and summary benchmarks remain removed. | Tests retrieval-time interpretation while keeping the capstone focused. |
| D27 | Content records are sparse JSON/JSONL; operational metadata and lifecycle state are stored in Parquet sidecars. | Separates AD content from processing and system state. |
| D28 | Full-corpus content extraction uses a versioned deterministic local parser; hosted LLM semantic extraction is not used. | Eliminates batch API cost and preserves raw difficult-section wording for RAG-time interpretation. |
| D29 | Retrieval remains local and hybrid: FTS5/BM25, local embeddings, FAISS, RRF, and reranking. Hosted generation is optional only for QA answers. | Retains exact and semantic search while avoiding hosted corpus-processing cost. |
| D30 | Temporary upload creates an isolated session index; permanent ingestion requires explicit confirmation and updates indexes without retraining. | Demonstrates unseen-document handling safely and reproducibly. |
| D31 | Missing historical revisions will not be acquired for v3; lifecycle claims are limited to the frozen snapshot. | Prevents schedule and scope expansion and avoids overstating historical completeness. |
| D32 | Original PDF chunks—not machine-normalized JSON—are authoritative for compliance timing, conditions, exceptions, intervals, branches, and terminating effects. | Preserves page context and avoids distortion from premature normalization. |
| D33 | Applicability, Definitions, Reason, complete Requirements/Compliance, reference wording, and Remarks are retained in every record when printed; only their difficult semantics remain unnormalized. | Corrects the overly narrow five-section lightweight interpretation without reintroducing hosted semantic extraction. |
| D34 | Section segmentation must remove repeated PDF page furniture but otherwise preserve contiguous printed wording across page breaks; printed header values take precedence over stale manifest fallbacks when directly readable. | Spot checks found that page headers/watermarks, loose heading boundaries, and manifest-date precedence could contaminate or truncate source-faithful content records. |

## Research questions

- RQ1: How accurately can a deterministic local parser extract reliable AD metadata and preserve raw difficult-section boundaries against the cleaned 20-record test set and PDF spot checks?
- RQ2: Does section-aware hybrid retrieval outperform flat dense-only retrieval for the correct AD and original compliance passage?
- RQ3: Can retrieval-time LLM interpretation preserve complex compliance logic from original PDF text?
- RQ4: Can corpus and uploaded-PDF QA provide correct page-cited answers and reliable abstention?
- RQ5: Can unseen PDFs be queried and ingested without retraining or unsafe lifecycle replacement?

## Change record

### 2026-07-30

- Compressed the original longer plan into the 13 July-30 September window.
- Fixed the revised core benchmark at 100 annotated ADs, 150 QA questions, and 30 reference summaries.
- Added optional stretch targets of 200 annotated ADs and 50 reference summaries without changing the locked core test set.
- Retained the full integrated contribution: corpus governance, structured extraction, classification, summarization, version-aware hybrid RAG, and evaluation.
- Made the PDF-to-gold framework authoritative for Step 3.
- Distinguished the 30-record pilot and 50-record combined release from the 100-record core and optional 200-record stretch.
- Fixed the Step 3 release rules: immutable queues, working-folder-only edits, explicit human approval, reusable strict release validation, versioned publication, and Drive readback.
- Fixed the cloud storage boundary: GitHub contains code and audit artifacts, while Google Drive contains the immutable corpus, canonical batch PDFs, and reproducible large derivatives.

### 2026-08-03

- Replaced the planned 100/200-record annotation expansion with full extraction of all 1,809 frozen PDF records.
- Preserved the existing validated 50-record release as an immutable audit source and created a separate sparse content-only projection.
- Froze a 30-development/20-test extraction split and a 50-question QA benchmark.
- Removed standalone classification and reference-summary modules and benchmarks.
- Retained RAG using section-aware hybrid retrieval, page/source citations, temporary uploaded-PDF QA, and confirmed permanent ingestion without retraining.
- Reserved five non-gold PDF families for unseen testing; development count is 1,804 and final count after ingestion is 1,809.
- Limited lifecycle claims to the current snapshot and declined acquisition of missing historical revisions.

### 2026-08-04

- Replaced full structured compliance extraction with a two-layer architecture: lightweight structured catalogue plus original-PDF RAG.
- Limited full-corpus records to identity/publication metadata, raw applicability, family/model tags, high-level action text, publication identifiers, and supersedure wording.
- Moved compliance timing, conditions, exceptions, repetitive intervals, follow-on logic, and terminating effects to retrieval-time interpretation from original PDF passages.
- Versioned the active derived reference as `easa_airbus_ad_lightweight_gold_50_v1` and the QA benchmark as `easa_airbus_ad_qa_50_v2`.
- Preserved the immutable evidence-bearing 50-record audit release and the five-family unseen set unchanged.
- Replaced hosted full-corpus semantic extraction with deterministic local parsing. Parser v1.3.2 completed all 1,804 development records with zero failures, zero duplicate content records, and no hosted calls.
- Corrected the narrow lightweight interpretation: schema 2.1.0 and parser v2.1.3 retain all standard AD information sections, structuring reliable values and preserving difficult sections as raw text. The derived reference is `easa_airbus_ad_content_gold_50_v2` and the previous generated corpus is `data_processed/canonical_content_v2.1.3/`.
- Spot checks of AD 2024-0038, AD 2024-0097R2, and AD 2025-0058R1 found material v2.1.3 boundary defects: wrong issue-date precedence in some records, `Foreign AD` field leakage, repeated EASA page furniture in raw sections, premature section termination on ordinary `compliance` prose, and truncation at Remark `contact:` lines.
- Parser v2.1.4 was introduced to fix those defects, with regression tests for printed date precedence, page-furniture removal, strict heading boundaries, cross-page section continuity, revision-field separation, Remark contact preservation, and appendix exclusion.
- The v2.1.3 generated corpus is therefore stale; the 1,804 development records must be regenerated, re-spot-checked, and re-evaluated before `canonical_content_v2.1.4/` is promoted.
