# E5 Engineering-Aware Retrieval — Methodology v1.0

**Status:** active post-E0/E4 development methodology  
**Date:** 5 August 2026  
**Purpose:** build a materially stronger retrieval and QA system without reusing the frozen QA-v2 benchmark as a tuning set.

## 1. Why E5 exists

The frozen E0/E4 experiment is complete and remains immutable.

Observed QA-v2 retrieval results:

- E0 flat dense-only Recall@5: **0.0000**;
- E4 section-aware hybrid Recall@5: **0.4091**;
- E4 correct-source@5: **0.5000**;
- E4 correct-source+page@5: **0.4091**.

Post-evaluation plumbing diagnostics passed. They also showed:

- E0 dense correct-source@20: **0/44**;
- E4 dense correct-source@20: **0/44**;
- E4 BM25 correct-source+page@20: **40/44 (0.9091)**.

Therefore the E4 improvement is primarily attributable to exact lexical retrieval and section-aware hybrid architecture, while the generic MiniLM dense branch contributes no correct target source within top 20 on QA-v2. The current bottleneck is evidence selection/reranking after a high-recall lexical candidate stage, especially for conditional multi-passage questions.

These findings motivate E5 but **must not be used to retune or overwrite E0/E4**. E5 is a new experiment with a new development set and a new untouched final test.

## 2. E5 research claim

E5 tests the hypothesis that aviation-document retrieval improves when the system treats regulatory identifiers, document identity, section semantics, and multi-passage evidence as first-class engineering signals rather than relying on corpus-wide semantic similarity alone.

The proposed contribution is:

> deterministic document/identifier routing + section-aware within-document retrieval + exact lexical retrieval + stronger local semantic retrieval/reranking + multi-passage evidence assembly + grounded hosted-LLM interpretation.

## 3. Query modes

Every question is routed deterministically before passage retrieval.

### 3.1 Known-document query

Use when exactly one EASA AD identifier is explicitly present.

```text
Question
  ↓
Parse exact AD identifier
  ↓
Resolve exact document/version in corpus metadata
  ↓
Search only chunks belonging to that AD
  ↓
Section-aware passage retrieval
  ↓
Evidence assembly
```

A known-document query must never conduct a corpus-wide dense search first. The user already supplied the document identity.

### 3.2 Multi-document query

Use when two or more AD identifiers are explicitly present.

Retrieve evidence independently inside each referenced AD. Do not merge lifecycle versions or silently replace one AD with another.

### 3.3 Discovery query

Use when no AD identifier is present and the user is asking which AD/document contains a fact.

```text
Question
  ↓
Global sparse + semantic retrieval
  ↓
Document-level candidate aggregation
  ↓
Passage retrieval inside candidate ADs
  ↓
Evidence assembly
```

Discovery questions prevent the benchmark from becoming trivial identifier lookup.

### 3.4 Abstention/conflict query

If the requested fact is unsupported, ambiguous, or depends on evidence outside the indexed AD corpus, the retriever/generator must preserve that uncertainty and allow abstention.

## 4. Deterministic query parsing

The router extracts without an LLM:

- EASA AD numbers and revisions;
- Airbus Service Bulletin-like identifiers when present;
- question intent;
- likely relevant sections.

Primary intents:

- `identity_lifecycle`;
- `applicability`;
- `required_action_compliance`;
- `referenced_publication`;
- `conditional_multi_passage`;
- `general`.

Section preferences are hints, not hard exclusions. For example:

| Intent | Preferred source sections |
|---|---|
| identity/lifecycle | Document, Effective Date, Reason, Supersedure, Remarks |
| applicability | Applicability, Document, Definitions |
| required action/compliance | Required Action(s), Compliance, Definitions, Reason |
| referenced publication | Ref. Publications, Required Action(s), Remarks |
| conditional/multi-passage | Required Action(s), Compliance, Definitions, Applicability, Reason |

## 5. Passage retrieval architecture

### 5.1 Exact-document path

For known-document questions, retrieve only from the resolved AD/version.

Candidate signals to evaluate on the E5 development set:

1. within-document BM25/FTS;
2. section preference score;
3. local dense similarity over that document's chunks;
4. adjacency/continuation expansion around highly ranked compliance passages;
5. local reranking.

The exact document route is deterministic and is not a learned ranking feature.

### 5.2 Discovery path

For identifier-free queries:

1. global BM25;
2. stronger local dense model;
3. document-level aggregation of chunk evidence;
4. shortlist candidate ADs;
5. within-document passage retrieval for shortlisted ADs;
6. reranking and evidence assembly.

This prevents a globally similar generic compliance sentence from being treated as sufficient document identification.

## 6. Candidate local semantic models

E5 development may compare a compact, predeclared set of local semantic models. Final model selection is frozen before the E5 final test is opened.

Primary candidate:

- embedding: `Qwen/Qwen3-Embedding-0.6B`;
- reranker: `Qwen/Qwen3-Reranker-0.6B`.

Reasons:

- 0.6B scale is feasible for local experimental use compared with 4B/8B alternatives;
- 32K context;
- instruction-aware embedding/reranking;
- official Sentence Transformers support for the reranker;
- Apache-2.0 release.

Secondary reranker comparator if runtime permits:

- `BAAI/bge-reranker-v2-m3`.

Do not expand the model search after seeing E5 final-test scores.

## 7. Predeclared E5 ablations

Development questions may be used to compare only the following conceptual stages:

### E5-A — engineering routing + lexical retrieval

- deterministic query mode;
- exact-document routing when AD ID is present;
- within-document BM25;
- section preferences;
- no new dense model;
- no learned reranker.

### E5-B — add multi-passage evidence assembly

E5-A plus:

- adjacent passage/page continuation expansion;
- section-diverse evidence pack;
- preserve multiple compliance/definition passages when required.

### E5-C — add stronger dense retrieval

E5-B plus:

- Qwen3-Embedding-0.6B local dense signal;
- dense signal is supplemental to identifiers/BM25, never a substitute for exact identifier routing.

### E5-D — add stronger local reranker

E5-C plus:

- Qwen3-Reranker-0.6B as the primary reranker candidate;
- optional predeclared comparison with BGE-reranker-v2-m3 if local runtime permits.

The best development configuration becomes the **single frozen E5-final configuration**. No E5-final scores may be used to change routing, models, weights, candidate counts, section rules, adjacency rules, or evidence-pack size.

## 8. E5 benchmark isolation

The frozen QA-v2 benchmark remains E0/E4-only and is never reused for E5 tuning or final claims.

A new benchmark uses **40 entirely new base AD families**:

- 24 development families;
- 16 final-test families;
- family-level separation only;
- all eight QA-v2 target families excluded;
- five frozen unseen-ingestion families remain excluded because they are reserved for a different experiment.

The family selector is deterministic and stratified by publication era.

### 8.1 E5 development questions — 60

| Category | Count |
|---|---:|
| Identity/lifecycle | 8 |
| Applicability | 10 |
| Required action/compliance | 20 |
| Referenced publication | 8 |
| Conditional/multi-passage | 8 |
| Insufficient/conflict/abstention | 6 |
| **Total** | **60** |

Query-mode target:

- known-document: 36;
- discovery: 18;
- abstention/conflict: 6.

### 8.2 E5 untouched final questions — 40

| Category | Count |
|---|---:|
| Identity/lifecycle | 5 |
| Applicability | 7 |
| Required action/compliance | 14 |
| Referenced publication | 5 |
| Conditional/multi-passage | 5 |
| Insufficient/conflict/abstention | 4 |
| **Total** | **40** |

Query-mode target:

- known-document: 24;
- discovery: 12;
- abstention/conflict: 4.

The 40 final questions remain unopened until the E5 configuration and hosted-QA prompt are frozen.

## 9. Question authoring rules

Each question must be source-grounded and human-reviewed against the original PDF/page-text.

Required fields:

- question ID;
- split;
- base AD family;
- target AD number/version when answerable;
- category;
- query mode;
- question text;
- answerable-from-AD boolean;
- reference page(s);
- reference section(s);
- concise reference answer;
- notes for conditions/exceptions/multi-passage dependencies.

Rules:

1. Do not copy QA-v2 questions or paraphrase them onto new ADs mechanically.
2. Do not use E5-final questions during model, threshold, prompt, routing, or candidate selection.
3. Keep all questions from one base AD family in one split.
4. Discovery questions must omit the target AD number from the user-visible question.
5. Compliance questions must preserve exact thresholds, units, branches, exceptions, and timing in the reference answer.
6. Multi-passage questions must identify every reference page required for a complete answer.
7. Abstention questions must define why the indexed AD evidence is insufficient or conflicting.

## 10. E5 retrieval metrics

Report separately for known-document and discovery modes.

Core:

- document-route accuracy;
- correct source@1/5/10;
- correct source+page Recall@1/3/5/10;
- MRR;
- nDCG@5;
- multi-passage coverage;
- abstention-candidate support status.

For known-document queries, passage/page retrieval is the primary metric because the document identity is supplied by the user.

For discovery queries, both document identification and passage retrieval are scored.

## 11. Hosted LLM QA layer

The hosted model is invoked only after retrieval. It is not used for full-corpus extraction or index construction.

Provider interface: OpenAI-compatible/configurable.

Initial fixed hosted model candidate:

```text
provider = deepseek
model = deepseek-v4-pro
```

The implementation must not hard-code provider-specific logic into retrieval.

### 11.1 LLM input

The model receives only:

- system instructions;
- user question;
- selected evidence passages;
- stable evidence IDs.

It does **not** receive hidden benchmark gold answers/pages.

### 11.2 Citation safety

The LLM is not trusted to invent page numbers. It returns evidence IDs; application code resolves evidence IDs to:

- AD number;
- source PDF;
- page range;
- section.

Any citation to an unknown evidence ID is rejected.

### 11.3 Structured output

Minimum schema:

```json
{
  "status": "answer|abstain",
  "answer": "...",
  "conditions": ["..."],
  "compliance_time": ["..."],
  "exceptions": ["..."],
  "evidence_ids": ["E1", "E3"]
}
```

Do not request or store chain-of-thought. Only the final answer and evidence references are retained.

## 12. QA evaluation decomposition

Every final question is classified after scoring as one of:

1. **retrieval failure** — required reference evidence was absent from the evidence pack;
2. **generation failure** — required evidence was supplied, but the LLM answer was wrong/incomplete;
3. **end-to-end success** — answer and citations are correct;
4. **correct abstention**;
5. **unsafe/unsupported answer** — model answered despite insufficient/conflicting evidence.

In addition to end-to-end QA, run an **oracle-evidence generation evaluation** using the same frozen LLM prompt but supplying the human-verified reference passages. This estimates the generation ceiling independently of retrieval quality.

Hosted-QA metrics:

- answer accuracy;
- condition/exception completeness;
- citation correctness;
- citation completeness;
- groundedness/unsupported-claim rate;
- abstention precision/recall;
- supported-subset answer accuracy;
- oracle-evidence answer accuracy.

## 13. Freeze sequence

```text
1. Freeze 40-family E5 benchmark split
2. Author/review 60 development questions
3. Implement E5-A/B/C/D
4. Evaluate/tune only on E5 development
5. Select one E5 configuration
6. Freeze E5 retrieval configuration
7. Freeze hosted QA prompt/model/settings
8. Author/review and lock 40 final questions if not already sealed
9. Open E5 final test once
10. Report without tuning
11. Run temporary-upload + unseen-ingestion experiment separately
```

If final performance is poor, report it. Do not reopen the final set.

## 14. Relationship to E0/E4

E0/E4 remain final historical experiments and are not replaced.

The thesis reports them as the first retrieval study, followed by E5 as a post-error-analysis engineering-aware system evaluated on a fresh benchmark.

This gives a transparent progression:

```text
E0: flat dense baseline
  ↓
E4: first section-aware hybrid system
  ↓
error analysis (no E0/E4 retuning)
  ↓
E5: engineering-aware routed retrieval
  ↓
new development + new untouched final evaluation
  ↓
hosted evidence-grounded QA
```
