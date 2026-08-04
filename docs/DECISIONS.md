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
| D08 | Corpus-manifest corrections live in `manual_overrides.csv`; legacy annotation corrections were made only through their controlled review workflow. | Keeps generated manifests reproducible and frozen review artifacts immutable. |
| D09 | Split by base AD family, never individual PDF. | Prevents revision leakage across development and test data. |
| D10 | The full-corpus extraction object is section-complete: reliable fields are structured and difficult standard sections are preserved as raw text. | Avoids content loss without distorting difficult compliance semantics. |
| D12 | Primary retrieval comparison is generic dense-only flat RAG versus the full lifecycle-aware system. | Tests the integrated research contribution directly. |
| D13 | Retrieval uses structured metadata, BM25, dense search, rank fusion, reranking, and lifecycle filtering. | Exact identifiers and semantic questions require complementary retrieval signals. |
| D14 | Answers must cite AD number, source PDF, page, and section from retrieval metadata and must abstain when support is insufficient or conflicting. | QA remains auditable without placing evidence spans in extracted content JSON. |
| D15 | Planned thresholds are goals, not claims. | Academic reporting must include actual measured results, including failures. |
| D18 | The historical PDF-to-gold framework governs the immutable audit release. | Preserves the provenance rules under which the 50-record gold source was created. |
| D19 | The combined 50-record evidence-bearing release is an immutable audit source; a separate content-only projection is used for v3.1 evaluation. | Preserves audit history without carrying evidence/review metadata into application records. |
| D20 | Frozen selections and review artifacts are read-only. | Prevents source, membership, and review-history drift. |
| D21 | Automated extraction or validator success never grants human approval or gold status. | Gold requires explicit independent human review and approval provenance. |
| D22 | Gold-release publication requires exact membership/provenance validation and Drive readback. | Makes the audit source reproducible and publication auditable. |
| D23 | GitHub versions implementation and audit artifacts; Google Drive/local storage retains raw PDFs, page-text derivatives, and generated large outputs. | Keeps the repository reproducible without duplicating large immutable/generated data. |
| D24 | Process all 1,809 frozen physical PDF records; hold out five during development, producing a 1,804-record development corpus and 1,809 final corpus after ingestion testing. | Fixes exact record accounting and supports unseen-document evaluation. |
| D25 | The nominal v3.1 content benchmark remains the family-level 30/20 split with seed 42. | Preserves the originally frozen split for auditability. |
| D26 | QA v2 contains 50 locked questions, including complex compliance cases; standalone classification and summary benchmarks remain removed. | Tests retrieval-time interpretation while keeping the capstone focused. |
| D27 | Content records are sparse JSON/JSONL; operational metadata and lifecycle state are stored in Parquet sidecars. | Separates AD content from processing and system state. |
| D28 | Full-corpus content extraction uses a versioned deterministic local parser; hosted LLM semantic extraction is not used. | Eliminates batch API cost and preserves raw difficult-section wording for RAG-time interpretation. |
| D29 | Retrieval remains local and hybrid: FTS5/BM25, local embeddings, FAISS, RRF, and reranking. Hosted generation is optional only for QA answers. | Retains exact and semantic search while avoiding hosted corpus-processing cost. |
| D30 | Temporary upload creates an isolated session index; permanent ingestion requires explicit confirmation and updates indexes without retraining. | Demonstrates unseen-document handling safely and reproducibly. |
| D31 | Missing historical revisions will not be acquired for v3; lifecycle claims are limited to the frozen snapshot. | Prevents schedule and scope expansion and avoids overstating historical completeness. |
| D32 | Original PDF chunks—not machine-normalized JSON—are authoritative for compliance timing, conditions, exceptions, intervals, branches, and terminating effects. | Preserves page context and avoids distortion from premature normalization. |
| D33 | Applicability, Definitions, Reason, complete Requirements/Compliance, reference wording, and Remarks are retained in every record when printed; only their difficult semantics remain unnormalized. | Corrects the overly narrow five-section interpretation without reintroducing hosted semantic extraction. |
| D34 | Section segmentation removes repeated PDF page furniture but otherwise preserves contiguous printed wording across page breaks; printed header values take precedence over stale manifest fallbacks when directly readable. | Spot checks found page headers/watermarks, loose heading boundaries, and manifest-date precedence could contaminate or truncate source-faithful records. |
| D35 | Extraction evaluation separates comparable stable metadata, reference/lifecycle identifiers, secondary taxonomy, and raw-section preservation; exact overlap with the semantic content projection is diagnostic only. | The content projection and live parser intentionally represent difficult source material differently, so the old flatten-and-set score penalized correct v3.1 behavior. |
| D36 | AD `2024-0038` is excluded from clean extraction-test scoring because its PDF was used to diagnose and tune parser v2.1.4; the nominal 30/20 split remains frozen, and the primary clean test is reported as n=19. | Preserves methodological honesty after confirmed test leakage without silently substituting a development record or rewriting the frozen split. |

## Research questions

- RQ1: How accurately can a deterministic local parser extract comparable reliable AD metadata and preserve raw difficult-section boundaries against the clean 19-record extraction test plus source-PDF spot checks?
- RQ2: Does section-aware hybrid retrieval outperform flat dense-only retrieval for the correct AD and original compliance passage?
- RQ3: Can retrieval-time LLM interpretation preserve complex compliance logic from original PDF text?
- RQ4: Can corpus and uploaded-PDF QA provide correct page-cited answers and reliable abstention?
- RQ5: Can unseen PDFs be queried and ingested without retraining or unsafe lifecycle replacement?

## Change record

### 2026-07-30

- Compressed the original longer plan into the 13 July-30 September window.
- Established the original evidence-bearing annotation and review framework.
- Fixed controlled source, review, validation, and Drive-readback rules for gold publication.

### 2026-08-03

- Replaced planned annotation expansion with full deterministic extraction of the frozen corpus.
- Preserved the existing validated 50-record release as an immutable audit source and created a separate sparse content-only projection.
- Froze a nominal 30-development/20-test extraction split and a 50-question QA benchmark.
- Removed standalone classification and reference-summary modules and benchmarks.
- Retained RAG with section-aware hybrid retrieval, page/source citations, temporary uploaded-PDF QA, and permanent ingestion without retraining.
- Reserved five non-gold PDF families for unseen testing; development count is 1,804 and final count after ingestion is 1,809.
- Limited lifecycle claims to the current snapshot and declined acquisition of missing historical revisions.

### 2026-08-04

- Replaced full structured compliance extraction with a two-layer architecture: section-complete deterministic content records plus original-PDF RAG.
- Moved compliance timing, conditions, exceptions, repetitive intervals, follow-on logic, and terminating effects to retrieval-time interpretation from original PDF passages.
- Replaced hosted full-corpus semantic extraction with deterministic local parsing.
- Corrected the narrow lightweight interpretation: schema 2.1.0 and parser v2.1.3 retained all standard AD information sections, structuring reliable values and preserving difficult sections as raw text.
- Spot checks of AD 2024-0038, AD 2024-0097R2, and AD 2025-0058R1 found material v2.1.3 defects: wrong issue-date precedence in some records, `Foreign AD` field leakage, repeated EASA page furniture in raw sections, premature section termination on ordinary `compliance` prose, and truncation at Remark `contact:` lines.
- Parser v2.1.4 fixed those defects with regression tests for printed date precedence, page-furniture removal, strict heading boundaries, cross-page section continuity, revision-field separation, Remark contact preservation, and appendix exclusion.
- The 1,804-record v2.1.4 extraction was regenerated locally.
- The first development evaluation showed 100% coverage and schema validity, but exposed that the old evaluator mixed semantic-projection representation differences into the primary F1.
- Evaluator `content-eval-v3.1.2` now reports comparable stable metadata, secondary taxonomy, reference/lifecycle identifiers, and raw-section integrity separately; legacy projection overlap is diagnostic only.
- A development-reference audit was added to verify all 30 development gold references against frozen hashes, human-review provenance, deterministic reprojection, accepted assertions, and evidence integrity without opening clean test labels.
- Confirmed that AD `2024-0038` belongs to the nominal locked test split and had been used during parser tuning. It is therefore disclosed and excluded from the clean primary test result, leaving n=19.
