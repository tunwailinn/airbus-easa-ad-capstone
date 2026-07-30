# Step 3 annotation packets

`prepare_annotation_packets.py` converts the frozen pilot selection and the
verified per-page JSONL into separate blind, reviewer-QC and annotator working
artifacts. It performs no network access and never writes to `corpus_raw`.

## Before generation

1. Finish and freeze the selection audit. Every selection row must have a
   non-pending `selection_status`.
2. Run `retrieve_pilot_sources.py` successfully so all 30 verified PDFs and
   all 30 per-document `*.pages.jsonl` files exist.
3. Keep the Step 2 blank template unchanged.

The current pending selection can be checked safely without writing any
packets:

```bash
python3 step3_pilot/prepare_annotation_packets.py --audit-only
```

This verifies the 30/10 assignment counts, stable identities, selection
vocabularies, deterministic record construction and blind-packet leak checks.
It also reports how many PDF and page-text inputs are currently available.

After the selection audit is final, generate the artifacts:

```bash
python3 step3_pilot/prepare_annotation_packets.py
```

Existing outputs are never overwritten. The command fails before writing if
any planned packet or annotation filename already exists.

## Outputs

```text
step3_pilot/packets/blind/             30 blind source packets
step3_pilot/packets/reviewer_qc/       30 reviewer-QC packets
step3_pilot/annotations/annotator_a/   30 source/identity-prefilled drafts
step3_pilot/annotations/annotator_b/   10 independent duplicate drafts
step3_pilot/packet_inventory.json      deterministic paths and SHA-256 values
```

Blind packets contain PDF/page provenance and page text. They exclude
selection strata, rationale, near-duplicate cluster labels, supersedure
predictions and all candidate-link fields.

Reviewer-QC packets contain the same source material plus the selection
rationale and candidate relationships. Every candidate is explicitly marked
`candidate_unverified`, `manually_verified=false`, and accompanied by the
rule that it must not enter gold without source-PDF confirmation.

Annotator A and B drafts start from the same untouched baseline and share the
deterministic `adann-<canonical_file_instance_id>` record ID. Keep the two
directories isolated and never validate A and B together as one corpus batch.

## Prefill boundary

The annotation drafts prefill only:

- immutable source identifiers, paths, hashes and page count;
- AD/base number, revision/emergency/correction manifest identity;
- the exact Step 1 `logical_version_key`;
- unassigned benchmark selection metadata.

They remain `draft`, `creation_method=manual`, `human_confirmed=false`,
`gold_record=false`, with empty requirements, applicability, evidence and
relationships. For corrected publications, the normalized manifest date is
present but exact raw wording and page evidence remain intentionally blank;
the annotator must add those before running semantic validation.
