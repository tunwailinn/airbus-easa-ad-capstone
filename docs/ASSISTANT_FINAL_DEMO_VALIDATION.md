# Final Assistant Demo Validation

Publication labels: E1 = legacy E4; E2-A–D = legacy E5-A–D. Artifact names, question IDs and code excerpts retain their original labels. See [experiment label mapping](EXPERIMENT_LABELS.md).

Last updated: 27 August 2026

## Purpose

This document defines the final user-facing validation scope for the modern Airbus EASA AD Assistant and records that the scope was completed on **26 August 2026**.

It is **not a research benchmark**. It does not replace the frozen E2 final result, frozen E2-D retrieval result, or locked unseen-generalization results. Its purpose is software/demo acceptance: verifying that the accepted serving architecture behaves reliably, presents source evidence clearly, and preserves the intended research boundary during the capstone demonstration.

The detailed executed-run record is:

```text
docs/D1_D8_FINAL_LIVE_DEMO_VALIDATION.md
```

## Validation status

```text
warm compatibility top-5 exact: PASS
TypeScript: PASS
ESLint: PASS
Vitest: PASS
Next.js production build: PASS
Playwright: PASS
backend contract tests: PASS
make demo: PASS
D1-D8 live browser validation: PASS
Stop/retry: PASS
Evidence inspector interaction checks: PASS
```

The assistant runtime is therefore **demo-frozen**.

Frozen runtime baseline commit:

```text
88f96d5aca67fb0c98113f4f7b04410402a7e559
```

Later documentation-only commits do not redefine the implemented retrieval or serving methodology.

## Executed showcase set

### D1 — Known-document compliance — PASS

Prompt:

> For EASA AD 2011-0041R1, what actions had to be completed within 3 days after 14 March 2011?

Observed:

- route: `known_document`;
- evidence appeared before the final hosted answer;
- final status: `answered`;
- citation/page verified: 2011-0041R1, page 2, EV1;
- UI latency: 20.1 s.

### D2 — Applicability — PASS

Prompt:

> Which A310 models are affected by EASA AD 2008-0008?

Observed:

- route: `known_document`;
- applicability evidence was present;
- Raw/Verbatim Source mode preserved the retrieved passage;
- final status: `answered`;
- citation/page verified: 2008-0008, page 1, EV3;
- UI latency: 11.7 s.

### D3 — Corpus-wide discovery — PASS

Prompt:

> Which Airbus directive requires reporting inspection results including no findings within 30 days after each inspection?

Observed:

- route: `discovery`;
- no target AD identifier was supplied in the user question;
- final answer identified EASA AD 2025-0276;
- citation/page verified: page 6, EV5;
- UI latency: 54.7 s.

### D4 — Lifecycle relationship — PASS

Prompt:

> Which earlier directive does EASA AD 2011-0041R1 revise?

Observed:

- route: `known_document`;
- answer identified EASA Emergency AD 2011-0041-E dated 10 March 2011;
- lifecycle evidence was explicit and no unrelated revision family was mixed;
- citation/page verified: 2011-0041R1, page 1, EV1;
- UI latency: 6.7 s.

### D5 — Reference publication — PASS

Prompt:

> Which referenced publication supports the required action in EASA AD 2011-0041R1?

Observed:

- route: `known_document`;
- exact identifiers were preserved, including A380-27A8027, AFM TR 83 or 84, A380-27-8040 and A380-31-8071;
- no unsupported Service Bulletin content was invented;
- citations/pages were verified across pages 1-2 and page 2;
- UI latency: 55.1 s.

### D6 — Explicit follow-up context — PASS

Precondition:

```text
Use 2011-0041R1 for follow-up
```

Prompt:

> What is the next required action after that inspection?

Observed:

- route: `known_document` via explicit context;
- exactly one AD was in follow-up scope;
- all five retrieved passages came from 2011-0041R1;
- the context chip was visible and removable;
- final status: `answered`;
- UI latency: 61.6 s.

### D7 — Abstention / missing procedure detail — PASS

Prompt:

> For EASA AD 2007-0173, what are the exact fastener dimensions, quantities and tightening torques required by this AD?

Observed:

- route: `known_document`;
- final status: `insufficient_evidence`;
- the assistant did not fabricate unavailable maintenance details;
- referenced Service Bulletins were identified without inventing their contents;
- retrieved AD evidence remained visible;
- UI latency: 12.8 s.

### D8 — Evidence-only mode — PASS

Precondition:

```text
Enable Evidence only mode.
```

Executed prompt:

> For EASA AD 2011-0041R1, what actions had to be completed within 3 days after 14 March 2011?

Observed:

- route: `known_document`;
- final status: `retrieval_only`;
- hosted Layer C was intentionally skipped;
- five 2011-0041R1 passages remained available;
- no generated answer was produced;
- UI displayed 0.0 s because the repeated retrieval was served from cache.

The original checklist allowed D8 to reuse either D1 or D3. The executed validation used the D1 known-document prompt; the machine-readable showcase record is synchronized to that actual run.

## Stop/cancellation check — PASS

During a live request, Stop was pressed after five passages had arrived while answer generation was still active.

Verified behavior:

- the browser stopped waiting immediately;
- the complete question returned to the composer;
- no partial DeepSeek JSON appeared;
- the same question could be submitted again;
- the API log recorded a successful cancellation request.

An already-running PyTorch/MPS model kernel is not forcibly preempted; cancellation prevents the request from advancing beyond the next safe stage boundary.

## Evidence-inspector check — PASS

Verified for successful live queries:

- citation chips selected the intended evidence records;
- AD number, page, section, E2-D rank and PDF filename matched;
- Reader and Raw modes rendered correctly;
- copied text matched the selected retrieved passage;
- pointer resizing worked;
- keyboard resizing used the documented 24 px step;
- Reset width returned the inspector to the 420 px default.

## Final acceptance table

| ID | Route observed | Evidence first | Final status | Citation/page correct | UI latency | Result |
|---|---|---:|---|---:|---:|---|
| D1 | `known_document` | Yes | `answered` | Yes | 20.1 s | PASS |
| D2 | `known_document` | Yes | `answered` | Yes | 11.7 s | PASS |
| D3 | `discovery` | Yes | `answered` | Yes | 54.7 s | PASS |
| D4 | `known_document` | Yes | `answered` | Yes | 6.7 s | PASS |
| D5 | `known_document` | Yes | `answered` | Yes | 55.1 s | PASS |
| D6 | `known_document` with explicit AD context | Yes | `answered` | Yes | 61.6 s | PASS |
| D7 | `known_document` | Yes | `insufficient_evidence` | Yes | 12.8 s | PASS |
| D8 | `known_document`, retrieval only | Yes | `retrieval_only` | Yes | 0.0 s cached | PASS |

This table is a **demo/software acceptance record only**. Eight passing scenarios must not be reported as 100% research accuracy.

## Presentation assets still to prepare

Software acceptance and runtime freeze are complete. The following are presentation/report assets and are **not prerequisites for the already-completed runtime freeze**:

1. landing screen with corpus/model readiness;
2. known-document response with structured compliance fields;
3. evidence inspector showing page/section/source provenance;
4. discovery-mode response;
5. explicit follow-up context chip;
6. abstention or evidence-only state;
7. final architecture diagram;
8. final report and presentation integration.

For report/presentation screenshots, prefer views that show both the answer and its supporting evidence.

## Freeze boundary

The runtime freeze criteria are satisfied:

```text
automated regression checks passed
warm top-5 compatibility remained exact
D1-D8 manually reviewed and passed
no known citation/provenance mismatch remained
Stop/retry passed
make demo worked from the validated runtime
frozen runtime baseline SHA recorded
```

The assistant is **demo-frozen**. Avoid further UI, retrieval, model, prompt, or serving changes unless fixing a reproducible demo-blocking defect.
