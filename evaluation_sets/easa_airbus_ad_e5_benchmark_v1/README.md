# EASA Airbus AD E5 Benchmark v1

This directory is reserved for the **new post-E0/E4 benchmark** used to develop and evaluate E5 engineering-aware retrieval.

## Why this benchmark is separate

The 50-question QA-v2 set has already been exposed through the frozen E0/E4 experiment and subsequent error analysis. It is therefore not a valid tuning or final-test set for E5.

E5 uses new base AD families selected from the verified 1,786-document development retrieval corpus.

## Family split

Generate locally with:

```bash
.venv/bin/python -m full_corpus_pipeline.prepare_e5_benchmark_families
```

This writes:

```text
family_split.csv
split_lock.json
```

The split is deterministic:

- seed: `20260805`;
- 40 new base AD families total;
- 24 development families;
- 16 final-test families;
- 10 selected families from each publication era;
- within every era: 6 development + 4 final-test;
- all QA-v2 target base families are excluded;
- five frozen unseen-ingestion PDFs remain outside this benchmark because they belong to the separate ingestion experiment.

Do not hand-edit `family_split.csv` after it is generated. Its SHA-256 is stored in `split_lock.json`.

## Question targets

### Development — 60 questions

| Category | Count |
|---|---:|
| identity/lifecycle | 8 |
| applicability | 10 |
| required action/compliance | 20 |
| referenced publication | 8 |
| conditional/multi-passage | 8 |
| insufficient/conflict/abstention | 6 |
| **Total** | **60** |

Query-mode target:

- 36 known-document questions;
- 18 identifier-free discovery questions;
- 6 abstention/conflict questions.

### Final test — 40 questions

| Category | Count |
|---|---:|
| identity/lifecycle | 5 |
| applicability | 7 |
| required action/compliance | 14 |
| referenced publication | 5 |
| conditional/multi-passage | 5 |
| insufficient/conflict/abstention | 4 |
| **Total** | **40** |

Query-mode target:

- 24 known-document questions;
- 12 identifier-free discovery questions;
- 4 abstention/conflict questions.

## Question record contract

Store authoring records as JSONL. Recommended fields:

```json
{
  "question_id": "E5D-001",
  "split": "development",
  "base_ad_number": "2020-0001",
  "target_ad_number": "2020-0001R1",
  "category": "required_action_compliance",
  "query_mode": "known_document",
  "question": "Under EASA AD 2020-0001R1, when must ...?",
  "answerable_from_ad": true,
  "reference_pages": [2, 3],
  "reference_sections": ["Required Action(s) and Compliance Time(s)"],
  "reference_answer": "...",
  "required_conditions": ["..."],
  "required_exceptions": ["..."],
  "review_status": "human_verified"
}
```

For discovery questions, omit the AD identifier from the **question text** while retaining the private target metadata used for scoring.

For abstention questions, `target_ad_number` may be omitted when there is intentionally no valid target inside the corpus. The reference record must explain why abstention is correct.

## Source-grounding rules

1. Every answerable question is verified against original PDF/page-text.
2. Reference pages must contain the evidence needed for the answer.
3. Conditional/multi-passage questions list all pages necessary for a complete answer.
4. Reference answers preserve numeric values, units, conditions, exceptions, alternative branches, and terminating-action wording.
5. Questions from one base family never cross development/final splits.
6. Development questions may be used for E5 model/configuration selection.
7. Final-test questions must remain unopened until E5 retrieval configuration and hosted-QA prompt/model/settings are frozen.
8. QA-v2 questions must not be copied, paraphrased, or mechanically ported to new ADs for E5.

## Planned files

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/
├── README.md
├── family_split.csv                 # generated/frozen locally
├── split_lock.json                  # generated/frozen locally
├── development_questions.jsonl      # 60 human-verified questions
├── development_lock.json
├── final_questions.jsonl            # 40 sealed questions
└── final_lock.json
```

The final set is opened once and reported without post-test tuning.
