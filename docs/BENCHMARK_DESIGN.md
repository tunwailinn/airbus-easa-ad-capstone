# Benchmark Design

This file defines the evaluation artifacts for the Airbus EASA AD capstone. It is authoritative for benchmark counts and locking rules; implementation details remain in `PROJECT_PLAN.md`.

## Fixed core and stretch scope

| Artifact | Fixed core | Optional stretch |
|---|---:|---:|
| Manually annotated logical AD versions | 100 | 200 total |
| Evidence-backed QA questions | 150 | No expansion required |
| Human reference summaries | 30 | 50 total |

The fixed core is the capstone commitment. Do not trade core validation, retrieval evaluation, or thesis completion for the stretch targets.

## Step 3 release progression

`PDF_TO_GOLD_FRAMEWORK.md` governs how annotations become gold. Release size and benchmark size are related but distinct:

- the frozen 30-record pilot is the first Step 3 reviewed release;
- the separate 20-record Step 3 batch remains non-gold until explicit human approval and all release gates pass;
- after approval, the 30 and 20 may be combined only as a new versioned 50-record release that preserves the 30-record release; and
- those 50 records are an intermediate checkpoint toward the fixed 100-AD core, not the optional 200-record stretch.

Every Step 3 batch and combined release must use its exact frozen selection, canonical sources, page-text cache, strict schema validation, evidence validation, `dataset_framework/validate_gold_release.py`, and Drive readback. Approved working files are not themselves a published release.

## Gold AD dataset

Core sampling quotas:

| Primary bucket | Count |
|---|---:|
| Ordinary latest ADs | 50 |
| Revisions or corrected issues | 20 |
| Emergency ADs | 10 |
| Superseded or historical versions | 10 |
| OCR-heavy or structurally complex ADs | 10 |
| **Total** | **100** |

Core split:

- 60 training/prompt-development ADs
- 20 development/model-selection ADs
- 20 locked test ADs

All splitting is by `base_ad_number`, never by physical PDF or logical version. The 20 core test ADs remain frozen if the gold set later expands.

Optional extension:

- add 100 newly sampled ADs only after the core passes schema and human-review checks;
- use 70 for training, 10 for development, and 20 for a separately locked extension test;
- publish core-test and extension-test results separately before any pooled analysis.

The phrase “optional extension” in this section means expansion from the completed 100-record core to 200 records. It does not refer to the current 20-record Step 3 batch used to progress from the 30-record pilot toward the 100-record core.

## QA benchmark

Question allocation:

| Question type | Count |
|---|---:|
| Identity and lifecycle status | 25 |
| Aircraft applicability | 25 |
| Required action and compliance time | 40 |
| Referenced publications | 15 |
| Revision or supersedure reasoning | 20 |
| Multi-passage synthesis | 15 |
| Insufficient evidence, conflict, or abstention | 10 |
| **Total** | **150** |

Each QA record must include:

- stable `question_id`;
- question text and acceptable answer variants;
- question type and difficulty;
- expected current/historical query mode;
- supporting AD number and exact version;
- source `file_instance_id`, page, section, and evidence span;
- whether abstention is expected;
- author, reviewer, review date, and adjudication notes; and
- split assignment inherited from the supporting `base_ad_number`.

Do not place near-identical questions about two revisions of the same AD family in different splits. Lock the final benchmark in Week 7 and do not tune prompts, retrieval settings, or thresholds on locked questions.

## Reference-summary benchmark

Use 30 human-written or fully human-verified reference summaries:

| Summary stratum | Count |
|---|---:|
| Ordinary latest ADs | 10 |
| Revised or corrected ADs | 6 |
| Emergency ADs | 4 |
| Superseded or historical ADs | 4 |
| Complex multi-action/compliance ADs | 4 |
| OCR-heavy or structurally difficult ADs | 2 |
| **Total** | **30** |

Thirty summaries are appropriate for this two-month capstone because summary creation requires whole-document synthesis and evidence checking. The 150 QA items provide the broader item-level evaluation. Expand to 50 summaries only after all 30 core references pass review.

Each reference summary must cover, when stated:

1. AD identity and lifecycle status;
2. applicability;
3. unsafe condition and consequence;
4. required actions and methods;
5. initial compliance thresholds;
6. repetitive intervals;
7. terminating actions and exceptions;
8. referenced publications;
9. version or supersedure warnings; and
10. page-level evidence.

## Quality and locking gates

- Every gold record passes JSON Schema validation.
- Every non-derived gold field has evidence.
- All 150 questions receive an independent evidence check.
- All 30 summaries receive an independent critical-fact and citation check.
- At least 20% of gold AD records receive second review or delayed re-annotation.
- Test IDs are frozen before final model comparison.
- Predictions are stored separately from gold labels.
- Any post-lock correction is logged with reason, date, reviewer, and affected results.
- Every gold release is versioned and preserves all earlier releases.
- A release is not complete until Drive readback confirms exact membership, hashes, and the final validation report.

## Required files

- `gold_ad_records_v1.jsonl`
- `dataset_splits_by_family.csv`
- `qa_benchmark_v1.jsonl`
- `reference_summaries_v1.jsonl`
- `annotation_agreement_report.md`
- `benchmark_lock_manifest.json`
