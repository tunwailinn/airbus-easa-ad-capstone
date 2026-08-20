# Final Assistant Demo Validation

Last updated: 20 August 2026

## Purpose

This is the **final user-facing demo validation checklist** for the modern Airbus EASA AD Assistant.

It is not a new research benchmark. It does not replace the frozen E5 final result or the unseen-generalization results. Its purpose is to verify that the accepted serving architecture behaves reliably and presents evidence clearly during the capstone demonstration.

## Preconditions

Before running the showcase questions:

```text
warm compatibility top-5 exact: PASS
TypeScript: PASS
ESLint: PASS
Vitest: PASS
Next.js production build: PASS
Playwright: PASS
backend contract tests: PASS
make demo: starts successfully
```

Start the live system with:

```bash
make demo
```

Open:

```text
http://127.0.0.1:3000
```

## Showcase set

### D1 — Known-document compliance

Prompt:

> For EASA AD 2011-0041R1, what actions had to be completed within 3 days after 14 March 2011?

Check:

- route is known-document;
- top evidence appears before or independently of the final hosted answer;
- compliance time is displayed separately when supplied by Layer C;
- citations open the corresponding evidence passage;
- page, section and source PDF are visible.

### D2 — Applicability

Prompt:

> Which A310 models are affected by EASA AD 2008-0008?

Check:

- known-document routing;
- applicability evidence is present in the evidence inspector;
- model designations are not silently generalized beyond the evidence;
- Raw/Verbatim Source mode preserves the retrieved passage exactly.

### D3 — Corpus-wide discovery

Prompt:

> Which Airbus directive requires reporting inspection results including no findings within 30 days after each inspection?

Check:

- route is discovery;
- the target AD identifier is not supplied in the user question;
- evidence comes from corpus-wide retrieval rather than direct ID lookup;
- the final answer cites the retrieved directive/page.

### D4 — Lifecycle

Prompt:

> Which earlier directive does EASA AD 2011-0041R1 revise?

Check:

- lifecycle evidence is visible;
- the answer does not mix unrelated revision families;
- the cited evidence contains the lifecycle statement.

### D5 — Reference publication

Prompt:

> Which referenced publication supports the required action in EASA AD 2011-0041R1?

Check:

- referenced-publication evidence is surfaced;
- identifiers are preserved exactly;
- no service-bulletin content is invented beyond what the AD evidence states.

### D6 — Explicit follow-up context

First complete a known-document question, then select one retrieved AD using:

```text
Use <AD> for follow-up
```

Ask:

> What is the next required action after that inspection?

Check:

- only one explicit AD is used as follow-up scope;
- the UI shows the selected context;
- the user can remove the context;
- no full hidden conversation history is injected into E5 retrieval.

### D7 — Abstention / missing procedure detail

Prompt:

> For EASA AD 2007-0173, what are the exact fastener dimensions, quantities and tightening torques required by this AD?

Check:

- the assistant does not fabricate unavailable maintenance details;
- evidence remains visible;
- if the AD directs the user to referenced approved maintenance data, the response preserves that boundary.

### D8 — Evidence-only mode

Enable **Evidence only** and run either D1 or D3.

Check:

- hosted Layer C is skipped;
- retrieved evidence remains fully usable;
- the UI clearly distinguishes retrieval-only mode from an answered Layer C response.

## Stop/cancellation check

Start a query and press **Stop** during either retrieval or hosted generation.

Required behavior:

- the browser stops waiting immediately;
- the interrupted question returns to the composer;
- no partial DeepSeek JSON is shown;
- if local embedding/reranking is already inside a model kernel, that kernel may finish, but the request must not continue into the next stage;
- a second query can be submitted after cancellation.

## Evidence-inspector check

For at least one successful question:

- click every citation chip;
- confirm each citation selects the expected evidence record;
- inspect AD number, page, section, rank and PDF name;
- toggle Reader ↔ Raw;
- copy the passage and verify the copied text is the original retrieved passage;
- resize the evidence panel with mouse/trackpad;
- resize it with keyboard arrows;
- reset the panel width.

## Manual validation record

Record each live run in a table like this:

| ID | Route observed | Evidence first | Final status | Citation/page correct | Total latency | PASS/FAIL | Notes |
|---|---|---:|---|---:|---:|---|---|
| D1 |  |  |  |  |  |  |  |
| D2 |  |  |  |  |  |  |  |
| D3 |  |  |  |  |  |  |  |
| D4 |  |  |  |  |  |  |  |
| D5 |  |  |  |  |  |  |  |
| D6 |  |  |  |  |  |  |  |
| D7 |  |  |  |  |  |  |  |
| D8 |  |  |  |  |  |  |  |

This table is a demo acceptance record only. Do not merge it into the frozen E5 accuracy table.

## Required screenshots

Capture at minimum:

1. landing screen with corpus/model readiness;
2. known-document response with structured compliance fields;
3. evidence inspector showing page/section/source provenance;
4. discovery-mode response;
5. explicit follow-up context chip;
6. abstention or evidence-only state.

For the final report/presentation, prefer screenshots that visibly show both the response and the supporting evidence.

## Demo freeze criteria

The demo can be tagged/frozen only when:

```text
all automated regression checks pass
warm top-5 compatibility remains exact
D1-D8 have been manually reviewed
no known citation/provenance mismatch remains
Stop/retry works
make demo works from a clean terminal session
screenshots have been captured
```

After this point, avoid UI or serving changes unless fixing a reproducible demo-blocking defect.
