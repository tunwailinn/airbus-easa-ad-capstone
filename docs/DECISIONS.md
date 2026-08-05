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
| D37 | Primary extraction scoring derives project-scope eligibility from reviewed Design Approval Holder metadata; out-of-scope gold members remain immutable audit artifacts but are excluded and reported separately. | The audit release contains development cases that do not match the Airbus S.A.S. holder scope; test scope is handled by the same rule. |
| D38 | Malformed or missing machine-extracted holder values are classified as `unknown`, never automatically as out-of-scope. | Parser boundary failures must not silently shrink the corpus. |
| D39 | Raw-section presence is evaluated against actual source headings when the document-text cache is available; source containment and page-furniture contamination are the primary raw-section checks. | The semantic gold projection may omit a raw section field or represent it as reviewed units. |
| D40 | Detailed applicability models remain a primary comparable structured field; publication-header model expansion and family labels are secondary diagnostics. | Some AD headers print broad family wording while reviewed gold expands individual models. |
| D41 | v2.1.5 is retained as successful development evidence, not the final parser freeze. | The raw difficult-section problem was solved but narrow catalogue/scope defects remained. |
| D42 | `content-local-v2.1.6` is the active final parser and is frozen after development hardening. | Prevents locked-test overfitting. |
| D43 | Confirmed external or mixed approval-holder PDFs remain in the immutable physical inventory/content extraction but are excluded from the strict Airbus-only operational view. | Scope filtering must not destroy source accounting or auditability. |
| D44 | Any holder classification that is missing, malformed, or not an accepted Airbus alias/confirmed external holder remains `unknown` until reviewed. | Prevents parser quality from being confused with research-scope membership. |
| D45 | Do not add aggressive publication-reference heuristics merely to raise recall after high precision was achieved; residual recall limitations are reported unless a deterministic source pattern is well supported. | Avoids identifier overfitting. |
| D46 | The development RAG source is the exact 1,786-document strict Airbus-only view, using verified original-PDF page text `page-text-v1.1`; the five unseen PDFs remain excluded. | Ensures the retrieval corpus matches the frozen scope and preserves unseen-document evaluation. |
| D47 | A weak native-text page may enter retrieval only through a versioned, source-hash-bound reviewed derivative that preserves native provenance; the current corpus has one such page, AD `2011-0006` page 3. | Avoids silently treating image-only content as reliable native text while allowing audited retrieval of a meaningful graphical appendix. |
| D48 | Frozen E0 and E4 use the same `sentence-transformers/all-MiniLM-L6-v2` dense model and the same 1,786-document manifest. E0 is flat <=350 deterministic whitespace chunk units and dense-only; E4 is section-aware approximately 250–450 whitespace chunk units with BM25 + dense + FAISS + RRF + cross-encoder reranking and candidate depth 20 per sparse/dense path. | Makes the comparison attributable to retrieval architecture rather than corpus or embedding-model changes. |
| D49 | Frozen thesis E0/E4 measurements must fail rather than silently fall back to hashing embeddings, numpy-only dense indexing, or lexical reranking. Retrieval configuration is frozen before opening locked retrieval scores. | Preserves reproducibility and prevents benchmark-driven tuning or accidental backend substitution. |
| D50 | `rag-index-build-v1.0` and the partial v1.1 workspace are retained only as pre-benchmark implementation artifacts. Final retrieval evaluation requires accepted `rag-index-build-v1.2` under `data_processed/indexes/rag_v1_2/`. | v1.0 exposed mixed chunk counters; v1.1 exposed a real E4 476>450 construction defect; both were corrected before locked retrieval scores were opened. |
| D51 | `rag-index-build-v1.2` is frozen with E0 9,394 chunks (max 350) and E4 12,634 chunks (max 450), both over the same 1,786 documents with the same dense model and FAISS backend. | The reviewed v1.2 build summary passes corpus, backend, and chunk-size gates and is the benchmark-eligible retrieval artifact. |
| D52 | After v1.2 acceptance, locked retrieval results are report-only: do not change chunking, model, candidate depth, fusion, reranker, corpus membership, or lifecycle policy based on observed scores. | Prevents retrieval benchmark overfitting and preserves the pre-score experimental freeze. |
| D53 | `retrieval-eval-v1.3` isolates SentenceTransformer query encoding, FAISS search, and CPU cross-encoder reranking into separate processes on macOS ARM. | Multiple runtime-only attempts showed a native PyTorch/FAISS process conflict; isolation preserves the frozen algorithms while preventing the native crash. |
| D54 | The final frozen retrieval result is E0 Recall@5 **0.0000** versus E4 Recall@5 **0.4091**, with E4 better on 18 paired questions, E0 better on 0, and 26 ties. | The complete v1.3 run is accepted after a post-evaluation plumbing audit verified FAISS row alignment, embedding consistency, and target-document presence. |
| D55 | Attribute the observed E4 gain primarily to the hybrid lexical/section-aware architecture, not to dense MiniLM retrieval. | At candidate depth 20, both E0 dense and E4 dense retrieve the correct source on **0/44** questions, while E4 BM25 retrieves the correct source/page on **40/44 (90.9%)**. |
| D56 | Do not tune the frozen reranker after observing that BM25 candidate recall@20 is 90.9% but final E4 correct-source+page@5 is 40.9%; report this ranking bottleneck as a limitation. | Post-score reranker or fusion changes would invalidate the pre-score retrieval freeze. |
| D57 | Hosted LLMs may be used only for retrieval-time QA interpretation/generation, with page/source citations and abstention; retrieval-induced failures must be separated from generation failures. | A hosted model can reason over supplied evidence but cannot recover authoritative evidence that retrieval failed to include. |

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
- Preserved the validated 50-record release as an immutable audit source and created a separate content-only projection.
- Froze a nominal 30-development/20-test extraction split and a 50-question QA benchmark.
- Removed standalone classification and reference-summary modules and benchmarks.
- Retained RAG with section-aware hybrid retrieval, page/source citations, temporary uploaded-PDF QA, and permanent ingestion without retraining.
- Reserved five non-gold PDF families for unseen testing.
- Limited lifecycle claims to the current snapshot and declined acquisition of missing historical revisions.

### 2026-08-04 / 2026-08-05

- Replaced full structured compliance extraction with a two-layer architecture: section-complete deterministic content records plus original-PDF RAG.
- Final parser v2.1.6 reached 1,804/1,804 development extraction with zero failures and was frozen before clean locked-test scoring.
- Final scope audit resolved the 1,804 development physical records to 1,786 strict Airbus-only eligible, 18 retained external/mixed-holder, and 0 unknown.
- Clean extraction scoring retained the frozen nominal split, excluded two out-of-scope test members and the disclosed `2024-0038` leakage, and reported final 17-record results without further parser tuning.
- Original-PDF page extraction completed over all 1,786 strict-scope development records: 6,002 pages, zero document failures, and one weak native page.
- Visual review of `2011-0006` page 3 confirmed a graphical hydraulic-accumulator design appendix. A source-hash-bound reviewed derivative resolved the only weak page while preserving native provenance, producing `page-text-v1.1` with `ready_for_indexing=true`.
- E0/E4 retrieval configuration was frozen before observing locked retrieval scores, and strict build/evaluation tooling was added to prohibit fallback backends in reported thesis measurements.
- `rag-index-build-v1.0` validated the corpus/model/backend path but was rejected before benchmark because its report mixed chunk counters.
- `rag-index-build-v1.1` built a valid E0 but stopped before E4 indexing when the strict gate found a 476-unit section chunk against the 450 maximum.
- `rag-index-build-v1.2` corrected E4 construction accounting and passed the full pre-benchmark gate: E0 9,394 chunks/max 350, E4 12,634 chunks/max 450, both 1,786 documents, real sentence-transformers + FAISS backends.
- Three macOS ARM runtime attempts exposed a native PyTorch/FAISS coexistence crash; `retrieval-eval-v1.3` solved it through process isolation without changing retrieval algorithms.
- The complete frozen retrieval comparison produced E0 Recall@5 0.0000 and E4 Recall@5 0.4091; E4 was better on 18 paired questions, E0 on 0, with 26 ties.
- Post-evaluation plumbing diagnostics verified FAISS/chunk alignment, fresh-vs-stored embedding consistency, and presence of all target ADs. Both dense branches had 0/44 correct-source recall@20, while E4 BM25 had 40/44 correct-source/page recall@20.
- Retrieval is now closed/frozen. The next stage is hosted-LLM/full-QA evaluation using retrieved original-PDF evidence, with retrieval and generation errors reported separately.
