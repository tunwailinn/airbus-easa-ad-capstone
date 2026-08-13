# Layer C Development Evaluation Record

## Purpose

This document records the DeepSeek V4 Pro Layer C development evaluation after inference. It preserves the original frozen benchmark and retrieval outputs while documenting hosted-QA behavior, transport failures, post-hoc ambiguity findings, and error attribution.

The 40-question final benchmark remains sealed. Nothing in this document changes E5-D retrieval, development labels, or final-test questions.

## Evaluated configuration

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
batch runner: e5-layer-c-development-runner-v1.1
evidence pack: e5-evidence-pack-v1.0
retrieval: frozen E5-D top 5
```

No prompt, retrieval, model, reasoning-effort, evidence-depth, or benchmark changes were made between the smoke test and the full 60-question development run.

## Smoke test

The 3-question smoke run completed successfully:

- selected questions: 3
- hosted successes: 3
- hosted failures: 0
- answerability/status accuracy: 1.0
- reference-page citation hit rate: 1.0
- target-AD citation hit rate: 1.0

The smoke test was judged technically and semantically adequate to proceed without changing the declared configuration.

## Full development run

The full development run contained 60 frozen questions.

First-pass automatic results:

```text
selected questions: 60
hosted successes: 59
hosted failures: 1
first-pass hosted completion: 59/60 = 98.3%
answerability/status accuracy on successful calls: 0.9830508474576272
reference-page citation hit rate: 0.9811320754716981
target-AD citation hit rate: 0.9811320754716981
```

The single failed request was E5D-034. DeepSeek returned empty final JSON-output content. The failure was classified as a technical/provider output failure rather than a semantic failure.

## Transport-failure recovery

E5D-034 was repeated once with the exact same:

- model;
- prompt;
- thinking mode;
- reasoning effort;
- max-token limit;
- frozen evidence pack; and
- frozen retrieval result.

The retry succeeded with 1/1 hosted response and zero failures. The original 59/60 first-pass run remains unchanged and preserved for audit.

Report both:

```text
first-pass hosted completion: 59/60 = 98.3%
recovered hosted completion after one identical technical retry: 60/60 = 100%
```

The recovered result must not silently replace the original first-pass failure.

## Error attribution

### E5D-017 — Layer C generation error

Question type: applicability / known-document.

Frozen retrieval support was present. The model answered only that A321 aeroplanes were affected and omitted the required exact population:

- A321-251NX;
- A321-252NX;
- A321-253NX;
- A321-271NX;
- A321-272NX;
- all MSNs up to and including 09287; and
- Airbus modification 160286 embodied in production.

Classification: **Layer C generation/completeness failure**.

### E5D-030 — Layer B retrieval error

Question type: required-action/compliance / discovery.

The frozen E5-D top-5 evidence did not contain the target/reference evidence for EASA AD 2016-0222. The supplied evidence instead strongly supported another A320-family AD with a similar three-month timing rule, and the hosted model answered EASA AD 2018-0218.

Classification: **Layer B retrieval failure**. Do not attribute this miss to Layer C generation.

This miss was already known during E5-D retrieval development and must not be used for post-freeze retrieval retuning.

### E5D-056 — Layer C abstention/status error

Question type: insufficient/conflict/abstention.

The hosted prose correctly stated that EASA AD 2011-0176 does not provide exact repair geometry, fastener sizes, or repair drawing and directs the operator to obtain Airbus-approved repair instructions before next flight.

However, the model returned:

```text
status = answered
```

rather than:

```text
status = insufficient_evidence
```

Classification: **Layer C answer-state/abstention failure**. The semantic explanation was useful, but the response-contract decision was wrong.

### E5D-045 — Reference-page retrieval miss with usable answer

Question type: referenced-publication / discovery.

The benchmark reference page was not present in frozen top-5 retrieval. However, the supplied evidence still exposed enough publication identifiers for the hosted model to correctly identify:

- Airbus AOT A73P002-21; and
- Rolls-Royce Alert NMSB TRENT XWB 73-AK747.

The model did not reproduce the reference publication dates, but the literal question asked which publications were referenced.

Classification: **reference-page retrieval miss with usable end-to-end answer**, not a clear Layer C generation failure.

## Post-hoc discovery-question ambiguity audit

The original development benchmark remains frozen and is not edited after seeing hosted-model outputs. Two questions were found to be corpus-wide ambiguous only after auditing the exact frozen evidence supplied to Layer C.

### E5D-027

The question asks which cargo-door directive has aft-door repetitive inspections at intervals not exceeding 400 flight cycles and forward-door inspections at intervals not exceeding 800 flight cycles.

The frozen evidence pack contains passages from both:

- EASA AD 2012-0274; and
- EASA AD 2011-0007R1.

Both passages genuinely contain the same distinctive 400-FC aft / 800-FC forward repetitive interval combination. The hosted answer named both directives and cited evidence for both.

The benchmark reference answer names only EASA AD 2012-0274.

Classification: **benchmark ambiguity / non-unique discovery wording**. Do not count as a Layer C generation failure in ambiguity-adjusted analysis.

### E5D-034

The question asks which A380 ram-air-turbine gearbox directive requires repetitive gearbox-oil detailed inspections at intervals not exceeding 6 months or 4,000 flight hours.

The frozen evidence pack contains relevant passages from multiple lifecycle-related directives, including:

- EASA AD 2020-0009;
- EASA AD 2020-0183; and
- EASA AD 2021-0254.

These directives genuinely share the same distinctive 6-month / 4,000-flight-hour repetitive gearbox-oil DET interval. On the identical retry, the hosted model selected 2021-0254 as the current directive and explicitly noted that 2020-0183 and 2020-0009 contained the same interval.

The benchmark reference answer names only EASA AD 2020-0009.

Classification: **benchmark/lifecycle ambiguity / non-unique discovery wording**. The initial empty-output request remains separately recorded as a technical failure.

## Strict versus ambiguity-adjusted reporting

The benchmark itself is not rewritten. Thesis/reporting should distinguish:

1. the strict frozen-benchmark results;
2. the first-pass hosted completion rate;
3. recovered completion after the one permitted identical technical retry;
4. post-hoc ambiguity findings; and
5. error attribution by system layer.

For ambiguity-adjusted development analysis, remove only E5D-027 and E5D-034 from the denominator because the frozen evidence audit demonstrated that the discovery wording was non-unique across the corpus.

This leaves 58 unambiguous development questions.

Clear end-to-end failures among those 58 are:

- E5D-017 — Layer C generation/completeness;
- E5D-030 — Layer B retrieval; and
- E5D-056 — Layer C abstention/status.

Preliminary ambiguity-adjusted end-to-end correctness:

```text
55 / 58 = 94.8%
```

This 94.8% figure is a **post-hoc development-analysis statistic**, not a replacement benchmark score.

Layer attribution among the three clear unambiguous failures:

```text
Layer B retrieval-caused answer failures: 1
Layer C generation/decision failures: 2
```

## Methodological lesson

Human verification of a discovery question against its intended target AD is not sufficient to prove corpus-wide uniqueness. A discovery question can be fully supported by its target while another revision, superseded directive, or lifecycle-related AD also satisfies the same wording.

Future discovery benchmark construction should therefore include a corpus-wide uniqueness audit before sealing the question set. The current development benchmark is not changed post hoc; this lesson applies to future benchmark design and interpretation.

## No post-hoc tuning decision

The isolated development errors do not justify changing the prompt, reasoning effort, evidence depth, retrieval configuration, or model before the oracle-evidence condition.

Changing the configuration now would risk overfitting to observed development errors. The next controlled experiment therefore keeps the exact same Layer C configuration and changes only the evidence source from frozen retrieved evidence to human reference/oracle evidence.

## Next experiment — oracle/reference evidence

The oracle-evidence development condition must keep fixed:

```text
provider: deepseek
model: deepseek-v4-pro
thinking: enabled
reasoning_effort: high
max_tokens: 4096
prompt: e5-hosted-qa-prompt-v1.0-dev
response contract: e5-hosted-qa-contract-v1.0
```

Only the evidence input changes from frozen E5-D top-5 retrieval to the human reference/oracle evidence associated with each development question.

The comparison is intended to separate:

- retrieval limitations: target/reference evidence missing or misleading in retrieved top 5; from
- generation/reasoning limitations: correct oracle evidence is present but the hosted answer is still wrong, incomplete, unsupported, or uses the wrong answer state.

Only after this comparison should the hosted-QA development configuration be finalized and frozen. The sealed final 40 questions must remain unopened until then.
