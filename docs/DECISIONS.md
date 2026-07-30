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
| D10 | Central extraction object is a repeatable compliance unit with page-level evidence. | Preserves the relationship between condition, action, timing, interval, and termination. |
| D11 | Core benchmark size is 100 annotated ADs, 150 locked QA questions, and 30 human reference summaries. | Provides broad retrieval/QA coverage while keeping whole-document summary annotation feasible. |
| D16 | If time remains, expand to 200 annotated ADs and 50 reference summaries only after the core passes validation. | Protects the quality and deadline of the primary benchmark. |
| D17 | The original 20-document core test set remains frozen during any expansion; extension-test results are reported separately before pooling. | Prevents benchmark drift and post-hoc test contamination. |
| D18 | `docs/PDF_TO_GOLD_FRAMEWORK.md` is authoritative for every Step 3 annotation batch and gold release. | Keeps selection, review, approval, validation, and publication gates consistent. |
| D19 | The 30-record pilot and combined 50-record dataset are immutable, versioned interim releases toward the 100-AD core. | Separates release checkpoints from the final benchmark size and preserves audit history. |
| D20 | Frozen selections and review queues are read-only; annotation corrections are made only in `human_review_working/`. | Prevents source, membership, and review-history drift. |
| D21 | Automated extraction or validator success never grants human approval or gold status. | Gold requires explicit independent human review and approval provenance. |
| D22 | New Step 3 releases use `dataset_framework/validate_gold_release.py` and are complete only after Drive readback verifies exact files and the final report. | Makes release validation batch-size-independent and publication auditable. |
| D23 | GitHub versions implementation and audit artifacts; Google Drive retains `corpus_raw`, canonical batch PDFs, page-text derivatives, temporary renders, credentials, and generated handoff archives. | Keeps the repository reproducible and reviewable without duplicating immutable or large Drive-resident data or exposing secrets. |
| D12 | Primary comparison is generic dense-only flat RAG versus the full lifecycle-aware system. | Tests the integrated research contribution directly. |
| D13 | Retrieval uses structured metadata, BM25, dense search, rank fusion, reranking, and lifecycle filtering. | Exact identifiers and semantic questions require complementary retrieval signals. |
| D14 | Answers must cite AD number, version, page, and supporting evidence and must abstain when support is insufficient or conflicting. | Safety-critical answers must be auditable. |
| D15 | Planned thresholds are goals, not claims. | Academic reporting must include actual measured results, including failures. |

## Research questions

- RQ1: How accurately can deterministic parsing and schema-constrained models extract structured maintenance-compliance information?
- RQ2: How much does explicit lifecycle modelling improve current-version selection and reduce stale retrieval?
- RQ3: Does version-aware hybrid retrieval outperform flat dense-only retrieval?
- RQ4: Can evidence-constrained generation provide faithful, page-cited answers and reliable abstention?

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
