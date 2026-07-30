# Project Plan

## Target outcome

By 30 September 2026, deliver a reproducible research prototype and evaluation showing whether lifecycle-aware processing improves structured extraction and evidence-grounded retrieval over a generic flat-chunk, dense-only RAG baseline.

## Work packages

| Phase | Dates | Work | Required output |
|---|---|---|---|
| 6.1 | 13-26 Jul | Build manifest; detect duplicates, revisions, corrections, supersedure candidates, and OCR issues | Manifest, extracted-text cache, audit reports |
| 6.2 | 27 Jul-2 Aug | Review candidates, apply overrides, OCR flagged files, create canonical views | Verified historical and operational corpora |
| 6.3 | 27 Jul-2 Aug | Finalize the schema and PDF-to-gold framework; preserve the validated 30-record pilot; prepare and independently review the separate 20-record batch | Versioned schema, framework, 30-record release evidence, and reviewed 20-record batch |
| 6.4 | 3-16 Aug | Publish a new combined 50-record release; continue to the 100-AD core; freeze family-level splits; expand toward 200 only after core validation | Versioned 50-record checkpoint, core gold dataset, and train/dev/test split |
| 6.5 | 3-9 Aug | Reconstruct headings and sections; create semantic chunks with provenance | Section and chunk datasets |
| 6.6 | 10-23 Aug | Compare rules, zero-shot, and few-shot structured extraction; add validators | Selected extraction pipeline |
| 6.7 | 17-23 Aug | Classify action and compliance characteristics | Classification predictions and metrics |
| 6.8 | 17-30 Aug | Create schema-driven, evidence-grounded summaries | Summary pipeline and 30 references; optional expansion to 50 |
| 6.9 | 24 Aug-6 Sep | Build BM25, dense, hybrid, fusion, reranking, metadata, and lifecycle retrieval | Version-aware retriever |
| 6.10 | 7-13 Sep | Add grounded answers, citations, warnings, confidence, and abstention | End-to-end assistant |
| 6.11 | 14-27 Sep | Evaluate baselines and full system; run ablations and error analysis | Metrics, predictions, statistical and error reports |
| 6.12 | 21-30 Sep | Complete UI, tests, documentation, thesis, presentation, and demo | Final reproducibility and submission package |

## Weekly milestones

| Week | Dates | Milestone |
|---:|---|---|
| 1 | 13-19 Jul | Scope, research questions, methodology, and manifest pilot |
| 2 | 20-26 Jul | Full initial manifest and automatic audit |
| 3 | 27 Jul-2 Aug | Canonical-corpus review, versioned schema/framework, preserved 30-record pilot, and validated 20-record review batch |
| 4 | 3-9 Aug | Independently review the 20-record batch; publish a new combined 50-record release; draft the first 50 questions and section-aware chunks |
| 5 | 10-16 Aug | All 100 core annotations, first 100 questions, adjudication, frozen family splits, extraction baseline |
| 6 | 17-23 Aug | Questions 101-150, 30 summary references, and selected extraction/classification pipeline |
| 7 | 24-30 Aug | Evidence-check and lock 150 QA items and 30 summaries; report retrieval baselines |
| 8 | 31 Aug-6 Sep | Version-aware hybrid retriever v1 |
| 9 | 7-13 Sep | End-to-end grounded assistant v1 |
| 10 | 14-20 Sep | Complete evaluation and archived predictions |
| 11 | 21-27 Sep | Ablations, errors, release candidate, thesis draft |
| Final | 28-30 Sep | Freeze code/data; final thesis, presentation, and demonstration |

## Completion gates

### G1-A: automatic audit

- One unique manifest row and SHA-256 per physical PDF.
- At least 95% of AD numbers parsed automatically, or every failure queued for review.
- Exact duplicate groups and lifecycle candidates generated.
- No source PDF modified.

### G1-B: canonical corpus

- 100% of included files have confirmed AD identity.
- 100% of operational documents have verified lifecycle state.
- No unresolved same-version conflict enters the operational index.
- OCR results preserve readable identifiers, headings, and compliance text.

### G2-G4: schema, gold data, and chunks

- Schema and annotation rules cover repeatable compliance units and evidence.
- Every Step 3 batch follows `docs/PDF_TO_GOLD_FRAMEWORK.md` without skipping lifecycle gates.
- Frozen selections and review queues remain read-only; only working copies are edited.
- Automated validation is never treated as human approval.
- Every gold record passes schema validation and human review.
- Every release passes strict schema, evidence, and `dataset_framework/validate_gold_release.py` gates.
- Every release is published under a new version and passes exact Drive readback.
- The 30-record release remains unchanged when the separate 20-record batch is combined into a new 50-record release.
- The 100-AD core is complete before optional expansion starts.
- All versions of an AD family stay in one split.
- Every chunk retains file ID, AD/version, section, page range, and lifecycle metadata.

### G5-G10: system and evaluation

- Extraction outputs are schema-constrained and evidence-linked.
- Version selection occurs before answer generation.
- Answers cite evidence and abstain on insufficient or conflicting support.
- Baselines, full system, and selected ablations run on the locked test set.
- Predictions, configurations, prompts, and metrics are archived.

### G11: final package

- Fresh-environment reproduction succeeds.
- Thesis reports actual outcomes and limitations.
- Demo shows current and historical queries, citations, lifecycle warnings, and abstention.

## Planned success thresholds

| Area | Target |
|---|---:|
| Confirmed AD identity in included corpus | 100% |
| Verified lifecycle state in operational corpus | 100% |
| Gold records passing schema validation | 100% |
| Extraction schema-valid output | >= 98% |
| Core-field extraction macro F1 | >= 0.85 |
| Compliance-unit tuple F1 | >= 0.80 |
| Classification macro F1 | >= 0.85 |
| Retrieval Recall@5 | >= 0.90 |
| Retrieval MRR | >= 0.80 |
| Latest-version selection accuracy | >= 0.98 |
| Citation correctness | >= 0.95 |
| Evidence faithfulness | >= 0.95 |
| Unsupported-claim rate | <= 0.05 |

These are goals, not results. Report the measured values without hiding missed targets.

## Control routine

- Monday: define one measurable weekly deliverable.
- Wednesday: review a small sample and record blockers.
- Friday: test, commit or archive outputs, update `docs/PROJECT_STATUS.md`, and update the technical diary.
- Supervisor review: demonstrate artifacts and error cases, not only progress descriptions.
- Never tune against the locked test benchmark after Week 7.
- For every Step 3 release, archive the selection, source/page/annotation hashes, reviewer provenance, validation commands and reports, release notes, Drive location, and readback date.
