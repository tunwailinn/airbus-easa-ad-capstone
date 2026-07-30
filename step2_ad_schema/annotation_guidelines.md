# EASA Airbus AD annotation guidelines

Version: **1.0.0**  
Schema: `easa_airbus_ad_annotation.schema.json`  
Scope: EU-issued EASA Airworthiness Directives applicable to Airbus products

## 1. Purpose

These guidelines define the gold-data contract for extracting applicability and compliance information from the Airbus AD corpus. The dataset will support rule-based, zero-shot, and few-shot schema-guided extraction experiments, classification, evidence retrieval, and citation-backed summaries.

The governing rule is simple: **annotate only what the current PDF states and attach source evidence to every safety-critical fact.** Do not complete missing information from aviation knowledge, another revision, a filename, or a Service Bulletin that is not part of the annotated source.

## 2. Annotation unit

Create one annotation record for one canonical, unique-content AD publication.

- `2020-0123`, `2020-0123R1`, and `2020-0123R2` are separate records linked through `base_ad_number`.
- A corrected publication is a separate record even when the AD number and revision remain unchanged.
- Exact binary or exact-text copies share one canonical annotation. Record the other paths in `source_document.file_aliases`.
- Do not merge the current 17 near-duplicate candidates automatically.
- If a same-version content conflict reappears, preserve both files until a reviewer adjudicates them.
- Keep all revisions, corrections, exact duplicates, and near-duplicate cluster members in the same train/validation/test split.

Use `file_instance_id` for the physical source, `record_id` for the annotation, `logical_version_key` for a revision/correction unit, and `base_ad_number` for leakage-safe dataset grouping.

## 3. Source precedence

Use sources in this order:

1. Rendered PDF content.
2. Page-level native or OCR text used to create evidence offsets.
3. Official EASA publication metadata for confirmation.
4. Step 1 manifest and filename for navigation and quality control only.

If the rendered PDF and extracted text disagree, the rendered PDF wins. Transcribe the relevant text, use `visual_transcription`, and add the `visual_transcription_used` quality flag.

Do not copy an annotation from another revision. Annotate each version independently first; compare versions only during quality control.

## 4. Missingness, raw values, and normalization

- Use `null` for a missing scalar.
- Use `[]` for a missing collection.
- Never use an empty string as a missing value.
- Preserve the exact printed wording in `raw_text`, `raw_value`, or `exact_quote`.
- Store normalized dates as ISO `YYYY-MM-DD`, while preserving the printed date.
- Preserve serial numbers as strings so leading zeros and alphanumeric values are not lost.
- Preserve printed units. Do not convert months to days, flight cycles to hours, or relative limits to calculated due dates.
- Use a field state to distinguish `explicit_none`, `not_stated`, `illegible`, `ambiguous`, and `conflicting`.
- Human gold labels use verification states, not artificial numeric confidence. Numeric confidence is permitted only for automatic extraction assertions.

When a value is ambiguous, retain the competing evidence, mark the field `ambiguous` or `conflicting`, and request adjudication.

## 5. Evidence requirements

Every important identity/date, applicability group, unsafe-condition claim, mandatory action, compliance rule, publication role, exception, credit statement, and relationship must reference at least one evidence span.

Each span records:

- Stable evidence ID
- Source `file_instance_id`
- One-based PDF page number
- Printed page label when different
- Normalized and raw section heading
- Clause path when present
- Exact quotation
- Start/end offsets in the stored page text when available
- Extraction method and quality
- Optional normalized bounding box
- Table row, column, and footnote context

Use the smallest quotation that still preserves meaning. For a compliance requirement, the quotation must include the mandated action, trigger, quantity/unit, and logical connector. Quoting only “100 days” is insufficient.

For tables, cite the selected cell together with its row/column headers and relevant footnotes. Use multiple spans when a clause or row continues across pages.

An explicit `Supersedure: None` still needs evidence. Set
`ad_identity.supersedure_statement.state` to `explicit_none`; do not create a
positive `supersedes` edge. Historical `referenced_only` relationships may still
coexist because they are not supersedure claims.

## 6. Field rules

### 6.1 AD identity and publication status

The cover-page `AD No.` is authoritative. Normalize spaces and dash variants:

- `AD No.: 2007 - 0281` becomes `2007-0281`.
- `AD No.: 2008 – 0032` becomes `2008-0032`.
- `2022-0096R2` has base `2022-0096` and revision number `2`.

If the cover header and filename disagree, retain the cover value and add `header_filename_mismatch`.

Keep these concepts separate:

- Revision: `R1`, `R2`, and later revision numbers.
- Correction: a notice such as `[Corrected: 21 January 2014]`; it does not increment the revision.
- Supersedure: a new AD number replaces an older AD because the older action no longer assures adequate safety.
- Cancellation: the source explicitly cancels an AD.

An `_C1` filename is only a review clue. Correction status requires the PDF notice or official metadata. `is_latest_version` and reverse `superseded_by` are corpus-derived and snapshot-dependent; do not present them as facts extracted from one PDF.

A correction may keep exactly the same printed AD number and revision. For a
`corrects` or `corrected_by` relationship, identify the other publication with
`target_record_id` or `target_logical_version_key`; the AD number alone is not
enough to distinguish the two publications. Correction relationships must keep
the same printed `target_ad_number`, and their record/version target must resolve
against the annotation batch before approval.

### 6.2 Manufacturer, approval holder, and Airbus scope

Normalize these manufacturer forms to `Airbus`, while preserving the raw value:

- Airbus
- Airbus S.A.S.
- Airbus Industrie
- Airbus, formerly Airbus Industrie
- AIRBUS (formerly AIRBUS INDUSTRIE)

Do not require the literal phrase `Airbus SAS`.

Keep Design Approval Holder, Manufacturer, product applicability, and STC/modification holder separate. For an AD whose approval holder is Lufthansa Technik but whose structured manufacturer is `Airbus, formerly Airbus Industrie`, annotate Lufthansa Technik as the approval/STC holder and Airbus as manufacturer.

An incidental or historical mention of Airbus is not enough; use the structured Manufacturer(s) and Applicability sections.

### 6.3 Dates, ATA chapter, and subject

- Annotate issue, effective, and correction dates separately.
- Do not substitute issue date for effective date.
- Do not calculate a due date from a relative compliance rule.
- Record an ATA chapter only when explicitly printed.
- Allow multiple ATA chapters if the source explicitly lists them.
- Preserve the exact subject/title; do not generate a summary title.

### 6.4 Applicability

Applicability is a Boolean expression, not a flat model list. Preserve:

- Aircraft family and exact model/variant
- Included/excluded MSNs or serial numbers
- Installed part numbers
- Modification or Service Bulletin embodiment status
- STC/configuration conditions
- Production dates where stated
- `all serial numbers` wording
- `and`, `or`, `except`, and conditional logic

Create stable groups such as `APP-001`, then link each action and compliance rule to the applicable groups. Do not copy aircraft types mentioned only in the Reason section, a publication title, or historical discussion.

Example: `A319, A320 and A321 aeroplanes ... if modified by EASA STC 10049524` requires model/MSN scope plus an STC configuration condition. The STC holder is not the aircraft manufacturer.

### 6.5 Definitions

Annotate a term only when the AD explicitly defines it. Preserve the exact definition and link later requirements to it in notes or clause paths. Do not insert project-level definitions into the AD record.

### 6.6 Unsafe condition and reason

Use the `Reason` or equivalent unsafe-condition section. Separate, where explicitly supported:

- Observed event or defect
- Stated cause
- Unsafe condition or failure mode
- Potential consequence
- Affected component
- Intended mitigation

Preserve modal wording. `Could lead to loss of control` is a potential consequence, not a confirmed occurrence.

### 6.7 Required actions

Create one requirement object per independently mandated action. Split conditional branches instead of collapsing them.

`Inspect and, if cracked, replace` normally becomes:

1. An inspection requirement.
2. A conditional replacement requirement linked to the inspection finding.

Each requirement preserves:

- Mandated verb and object
- Obligation and condition
- Applicability group IDs
- Publication used as the method
- Initial compliance rule
- Repetitive interval
- Follow-on requirements
- Terminating-action scope
- Evidence IDs

Use the controlled action labels. Choose `other` only when no label applies, and explain it in annotation notes.

### 6.8 Compliance time

Represent every limit with its printed relation, quantity, unit, and reference event.

Do not calculate absolute deadlines. `Within 30 days after the effective date` remains a 30-calendar-day limit anchored to `effective_date`. `Before next flight` remains a categorical event, not zero days.

Preserve compound logic:

- `whichever occurs first`
- `whichever occurs later`
- all listed limits
- any listed alternative
- conditional branches

Example from AD 2007-0178:

> Within 600 flight hours or 750 flight cycles or 100 days after the effective date of this AD, whichever occurs first.

Encode three limits with `whichever_occurs_first`; do not choose one limit or compute a date.

Repetition must be explicit through wording such as `thereafter`, `repeat`, or `at intervals not to exceed`. The plural word `inspections` alone does not establish a repetitive requirement.

### 6.9 Terminating actions, exceptions, and previous-action credit

- Mark an action terminating only when the AD explicitly says that it terminates specified requirements.
- Link partial terminating actions only to the affected requirement IDs.
- Previous-action credit is not a terminating action.
- Keep requirement exceptions separate from applicability exclusions.
- Annotate credit only when explicitly granted and preserve its publication revision/date and conditions.
- An AMOC or optional method is not previous-action credit unless the AD states that it is.

### 6.10 Referenced publications

Capture the exact identifier, issuer, revision, and date when stated. Assign one or more roles:

- Required method
- Referenced information
- Previous-action credit
- Optional method
- Superseded publication

Do not look up missing Service Bulletin details externally. If the AD delegates timing to a publication, retain `as specified` in raw wording rather than inventing a limit.

Do not classify STC, TCDS, approval, or Service Bulletin numbers as AD numbers.

### 6.11 Supersedure, revision, correction, and historical references

Confirm a supersedure edge only from:

1. The structured `Supersedure:` field, or
2. An explicit directional sentence whose current and target ADs are clear.

Direction examples:

- `This AD supersedes EASA AD 2006-0047`: current AD supersedes `2006-0047`.
- `EASA AD 2006-0047 is superseded by this AD`: current AD supersedes `2006-0047`.
- `This AD is superseded by EASA AD 2020-0123`: current AD is superseded by `2020-0123`.
- `Supersedure: None`: `supersedure_statement.state=explicit_none`, with no positive `supersedes` edge.
- `does not supersede`: no positive relationship.

A historical sentence such as `SB A320-27-1164 was mandated by EASA AD 2006-0223` is **not** a supersedure edge. If retained, label it `referenced_only`.

Normally, a relationship target must have a different AD number. Same-number
targets are allowed only for `corrects` and `corrected_by`, and must carry a
different target record or logical-version key.

Step 1 candidate links remain `candidate` and `manually_verified=false` until an annotator reviews the source PDF. A confirmed revision-family link does not automatically prove a cross-number supersedure relationship.

### 6.12 AMOC and contacts

Capture the authority or organization, contact text, and any stated conditions. Do not infer that an AMOC is permitted from general policy; annotate only the AD's Remarks or equivalent text.

## 7. Known-corpus regression cases

Use these during training and quality control:

- `2007-0281` is the document identity; `2006-0047` is its supersedure target.
- `2008-0032` remains the identity despite a spaced en-dash header; `2006-0108` is the supersedure target.
- `2007-0178` is not `2006-0223`, and it does not supersede `2006-0223`; that older AD appears only in body history.
- A header `2024-0091R1` with filename `2024-0092...pdf` uses the header identity and receives a mismatch flag.
- A correction requires the PDF correction notice, not only `_C1` in a filename.
- `Airbus, formerly Airbus Industrie` normalizes to Airbus.
- Do not merge a near-duplicate pair unless exact duplicate evidence is established.

## 8. Human and automatic boundaries

| Data | Treatment |
|---|---|
| Paths, hashes, page count, extraction status | Import from Step 1 |
| AD/base number, revision, issue/correction metadata | Auto-prefill; human verifies gold records |
| Exact duplicate group and version chain | Corpus-derived provenance, not extraction gold |
| Subject, effective date, ATA, manufacturer | Auto-prefill allowed; human accepts/corrects |
| Applicability groups, MSN logic, conditions, exclusions | Human annotation required |
| Unsafe condition and consequence | Human annotation required |
| Atomic actions and dependencies | Human annotation required |
| Compliance limits, anchors, logic, repetition | Human annotation required |
| Terminating action, exceptions, and credit | Human annotation required |
| Publication identity/role | Auto-prefill allowed; human verification required |
| Supersedure candidates | Human confirmation required |
| Evidence spans | Human-created or human-verified for gold data |
| Automatic confidence | Model/rules only |
| Accepted/corrected/rejected status | Human reviewer/adjudicator only |

## 9. Annotator workflow

1. Open the canonical PDF and its Step 1 manifest row.
2. Verify AD number, revision, correction, page count, and manufacturer visually.
3. Annotate cover-page fields and evidence.
4. Annotate applicability groups and definitions.
5. Annotate the Reason section.
6. Split mandatory actions into requirement objects.
7. Attach compliance and applicability groups to every action.
8. Annotate publications, exceptions, credit, terminating actions, and contacts.
9. Review the full sentence before assigning a relationship.
10. Add or verify evidence for every critical value.
11. Run schema and semantic validation.
12. Perform a second pass for negation, conditionals, tables, cross-page clauses, and historical references.
13. Submit for independent review or adjudication.

## 10. Double annotation and agreement

Calibration:

- Jointly discuss five varied ADs excluded from final evaluation.
- For the 30-AD pilot, independently double-annotate at least 10; all 30 is preferable.
- At scale, double-annotate at least 20%, stratified across simple, revised, corrected, table-heavy, STC-conditioned, and complex-applicability documents.
- Annotators must not see each other's labels before submission.

Report:

- Exact agreement for identity, dates, ATA, revision, and correction status
- Precision/recall/F1 or Jaccard for models, publications, actions, and relationships
- Token/span F1 for applicability, compliance, and evidence
- Relation F1 for action-to-applicability and action-to-compliance links
- Cohen's kappa or Krippendorff's alpha for categorical labels, with raw agreement
- Missingness-state agreement

Initial project gates—not universal scientific thresholds—are:

- 98% exact agreement for identity/status
- 95% exact agreement for dates and ATA
- 0.85 span F1 for applicability/compliance evidence
- 0.85 F1 for actions and relationships
- 0.80 kappa/alpha for major categorical labels

If a gate is missed, revise the guideline, repeat calibration, and recheck affected records.

## 11. Adjudication

A senior annotator or aviation-domain reviewer adjudicates every disagreement involving:

- Applicability Boolean logic
- Compliance trigger or deadline
- Terminating action
- Supersedure direction
- Revision/correction identity
- Rendered-PDF versus extracted-text conflict

Preserve both original annotations, the adjudicated record, reviewer/date, evidence, decision rationale, and guideline rule. When adjudication exposes a reusable ambiguity, add a numbered rule and recheck earlier annotations affected by it.

## 12. Quality-control rules

The semantic validator must reject or flag:

- Inconsistent AD number/base/revision/emergency fields
- Correction status without correction evidence
- Evidence page numbers outside the PDF page count
- Missing or duplicate evidence IDs
- Broken action/applicability/publication/requirement references
- Repetition without an interval
- Terminating action without linked requirements
- A supersedure target equal to the current AD
- Candidate relationships inside an approved gold record
- Same-number correction links without a distinct target record/logical version
- Correction record/version targets that do not resolve to the same annotation
- SB/STC/TCDS identifiers used as AD targets
- Dates normalized without raw source wording
- Confidence attached to human-origin assertions
- An `explicit_none` assertion paired with a populated value
- Train/validation/test split groups that differ inside one `base_ad_number` family
- Train/validation/test splits that differ inside an exact- or near-duplicate cluster
- Approval performed by the same person who supplied the annotation

Manual review is mandatory for OCR/visual transcription, header-filename mismatch, ambiguity/conflict, complex tables, same-version conflicts, and supersedure before `manually_verified=true`.

## 13. Completion criteria for Step 2

Step 2 is complete when:

- The Draft 2020-12 schema is valid.
- The blank template and example pass schema validation.
- The semantic validator passes the example and rejects known-invalid fixtures.
- The controlled vocabularies and this guideline use matching labels.
- A versioned package is stored beside the corpus metadata.
- Schema/guideline version `1.0.0` is frozen before the 30-AD pilot.

## 14. Primary references

- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
- [EASA AD Writing Instructions, WI.CAP.00002](https://www.easa.europa.eu/en/document-library/certification-procedures/easa-ad-writing-instructions)
- [EASA Airworthiness Directives FAQ](https://www.easa.europa.eu/en/the-agency/faqs/airworthiness-directives-ads)
- Project literature synthesis: schema-constrained extraction, hierarchy preservation, source evidence, and human validation recommendations supplied with this capstone.
