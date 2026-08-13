# Layer C Oracle-Evidence Development Evaluation

## Purpose

This document records the development-only oracle/reference-evidence comparison for Layer C. The oracle condition is a diagnostic control: it keeps the hosted-QA model and generation settings unchanged while replacing frozen retrieved evidence with benchmark reference-page evidence for answerable questions. It does not run retrieval and does not expose reference answers to the hosted model.

The final 40-question benchmark remains sealed.

## Frozen QA configuration used

```text
provider: DeepSeek official API
provider adapter: deepseek-direct-v1.1
model: deepseek-v4-pro
thinking: enabled
reasoning_effort: high
max_tokens: 4096
temperature: not used in thinking mode
prompt: e5-hosted-qa-prompt-v1.0-dev
runner: e5-hosted-qa-runner-v1.1
oracle batch runner: e5-layer-c-oracle-development-runner-v1.0
response contract: e5-hosted-qa-contract-v1.0
```

Only the evidence condition changed.

## Oracle run artifact

Run ID:

```text
deepseek-v4-pro-high-oracle-60
```

Recorded oracle evidence-pack SHA-256:

```text
33beaf3b0f6b45be80cf2ef70fc9ac94e1fe593986915c180c3685f494939b32
```

Recorded response SHA-256:

```text
c1757226df9d7793bdce47bba4dd9b68517951d361720c768b58d1665784be75
```

## Automatic results

```text
selected questions: 60
hosted successes: 60
hosted failures: 0
request success rate: 1.0000
answerability/status accuracy: 1.0000
reference-page citation hit rate: 1.0000
target-AD citation hit rate: 1.0000
```

The frozen retrieved-evidence reference-in-top-5 rate reported by the evaluator remains 0.9629629629629629 for the 54 answerable development questions. That number describes the original E5-D retrieval condition, not the oracle evidence itself.

## Semantic comparison with the retrieved-evidence condition

An assistant semantic audit of the 60 oracle responses found no clear answer/reference contradiction in the oracle packet. This is not labelled as human review; the formal human-review CSV remains a separate artifact.

### E5D-017 — evidence-conditioned generation/completeness

Retrieved-evidence run: the model incompletely reproduced the exact A321neo applicability population even though supporting evidence was present in the frozen top five.

Oracle run: the model correctly returned all five models, MSN limit 09287, and production modification 160286.

Interpretation: the model can answer the question correctly when the decisive applicability passage is isolated. The original miss remains a Layer C end-to-end completeness error, but the oracle result suggests context/evidence-selection pressure rather than inability to interpret the applicability statement.

### E5D-030 — confirmed Layer B retrieval failure

Retrieved-evidence run: the target/reference passage for EASA AD 2016-0222 was absent from frozen top-5 evidence and the model answered from another retrieved AD.

Oracle run: with the reference passage supplied, the model correctly identified EASA AD 2016-0222 and preserved the three-month timing rule.

Interpretation: confirmed Layer B candidate-generation/retrieval limitation, not a fundamental Layer C reasoning failure. Do not retune E5-D against this known development miss.

### E5D-045 — confirmed reference-page retrieval miss

Retrieved-evidence run: the correct reference page was outside top five, although other supplied evidence still exposed enough information to identify the Airbus and Rolls-Royce publications.

Oracle run: the model correctly returned Airbus AOT A73P002-21, original issue dated 23 February 2022, and Rolls-Royce Alert NMSB TRENT XWB 73-AK747, original issue dated 22 February 2022.

Interpretation: the oracle result confirms that complete source evidence supports a complete answer. The original E5-D limitation remains a near-boundary ranking miss.

### E5D-056 — abstention variability

Retrieved-evidence run: the prose correctly said that exact repair geometry, fastener sizes, and drawing were not supplied, but the response status was `answered` instead of `insufficient_evidence`.

Oracle development builder policy keeps the original frozen evidence for negative/abstention questions because they intentionally have no answer-bearing reference pages. In the oracle run, E5D-056 returned the correct `insufficient_evidence` status.

Interpretation: because the negative-control evidence was not intentionally improved, this change should not be attributed to oracle evidence. It demonstrates run-to-run hosted-model variability in the answer-state decision. The original E5D-056 result remains a valid Layer C abstention failure and should be reported alongside this stability note.

## Ambiguous discovery questions

### E5D-027

The original retrieved evidence demonstrated that more than one corpus directive genuinely satisfies the 400-FC aft / 800-FC forward wording. The oracle pack is intentionally target-scoped and therefore returns only EASA AD 2012-0274.

This does not remove the previously documented benchmark ambiguity. Oracle evidence cannot be used to prove corpus-wide uniqueness because it excludes competing corpus evidence by design.

### E5D-034

The original retrieved evidence contained multiple lifecycle-related RAT gearbox directives sharing the 6-month / 4,000-FH interval. The oracle pack is target-scoped and therefore returns EASA AD 2020-0009.

This also does not remove the previously documented lifecycle ambiguity. The original first-pass empty-output API failure and the later identical transport retry remain separate technical observations.

## Retrieved vs oracle interpretation

The comparison supports the intended Layer B / Layer C separation:

- E5D-030 is clearly retrieval-caused because oracle evidence restores the correct answer.
- E5D-045 is a reference-page ranking limitation; oracle evidence restores the full publication details.
- E5D-017 shows that correct isolated evidence enables a complete answer, while the real retrieved-evidence condition still exposed a Layer C completeness miss.
- E5D-056 shows that hosted answer-state selection is not perfectly stable across repeated evidence-equivalent conditions.
- E5D-027 and E5D-034 remain benchmark-ambiguity findings and are not erased by target-scoped oracle evidence.

## Configuration selection decision

No development finding justifies post-hoc changes to:

- the frozen E5-D retriever;
- evidence depth;
- the Layer C prompt;
- DeepSeek model selection;
- reasoning effort;
- response schema; or
- citation rules.

The selected Layer C configuration for freezing is therefore the same development configuration used in both retrieved and oracle conditions:

```text
deepseek-v4-pro
thinking enabled
reasoning_effort high
max_tokens 4096
e5-hosted-qa-prompt-v1.0-dev
e5-hosted-qa-contract-v1.0
frozen E5-D top-5 evidence for the real end-to-end path
```

## Freeze gate

The next action is to build and validate `hosted_qa_freeze.json` from the exact code, prompt/schema, evidence-pack, development-run, oracle-run, and retrieval-freeze hashes.

Only after that freeze is committed and validated may the sealed final 40-question benchmark be opened/finalized for one-time evaluation.
