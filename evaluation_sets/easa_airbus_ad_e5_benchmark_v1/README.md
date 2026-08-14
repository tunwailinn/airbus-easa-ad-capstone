# EASA Airbus AD E5 Benchmark v1

Last updated: 14 August 2026

This directory contains the separate post-E0/E4 benchmark used to develop and evaluate E5 engineering-aware retrieval and Layer C hosted QA.

## Why this benchmark is separate

QA-v2 had already been exposed through the frozen E0/E4 experiment and error analysis. It was therefore not reused for E5 tuning or final testing.

E5 uses new base AD families selected from the verified 1,786-document development retrieval corpus, with the five unseen-ingestion families kept outside the entire E5 benchmark.

## Family split

Frozen split:

- seed: `20260805`;
- 40 new base AD families total;
- 24 development families;
- 16 final-test families;
- 10 selected families from each publication era;
- within every era: 6 development + 4 final-test;
- all QA-v2 target base families excluded;
- five frozen unseen-ingestion families excluded.

Machine-readable split artifacts:

```text
family_split.csv
split_lock.json
```

Do not hand-edit the frozen family split.

## Development set — 60 questions

| Category | Count |
|---|---:|
| identity/lifecycle | 8 |
| applicability | 10 |
| required action/compliance | 20 |
| referenced publication | 8 |
| conditional/multi-passage | 8 |
| insufficient/conflict/abstention | 6 |
| **Total** | **60** |

Query modes:

- 36 known-document;
- 18 identifier-free discovery;
- 6 abstention/conflict.

The development set was used for E5-A/B/C/D retrieval selection and Layer C hosted-QA configuration decisions.

Development question SHA-256:

```text
d43f08611d7d2f77eb37052a03f3deabf335b004ead9528e798e12fb8dad677b
```

## Final set — 40 questions — COMPLETE / FROZEN

| Category | Count |
|---|---:|
| identity/lifecycle | 5 |
| applicability | 7 |
| required action/compliance | 14 |
| referenced publication | 5 |
| conditional/multi-passage | 5 |
| insufficient/conflict/abstention | 4 |
| **Total** | **40** |

Query modes:

- 24 known-document;
- 12 identifier-free discovery;
- 4 abstention/conflict.

The final set was human reviewed, locked, and then opened exactly once for the primary final run after both retrieval and hosted-QA settings were frozen.

Final questions SHA-256:

```text
f6b008c1b5d24160cb5718e2d4e91a7e0d323277a531654e4b5c3a33995c9a85
```

## Question record contract

Records are JSONL with fields including:

```json
{
  "question_id": "E5F-001",
  "split": "final_test",
  "base_ad_number": "...",
  "target_ad_number": "...",
  "category": "required_action_compliance",
  "query_mode": "known_document",
  "question": "...",
  "answerable_from_ad": true,
  "reference_pages": [2, 3],
  "reference_sections": ["Required Action(s) and Compliance Time(s)"],
  "reference_answer": "...",
  "review_status": "human_verified"
}
```

For discovery questions, the target AD identifier is omitted from the question text while retained privately for scoring.

For abstention/conflict questions, the reference explains why the requested detail is not established by the AD evidence.

## Source-grounding rules

1. Every answerable question is verified against original PDF/page text.
2. Reference pages contain the evidence needed for the answer.
3. Conditional/multi-passage records identify all necessary pages.
4. Reference answers preserve material numeric values, units, conditions, exceptions, branches, lifecycle facts, and terminating-action wording.
5. Base AD families never cross development/final splits.
6. Development questions may be used for model/configuration selection.
7. Final questions may not be used for tuning after opening.
8. QA-v2 questions are not copied or mechanically ported into E5.
9. Oracle/reference-evidence analysis is diagnostic only and does not alter the final benchmark score.

## Frozen configuration files

```text
retrieval_freeze.json
hosted_qa_freeze.json
final_lock.json
```

The primary final run uses frozen E5-D retrieval plus frozen Layer C DeepSeek V4 Pro settings.

## Final benchmark result

Primary automatic:

- hosted requests: **40/40 successful**;
- answerability/status accuracy: **100%**;
- retrieval Recall@5: **35/36 = 97.22%**;
- known-document Recall@5: **24/24 = 100%**;
- discovery Recall@5: **11/12 = 91.67%**.

Human semantic:

- passes: **38/40**;
- failures: **2/40**;
- **strict end-to-end semantic accuracy: 95.0%**.

This is the authoritative primary result.

Primary failures:

- `E5F-011` — Layer C answer-selection/completeness failure under retrieved evidence;
- `E5F-021` — Layer B retrieval/candidate-generation failure.

## Final oracle diagnostic

After the primary result was preserved, a diagnostic oracle/reference-evidence condition was run with the same model/prompt/settings.

- original oracle successes: **39/40**;
- one technical/provider failure: `E5F-035`;
- exact transport retry of `E5F-035`: **recovered**;
- `E5F-021` becomes correct → Layer B failure confirmed;
- `E5F-011` becomes correct with focused evidence → Layer C evidence-selection/completeness sensitivity;
- `E5F-040` exhibits answer-status run-to-run variability under unchanged negative-control evidence.

Oracle and retry results are diagnostic only and cannot replace the strict primary 38/40 score.

## Main directory contents

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/
├── README.md
├── family_split.csv
├── split_lock.json
├── development_questions.jsonl
├── final_questions.jsonl
├── retrieval_freeze.json
├── hosted_qa_freeze.json
├── final_lock.json
├── e5_final_question_verification_audit.json
└── e5_final_question_final_review.md
```

Additional authoring/review artifacts may remain locally for audit history.

## Next boundary

Do not add the five frozen unseen PDFs to E5. Their temporary-QA and permanent-ingestion evaluation remains a separate generalization experiment under:

```text
evaluation_sets/unseen_incoming_5_v1/
```