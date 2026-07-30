# Step 3 final-gold validation

`validate_step3_pilot.py` is the final checklist for the adjudicated 30-record
pilot. It does not replace or relax Step 2: it runs the Step 2 JSON Schema,
strict semantic checks, and corpus-level checks before applying the additional
Step 3 gates.

Before human approval, run it on the assembled review queue and classify the
expected failure report. The queue is ready for review only when the blocker
summarizer reports zero fixable pre-human blockers:

```bash
python step3_pilot/validate_step3_pilot.py \
  step3_pilot/human_review_queue \
  --report step3_pilot/validation/human_review_queue_strict_blockers.json

python step3_pilot/summarize_strict_blockers.py
```

After human review, run the final gate only on the 30 approved files in
`gold/`, not the separate Annotator A and Annotator B submissions or the
pre-human queue:

```bash
python step3_pilot/validate_step3_pilot.py \
  step3_pilot/gold \
  --report step3_pilot/validation/final_validation.json
```

In Google Colab, install `jsonschema` before running the validator, as already
required by the Step 2 package.

## Section-completion assertions

The final annotation needs an accepted or corrected, human-origin
`field_assertion` at each exact path below:

- `/ad_identity`
- `/publication`
- `/applicability_groups`
- `/definitions`
- `/unsafe_condition`
- `/requirements`
- `/exceptions`
- `/previous_action_credit`
- `/referenced_publications`
- `/relationships`
- `/amoc_and_contacts`
- `/classification`

Use `value_state=present` plus evidence for a populated section. Use
`absent_in_source` or `not_applicable` for an intentionally empty section.
These markers distinguish an empty reviewed section from work that was skipped.

Populated `publication.type_model_designations` and `publication.tcds_numbers`
also require their own reviewed evidence assertion because those normalized
arrays do not carry `evidence_ids` directly in schema version 1.0.0.

## Review-trail requirements

Every final record must be `approved`, manually annotated, human-confirmed, and
set `benchmark_metadata.gold_record=true`. All field assertions must be
accepted or corrected.

For every record, the final metadata must include:

- Annotator A with start/submission timestamps and a `submitted` event
- An independent reviewer, adjudicator, or domain approver
- The existing Step 2 approval event

For the ten rows marked `double_annotation=true` in the frozen selection, it
must additionally include:

- A distinct Annotator B with timestamps and a `submitted` event
- A distinct adjudicator
- An `adjudicated` event containing the decision rationale

Keep the two independently submitted source annotations and any disagreement
log beside the final record for audit. They are not counted among the 30 final
JSON files.

## Selection gates

The validator requires the exact frozen `pilot_selection.json` membership:

- Exactly 30 final records
- Exactly 15 from 2019–2026 and 15 from 2006–2018
- The selected AD number, base number, logical version, canonical source file,
  source hashes, page count, and near-duplicate cluster must match
- At least ten selection rows must be designated for double annotation

Exit status is `0` only when all Step 2 and Step 3 gates pass, `1` for validation
failures, and `2` for configuration or input-loading errors.
