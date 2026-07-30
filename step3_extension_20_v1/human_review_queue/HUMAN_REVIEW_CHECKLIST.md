# Human review checklist

These 20 records are populated machine-assisted first-pass annotations with
PDF-grounded evidence. They are review candidates, not human-approved records
or gold.

For every `*.annotation.json` working copy:

1. Compare the complete original PDF with every annotation field.
2. Accept or correct applicability, definitions, unsafe condition,
   requirements, compliance times, exceptions, credit, publications, contacts,
   and classification.
3. Verify every cited evidence span against its printed PDF page; add or narrow
   evidence where necessary.
4. Confirm the source explicitly states `Supersedure: None`; do not infer or
   add a supersedure relationship.
5. Resolve every field assertion as accepted or corrected.
6. Keep `human_confirmed=false` and `gold_record=false` until explicit approval.
7. Run schema, evidence-quote, and Step 3 validators before gold promotion.

Edit files only in `human_review_working/`. Keep `human_review_queue/`
unchanged as the source review queue.
