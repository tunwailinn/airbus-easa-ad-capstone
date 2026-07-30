# Extraction benchmark gate

Do not score an extraction method until `gold/` contains the 30 independently
reviewed records and the Step 3 strict validator returns zero. The evaluator
enforces this and cannot be pointed at the machine-assisted A/B streams as a
substitute.

Keep one prediction JSON per selected source in each method folder:

```text
baselines/regex/
baselines/zero_shot/
baselines/schema_guided/
```

Each prediction needs `source_document.file_instance_id`; a full Step 2 record
is preferred. Incomplete predictions are allowed and score as missing fields,
which is useful for a deliberately narrow regex baseline.

After human approval and strict validation:

```bash
python step3_pilot/evaluate_extractions.py \
  step3_pilot/gold step3_pilot/baselines/regex \
  --method regex

python step3_pilot/evaluate_extractions.py \
  step3_pilot/gold step3_pilot/baselines/zero_shot \
  --method zero_shot

python step3_pilot/evaluate_extractions.py \
  step3_pilot/gold step3_pilot/baselines/schema_guided \
  --method schema_guided
```

The report includes exact scalar accuracy; precision, recall and F1 for ATA,
manufacturer, models, TCDS, applicability models, action types, Airbus family,
referenced publications and relationships; and token-level F1 for unsafe
condition, requirements, compliance logic and applicability text. Compare
methods on the same frozen 30 files and preserve prompts, model IDs, rule
versions and raw outputs beside each prediction set.
