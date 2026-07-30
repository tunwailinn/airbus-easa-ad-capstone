# Step 3 no-supersedure extension selection

Frozen: 2026-07-30  
Extension size: 20 logical publications  
Existing 30-record pilot: unchanged

## Decision

This is a separate human-review extension, not an in-place mutation of the
validated 30-record `gold/` set. It contains 10 publications from 2006-2018
and 10 from 2019-2026. Every selected record is an original, uncorrected
publication with no incoming or outgoing supersedure edge in the Step 1
manifest and an explicit `Supersedure: None` header in cached source text.

The screening labels and no-supersedure decision must still be visually
confirmed against the verified PDF before a record can be approved as gold.

## Frozen selection

| AD | Cohort | Aircraft family/group | ATA | Pages | Screening strata | Selection rationale |
|---|---|---|---|---:|---|---|
| 2006-0077 | 2006-2018 | A300/A310 | 33 | 2 | legacy_format|complex_applicability | Legacy A310/A300-600 emergency-lighting case; adds ATA 33 coverage. |
| 2007-0249 | 2006-2018 | A318-A321 | 26 | 2 | legacy_format|simple | Short cargo fire-extinguishing wiring inspection; adds ATA 26 coverage. |
| 2008-0066 | 2006-2018 | A310 | 54 | 2 | legacy_format|threshold_logic | A310 pylon structural inspection with model-dependent thresholds; adds ATA 54. |
| 2009-0171 | 2006-2018 | A300/A310/A300-600ST | 26|29 | 3 | multi_ata|broad_family | Legacy and Beluga multi-ATA valve case spanning ATA 26 and 29. |
| 2010-0271 | 2006-2018 | A330/A340 | 22 | 2 | operational_procedure|simple | Short A330/A340 autopilot and autothrust procedure; adds ATA 22. |
| 2011-0098 | 2006-2018 | Multi-family | 25 | 6 | broad_family|long_document|multi_manufacturer | Six-page passenger-seat case spanning Airbus, Boeing and Fokker types. |
| 2012-0259 | 2006-2018 | A340 | 38 | 2 | simple|modification | Short A340-500/-600 waste-water modification; adds ATA 38 coverage. |
| 2013-0011 | 2006-2018 | A318-A321 | 56 | 3 | complex_applicability|inspection_modification | A320-family sliding-window seal case; adds ATA 56 coverage. |
| 2016-0175 | 2006-2018 | A380 | 36 | 3 | part_conditioned|replacement | A380 pneumatic duct material replacement; adds A380 and ATA 36 coverage. |
| 2018-0246 | 2006-2018 | A350 | 36 | 3 | afm_amendment|modification | A350 bleed-air modification with an AFM amendment requirement. |
| 2019-0188 | 2019-2026 | A300-600ST | 29 | 3 | functional_test|complex_compliance | Beluga hydraulic reservoir line functional tests; recent ATA 29 case. |
| 2020-0016 | 2019-2026 | A380 | 36 | 3 | configuration_grouped|part_conditioned | A380 bleed-air valve modification/replacement with configuration groups. |
| 2021-0221 | 2019-2026 | A380 | 21|24|25|28|53|71 | 5 | multi_ata|complex_applicability|table_heavy | Six-ATA A380 production-conformity case with multiple independent actions. |
| 2021-0286 | 2019-2026 | A330 | 11 | 3 | stc_conditioned|third_party_dah | A330 MRTT STC-conditioned placard installation; adds ATA 11. |
| 2022-0058 | 2019-2026 | A300/A310/A300-600ST | 56 | 6 | long_document|table_heavy|complex_applicability | Six-page windshield inspection spanning legacy Airbus and Beluga types. |
| 2023-0057 | 2019-2026 | A330/A340 | 49 | 3 | part_conditioned|replacement | A330/A340 APU fuel-control-unit replacement; adds ATA 49. |
| 2024-0001 | 2019-2026 | A310 | 05 | 4 | maintenance_program|complex_compliance | A310 ALS/maintenance-program amendment; adds ATA 05. |
| 2025-0138 | 2019-2026 | A350 | 35 | 3 | part_conditioned|records_review | A350 chemical oxygen generator replacement; adds ATA 35. |
| 2025-0181 | 2019-2026 | A350 | 42 | 4 | serial_number_list|appendix|replacement | A350 CPIOM replacement with an affected serial-number appendix; adds ATA 42. |
| 2026-0100 | 2019-2026 | A330 | 71 | 4 | part_conditioned|inspection | A330 intake nose-cowl inspection; recent ATA 71 case. |

## Coverage summary

- Cohorts: {'2006-2018': 10, '2019-2026': 10}
- Families/groups: {'A300-600ST': 1, 'A300/A310': 1, 'A300/A310/A300-600ST': 2, 'A310': 2, 'A318-A321': 2, 'A330': 2, 'A330/A340': 2, 'A340': 1, 'A350': 3, 'A380': 3, 'Multi-family': 1}
- ATA chapters: {'05': 1, '11': 1, '21': 1, '22': 1, '24': 1, '25': 2, '26': 2, '28': 1, '29': 2, '33': 1, '35': 1, '36': 3, '38': 1, '42': 1, '49': 1, '53': 1, '54': 1, '56': 2, '71': 2}
- ATA chapters new relative to the original 30: ['05', '11', '21', '22', '26', '29', '33', '35', '36', '38', '42', '49', '54', '56']
- New ATA chapter count: 14
- Short documents (2-3 pages): 14
- Medium documents (4-5 pages): 4
- Long documents (6+ pages): 2
- Revisions: 0
- Corrections: 0
- Near-duplicate-candidate endpoints: 0
- Manifest supersedure edges: 0

## Approval boundary

Selection and automated integrity checks do not make these records gold.
Each PDF and annotation must be compared during human review. Only after
explicit approval should a new 50-record dataset version and matching frozen
validator configuration be created.
