# Project Decisions

This log contains stable methodological decisions. Add a dated entry when a decision changes; do not silently rewrite the project boundary.

## Active decisions

| ID | Decision | Reason |
|---|---|---|
| D01 | Project period is 13 July-30 September 2026. | Fixed capstone deadline. |
| D02 | Main corpus scope is final EU-issued EASA ADs whose approval holder is Airbus S.A.S., accepting legacy Airbus/Airbus Industrie naming. | Keeps the study coherent and feasible. |
| D03 | PADs, SIBs, foreign-issued ADs, Airbus Helicopters, Airbus Canada, engines, and other approval holders are excluded from the primary research scope. | Prevents scope drift and mixed regulatory populations. |
| D04 | Service Bulletins and other technical publications are references, not primary indexed documents. | Full referenced-publication content is outside the available corpus and project boundary. |
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
| D24 | Keep one generated content record per nominal physical PDF; five PDFs are held out for unseen-document ingestion testing. | Preserves source accounting and supports unseen-document evaluation. |
| D25 | The nominal v3.1 content benchmark remains the family-level 30/20 split with seed 42. | Preserves the originally frozen split for auditability. |
| D26 | QA v2 contains 50 locked questions, including complex compliance cases; standalone classification and summary benchmarks remain removed. | Tests retrieval-time interpretation while keeping the capstone focused. |
| D27 | Content records are sparse JSON/JSONL; operational metadata and lifecycle state are stored in Parquet sidecars. | Separates AD content from processing and system state. |
| D28 | Full-corpus content extraction uses a versioned deterministic local parser; hosted LLM semantic extraction is not used. | Eliminates batch API cost and preserves raw difficult-section wording for RAG-time interpretation. |
| D29 | Retrieval remains local and hybrid: FTS5/BM25, local embeddings, FAISS, RRF, and reranking. Hosted generation is optional only for QA answers. | Retains exact and semantic search while avoiding hosted corpus-processing cost. |
| D30 | Temporary upload creates an isolated session index; permanent ingestion requires explicit confirmation and updates indexes without retraining. | Demonstrates unseen-document handling safely and reproducibly. |
| D31 | Missing historical revisions will not be acquired for v3; lifecycle claims are limited to the frozen snapshot. | Prevents schedule and scope expansion and avoids overstating historical completeness. |
| D32 | Original PDF chunks—not machine-normalized JSON—are authoritative for compliance timing, conditions, exceptions, intervals, branches, and terminating effects. | Preserves page context and avoids distortion from premature normalization. |
| D33 | Applicability, Definitions, Reason, complete Requirements/Compliance, reference wording, and Remarks are retained in every record when printed; only their difficult semantics remain unnormalized. | Corrects the overly narrow lightweight interpretation without reintroducing hosted semantic extraction. |
| D34 | Section segmentation removes repeated PDF page furniture but otherwise preserves contiguous printed wording across page breaks; printed header values take precedence over stale manifest fallbacks when directly readable. | Spot checks found page headers/watermarks, loose heading boundaries, and manifest-date precedence could contaminate or truncate source-faithful records. |
| D35 | Extraction evaluation separates comparable stable metadata, reference/lifecycle identifiers, secondary taxonomy, and raw-section preservation; exact overlap with the semantic content projection is diagnostic only. | The content projection and live parser intentionally represent difficult source material differently. |
| D36 | AD `2024-0038` is excluded from clean extraction-test scoring because its PDF was used to diagnose and tune parser v2.1.4; the nominal 30/20 split remains frozen. | Preserves methodological honesty after confirmed test leakage without silently substituting a development record. |
| D37 | Primary extraction scoring derives project-scope eligibility from reviewed Design Approval Holder metadata; out-of-scope gold members remain immutable audit artifacts but are excluded and reported separately. | The audit release contains development cases `2024-0095` (Airbus Defence and Space) and `2026-0079` (Lufthansa Technik) that do not match the Airbus S.A.S. holder scope; test scope is handled by the same rule. |
| D38 | Malformed or missing machine-extracted holder values are classified as `unknown`, never automatically as out-of-scope. | v2.1.4 showed that Type/Model and long section text could leak into the DAH field; treating those as exclusions would silently shrink the corpus because of a parser defect. |
| D39 | Raw-section presence is evaluated against actual source headings when the document-text cache is available; source containment and page-furniture contamination are the primary raw-section checks. | The semantic gold projection may omit a raw section field or represent it as reviewed units, so it is not a reliable source of raw-section existence. |
| D40 | Detailed applicability models remain a primary comparable structured field; publication-header model expansion and family labels are secondary diagnostics. | Some AD headers print broad family wording while the reviewed gold expands individual models, making exact detailed expansion an unsafe primary requirement. |
| D41 | Parser v2.1.5 is the next active extraction version and was developed only from already-disclosed development evidence plus prior disclosed regression PDFs; the v2.1.4 generated run is stale and must be regenerated rather than edited in place. | Ensures reproducibility, version isolation, and protection of the remaining clean test cases. |

## Research questions

- RQ1: How accurately can a deterministic local parser extract comparable reliable AD metadata and preserve raw difficult-section boundaries on the project-scope-eligible clean extraction test plus source-PDF spot checks?
- RQ2: Does section-aware hybrid retrieval outperform flat dense-only retrieval for the correct AD and original compliance passage?
- RQ3: Can retrieval-time LLM interpretation preserve complex compliance logic from original PDF text?
- RQ4: Can corpus and uploaded-PDF QA provide correct page-cited answers and reliable abstention?
- RQ5: Can unseen PDFs be queried and ingested without retraining or unsafe lifecycle replacement?

## Change record

### 2026-07-30

- Established the project schedule and original evidence-bearing annotation/review framework.
- Fixed controlled source, review, validation, and Drive-readback rules for gold publication.

### 2026-08-03

- Replaced planned annotation expansion with full deterministic extraction of the frozen snapshot.
- Preserved the validated 50-record release as an immutable audit source and created a separate sparse content-only projection.
- Froze a nominal 30-development/20-test extraction split and a 50-question QA benchmark.
- Removed standalone classification and reference-summary modules and benchmarks.
- Retained RAG with section-aware hybrid retrieval, page/source citations, temporary uploaded-PDF QA, and permanent ingestion without retraining.
- Reserved five non-gold PDF families for unseen testing.
- Limited lifecycle claims to the current snapshot and declined acquisition of missing historical revisions.

### 2026-08-04

- Replaced full structured compliance extraction with a two-layer architecture: section-complete deterministic content records plus original-PDF RAG.
- Moved compliance timing, conditions, exceptions, repetitive intervals, follow-on logic, and terminating effects to retrieval-time interpretation from original PDF passages.
- Parser v2.1.4 fixed the first disclosed boundary defects: printed issue-date precedence, `Foreign AD`/Revision separation, repeated page furniture, ordinary `compliance` prose, cross-page continuity, Remark contact retention, and appendix exclusion.
- The nominal 1,804-record v2.1.4 extraction was regenerated locally.
- Evaluator v3.1.4 separated stable metadata, secondary taxonomy, reference/lifecycle identifiers, raw-section integrity, holder-scope exclusions, and test-contamination exclusions; legacy projection overlap became diagnostic only.
- The development-reference audit found zero critical reference-integrity issues and two out-of-scope development members: `2024-0095` and `2026-0079`.
- v2.1.4 development evaluation achieved 100% coverage/schema validity and ~0.945 stable metadata macro F1, but exposed remaining legacy-format defects in DAH extraction, Form 110 furniture, wrapped action headings, subject boundaries, legacy TCDS/reference identifiers, and direct original-issue supersedure.
- The v2.1.4 full-corpus scope audit (`1729 eligible / 59 excluded / 16 unknown`) was declared non-final because many reported exclusions were malformed holder parses rather than genuine external holders.
- Parser v2.1.5 was introduced using eligible development evidence only. It adds legacy Form 110 cleanup, wrapped action heading support, strict DAH/Type-Model boundaries, conservative legacy Airbus holder fallback, complete ATA-subject extraction, France TCDS support, publication-ID-safe model matching, broader deterministic reference-ID extraction, and direct original-issue supersedure recovery.
- Evaluator v3.1.5 classifies malformed holder values as unknown, drives raw-section expectation from source headings, treats raw reference wording as source-scorable, distinguishes uppercase status watermarks from normal supersedure prose, and moves publication-header model expansion to secondary diagnostics.
- The v2.1.4 generated run is stale; the next required run is `local-content-development-1804-v2.1.5` and must pass development/reference/scope gates before clean test evaluation or promotion.
