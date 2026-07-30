# Step 3 human-review checklist

## Before review

- Regenerate the human-review queue and its strict-validator report.
- Run `python3 step3_pilot/summarize_strict_blockers.py`.
- Do not begin approval while the summarizer reports any pre-human blocker.
- Fix missing compliance rules, missing page evidence, unresolved or conflicting
  values, incomplete initial annotation provenance, and any schema, batch, or
  frozen-selection error at the source; then regenerate both reports.

## Review each logical AD publication

- Open the canonical PDF and verify every populated value against the attached
  page evidence; correct the value, evidence span, or both when necessary.
- Accept or correct every field assertion and add the required human
  section-completion assertion for all 12 substantive sections.
- Resolve all `unclear` and `conflicting` values with an adjudicated decision,
  rationale, and evidence.
- Resolve relationship candidates explicitly; an approved record must not keep
  candidate, conflicting, or rejected relationships.
- Add an independent reviewer/approver whose identity is distinct from the
  original annotator.
- For each selected double-annotation record, retain distinct A and B annotator
  provenance plus an adjudicator and an adjudicated event with rationale.

## Finalize the gold record

- Set `annotation_metadata.creation_method` to `manual` only after the human
  review has materially finalized the record.
- Set `classification.human_confirmed` and `benchmark_metadata.gold_record` to
  `true`, set `annotation_metadata.record_status` to `approved`, and add an
  authorized reviewer approval event.
- Run the frozen Step 2 schema/semantic validator, evidence-quote validator, and
  Step 3 strict validator across all 30 records. The final gold pilot is ready
  only when every validator passes with zero errors.
