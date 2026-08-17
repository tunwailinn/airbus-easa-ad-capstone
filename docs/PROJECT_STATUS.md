# Project Status

Last updated: 17 August 2026

## Current position

- Frozen physical snapshot: **1,809 PDFs / 1,808 base AD families**.
- Five frozen unseen PDFs are now in the final generalization evaluation.
- Nominal development extraction: **1,804 physical PDFs**.
- Strict Airbus-only operational retrieval view: **1,786 PDFs / 6,002 verified pages**.
- Frozen parser: **`content-local-v2.1.6`**.
- Verified page-text source: **`page-text-v1.1`**.
- Frozen retrieval source: **`rag-index-build-v1.2`**.
- Selected retrieval configuration: **E5-D**.
- Hosted QA: **DeepSeek V4 Pro**, frozen configuration.
- One-time 40-question E5 final benchmark: **complete**.
- Human semantic final result: **38/40 = 95.0%**.
- Final oracle/reference-evidence diagnostic: **complete**, including one separately audited exact transport retry.
- Unseen U0/U1 source validation + non-destructive preparation: **complete**.
- Unseen U2 question authoring: **15 draft questions authored; human review pending**.
- Unseen temporary hosted QA: **not started**.
- Unseen permanent ingestion: **not started**.

Parser, retrieval, hosted-QA configuration, final questions, and the strict primary final result are frozen. Final-test and unseen outcomes must not be used for retuning.

## Layer A — deterministic extraction

**PASS / FROZEN.**

Development:

- requested/successful: **1,804 / 1,804**;
- failures: **0**;
- schema-valid: **100%**;
- primary development count: **28**;
- stable metadata macro F1: **0.9948**;
- applicability-model F1: **0.9929**;
- reference-number F1: **0.8065**;
- superseded-AD-number F1: **1.0000**;
- all five difficult raw-section presence F1 values: **1.0000**;
- source containment: **130/130**;
- detected contamination: **0**.

Clean locked extraction test:

- nominal test: **20**;
- primary clean count: **17** after holder-scope exclusions and disclosed `2024-0038` leakage;
- coverage/schema validity: **1.0000 / 1.0000**;
- stable metadata macro F1: **0.9831**;
- applicability-model F1: **0.9222**;
- reference-number F1: **0.9000**;
- superseded-AD-number F1: **0.6667**;
- all five difficult raw-section presence F1 values: **1.0000**;
- source containment: **74/74**;
- detected contamination: **0**.

These are final extraction outcomes, not tuning targets.

## Strict Airbus operational scope

Scope audit over the 1,804 generated development records:

- **1,786 eligible** for the strict Airbus S.A.S. operational view;
- **18 confirmed external/mixed-holder records** retained in the physical/content inventory;
- **0 unknown**.

## Layer B source layer — verified original-PDF page text

**PASS / FROZEN.**

- selected/successful documents: **1,786 / 1,786**;
- failures: **0**;
- total pages: **6,002**;
- one visually reviewed weak page: **AD 2011-0006, page 3**;
- reviewed visual override count: **1**;
- unresolved weak/OCR documents/pages: **0 / 0**;
- `ready_for_indexing`: **true**.

Canonical source:

```text
data_processed/page_text_v1_1/operational_airbus/
```

## Historical E0/E4 retrieval

E0/E4 are closed/frozen historical experiments under:

```text
data_processed/indexes/rag_v1_2/
```

E0:

- **9,394** flat dense chunks;
- QA-v2 Recall@5: **0.0000**.

E4:

- **12,634** section-aware chunks;
- **2,924** multi-page chunks;
- BM25 + dense + FAISS + RRF + reranker;
- QA-v2 Recall@5: **0.4091**.

Post-evaluation diagnostics showed the E4 gain came primarily from lexical/section-aware retrieval, while the frozen MiniLM dense branch contributed no correct-target top-20 candidates on QA-v2. These results remain historical and are not tuning targets.

## E5 engineering-aware retrieval

E5 uses 24 development families and 16 final-test families, isolated from QA-v2 and the five unseen-document families.

Selected configuration: **E5-D**.

Development result:

- Recall@1: **0.7963**;
- Recall@3: **0.9259**;
- Recall@5: **0.9630**;
- MRR@5: **0.8633**;
- nDCG@5: **0.8884**;
- correct source+page@5: **0.9630**;
- candidate source+page recall@20: **0.9815**;
- known-document Recall@5: **1.0000 (36/36)**;
- discovery Recall@5: **0.8889 (16/18)**;
- routing accuracy: **1.0000**.

Frozen E5-D stack:

- E5-C BM25 + `Qwen/Qwen3-Embedding-0.6B@97b0c61` candidate generation;
- candidate depth: **20**;
- `Qwen/Qwen3-Reranker-0.6B@e61197e` passage reranker;
- final evidence depth: **5**;
- known-document deterministic routing;
- frozen E4 section chunks.

Machine-readable freeze:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/retrieval_freeze.json
```

## Layer C — frozen hosted evidence-grounded QA

Hosted LLM is used only at question-answering time. Extraction and indexing remain deterministic/local.

Frozen generation configuration:

```text
provider: DeepSeek official API
adapter: deepseek-direct-v1.1
model: deepseek-v4-pro
thinking: enabled
reasoning_effort: high
max_tokens: 4096
prompt: e5-hosted-qa-prompt-v1.0-dev
runner: e5-hosted-qa-runner-v1.1
response contract: e5-hosted-qa-contract-v1.0
semantic retry: prohibited
```

The model receives only question text plus stable evidence passages/IDs. Private reference answers and benchmark labels are joined only during offline evaluation.

Hosted-QA freeze:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json
```

## E5 final benchmark — COMPLETE / FROZEN

Final benchmark:

- **40 human-reviewed questions**;
- 36 answerable + 4 abstention/conflict;
- 24 known-document + 12 identifier-free discovery + 4 abstention/conflict;
- final questions SHA-256: `f6b008c1b5d24160cb5718e2d4e91a7e0d323277a531654e4b5c3a33995c9a85`.

### Primary automatic result

- hosted requests: **40/40 successful**;
- answerability/status accuracy: **1.0000**;
- retrieval Recall@1/3/5: **0.8333 / 0.9722 / 0.9722**;
- Recall@5: **35/36 = 97.22%**;
- MRR@5: **0.8981**;
- nDCG@5: **0.9173**;
- correct source+page@5: **0.9722**;
- known-document Recall@5: **24/24 = 100%**;
- discovery Recall@5: **11/12 = 91.67%**;
- reference-page citation hit rate: **0.9722**;
- target-AD citation hit rate: **0.9722**.

### Human semantic result

- semantic passes: **38/40**;
- semantic failures: **2/40**;
- strict end-to-end semantic accuracy: **95.0%**.

**This 38/40 = 95.0% result is authoritative.** Oracle or post-hoc analyses cannot replace it.

Primary failures:

- `E5F-011`: Layer C answer-selection/completeness failure under retrieved evidence;
- `E5F-021`: Layer B retrieval/candidate-generation failure.

Diagnostic-only notes:

- `E5F-015`: primary PASS with a post-hoc lifecycle/benchmark ambiguity note;
- `E5F-030`: primary PASS with a canonical reference-page citation diagnostic.

## Final oracle/reference-evidence diagnostic — COMPLETE

Oracle policy:

- answerable questions receive source chunks from the human-reviewed target AD/reference pages;
- abstention questions retain their exact primary evidence;
- model/prompt/settings remain identical;
- no retrieval rerun or retuning;
- diagnostic only.

Original oracle batch:

- **39/40 successful**;
- one technical/provider failure: `E5F-035` (`DeepSeek JSON Output returned empty final content`);
- answerability/status accuracy on successful requests: **0.9744**;
- reference-page citation hit rate: **1.0000**;
- target-AD citation hit rate: **1.0000**.

Key attribution findings:

- `E5F-021` becomes correct with oracle evidence → **Layer B retrieval failure confirmed**;
- `E5F-011` becomes correct with focused oracle evidence → primary failure is **Layer C evidence-selection/completeness sensitivity**, not inability to reason from the intended evidence;
- `E5F-040` used unchanged negative-control evidence but changed status from `insufficient_evidence` to `answered` while still stating that the requested exact details were unavailable → **Layer C status-calibration/run-to-run variability**.

### Oracle technical retry

A single exact transport retry was performed for `E5F-035` under the predeclared retry policy.

- prompt payload SHA-256: `74ad9826c35d14082c13f15d94a639d017462b0515092c17e0fa4fd42b28892c`;
- exact question/evidence/config preserved;
- retry status: **recovered**;
- recovered answer: semantically correct.

The original 39-success/1-failure batch remains preserved. The retry is a separate audit artifact.

## Unseen-document generalization — ACTIVE

Five non-gold PDFs remain isolated from all development/final benchmark construction at:

```text
evaluation_sets/unseen_incoming_5_v1/
```

Frozen cases:

- `2008-0008` — corrected;
- `2011-0041R1` — revised;
- `2011-0142` — supersedure;
- `2026-0084` — long document;
- `2007-0173` — simple original.

### U0/U1 — COMPLETE

Non-destructive preparation completed successfully:

- source documents: **5/5**;
- exact source-hash matches: **5/5**;
- total pages: **21**;
- deterministic extraction successes: **5/5**;
- schema-valid records: **5/5**;
- parser: `content-local-v2.1.6`;
- inference started: **false**;
- permanent ingestion started: **false**.

Preparation manifest SHA-256:

```text
e3a60433348003b8e238a6704d40ddcd6e389e4f7804df92057f4eec9bbadc05
```

### U2 — DRAFT AUTHORED / HUMAN REVIEW PENDING

A 15-question unseen QA draft has been authored from the source packets:

- exactly **3 questions per PDF**;
- `identity_lifecycle`: 4;
- `applicability`: 3;
- `required_action_compliance`: 3;
- `conditional_multi_passage`: 3;
- `referenced_publication`: 1;
- `insufficient_conflict_abstention`: 1.

Draft question SHA-256:

```text
1d9600dd4379f501d0878adf6ae434076ef47ae0a299ef8be5bdc12cb55fc43b
```

Review state:

- human verified: **0/15**;
- needs human review: **15/15**.

**Do not run unseen hosted QA yet.** The next gate is human review, incorporation of any edits, and a locked unseen-question artifact.

### Remaining unseen sequence

After the unseen question lock:

1. temporary-document retrieval + frozen Layer C QA;
2. offline/human semantic evaluation;
3. permanent ingestion into an isolated evaluation store/index;
4. duplicate/lifecycle/index-update safeguards;
5. post-ingestion QA/citation verification;
6. final unseen-generalization report.

Do not permanently ingest any held-out PDF before its temporary-document QA result is preserved.

## Reporting boundaries

Do not claim that:

- all 1,809 physical PDFs are strict Airbus S.A.S.-holder records;
- the 18 external/mixed-holder records were deleted;
- structured extraction fully normalizes complex compliance logic;
- the nominal 20-record extraction test remained fully unseen after disclosed `2024-0038` leakage;
- the single visual page override is native OCR text;
- the system makes aircraft-specific legal compliance determinations;
- the oracle diagnostic replaces the strict primary final result;
- the unseen 15-question draft is human verified before explicit review and lock.

Original PDF passages remain authoritative for detailed applicability/compliance interpretation and page-cited QA.