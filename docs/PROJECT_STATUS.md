# Project Status

Last updated: 4 August 2026

This file records confirmed progress. Agents must not infer completion from planned work.

## Current position

- Calendar position: Week 4 of the 13 July-30 September schedule.
- Corpus position: the frozen snapshot contains exactly 1,809 physical PDF records representing 1,808 base AD families. Five non-gold families are now locked for unseen testing, leaving a 1,804-record development corpus.
- Methodology position: v3.1 uses section-complete content records plus original-PDF RAG. Reliable values are structured; Applicability, Definitions, Reason, complete Requirements/Compliance, reference wording, and Remarks are preserved as raw text. Difficult semantics are interpreted from retrieved PDF passages rather than normalized across all 1,809 records.
- Audit-release position: `gold_releases/easa_airbus_ad_gold_v2/` remains the immutable, published 50-record audit source. It is not used directly by the app or full-corpus extractor.
- Evaluation position: the active `easa_airbus_ad_content_gold_50_v2` projection retains the frozen 30/20 split; the five-PDF unseen set remains unchanged; QA v2 contains 50 questions, including retrieval-time compliance cases.
- Implementation position: content schema 2.1.0, deterministic parser v2.1.3, original-PDF hybrid retrieval, corpus and temporary QA, ingestion safeguards, metric runners, and Streamlit prototype are implemented. The corrected local 1,804-record development extraction is complete.
- Immediate goal: obtain supervisor approval of v3.1, human spot-check the content projection/raw boundaries and QA v2 references, then build the page-aware retrieval indexes.

## Confirmed artifacts

- Exact project plan in Markdown and PDF.
- A local 1,809-row corpus manifest snapshot with stable file IDs, hashes, extracted-text Parquet, duplicate/version/near-duplicate/supersedure reports, and `corpus_summary.json`.
- Versioned Step 2 JSON Schema, annotation guidance, controlled vocabularies, strict/non-strict validation, and regression tests.
- `docs/PDF_TO_GOLD_FRAMEWORK.md` version 1.0.0 and the reusable `dataset_framework/` checklist, registry, and release validator.
- Frozen 30-record Step 3 pilot selection covering 171 pages, with 10 designated double annotations and preserved review/adjudication provenance.
- Thirty local approved working annotations with `creation_method=manual`, `record_status=approved`, `human_confirmed=true`, and `gold_record=true`.
- Current local validation of those 30 records:
  - `step3_pilot/validate_step3_pilot.py step3_pilot/human_review_working`: 30 records, 0 errors;
  - `step3_pilot/validate_evidence_quotes.py step3_pilot/human_review_working`: all 30 pass;
  - `dataset_framework/validate_gold_release.py` against the exact pilot selection, sources, and page text: 30 records, 0 errors;
  - Step 2 tests: 18 pass; and
  - Step 3 tests: 21 pass.
- Frozen 20-record Step 3 selection with verified source PDFs/page text, review packets, immutable queue, editable working copies, and validation reports.
- All 20 extension annotations now retain explicit human-review and approval provenance with `creation_method=manual`, `record_status=approved`, `human_confirmed=true`, `gold_record=true`, and accepted field assertions.
- `step3_extension_20_v1/gold/` contains the frozen 20 approved annotations, exact selection, annotation manifest, release notes, and a final validation report with all five reusable gates passing and zero errors.
- `gold_releases/easa_airbus_ad_gold_v2/` contains a new 50-record combined release: exact merged selection, 50 frozen annotations, annotation/source/page-text manifests, reviewer provenance, release notes, and a final validation report with all five gates passing and zero errors.
- The combined release is published under Drive `metadata/gold_releases/easa_airbus_ad_gold_v2/`; its `annotations/` folder contains exactly the same 50 filenames and byte sizes as the local frozen folder, with no missing or unexpected files. Exact Drive IDs and readback evidence are recorded in `drive_readback.json`.
- `evaluation_sets/easa_airbus_ad_content_gold_50_v2/` contains exactly 50 content JSON records, 50 matching JSONL lines, projection lineage/manifests/report, and the frozen 30-development/20-test split.
- The projection report confirms the same aggregate immutable-source hash before and after projection, zero warnings, zero forbidden keys, and zero schema errors.
- `evaluation_sets/unseen_incoming_5_v1/` contains five locked non-gold source identities from five distinct AD families with no overlap with the cleaned 50.
- `evaluation_sets/easa_airbus_ad_qa_50_v2/` contains exactly 50 locked questions with the required 8/8/16/6/6/6 category distribution. Complex reference answers remain private evaluation data and are not added to content records.
- `full_corpus_pipeline/` contains the v3.1 content schema, projection/split/benchmark validators, deterministic local extractor, PDF/page input, hybrid retrieval, retrieval-time QA, lifecycle, local permanent-ingestion, metric, promotion, and Streamlit modules.
- `data_processed/runs/local-content-development-1804-v2.1.3/` contains the corrected development run: 1,804 individual JSON records, matching JSONL, extraction/lifecycle manifests, zero-row failure report, and run configuration with `hosted_execution=false`.
- `data_processed/canonical_content_v2.1.3/` is the active promoted generated corpus containing 1,804 records and operational sidecars. Earlier lightweight/intermediate runs are superseded but preserved; `data_processed/` remains ignored generated data.

## Not yet complete or not represented by repository-local release artifacts

- Completed human verification of all corpus lifecycle, near-duplicate, metadata-review, and supersedure candidates.
- Applied corpus-manifest decisions in `manual_overrides.csv`.
- Canonical historical and operational corpus files.
- A repository-local versioned 30-record release package containing the exact selection, approved annotations, manifests, release notes, validation report, and Drive readback metadata.
- Drive publication/readback for the validated 20-record release.
- Human spot review of the content projection, raw section boundaries, and QA v2 reference wording/pages.
- Locked-test evaluation of deterministic metadata and raw section boundaries.
- A production page-aware BM25/FAISS index over all 1,804 development PDFs.
- Retrieval, QA, citation, abstention, cost, and latency results.
- Temporary and permanent tests over all five held-out PDFs.
- The final 1,809-record corpus after permanent-ingestion testing.

If any of these outputs exist outside the repository, inspect or import them before updating their status.

## Next actions

1. Obtain supervisor approval of `airbus_easa_ad_project_exact_plan.md` v3.1.
2. Human spot-check the content 50 projection, raw section boundaries, and QA v2 reference answers/pages.
3. Review the completed local pilot and freeze parser v2.1.3.
4. Evaluate deterministic metadata and section boundaries on the locked 20 only when final scoring begins.
5. Build page-aware E0 and E4 indexes and execute locked retrieval/QA evaluation.
6. Test the five temporary uploads, then permanently ingest them and verify the final count of 1,809.

## Evidence required to mark 6.1 complete

- Command/configuration used for the full run.
- `corpus_summary.json`.
- All expected manifest and review files.
- Assertions showing one row per PDF, unique file IDs, and non-empty SHA-256 values.
- Counts of parsing failures, OCR flags, duplicates, conflicts, revision families, and supersedure candidates.
- Test command and passing result.

## Evidence required to mark 6.2 complete

- Completed manual overrides with reviewer and date.
- Resolved or documented identity failures and same-version conflicts.
- Verified version chains and supersedure relationships.
- OCR quality report.
- Reproducibly generated canonical historical and operational views.
- Corpus flow counts explaining every inclusion and exclusion.

## Evidence required for each Step 3 gold release

- Versioned batch/release identifier and creation date.
- Exact frozen selection and canonical source identities.
- Source PDF, page-text, and annotation hashes.
- Explicit reviewer/approver provenance and approval events.
- Strict schema/semantic validation with zero errors.
- Evidence quote/page-hash validation with zero errors.
- `dataset_framework/validate_gold_release.py` report with all five gates passing.
- Versioned gold annotations, manifests, source manifest, and release notes.
- Drive folder identifier and readback date confirming exact files, counts, hashes, and final report.

## Blockers and decisions needed

- Obtain supervisor approval of the v3 two-layer methodology.
- Complete the human spot review of the content/QA v2 evaluation artifacts.
- Mount or generate page-preserving text for the complete 1,804-document index; the existing full-corpus text Parquet is document-level.

## Update template

Append the following after material work:

```markdown
### YYYY-MM-DD - Short milestone

- Changed:
- Evidence/artifacts:
- Verification command and result:
- Remaining issues:
- Next action:
```

## Activity log

### 2026-07-30 - Agent handoff package

- Added repository-level agent context, decisions, schedule, and status files.
- Separated confirmed implementation from unconfirmed full-corpus execution.
- Set the immediate handoff to phases 6.1 and 6.2.
- Verification: `PYTHONPATH=src python -m unittest discover -s tests -v` passed all 6 tests.

### 2026-07-30 - Benchmark revision

- Changed the core benchmark to 100 manually annotated ADs, 150 locked questions, and 30 human reference summaries.
- Added stretch targets of 200 total annotated ADs and 50 total reference summaries.
- Preserved the original locked core test partition if the optional extension is attempted.
- Updated the exact project plan and agent handoff documents; this entry records planning changes, not completed annotation.

### 2026-07-30 - Step 3 framework alignment

- Made `docs/PDF_TO_GOLD_FRAMEWORK.md` authoritative for Step 3 batches and releases.
- Distinguished the 30-record pilot and combined 50-record release from the fixed 100-record core and optional 200-record stretch.
- Recorded the current local 30-record approved/validated state and the 20-record pre-human non-gold state.
- Added the immutable queue, working-folder-only edits, explicit approval, reusable release validation, versioned publication, and Drive readback gates.
- Verification: pilot and reusable release validation each passed 30 records with 0 errors; evidence validation passed all 30; Step 2 tests passed 18; Step 3 tests passed 21.

### 2026-07-30 - Cloud repository package

- Changed: documented the GitHub/Drive storage boundary, corrected the Colab notebook path, removed unsupported CLI instructions, and excluded credentials, raw or canonical PDFs, page-text caches, local renders, scratch folders, and duplicate handoff archives from Git.
- Evidence/artifacts: `docs/CLOUD_WORKFLOW.md`, the root and Step 3 ignore rules, versioned notebooks/scripts/schemas, frozen selections and hashes, source-verification reports, review and adjudication JSON, validation reports, and the 1,809-row manifest snapshot and audit reports.
- Verification command and result: Step 2 unit tests passed 18; Step 3 unit tests passed 21; the pilot validator and reusable 30-record release gate passed with 0 errors; evidence validation passed all 30 pilot records and all 20 extension candidates; non-strict schema validation passed all 20 extension candidates; all versioned JSON and notebooks parsed; Python compilation passed.
- Remaining issues: the 20-record extension remains machine-assisted and non-gold; Phase 6.2 lifecycle review and the repository-local versioned gold-release packages remain incomplete.
- Next action: publish this reviewed package to the private personal GitHub repository, then continue explicit independent review in `step3_extension_20_v1/human_review_working/`.

### 2026-08-02 - Local, GitHub, and Drive synchronization

- Fast-forwarded local `main` from `bf2c8b7` to GitHub `origin/main` at `da89ef5`; the incoming scope was the 20 editable `step3_extension_20_v1/human_review_working/` annotations.
- Revalidated the synchronized working set: all 20 records passed non-strict schema/semantic validation and evidence-quote validation. Strict validation correctly remained blocked because all 20 are still `creation_method=hybrid`, `record_status=first_pass_complete`, `human_confirmed=false`, and `gold_record=false` pending explicit independent approval.
- Updated the existing Drive files in place for the 20 working annotations, `01_build_ad_corpus_manifest.ipynb`, and `step3_pilot/03_build_review_gold_pilot.ipynb`; Drive readback file sizes matched the local files for all 22 updates.
- Moved the existing Drive `step3_extension_20_v1/` folder from inside `step3_pilot_v1/` to its documented sibling position under `metadata/`; no source PDF, page-text, queue, or gold content was changed.
- Verified the extension Drive counts: 20 source PDFs, 21 page-text files, 41 packet files recursively, 20 annotation files, 22 working-folder items, 22 immutable queue items, 2 validation reports, and 0 gold files.
- Protected anomaly: the frozen Drive `selection/` folder contains the canonical five selection artifacts plus a later Google Docs conversion also named `selection_report.md`. It was not removed or moved because frozen selections are read-only.
- The Drive pilot `validation/final_validation.json` and local `validation/human_review_working_final_validation.json` have different names but identical 84-byte validation content (`passed=true`, 30 records, 30 selected, no errors); neither release-evidence file was renamed or overwritten.

### 2026-08-02 - Extension source re-audit batch 1

- Changed: corrected the first five editable extension annotations (`2006-0077` through `2010-0271`) against all 11 pages of their frozen source PDFs. Corrections covered normalized approval-holder values, unsupported/duplicated unsafe-condition content, conditional action separation, nested compliance logic, publication-to-action links, populated exception/credit assertions, Table 1 FIN-to-time mappings, multi-column evidence scope, omitted publications, and A330/A340-specific AFM method mapping.
- Evidence/artifacts: only the five files under `step3_extension_20_v1/human_review_working/` were corrected; frozen sources, page text, selection files, and `human_review_queue/` were unchanged. Machine-audit reviewer events and correction notes were retained without claiming human approval.
- Verification command and result: the five corrected records passed non-strict `step2_ad_schema/validate_annotations.py`; all five passed `step3_pilot/validate_evidence_quotes.py` against the frozen page-text cache; all 20 frozen source PDF SHA-256 checks passed.
- Remaining issues: the five records remain `creation_method=hybrid`, `record_status=first_pass_complete`, `classification.human_confirmed=false`, and `benchmark_metadata.gold_record=false`; batches 2-4 still require correction and independent human approval remains outstanding for all 20.
- Next action: correct batch 2 (`2011-0098`, `2012-0259`, `2013-0011`, `2016-0175`, and `2018-0246`) against their frozen source PDFs, then rerun the same validators.

### 2026-08-02 - Extension source re-audit batch 2

- Changed: reviewed all 17 pages of the five batch 2 canonical PDFs (`2011-0098`, `2012-0259`, `2013-0011`, `2016-0175`, and `2018-0246`) against their editable working annotations. Corrected four working files; `2012-0259` required no change. Corrections covered page-grounded effective-date evidence, an omitted seat-cushion definition, two cited FAA advisory circulars, paragraph (6) atomicity, preserved LH/RH table pairings, preserved affected-to-replacement P/N mappings, separated prohibition branches, removal of a non-evidentiary page-header span, a spurious requirement condition, and the referenced-only relationship to EASA AD 2018-0213.
- Evidence/artifacts: only `2011-0098`, `2013-0011`, `2016-0175`, and `2018-0246` under `step3_extension_20_v1/human_review_working/` were changed. Visual transcriptions were added for the two layout-dependent tables while retaining native-text evidence. All five source PDF SHA-256 values matched the frozen identities stored in their annotations; source PDFs, page text, selection artifacts, and `human_review_queue/` were unchanged.
- Verification command and result: `.venv/bin/python step2_ad_schema/validate_annotations.py <five batch 2 annotation files>` passed all five; `.venv/bin/python step3_pilot/validate_evidence_quotes.py <five batch 2 annotation files> --page-text-dir step3_extension_20_v1/page_text` passed all five.
- Remaining issues: these records remain machine-assisted `first_pass_complete` candidates with unreviewed field assertions; no human approval, strict release validation, gold promotion, or Drive publication/readback was performed. Batches 3-4 still require source re-audit.
- Next action: correct batch 3 (`2019-0188`, `2020-0016`, `2021-0221`, `2021-0286`, and `2022-0058`) against their frozen source PDFs, then rerun the same validators.

### 2026-08-02 - Extension source re-audit batch 3

- Changed: reviewed all 20 pages of the five batch 3 canonical PDFs (`2019-0188`, `2020-0016`, `2021-0221`, `2021-0286`, and `2022-0058`) against their editable working annotations and corrected all five. Corrections covered split TCDS and aircraft-family values, fuller applicability, an omitted AMM method and historical AD reference, separated prohibition branches, exact cited SB revisions, removal of header-only evidence, a placard-installation terminating action, an omitted aeroplane-date definition, and complete Table 1-5 condition/evidence mappings.
- Evidence/artifacts: only the five batch 3 files under `step3_extension_20_v1/human_review_working/` were corrected. Seven focused visual transcriptions preserve the layout-dependent tables in `2021-0221` and `2022-0058`; AMOC/contact spans were narrowed to their actual pages. All five source PDF SHA-256 values matched the frozen identities stored in the annotations; source PDFs, page text, selection artifacts, and `human_review_queue/` were unchanged.
- Verification command and result: `.venv/bin/python step2_ad_schema/validate_annotations.py <five batch 3 annotation files>` passed all five; `.venv/bin/python step3_pilot/validate_evidence_quotes.py <five batch 3 annotation files> --page-text-dir step3_extension_20_v1/page_text` passed all five. A final rerun of both non-strict validators across all 20 working annotations also passed every record.
- Remaining issues: these records remain machine-assisted `first_pass_complete` candidates with `human_confirmed=false` and `gold_record=false`; no independent human approval, strict release validation, gold promotion, or Drive publication/readback was performed. Batch 4 still requires source re-audit.
- Next action: correct batch 4 (`2023-0057`, `2024-0001`, `2025-0138`, `2025-0181`, and `2026-0100`) against their frozen source PDFs, then rerun the same validators.

### 2026-08-02 - Extension source re-audit batch 4

- Changed: reviewed all 18 pages of the five batch 4 canonical PDFs (`2023-0057`, `2024-0001`, `2025-0138`, `2025-0181`, and `2026-0100`) against their editable working annotations and corrected all five. Corrections covered omitted TCDS values and definitions, split installation-prohibition branches, parent compliance context, recording-relief scope, an omitted unsafe-condition cause, affected-part records guidance, aircraft-versus-part applicability separation, duplicate Appendix 1 evidence, omitted service-bulletin references, and AMOC/contact page scope.
- Evidence/artifacts: only the five batch 4 files under `step3_extension_20_v1/human_review_working/` were corrected. The complete 27-row Appendix 1 serial-number list in `2025-0181` was visually checked and retained in one consolidated evidence span. All five source PDF SHA-256 values matched the frozen identities stored in the annotations; source PDFs, page text, selection artifacts, and `human_review_queue/` were unchanged.
- Verification command and result: `.venv/bin/python step2_ad_schema/validate_annotations.py <five batch 4 annotation files>` passed all five; `.venv/bin/python step3_pilot/validate_evidence_quotes.py <five batch 4 annotation files> --page-text-dir step3_extension_20_v1/page_text` passed all five. A final rerun of both non-strict validators across all 20 working annotations passed every record, and `git diff --check` reported no whitespace errors.
- Remaining issues: all four five-record source re-audit batches are complete, but every extension record remains a machine-assisted `first_pass_complete` candidate with unreviewed field assertions, `human_confirmed=false`, and `gold_record=false`. No independent human approval, strict release validation, gold promotion, or Drive publication/readback was performed.
- Next action: complete explicit independent human review of all 20 working annotations, resolve every field assertion and section-completion assertion, then apply approval state only when explicitly authorized and run the strict reusable release gates.

### 2026-08-02 - Extension approval and combined 50-record gold validation

- Changed: recorded the user's explicit approval across all 20 corrected extension working annotations; set manual/approved/human-confirmed/gold state, accepted every field assertion, added human section-completion provenance, finalized six source-grounded relationships, removed one obsolete classification action type, and added the direct publication assertions required by the release gate. The immutable `human_review_queue/` was not changed.
- Evidence/artifacts: froze the approved 20 records in `step3_extension_20_v1/gold/` with selection, annotation manifest, release notes, and final report. Created the new versioned combined release `gold_releases/easa_airbus_ad_gold_v2/` with 30 preserved pilot records plus 20 approved extension records, merged selection, 50 annotation hashes, 50 source identities and hashes, 50 page-text hashes, reviewer provenance, release notes, and final validation report.
- Verification command and result: `.venv/bin/python step2_ad_schema/validate_annotations.py --strict step3_extension_20_v1/human_review_working/*.annotation.json` passed all 20; `.venv/bin/python step3_pilot/validate_evidence_quotes.py step3_extension_20_v1/human_review_working --page-text-dir step3_extension_20_v1/page_text` passed all 20; the reusable release validator passed the frozen 20-record gold directory with 0 errors and the frozen combined 50-record annotations with 0 errors across all five gates.
- Remaining issues: neither local release has been uploaded and read back from Drive, so both are `gold_validated` rather than `gold_published`. The standalone versioned 30-record release package and its Drive readback evidence also remain to be preserved or imported.
- Next action: publish and read back the exact 20-record and combined 50-record release packages without overwriting any earlier release.

### 2026-08-02 - Combined 50-record Drive publication

- Changed: retained all 50 combined gold annotation JSON files in the single local `gold_releases/easa_airbus_ad_gold_v2/annotations/` folder and published them to the single Drive `metadata/gold_releases/easa_airbus_ad_gold_v2/annotations/` folder. The earlier empty extension `gold/` Drive folder and all prior release history were preserved.
- Evidence/artifacts: created the versioned Drive release and annotations folders; added local `drive_readback.json` containing the exact 50 Drive file IDs, names, URLs, and byte-size comparisons; updated release notes and reviewer provenance to `gold_published`.
- Verification command and result: live Drive folder readback returned exactly 50 annotation files; the Drive and local filename sets were identical, and all 50 exposed Drive byte sizes matched the corresponding frozen local annotations. No missing, unexpected, or size-mismatched files were found.
- Remaining issues: Drive listings did not expose content hashes, so readback proves exact name membership and byte-size equality rather than byte-for-byte hash equality. The separate 20-record release and standalone 30-record release package still need their own publication/readback evidence if they are to be represented independently.
- Next action: preserve the combined release unchanged and continue toward the fixed 100-record core.

### 2026-08-03 - Capstone methodology v2 implementation

- Changed: replaced expansion to 100/200 evidence-bearing annotations with sparse extraction of the complete 1,809-PDF frozen snapshot; retained RAG/QA; removed standalone classification and reference-summary benchmarks; added temporary and permanent unseen-PDF workflows without retraining.
- Evidence/artifacts: rewrote `airbus_easa_ad_project_exact_plan.md`; added `full_corpus_pipeline/`; generated the cleaned 50-record content dataset, frozen 30/20 split, five-record unseen set, and locked 50-question QA benchmark; preserved `gold_releases/easa_airbus_ad_gold_v2/` unchanged.
- Verification command and result: `.venv/bin/python -m full_corpus_pipeline.validate_content_dataset evaluation_sets/easa_airbus_ad_content_gold_50_v1 --expected-count 50` passed; `.venv/bin/python -m full_corpus_pipeline.validate_qa_benchmark` passed; `.venv/bin/python -m unittest discover -s full_corpus_pipeline/tests -v` passed 12 tests at this checkpoint; the hosted extractor correctly refused execution without `--execute-hosted`.
- Remaining issues: QA references require human spot review; production dense dependencies are not installed in the current `.venv`; no hosted pilot, paid full extraction, full page-aware index, or final evaluation has run.
- Next action: supervisor approval, human spot review, gateway setup, and 30-document pilot with measured cost.

### 2026-08-04 - Lightweight catalogue and retrieval-time compliance architecture

- Changed: replaced full structured compliance extraction with a two-layer design. Full-corpus records now contain only lightweight catalogue fields; compliance timing, conditions, exceptions, intervals, branches, and terminating effects are interpreted from retrieved original-PDF passages.
- Evidence/artifacts: added schema/projection version 2.0.0; generated `evaluation_sets/easa_airbus_ad_lightweight_gold_50_v1/`; generated `evaluation_sets/easa_airbus_ad_qa_50_v2/`; updated extraction and answer prompts, evaluation paths, Streamlit wording, plan, benchmark, decisions, README, and agent handoff. The prior richer derived dataset is superseded but the immutable audit release remains unchanged.
- Verification command and result: lightweight projection produced 50 schema-valid JSON records and 50 JSONL records; the frozen 30/20 split was reproduced; the existing five-family unseen set was reused without overlap; QA v2 validated exactly 50 questions with the required category counts; `.venv/bin/python -m unittest discover -s full_corpus_pipeline/tests -v` passed 13 tests, including rejection of normalized compliance fields.
- Remaining issues: lightweight and QA v2 records need human spot review; no production original-PDF index or final locked evaluation has run.
- Next action: supervisor approval of v3, human spot review, local extraction error analysis, and page-aware index construction.

### 2026-08-04 - Local 1,804-record lightweight extraction

- Changed: removed hosted LLM extraction from the batch and permanent-ingestion paths; added deterministic parser v1.3.2 for printed AD identity, publication metadata, raw applicability/action sections, publication identifiers, and supersedure wording. Hosted generation remains optional only for QA answers.
- Evidence/artifacts: the 30-development-record pilot completed with 30 successes and zero failures. The final run `data_processed/runs/local-lightweight-development-1804-v1.3.2/` completed all 1,804 development records and was promoted to `data_processed/canonical_lightweight_v1.3.2/`. The five frozen unseen IDs were excluded. All 1,804 records contain identity, publication, applicability, required-action, and referenced-publication sections; 1,447 contain an explicitly detected supersedure section.
- Verification command and result: `.venv/bin/python -m full_corpus_pipeline.extract_corpus --run-id local-lightweight-development-1804-v1.3.2` reported 1,804 requested, 1,804 successes, zero failures, and `hosted_execution=false`; `.venv/bin/python -m full_corpus_pipeline.validate_content_dataset data_processed/runs/local-lightweight-development-1804-v1.3.2 --expected-count 1804` passed; the promoted canonical copy also passed; integrity checks found 1,804 manifest rows, 1,804 lifecycle rows, 1,804 JSONL lines, zero duplicate AD numbers, and zero duplicate content records. Development-only exact scalar scoring produced field F1 0.529; this is retained as an honest diagnostic, not treated as action-quality evidence, because raw sections intentionally differ from split/paraphrased gold actions. All 15 pipeline tests and the QA/content validators passed, Markdown relative-link checking found zero missing links, `git diff --check` passed, and the immutable 50-record audit aggregate remained `4efbc14a7b4b63d4cf50df3dcd559a41f0e9eb85d5df7faf1cd848091209cd32`.
- Remaining issues: development pilot exact field F1 is not a valid end-to-end action-quality measure because raw compliance sections intentionally differ from manually split/paraphrased action units. Metadata and raw-section boundary scoring must be reported separately; the locked 20 has not been inspected or scored. Page-aware retrieval indexes and final QA evaluation remain outstanding.
- Next action: spot-check deterministic metadata/section boundaries, prepare page-preserving full-corpus inputs, and build the E0/E4 retrieval indexes.

### 2026-08-04 - Section-complete extraction correction

- Changed: superseded the overly narrow five-section lightweight output. Content schema 2.1.0 and deterministic parser v2.1.3 now structure reliable header/publication values and preserve raw Applicability, Definitions, Reason, complete Required Action(s) and Compliance Time(s), reference-publication wording, revision/supersedure/correction/cancellation wording, and Remarks. Difficult compliance semantics remain unnormalized, and no hosted LLM is used for extraction.
- Evidence/artifacts: generated `evaluation_sets/easa_airbus_ad_content_gold_50_v2/` with the unchanged frozen 30/20 family split; generated `data_processed/runs/local-content-development-1804-v2.1.3/`; promoted the successful run to `data_processed/canonical_content_v2.1.3/`. Earlier runs were preserved and are superseded.
- Verification command and result: the run reported 1,804 requested, 1,804 successes, zero failures, five held-out records, and `hosted_execution=false`. All 1,804 records contain identity, publication, applicability, Reason, complete requirements/compliance text, parsed and raw referenced-publication content, and Remarks. Definitions were retained in 831 records where the heading was detected; supersedure text was retained in 1,447, with revision and cancellation wording represented separately. Individual JSON and JSONL matched; no duplicate AD/content record was found; all 15 pipeline tests and both run/canonical validators passed. Development-only structured-field F1 was 0.589 and raw difficult-section presence F1 was 0.986; raw boundary completeness still requires PDF inspection rather than semantic exact match. The immutable 50-record audit aggregate remained `4efbc14a7b4b63d4cf50df3dcd559a41f0e9eb85d5df7faf1cd848091209cd32`.
- Remaining issues: raw section boundary quality still requires human PDF spot checks, and the locked 20 has not been used for final scoring. Page-aware retrieval indexes and final QA evaluation remain outstanding.
- Next action: visually spot-check representative raw sections, then build page-aware E0/E4 indexes over the original PDFs.
