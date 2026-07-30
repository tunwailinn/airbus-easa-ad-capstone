# Step 3 extension: 20 no-supersedure records

This extension adds diverse coverage without changing the validated 30-record
pilot.

## Workflow

1. Run `select_extension.py` to freeze and validate the 20-record selection.
2. Run `retrieve_extension_sources.py` to retrieve each PDF, verify its frozen
   SHA-256 and page count, and create page-level text for review.
3. Render the verified PDFs for visual source review.
4. Run `prepare_extension_review_files.py` to create the source-review packets,
   immutable identity/provenance-prefilled drafts in `human_review_queue/`, and
   byte-identical editable copies in `human_review_working/`.
5. Run `build_extracted_review_candidates.py` to extract populated
   source-grounded first-pass records, then run
   `publish_extracted_review_candidates.py` to replace the blank drafts.
6. Review and correct every populated field and evidence span only in
   `human_review_working/`; the machine-assisted records are not
   human-confirmed or gold.
7. Validate schema and evidence against the verified PDFs.
8. After explicit human approval, publish a new versioned 50-record gold set
   and update the frozen selection validator for that version.

The original `step3_pilot/gold/` directory and its exactly-30 validator remain
unchanged throughout extension review.
