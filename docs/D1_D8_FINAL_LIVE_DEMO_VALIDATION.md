# D1-D8 Final Live Demo Validation

- Validation date: 26 August 2026
- Runtime: FastAPI + Next.js via `ASSISTANT_PYTHON=../Capstone/.venv/bin/python make demo`
- Browser target: `http://127.0.0.1:3000`
- Serving state: 1,791 documents, Apple MPS, frozen E5-D retrieval and frozen Layer C contract

## Result

All eight final demo scenarios passed manual browser acceptance. The Stop/retry flow and the detailed evidence-inspector interaction checks also passed. The assistant is demo-frozen for screenshots, architecture diagrams, report work, and presentation preparation.

This is post-evaluation software acceptance. It does not change or replace the frozen E5 final result of 38/40 (95.0%), the frozen E5-D retrieval result, or any locked unseen result. Eight passing demo scenarios must not be reported as 100% research accuracy.

## Scenario record

The latency values below are the values displayed by the live UI. The backend was warm, and repeated retrievals could use the serving cache.

| ID | Route | Evidence first? | Final status | Citation/page correct? | UI latency | Result |
| --- | --- | --- | --- | --- | ---: | --- |
| D1 | `known_document` | Yes | `answered` | Yes - 2011-0041R1, page 2, EV1 | 20.1 s | PASS |
| D2 | `known_document` | Yes | `answered` | Yes - 2008-0008, page 1, EV3 | 11.7 s | PASS |
| D3 | `discovery` | Yes | `answered` | Yes - 2025-0276, page 6, EV5 | 54.7 s | PASS |
| D4 | `known_document` | Yes | `answered` | Yes - 2011-0041R1, page 1, EV1 | 6.7 s | PASS |
| D5 | `known_document` | Yes | `answered` | Yes - 2011-0041R1, pages 1-2 and page 2 | 55.1 s | PASS |
| D6 | `known_document` with explicit AD context | Yes | `answered` | Yes - only 2011-0041R1 was in scope | 61.6 s | PASS |
| D7 | `known_document` | Yes | `insufficient_evidence` | Yes - 2007-0173 evidence remained visible | 12.8 s | PASS |
| D8 | `known_document`, retrieval only | Yes | `retrieval_only` | Yes - five 2011-0041R1 passages | 0.0 s cached | PASS |

## Acceptance notes

### D1 - Known-document compliance

- Evidence appeared while the request was still active and before the final answer.
- The answer preserved the three-day compliance time, the applicable MSN list, the `unless already accomplished` exception, and both concurrent actions.
- Clicking the answer citation selected EV1 and showed AD 2011-0041R1, page 2, the retrieved section and the PDF filename `2011-0041R1__AD_2011-0041R1_1__easa_ad_2011_0041_R1.pdf`.

### D2 - Applicability

- The answer preserved models A310-221, A310-222, A310-322, A310-324 and A310-325 and the modification 10149 exception.
- The answer citation selected EV3 on page 1.
- Reader to Raw displayed the verbatim retrieved applicability passage; switching back restored the formatted reader.

### D3 - Corpus-wide discovery

- The UI reported route `discovery`; no AD identifier was supplied in the question.
- The final answer identified EASA AD 2025-0276.
- Its citation selected EV5, page 6, `Required Action(s) and Compliance Time(s)`, which explicitly requires reporting inspection results including no findings within 30 days after an inspection or since 14 April 2025, whichever occurs later.

### D4 - Lifecycle relationship

- The answer identified EASA Emergency AD 2011-0041-E dated 10 March 2011.
- EV1, page 1, explicitly states that revision relationship and did not mix another lifecycle record.

### D5 - Reference publication

- The answer preserved the exact identifiers A380-27A8027, AFM TR 83 or 84, A380-27-8040 and A380-31-8071.
- It stayed within what the AD passages state and did not invent unsupported Service Bulletin content.

### D6 - Explicit follow-up context

- Clicking `Use 2011-0041R1 for follow-up` displayed one removable context chip.
- The follow-up retrieved five passages, all from 2011-0041R1.
- The answer described the finding-dependent correction or serviceable-part replacement and the additional A380-31-8071 modification condition.
- Removing the chip cleared the explicit context.

### D7 - Abstention boundary

- The final status was `insufficient_evidence`.
- The response stated that exact dimensions, quantities and tightening torques were not present and pointed to the referenced service bulletins without inventing those details.
- The five retrieved AD passages remained visible.

### D8 - Evidence-only mode

- The final status was `retrieval_only`.
- The UI explicitly stated `Hosted Layer C was intentionally skipped.`
- Five retrieved passages remained available and no generated answer was produced.

## Additional required checks

### Stop and retry

PASS.

- Stop was pressed after five passages had arrived and while answer generation was still active.
- The UI displayed `Request stopped. Your question is ready to edit or send again.`
- The complete question returned to the composer.
- No partial DeepSeek JSON appeared.
- The same question was successfully submitted again in evidence-only mode.
- The API log recorded a successful cancellation request.

### Evidence inspector

PASS.

- Citation chips selected the intended evidence records.
- AD number, page, section, E5-D rank and PDF filename matched the selected passages.
- Reader and Raw modes both rendered correctly.
- Copy changed to `Copied`, and the clipboard contained the selected passage text.
- Pointer drag changed the panel width.
- Keyboard resizing changed the ARIA width value by the documented 24 px step.
- Reset width returned the inspector to the 420 px default and removed the reset control.

### Regression confirmation

The focused frontend regression suite passed after the live checks:

```text
Test Files  2 passed (2)
Tests       8 passed (8)
```

The suite includes cancellation, keyboard resizing, pointer resizing, double-click/reset behavior, Reader/Raw mode and passage-copy coverage.
