# Project Status

Last updated: 2 August 2026

This file records confirmed progress. Agents must not infer completion from planned work.

## Current position

- Calendar position: Week 3 of the 13 July-30 September schedule.
- Corpus position: a local full-run snapshot contains 1,809 manifest rows and the expected audit reports; Phase 6.2 lifecycle review and canonical views remain incomplete.
- Step 3 position: the frozen 30-record pilot has approved working records that pass strict Step 2/Step 3 and evidence validation. The separate 20-record batch has source-verified, populated candidates that pass pre-human schema/evidence checks and intentionally remain non-approved and non-gold.
- Immediate Step 3 goal: preserve the 30-record release history, complete explicit independent review of the 20-record batch, publish it through the reusable release gate, and create a new combined 50-record release without modifying the earlier release.

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
- All 20 current candidates pass non-strict schema/semantic and evidence checks while retaining `creation_method=hybrid`, `record_status=first_pass_complete`, `human_confirmed=false`, and `gold_record=false`.

## Not yet complete or not represented by repository-local release artifacts

- Completed human verification of all corpus lifecycle, near-duplicate, metadata-review, and supersedure candidates.
- Applied corpus-manifest decisions in `manual_overrides.csv`.
- Canonical historical and operational corpus files.
- A repository-local versioned 30-record release package containing the exact selection, approved annotations, manifests, release notes, validation report, and Drive readback metadata.
- Explicit independent human review and approval of the 20-record batch.
- Strict reusable release validation and Drive publication/readback for the 20-record batch.
- A new combined 50-record versioned release preserving the earlier 30-record release.
- The final 100-record core, family-level 60/20/20 split, 150-question benchmark, 30 reference summaries, retrieval index, assistant, or final evaluation results.

If any of these outputs exist outside the repository, inspect or import them before updating their status.

## Next actions

1. Preserve or import the validated 30-record release into the versioned `gold_releases/` contract with its exact selection, hashes, final report, release notes, Drive location, and readback date. Do not modify its records.
2. Review and correct each of the 20 Step 3 candidates only in `step3_extension_20_v1/human_review_working/`.
3. Obtain explicit independent approval before setting manual, approved, human-confirmed, or gold state.
4. Run strict schema validation, evidence validation, and `dataset_framework/validate_gold_release.py` against the exact 20-record selection and sources.
5. Publish the approved 20-record batch as a new versioned release and verify it by Drive readback.
6. Create and validate a separate combined 50-record release from the preserved 30 plus approved 20; never overwrite the 30-record release.
7. Select and review the remaining records needed for the fixed 100-AD core, then freeze the family-level 60/20/20 split.
8. Continue Phase 6.2 corpus review in this order:
   - `corpus_summary.json`
   - `processing_and_metadata_review.csv`
   - `duplicate_review.csv`
   - `version_chains.csv`
   - `near_duplicate_candidates.csv`
   - `supersedure_links.csv`
9. Record corpus-manifest decisions only in `manual_overrides.csv`.
10. Generate and validate:
   - `canonical_manifest.parquet`
   - `canonical_historical_documents.parquet`
   - `canonical_operational_documents.parquet`
11. Build 150 evidence-backed questions and 30 human reference summaries in staged batches.
12. Attempt the optional expansion to 200 ADs and 50 summaries only after the fixed 100-record core passes validation.

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

- Confirm or import the exact versioned 30-record Drive release and readback evidence into the repository-local release contract.
- Complete independent review and explicit approval for the separate 20-record Step 3 batch.
- Complete the outstanding Phase 6.2 lifecycle and canonical-corpus review.
- Confirm supervisor approval of the fixed corpus boundary and compressed benchmark size.
- Confirm supervisor approval of the 100-AD core, optional 200-AD extension, 150-question benchmark, and 30-summary core.
- Record any available API/model budget before choosing hosted extraction or generation models.

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
- Updated the existing Drive files in place for the 20 working annotations and `01_build_ad_corpus_manifest.ipynb`; Drive readback file sizes matched the local files for all 21 updates.
- Moved the existing Drive `step3_extension_20_v1/` folder from inside `step3_pilot_v1/` to its documented sibling position under `metadata/`; no source PDF, page-text, queue, or gold content was changed.
- Verified the extension Drive counts: 20 source PDFs, 21 page-text files, 41 packet files recursively, 20 annotation files, 22 working-folder items, 22 immutable queue items, 2 validation reports, and 0 gold files.
- Protected anomaly: the frozen Drive `selection/` folder contains the canonical five selection artifacts plus a later Google Docs conversion also named `selection_report.md`. It was not removed or moved because frozen selections are read-only.
