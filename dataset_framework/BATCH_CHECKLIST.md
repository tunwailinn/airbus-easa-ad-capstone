# PDF-to-gold batch checklist

Copy this checklist into every new versioned batch directory and complete it
without skipping gates.

## Batch identity

- [ ] Assign a versioned batch name such as `step3_extension_20_v1`.
- [ ] Record the expected record count.
- [ ] Record the schema and guideline versions.
- [ ] State whether supersedure, revisions, corrections, double annotation, or
      adjudication are in scope.

## Gate 1: freeze selection

- [ ] Select only eligible canonical PDFs.
- [ ] Freeze AD number, logical version, source filename, PDF URL, SHA-256,
      normalized-text SHA-256, file instance ID, content ID, and page count.
- [ ] Record diversity strata and selection rationale.
- [ ] Confirm the new selection does not unintentionally overlap an earlier
      release.

## Gate 2: verify source

- [ ] Retrieve PDFs only from the frozen official source URLs.
- [ ] Verify every PDF SHA-256 and page count.
- [ ] Create one page-text JSONL record per page.
- [ ] Render every PDF and visually inspect all pages, especially tables,
      appendices, multi-column text, scans, and handwritten or graphical text.
- [ ] Keep the upstream `corpus_raw` collection read-only.

## Gate 3: prepare and populate review candidates

- [ ] Create blind and reviewer-QC packets.
- [ ] Create annotation files using the frozen schema/template.
- [ ] Populate all substantive sections from the complete PDF.
- [ ] Create exact page-grounded evidence spans.
- [ ] Run non-strict schema and semantic validation.
- [ ] Run evidence-quote validation.
- [ ] Copy byte-identical files to `human_review_queue/` and
      `human_review_working/`.
- [ ] Do not set `human_confirmed=true`, `gold_record=true`, or `approved`.

## Gate 4: independent human review

- [ ] Edit only `human_review_working/`.
- [ ] Compare every field, requirement, compliance limit, and evidence span
      against the complete canonical PDF.
- [ ] Accept or correct every field assertion.
- [ ] Add a human section-completion assertion for every substantive section.
- [ ] Resolve unclear, conflicting, relationship, revision, and supersedure
      decisions with rationale and evidence.
- [ ] Record reviewer identity, timestamps, and review events.
- [ ] Retain independent A/B submissions and adjudication decisions when the
      selection requires double annotation.

## Gate 5: approval and gold validation

- [ ] Obtain explicit human approval.
- [ ] Set `creation_method=manual`, `record_status=approved`,
      `classification.human_confirmed=true`, and
      `benchmark_metadata.gold_record=true`.
- [ ] Run the strict schema/semantic validator.
- [ ] Run the evidence-quote validator.
- [ ] Run `dataset_framework/validate_gold_release.py` using the exact frozen
      selection, source PDF folder, and page-text folder.
- [ ] Require zero errors from every validator.

## Gate 6: publish and freeze

- [ ] Copy only approved, validated working records into a new versioned
      `gold/` directory.
- [ ] Never overwrite a previous gold release.
- [ ] Save the final validation report, selection, source hashes, page-text
      hashes, annotation hashes, reviewer provenance, and release notes.
- [ ] Read the uploaded files back from Drive and verify membership, counts,
      filenames, and the final validation report.
