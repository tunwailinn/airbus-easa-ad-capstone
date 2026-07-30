# EASA AD PDF-to-gold framework

Version: 1.0.0  
Applies to: `Capstone_AD_Project` Step 3 annotation batches

## Purpose

This framework defines the controlled process for turning selected EASA AD
PDFs into human-reviewed gold JSON annotations. It records the scripts and
files used in the 30-record pilot and the 20-record extension, separates
reusable infrastructure from batch-specific code, and defines the gates a new
dataset expansion must pass.

A validator can prove structural and evidentiary consistency. It cannot grant
human approval. A record becomes gold only after an independent reviewer has
checked the complete PDF, finalized the annotation, explicitly approved it,
and every release validator passes.

## Non-negotiable rules

1. Treat `corpus_raw` and every frozen selection as read-only.
2. Use the canonical selected PDF, not a similar, superseded, or convenient
   attachment.
3. Freeze source identity before annotation: filename, URL, SHA-256, page
   count, file instance ID, content ID, and normalized-text SHA-256.
4. Review the complete PDF, including tables, appendices, footnotes, diagrams,
   and multi-column text.
5. Every populated safety-relevant value must trace to page-grounded evidence.
6. Keep the review queue immutable. Make corrections only in the working
   folder.
7. Automated extraction and validation do not constitute human review.
8. Do not set `human_confirmed=true`, `gold_record=true`, `approved`, or
   `creation_method=manual` until explicit human approval.
9. Publish a new versioned gold release; never overwrite a previous release.
10. A release is complete only after Drive readback verifies its exact files
    and final validation report.

## Lifecycle and gates

| State | Primary artifact | Entry condition | Exit gate |
|---|---|---|---|
| Selected | `selection/` | Diversity and scope are defined | Frozen membership and source identity |
| Source verified | `source_pdfs/`, `page_text/` | Selection is frozen | PDF hashes, page counts, text cache, and visual review pass |
| Machine first pass | `annotations/extracted_candidates/` | Sources are verified | Populated fields and evidence pass non-strict validation |
| Review pending | `human_review_queue/` | Candidates are validated | Queue membership and hashes are frozen |
| Review in progress | `human_review_working/` | Queue is copied byte-for-byte | Every field, assertion, and evidence span is checked |
| Human approved | approved working JSON | Independent reviewer explicitly approves | Approval provenance and final states are complete |
| Gold validated | versioned `gold/` staging folder | Only approved records are included | All strict release gates return zero errors |
| Gold published | versioned Drive release | Gold validation passed | Drive readback confirms exact membership and report |

The allowed transition is linear:

`selected → source_verified → machine_first_pass → human_review_pending → human_review_in_progress → human_approved → gold_validated → gold_published`

No script may jump directly from machine output to gold.

## Standard batch directory contract

Each expansion must have its own versioned directory:

```text
step3_extension_<count>_v<version>/
├── README.md
├── selection/
│   ├── <batch>_selection.csv
│   ├── <batch>_selection.json
│   ├── selected_sources.sha256
│   └── selection_report.md
├── source_pdfs/
├── page_text/
├── packets/
│   ├── blind/
│   ├── reviewer_qc/
│   └── packet_inventory.json
├── annotations/
│   ├── extracted_candidates/
│   ├── annotator_a/
│   └── annotator_b/                 # only when double annotation is required
├── submitted/                       # frozen independent submissions, if used
├── adjudication/                    # comparisons and decisions, if used
├── human_review_queue/              # immutable after publication
├── human_review_working/            # only editable review surface
├── validation/
└── gold_staging/                    # approved records only; never machine output
```

The final release belongs in a separate versioned location, for example:

```text
gold_releases/easa_airbus_ad_gold_v2/
├── selection.json
├── annotations/
├── validation/final_validation.json
├── annotation_manifest.csv
├── source_manifest.csv
└── RELEASE_NOTES.md
```

## Authoritative schema and guidance

These files define what an annotation means:

| File | Purpose |
|---|---|
| `step2_ad_schema/easa_airbus_ad_annotation.schema.json` | Frozen JSON Schema |
| `step2_ad_schema/annotation_guidelines.md` | Annotation decisions and field interpretation |
| `step2_ad_schema/controlled_vocabularies.json` | Allowed normalized values |
| `step2_ad_schema/blank_ad_annotation.json` | New-record structure |
| `step2_ad_schema/validate_annotations.py` | Schema, semantic, cross-record, and strict approval checks |

Schema or guideline changes require a new version, changelog entry, regression
validation of existing gold, and an explicit migration decision.

## Scripts used and their scope

### Selection and source verification

| Script | Use | Scope |
|---|---|---|
| `step3_extension_20_v1/select_extension.py` | Built and froze the diverse 20-record no-supersedure selection | Batch-specific: list and count are hard-coded |
| `step3_extension_20_v1/retrieve_extension_sources.py` | Retrieved and verified the 20 official PDFs and created page text | Batch wrapper: expected count is 20 |
| `step3_pilot/retrieve_pilot_sources.py` | Hardened reusable downloader, hash verifier, and page-text extractor | Reusable core |
| `step3_extension_20_v1/selection/source_visual_review.md` | Recorded complete-page visual review | Batch audit artifact |
| `step3_extension_20_v1/source_verification_report.json` | Recorded PDF/hash/page verification results | Batch audit artifact |

### Candidate and packet construction

| Script | Use | Scope |
|---|---|---|
| `step3_extension_20_v1/prepare_extension_review_files.py` | Created packets, provenance-prefilled drafts, queue and working copies, and manifests | Batch-specific: count and no-supersedure policy are hard-coded |
| `step3_pilot/prepare_annotation_packets.py` | Built blind packets, reviewer-QC packets, templates, and source checks | Reusable core |
| `step3_extension_20_v1/build_extracted_review_candidates.py` | Populated the 20 first-pass records and evidence spans | Current-batch extractor; contains record-specific parsing and overrides |
| `step3_extension_20_v1/publish_extracted_review_candidates.py` | Copied byte-identical populated candidates to annotator A, queue, and working folders | Batch-specific: expected count is 20 |

The current extraction script is reproducible for the frozen 20 records, but
it is not yet a universal EASA AD parser. For a new batch, preserve its general
parsing rules, isolate any record-specific override in a documented override
table, and regression-test all generated evidence against the new PDFs.

### Optional double-annotation and adjudication path

The 30-record pilot used these when two independent annotation streams were
required:

| Script | Use |
|---|---|
| `step3_pilot/freeze_submission_manifest.py` | Hash and freeze submitted A/B files |
| `step3_pilot/verify_submission_manifest.py` | Prove frozen A/B submissions did not change |
| `step3_pilot/compare_double_annotations.py` | Produce semantic disagreement reports without merging inputs |
| `step3_pilot/build_machine_adjudications.py` | Build transparent adjudication candidates |
| `step3_pilot/audit_machine_adjudications.py` | Audit candidates and decision logs |
| `step3_pilot/assemble_human_review_queue.py` | Assemble the independent human-review queue |

Several of these pilot scripts require exactly 30 records and exactly 10
double annotations. They must be parameterized or wrapped for another batch;
do not silently reuse their defaults.

### Validation and release

| Script | Use | Scope |
|---|---|---|
| `step2_ad_schema/validate_annotations.py` | Non-strict candidate validation and strict approved-record validation | Reusable |
| `step3_pilot/validate_evidence_quotes.py` | Verify quotes, offsets, page hashes, and source IDs against page text | Reusable |
| `step3_pilot/validate_step3_pilot.py` | Final frozen 30-record pilot validator | Pilot only |
| `dataset_framework/validate_gold_release.py` | Strict membership, source, schema, approval, and evidence gate for any versioned release | Reusable |
| `dataset_framework/script_registry.json` | Machine-readable script and artifact registry | Reusable |
| `dataset_framework/BATCH_CHECKLIST.md` | Copyable operational checklist | Reusable |

`validate_step3_pilot.py` must not be used as the final validator for a
20-record extension or a combined 50-record release because it requires
exactly 30 records, a 15+15 cohort split, and at least 10 double annotations.

## End-to-end runbook

The commands below reproduce the current 20-record extension from the project
root.

### 1. Freeze the selected records

```bash
python3 step3_extension_20_v1/select_extension.py
```

Review:

- `selection/extension_selection.json`
- `selection/extension_selection.csv`
- `selection/selection_report.md`
- `selection/selected_sources.sha256`

Do not continue until membership, diversity, duplicate handling, revision
policy, and supersedure policy are correct.

### 2. Retrieve and verify PDFs

```bash
python3 step3_extension_20_v1/retrieve_extension_sources.py
```

Required output:

- one verified PDF per selection row;
- one page-text JSONL file per PDF;
- matching hashes and page counts in `source_verification_report.json`;
- a completed visual-review record for every page.

### 3. Create review packets and draft folders

Run this only when its output folders are empty because it intentionally
refuses to overwrite non-empty review material.

```bash
python3 step3_extension_20_v1/prepare_extension_review_files.py
```

This creates the blind packets, reviewer-QC packets, identity-prefilled
templates, immutable queue, editable working folder, and manifests.

### 4. Build populated first-pass candidates

```bash
python3 step3_extension_20_v1/build_extracted_review_candidates.py
```

The output remains machine-assisted:

- `record_status=first_pass_complete`;
- `creation_method=hybrid`;
- `classification.human_confirmed=false`;
- `benchmark_metadata.gold_record=false`;
- field assertions remain unreviewed.

### 5. Validate candidates before publication

```bash
python3 step2_ad_schema/validate_annotations.py \
  step3_extension_20_v1/annotations/extracted_candidates/*.annotation.json

python3 step3_pilot/validate_evidence_quotes.py \
  step3_extension_20_v1/annotations/extracted_candidates \
  --page-text-dir step3_extension_20_v1/page_text
```

Both commands must exit with status 0.

### 6. Publish queue and working copies

```bash
python3 step3_extension_20_v1/publish_extracted_review_candidates.py
```

Immediately verify that:

- `annotations/annotator_a/`, `human_review_queue/`, and
  `human_review_working/` have identical annotation membership;
- queue and working copies are initially byte-identical;
- the generated manifests contain the expected count and hashes.

After this point:

- `human_review_queue/` is immutable;
- only `human_review_working/` may be edited;
- regeneration must create a new batch version if review has started.

### 7. Independent human review

For every working JSON, the reviewer must:

1. Open the canonical PDF and inspect every page.
2. Verify or correct identity, publication data, applicability, definitions,
   unsafe condition, requirements, compliance rules and limits, exceptions,
   previous-action credit, referenced publications, relationships, contacts,
   and classification.
3. Verify or correct every evidence quote, page number, page hash, and field
   linkage.
4. Resolve every field assertion as `accepted` or `corrected`.
5. Add a human-origin section-completion assertion at each required section
   path.
6. Resolve unclear or conflicting values with rationale and evidence.
7. Add reviewer identity, timestamps, and `reviewed` or `approved` events.
8. Preserve A/B and adjudicator provenance when double annotation is required.

An empty section must be explicitly reviewed and marked
`absent_in_source` or `not_applicable`; it must not be left ambiguous.

### 8. Apply explicit approval state

Only after the reviewer explicitly approves the record:

```text
annotation_metadata.creation_method = "manual"
annotation_metadata.record_status = "approved"
classification.human_confirmed = true
benchmark_metadata.gold_record = true
```

The record must also contain the required reviewer/approver provenance and
approval event. Approval must never be inferred from file location, validator
success, or a request to copy files.

### 9. Validate the approved batch

First run the two reusable validators:

```bash
python3 step2_ad_schema/validate_annotations.py --strict \
  step3_extension_20_v1/human_review_working/*.annotation.json

python3 step3_pilot/validate_evidence_quotes.py \
  step3_extension_20_v1/human_review_working \
  --page-text-dir step3_extension_20_v1/page_text
```

Then run the reusable release gate:

```bash
python3 dataset_framework/validate_gold_release.py \
  step3_extension_20_v1/human_review_working \
  --selection step3_extension_20_v1/selection/extension_selection.json \
  --source-pdf-dir step3_extension_20_v1/source_pdfs \
  --page-text-dir step3_extension_20_v1/page_text \
  --expected-count 20 \
  --report step3_extension_20_v1/validation/final_gold_validation.json
```

All five release gates must pass:

1. selection membership and source identity;
2. source PDF integrity and page-cache coverage;
3. schema and strict semantics;
4. human-review and approval completeness;
5. evidence quote and page-hash validation.

### 10. Publish a versioned gold release

After all validators pass:

1. Create a new versioned gold release directory.
2. Copy only the approved annotation JSON files.
3. Include the exact frozen selection and final validation report.
4. Generate a manifest of annotation SHA-256 values.
5. Upload the complete release to Drive.
6. Read the Drive files back and confirm exact membership, counts, filenames,
   validation status, and representative JSON content.

The queue and working folders remain review/audit artifacts. They are not the
gold release.

## Expanding from 30 to 50 or beyond

A combined release is a new dataset version, not a mutation of the earlier
30-record gold set.

For a combined 50-record release:

1. Create a 50-row frozen release selection equal to the approved 30-record
   selection plus the approved 20-record extension selection.
2. Create combined, read-only source PDF and page-text directories containing
   exactly those 50 sources.
3. Copy the 50 approved annotations into a new gold staging directory.
4. Run `validate_gold_release.py` with `--expected-count 50`.
5. Publish as a new version and retain the previous 30-record release intact.

The same rule applies to every later expansion.

## Handling difficult PDFs

Automatically flag a record for enhanced review when it has any of these
features:

- tables or appendices;
- multi-column or legacy formatting;
- scanned pages or OCR;
- serial-number or part-number lists;
- model-dependent thresholds;
- multiple compliance clocks;
- cross-referenced or terminating requirements;
- revisions, corrections, or supersedure;
- STC or configuration-dependent applicability;
- referenced service information that changes the action scope.

Enhanced review means visual inspection of all affected pages, explicit
table-to-JSON mapping, and a second reviewer or adjudicator when a material
interpretation remains uncertain.

## Versioning and audit requirements

Every batch and release must record:

- batch/release identifier and creation date;
- selection and schema versions;
- source and page-text hashes;
- annotation hashes;
- script versions or Git commit;
- extraction provenance;
- human reviewer and approver provenance;
- validation commands and reports;
- corrections and adjudication decisions;
- Drive folder IDs and readback date.

If a gold record changes, publish a new release version and preserve the old
record and its validation report.

## Current known limitations

1. The 20-record selection, preparation, extraction, and publication scripts
   have hard-coded counts or record-specific rules.
2. The pilot final validator is intentionally tied to the frozen 30-record
   experimental design.
3. Drive synchronization is currently an operational step rather than a
   repository script with API-based atomic replacement.
4. Automated parsing of tables and legacy layouts still requires visual human
   verification.

The reusable release validator added with this framework removes the
pilot-size restriction from the final gate, but future work should parameterize
batch creation through a frozen batch configuration rather than copying and
editing constants.
