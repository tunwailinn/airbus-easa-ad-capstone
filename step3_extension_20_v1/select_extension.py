#!/usr/bin/env python3
"""Freeze the 20-publication no-supersedure Step 3 extension.

The extension is deliberately separate from ``step3_pilot/gold`` so the
validated 30-record pilot remains immutable. Selection uses only cached Step 1
metadata, extracted text, and downloader provenance; it never modifies
``corpus_raw``.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
PILOT = PROJECT / "step3_pilot"
SOURCE = PILOT / "source_metadata"
OUTPUT = ROOT / "selection"
DOWNLOADER_MANIFEST = PROJECT / "easa_airbus_ad_manifest.csv"
VERIFICATION_REPORT = ROOT / "source_verification_report.json"
FROZEN_ON = "2026-07-30"


SELECTION = [
    # 2006-2018 (10)
    dict(
        ad="2006-0077",
        cohort="2006-2018",
        family="A300/A310",
        ata="33",
        strata="legacy_format|complex_applicability",
        rationale="Legacy A310/A300-600 emergency-lighting case; adds ATA 33 coverage.",
    ),
    dict(
        ad="2007-0249",
        cohort="2006-2018",
        family="A318-A321",
        ata="26",
        strata="legacy_format|simple",
        rationale="Short cargo fire-extinguishing wiring inspection; adds ATA 26 coverage.",
    ),
    dict(
        ad="2008-0066",
        cohort="2006-2018",
        family="A310",
        ata="54",
        strata="legacy_format|threshold_logic",
        rationale="A310 pylon structural inspection with model-dependent thresholds; adds ATA 54.",
    ),
    dict(
        ad="2009-0171",
        cohort="2006-2018",
        family="A300/A310/A300-600ST",
        ata="26|29",
        strata="multi_ata|broad_family",
        rationale="Legacy and Beluga multi-ATA valve case spanning ATA 26 and 29.",
    ),
    dict(
        ad="2010-0271",
        cohort="2006-2018",
        family="A330/A340",
        ata="22",
        strata="operational_procedure|simple",
        rationale="Short A330/A340 autopilot and autothrust procedure; adds ATA 22.",
    ),
    dict(
        ad="2011-0098",
        cohort="2006-2018",
        family="Multi-family",
        ata="25",
        strata="broad_family|long_document|multi_manufacturer",
        rationale="Six-page passenger-seat case spanning Airbus, Boeing and Fokker types.",
    ),
    dict(
        ad="2012-0259",
        cohort="2006-2018",
        family="A340",
        ata="38",
        strata="simple|modification",
        rationale="Short A340-500/-600 waste-water modification; adds ATA 38 coverage.",
    ),
    dict(
        ad="2013-0011",
        cohort="2006-2018",
        family="A318-A321",
        ata="56",
        strata="complex_applicability|inspection_modification",
        rationale="A320-family sliding-window seal case; adds ATA 56 coverage.",
    ),
    dict(
        ad="2016-0175",
        cohort="2006-2018",
        family="A380",
        ata="36",
        strata="part_conditioned|replacement",
        rationale="A380 pneumatic duct material replacement; adds A380 and ATA 36 coverage.",
    ),
    dict(
        ad="2018-0246",
        cohort="2006-2018",
        family="A350",
        ata="36",
        strata="afm_amendment|modification",
        rationale="A350 bleed-air modification with an AFM amendment requirement.",
    ),
    # 2019-2026 (10)
    dict(
        ad="2019-0188",
        cohort="2019-2026",
        family="A300-600ST",
        ata="29",
        strata="functional_test|complex_compliance",
        rationale="Beluga hydraulic reservoir line functional tests; recent ATA 29 case.",
    ),
    dict(
        ad="2020-0016",
        cohort="2019-2026",
        family="A380",
        ata="36",
        strata="configuration_grouped|part_conditioned",
        rationale="A380 bleed-air valve modification/replacement with configuration groups.",
    ),
    dict(
        ad="2021-0221",
        cohort="2019-2026",
        family="A380",
        ata="21|24|25|28|53|71",
        strata="multi_ata|complex_applicability|table_heavy",
        rationale="Six-ATA A380 production-conformity case with multiple independent actions.",
    ),
    dict(
        ad="2021-0286",
        cohort="2019-2026",
        family="A330",
        ata="11",
        strata="stc_conditioned|third_party_dah",
        rationale="A330 MRTT STC-conditioned placard installation; adds ATA 11.",
    ),
    dict(
        ad="2022-0058",
        cohort="2019-2026",
        family="A300/A310/A300-600ST",
        ata="56",
        strata="long_document|table_heavy|complex_applicability",
        rationale="Six-page windshield inspection spanning legacy Airbus and Beluga types.",
    ),
    dict(
        ad="2023-0057",
        cohort="2019-2026",
        family="A330/A340",
        ata="49",
        strata="part_conditioned|replacement",
        rationale="A330/A340 APU fuel-control-unit replacement; adds ATA 49.",
    ),
    dict(
        ad="2024-0001",
        cohort="2019-2026",
        family="A310",
        ata="05",
        strata="maintenance_program|complex_compliance",
        rationale="A310 ALS/maintenance-program amendment; adds ATA 05.",
    ),
    dict(
        ad="2025-0138",
        cohort="2019-2026",
        family="A350",
        ata="35",
        strata="part_conditioned|records_review",
        rationale="A350 chemical oxygen generator replacement; adds ATA 35.",
    ),
    dict(
        ad="2025-0181",
        cohort="2019-2026",
        family="A350",
        ata="42",
        strata="serial_number_list|appendix|replacement",
        rationale="A350 CPIOM replacement with an affected serial-number appendix; adds ATA 42.",
    ),
    dict(
        ad="2026-0100",
        cohort="2019-2026",
        family="A330",
        ata="71",
        strata="part_conditioned|inspection",
        rationale="A330 intake nose-cowl inspection; recent ATA 71 case.",
    ),
]


def truthy(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().eq("true")


def verification_status(selected: pd.DataFrame) -> str:
    if not VERIFICATION_REPORT.is_file():
        return "selected_pending_pdf_confirmation"
    try:
        report = json.loads(VERIFICATION_REPORT.read_text(encoding="utf-8"))
        documents = {item["ad_number"]: item for item in report["documents"]}
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return "selected_pending_pdf_confirmation"
    if report.get("status") != "complete" or len(documents) != len(selected):
        return "selected_pending_pdf_confirmation"
    for row in selected.itertuples(index=False):
        item = documents.get(row.ad_number, {})
        if (
            item.get("actual_sha256") != row.file_sha256
            or int(item.get("actual_page_count") or 0) != int(row.page_count)
            or item.get("pdf_status") not in {"downloaded_verified", "reused_verified"}
        ):
            return "selected_pending_pdf_confirmation"
    return "selected_pdf_hash_verified"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    manifest = pd.read_csv(SOURCE / "corpus_manifest.csv", dtype=str, keep_default_na=False)
    extracted = pd.read_parquet(SOURCE / "corpus_extracted_text.parquet")
    near = pd.read_csv(SOURCE / "near_duplicate_candidates.csv", dtype=str, keep_default_na=False)
    provenance = pd.read_csv(DOWNLOADER_MANIFEST, dtype=str, keep_default_na=False)
    provenance = provenance.drop_duplicates("filename", keep="last")
    pilot = pd.read_csv(PILOT / "selection" / "pilot_selection.csv", dtype=str, keep_default_na=False)

    spec = pd.DataFrame(SELECTION).rename(columns={"ad": "ad_number"})
    if len(spec) != 20 or spec.ad_number.nunique() != 20:
        raise RuntimeError("Extension selection must contain exactly 20 unique ADs")

    eligible = manifest[
        manifest.ad_number.ne("")
        & manifest.duplicate_of.eq("")
        & manifest.extraction_status.eq("ok")
        & ~truthy(manifest.needs_ocr)
        & truthy(manifest.is_airbus_sas_detected)
    ].copy()
    eligible = eligible.sort_values("relative_path").drop_duplicates("logical_version_key", keep="first")

    selected = spec.merge(eligible, on="ad_number", how="left", validate="one_to_one", indicator=True)
    missing = selected.loc[selected._merge.ne("both"), "ad_number"].tolist()
    if missing:
        raise RuntimeError(f"Selected ADs missing from eligible corpus: {missing}")
    selected = selected.drop(columns="_merge")

    selected = selected.merge(
        provenance[["filename", "subject", "pdf_url", "detail_url", "drive_file_id"]],
        left_on="file_name",
        right_on="filename",
        how="left",
        validate="one_to_one",
    ).drop(columns="filename")
    if selected.drive_file_id.eq("").any():
        missing_drive = selected.loc[selected.drive_file_id.eq(""), "ad_number"].tolist()
        raise RuntimeError(f"Missing Drive provenance: {missing_drive}")

    text_by_ad = (
        extracted[extracted.ad_number.isin(selected.ad_number)]
        .drop_duplicates("ad_number")
        .set_index("ad_number")
        .text.astype(str)
        .to_dict()
    )
    missing_text = sorted(set(selected.ad_number) - set(text_by_ad))
    if missing_text:
        raise RuntimeError(f"Missing cached extracted text: {missing_text}")

    near_endpoints = set(near.ad_number_a) | set(near.ad_number_b)
    disallowed_name = re.compile(r"(superseded|corrected|correction|_cn\b)", re.IGNORECASE)
    disallowed_subject = re.compile(r"(superseded|cancelled|correction|corrected)", re.IGNORECASE)
    header_pattern = re.compile(r"Supersedure\s*:\s*None\b", re.IGNORECASE)

    violations: list[str] = []
    for row in selected.itertuples(index=False):
        if row.ad_number in set(pilot.ad_number):
            violations.append(f"{row.ad_number}: already in frozen 30-record pilot")
        if row.ad_number in near_endpoints:
            violations.append(f"{row.ad_number}: near-duplicate candidate endpoint")
        if row.revision_number != "0" or str(row.has_revision_history).lower() == "true":
            violations.append(f"{row.ad_number}: revision or revision-history record")
        if str(row.is_correction).lower() == "true":
            violations.append(f"{row.ad_number}: corrected publication")
        if row.supersedes_ad_numbers or row.superseded_by_ad_numbers:
            violations.append(f"{row.ad_number}: manifest supersedure edge")
        if disallowed_name.search(row.file_name):
            violations.append(f"{row.ad_number}: disallowed filename marker")
        if disallowed_subject.search(row.subject):
            violations.append(f"{row.ad_number}: disallowed subject marker")
        if not header_pattern.search(text_by_ad[row.ad_number][:6000]):
            violations.append(f"{row.ad_number}: no explicit 'Supersedure: None' in source header")
    if violations:
        raise RuntimeError("Selection hygiene failure:\n- " + "\n- ".join(violations))

    selected["base_year"] = selected.base_ad_number.str[:4].astype(int)
    selected["supersedure_header"] = "None"
    selected["human_review"] = "required"
    selected["selection_frozen_on"] = FROZEN_ON
    selected["selection_status"] = verification_status(selected)

    if selected.groupby("cohort").size().to_dict() != {"2006-2018": 10, "2019-2026": 10}:
        raise RuntimeError("Selection must have a 10/10 old/recent cohort split")
    if selected.logical_version_key.nunique() != 20 or selected.file_sha256.nunique() != 20:
        raise RuntimeError("Logical publications and PDF hashes must be unique")

    pilot_atas = {chapter for value in pilot.ata for chapter in value.split("|")}
    extension_atas = {chapter for value in selected.ata for chapter in value.split("|")}
    new_atas = sorted(extension_atas - pilot_atas)
    if len(new_atas) < 14:
        raise RuntimeError(f"Expected at least 14 new ATA chapters, got {new_atas}")
    if selected.family.nunique() < 8:
        raise RuntimeError("Expected at least eight family/group labels")

    columns = [
        "ad_number",
        "base_ad_number",
        "base_year",
        "cohort",
        "family",
        "ata",
        "strata",
        "rationale",
        "logical_version_key",
        "revision_number",
        "is_correction",
        "issue_date",
        "page_count",
        "file_name",
        "relative_path",
        "file_instance_id",
        "content_id",
        "file_sha256",
        "normalized_text_sha256",
        "drive_file_id",
        "pdf_url",
        "detail_url",
        "supersedes_ad_numbers",
        "superseded_by_ad_numbers",
        "supersedure_header",
        "human_review",
        "selection_status",
        "selection_frozen_on",
    ]
    selected = selected[columns].sort_values(
        ["cohort", "base_year", "ad_number"], ascending=[True, True, True]
    )
    selected.to_csv(OUTPUT / "extension_selection.csv", index=False)
    (OUTPUT / "extension_selection.json").write_text(
        json.dumps(selected.to_dict(orient="records"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    strata_counts = Counter(label for value in selected.strata for label in value.split("|"))
    family_counts = selected.family.value_counts().sort_index().to_dict()
    ata_counts = Counter(chapter for value in selected.ata for chapter in value.split("|"))
    rows = [
        f"| {r.ad_number} | {r.cohort} | {r.family} | {r.ata} | {r.page_count} | {r.strata} | {r.rationale} |"
        for r in selected.itertuples(index=False)
    ]
    report = f"""# Step 3 no-supersedure extension selection

Frozen: {FROZEN_ON}  
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
{chr(10).join(rows)}

## Coverage summary

- Cohorts: {selected.groupby('cohort').size().to_dict()}
- Families/groups: {family_counts}
- ATA chapters: {dict(sorted(ata_counts.items()))}
- ATA chapters new relative to the original 30: {new_atas}
- New ATA chapter count: {len(new_atas)}
- Short documents (2-3 pages): {int(selected.page_count.astype(int).between(2, 3).sum())}
- Medium documents (4-5 pages): {int(selected.page_count.astype(int).between(4, 5).sum())}
- Long documents (6+ pages): {int(selected.page_count.astype(int).ge(6).sum())}
- Revisions: 0
- Corrections: 0
- Near-duplicate-candidate endpoints: 0
- Manifest supersedure edges: 0

## Approval boundary

Selection and automated integrity checks do not make these records gold.
Each PDF and annotation must be compared during human review. Only after
explicit approval should a new 50-record dataset version and matching frozen
validator configuration be created.
"""
    (OUTPUT / "selection_report.md").write_text(report, encoding="utf-8")

    sha_lines = [f"{r.file_sha256}  {r.file_name}" for r in selected.itertuples(index=False)]
    (OUTPUT / "selected_sources.sha256").write_text("\n".join(sha_lines) + "\n", encoding="utf-8")

    print(f"Wrote {len(selected)} selected publications to {OUTPUT}")
    print("Cohorts:", selected.groupby("cohort").size().to_dict())
    print("New ATA chapters:", new_atas)
    print("Selection status:", selected.selection_status.iloc[0])


if __name__ == "__main__":
    main()
