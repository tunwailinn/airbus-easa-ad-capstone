# Step 3 pilot handoff status

Updated: 2026-07-22

## Outcome

The 30-publication pilot is selected, source-verified, machine-annotated,
double-annotated for the designated ten records, reconciled, and ready for an
independent human aviation review. It is not yet a gold-standard dataset.

Gold status and formal baseline scoring remain blocked until a human reviewer
checks every value against the canonical PDFs, resolves any substantive
disagreement, records approval provenance, and passes the strict validator.

## Frozen pilot

- 30 canonical EASA AD PDFs and 171 PDF pages.
- 15 ADs from 2019-2026 and 15 ADs from 2006-2018.
- Every base year from 2006 through 2026 is represented.
- Coverage includes simple, revised, corrected, complex-applicability,
  table-heavy, long, STC-conditioned, and near-duplicate examples.
- The full list and rationale are in `selection/selection_report.md`.

## Completed machine-assisted work

- Annotator A: 30 of 30 submissions.
- Isolated Annotator B stream: 10 of 10 designated submissions.
- Frozen submission manifest: 40 files unchanged; SHA-256
  `cac5f4b4e9485bef99734018f1977d5a0c5ff23bcb60ebed262907535a00acc8`.
- Reconciliation: 10 of 10 machine candidates and decision logs pass the
  adjudication audit.
- Human-review queue: 30 records assembled from 13 original A candidates,
  7 corrected single-review candidates, and 10 reconciled double candidates.
- Step 2 schema/semantic validation: 30 of 30 pass in pre-approval mode.
- Exact evidence quote and page-hash validation: 30 of 30 pass.
- Strict blocker triage: 0 fixable pre-human blockers; 1,544 expected
  human-approval gates remain.
- Offline source verification: 30 PDFs and 171 pages pass.
- Test suite: 21 tests pass.

No frozen A/B submission was changed during reconciliation or queue repair.
All machine-assisted records intentionally retain `creation_method=hybrid`,
`human_confirmed=false`, `gold_record=false`, and non-approved status.

## Human work still required

Follow `HUMAN_REVIEW_CHECKLIST.md`. In summary, an independent reviewer must:

1. Open each canonical PDF and verify or correct every field and evidence span.
2. Accept or correct every field assertion and add all required human section
   completion assertions.
3. Resolve relationship candidates and any real annotation disagreements.
4. Retain distinct A/B/adjudicator provenance for the ten double annotations.
5. Add reviewer identity, timestamps, adjudication rationale, and approval
   events.
6. Only then set manual/approved/human-confirmed/gold state and copy the 30
   approved records to `gold/`.
7. Run `validate_step3_pilot.py` across `gold/`; gold is complete only at zero
   strict errors.

## Extraction benchmark

The leakage-safe regex runner, two LLM prompts, 30-record label-free LLM input
file, and common evaluator are ready. Regex predictions have been generated as
a dry artifact, but no method has been formally scored. The evaluator refuses
to score until the strict 30-record gold gate passes. Zero-shot and
schema-guided API calls also remain unrun.

## Google Colab handoff

The regenerated notebook is `03_build_review_gold_pilot.ipynb`. Extract the
handoff bundle into:

`MyDrive/Capstone_AD_Project/metadata/step3_pilot_v1`

The notebook keeps `corpus_raw` read-only, re-verifies the frozen sources,
checks A/B integrity, rebuilds the human-review queue, runs the pre-human
triage, and blocks baseline scoring until valid gold exists. A T4 GPU is not
needed for review or validation; enable it only if a later local LLM baseline
requires one.
