# Step 3 pilot selection report

Frozen: 2026-07-22  
Corpus snapshot: 1,809 PDFs / 1,809 logical publications  
Selection unit: one canonical PDF per `logical_version_key`

## Decision

The pilot contains exactly 30 EASA AD publications: 15 whose `base_ad_number` year is 2019-2026 and 15 whose year is 2006-2018. This is purposive test-set design, not a population-representative sample. Rare and failure-prone cases are deliberately oversampled.

The qualitative strata below are selection-screening labels. Each must be confirmed against the rendered PDF during annotation before the record can become gold.

## Frozen selection

| AD | Cohort | Airbus family | ATA | Screening strata | Double annotate | Selection rationale |
|---|---|---|---|---|---|---|
| 2019-0011R2 | 2019-2026 | A300 | 53 | revised|complex_applicability|table_heavy | no | R2 A300 case with tabular scope and production-modification-conditioned applicability. |
| 2019-0183 | 2019-2026 | A350 | 92 | simple | yes | Two-page original AD with one modification action and one non-repetitive compliance rule. |
| 2020-0028 | 2019-2026 | A350 | 78 | simple | no | Short original A350 AD used as a simple recent baseline. |
| 2020-0085R1 | 2019-2026 | A318-A321 | 71 | revised|complex_applicability|table_heavy | yes | R1 with structured supersedure and table-dependent engine applicability. |
| 2021-0087 | 2019-2026 | A380 | 73 | simple | no | Short original A380 AD used as a simple recent baseline. |
| 2021-0242 | 2019-2026 | A318-A321 | 53 | complex_applicability|table_heavy | no | Configuration-sensitive applicability and an explicit prior-AD relationship. |
| 2022-0026 | 2019-2026 | A318-A321 | 25 | complex_applicability|table_heavy|long_document | no | Twelve-page AD with tables/appendix and two explicit superseded ADs. |
| 2022-0197 | 2019-2026 | A330/A340 | 28 | complex_applicability|table_heavy|long_document | no | Long multi-family fuel-system AD with explicit supersedure. |
| 2023-0093R1 | 2019-2026 | A318-A321 | 32|92 | revised|complex_applicability|table_heavy | yes | R1 with two ATA chapters, tables, and a prior revised AD relationship. |
| 2024-0038 | 2019-2026 | A318-A321 | 25 | complex_applicability|table_heavy|long_document|near_duplicate_cluster | no | First member of the complete three-publication recent near-duplicate component. |
| 2024-0095 | 2019-2026 | A330 | 53 | complex_applicability|table_heavy|stc_conditioned | no | STC/configuration-conditioned applicability case. |
| 2025-0008 | 2019-2026 | A350 | 27 | table_heavy | no | A350 case whose replacement timing depends on Table 1 and compound first/later logic. |
| 2025-0068 | 2019-2026 | A318-A321 | 25 | complex_applicability|table_heavy|long_document|near_duplicate_cluster | yes | First member of the recent high-similarity pair; explicitly supersedes 2024-0038. |
| 2026-0017 | 2019-2026 | A318-A321 | 25 | complex_applicability|table_heavy|long_document|near_duplicate_cluster | yes | Second member of the recent high-similarity pair; explicitly supersedes 2025-0068. |
| 2026-0079 | 2019-2026 | A318-A321 | 23 | complex_applicability|stc_conditioned | no | Third-party approval-holder case with manufacturer wording 'Airbus, formerly Airbus Industrie'. |
| 2006-0047 | 2006-2018 | A330 | 25 | complex_applicability | no | Early-format widebody AD with repetitive/terminating-action logic. |
| 2007-0022 | 2006-2018 | A300-600ST | 24 | simple | no | Short early-format Beluga AD and negative/none relationship case. |
| 2007-0278 | 2006-2018 | A330/A340 | 28 | corrected|complex_applicability | yes | PDF-confirmed correction with explicit supersedure of 2006-0322. |
| 2008-0012 | 2006-2018 | A330/A340 | 55 | complex_applicability | no | Part-number-dependent applicability and compound compliance without an AD-internal table. |
| 2009-0025 | 2006-2018 | A318-A321 | 57 | corrected | yes | PDF-confirmed correction with an explicit-none supersedure field. |
| 2009-0141 | 2006-2018 | A318-A321 | 55 | complex_applicability|table_heavy|long_document | no | Eight-page table/appendix case later superseded by another selected AD. |
| 2010-0164 | 2006-2018 | A318-A321 | 55 | complex_applicability|table_heavy|long_document | yes | Seventeen-page table-heavy AD explicitly superseding selected AD 2009-0141. |
| 2011-0112 | 2006-2018 | A300 | 27 | simple | no | Two-page original AD with one installation action and one non-repetitive compliance rule. |
| 2012-0175R2 | 2006-2018 | A318-A321 | 27 | revised|complex_applicability|table_heavy | no | R2 flight-controls case whose threshold is in Table 1 and affected parts in Appendix 1. |
| 2013-0234R2 | 2006-2018 | A300/A310 | 57 | revised|complex_applicability|table_heavy | no | R2 legacy-widebody case with exclusions and tabular scope. |
| 2014-0062 | 2006-2018 | A330 | 78 | other | no | Short but non-simple case with conditional replacement, previous-action credit and installation constraint. |
| 2015-0135R3 | 2006-2018 | A318-A321 | 34 | revised|complex_applicability|table_heavy|long_document | no | R3, eight-page avionics case with tables and mature revision history. |
| 2016-0095 | 2006-2018 | A380 | 57 | complex_applicability|table_heavy|near_duplicate_cluster | yes | First member of the older high-similarity pair. |
| 2017-0013 | 2006-2018 | A380 | 57 | complex_applicability|table_heavy|near_duplicate_cluster | yes | Second member of the older pair; explicitly supersedes selected AD 2016-0095. |
| 2018-0108 | 2006-2018 | A350 | 52 | simple | no | Short original A350 AD used as a simple older baseline. |

## Coverage summary

- Cohorts: {'2006-2018': 15, '2019-2026': 15}
- Base-AD years: {'2006-2018:2006': 1, '2006-2018:2007': 2, '2006-2018:2008': 1, '2006-2018:2009': 2, '2006-2018:2010': 1, '2006-2018:2011': 1, '2006-2018:2012': 1, '2006-2018:2013': 1, '2006-2018:2014': 1, '2006-2018:2015': 1, '2006-2018:2016': 1, '2006-2018:2017': 1, '2006-2018:2018': 1, '2019-2026:2019': 2, '2019-2026:2020': 2, '2019-2026:2021': 2, '2019-2026:2022': 2, '2019-2026:2023': 1, '2019-2026:2024': 2, '2019-2026:2025': 2, '2019-2026:2026': 2}
- Screening strata: {'complex_applicability': 21, 'corrected': 2, 'long_document': 8, 'near_duplicate_cluster': 5, 'other': 1, 'revised': 6, 'simple': 6, 'stc_conditioned': 2, 'table_heavy': 18}
- Families: {'A300': 2, 'A300-600ST': 1, 'A300/A310': 1, 'A318-A321': 13, 'A330': 3, 'A330/A340': 3, 'A350': 4, 'A380': 3}
- ATA chapters: {'23': 1, '24': 1, '25': 5, '27': 3, '28': 2, '32': 1, '34': 1, '52': 1, '53': 3, '55': 3, '57': 4, '71': 1, '73': 1, '78': 2, '92': 2}
- Revised publications: 6
- PDF-confirmed corrected publications: 2
- Long documents (screening label): 8
- Simple baselines (screening label): 6
- Double-annotation assignments: 10 (5 recent, 5 older)

## Required paired cases

- Complete recent near-duplicate candidate component: `2024-0038`, `2025-0068` and `2026-0017`.
- Older near-duplicate candidate pair: `2016-0095` and `2017-0013`.
- Cross-number supersedure/reissue pair inside the pilot: `2009-0141` and `2010-0164` (the latter explicitly supersedes the former in Step 1 screening).
- Corrected publications: `2007-0278` and `2009-0025`. The cached corpus contains only the corrected physical publication for each, so no nonexistent uncorrected record is fabricated.

Near-duplicate labels remain candidates until both PDFs are compared. Candidate similarity never authorizes merging or a supersedure edge.

## Leakage and review controls

- `2007-0178` is excluded because the Step 2 package already uses it as an example.
- Revisions, corrections, base-number families, and near-duplicate components must stay together in any later development/held-out split.
- Blind annotator packets must hide Step 1 supersedure predictions, near-duplicate labels, and this rationale.
- Annotator B receives the 10 marked records from the same blank template and cannot see Annotator A output.
- Gold approval requires PDF review, page evidence, a separate reviewer/adjudicator, strict schema validation, and the Step 3 completeness checklist.
