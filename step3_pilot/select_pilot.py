#!/usr/bin/env python3
"""Freeze the 30-publication Step 3 pilot selection.

This script reads only the cached Step 1 reports and the downloader provenance
manifest.  It does not open or modify corpus_raw.  The qualitative labels in
SELECTION are screening labels that must be visually confirmed during PDF
annotation; they are not gold annotations.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source_metadata"
OUTPUT = ROOT / "selection"
DOWNLOADER_MANIFEST = ROOT.parent / "easa_airbus_ad_manifest.csv"
VERIFICATION_REPORT = ROOT / "source_verification_report.json"
FROZEN_ON = "2026-07-22"


# The year is the year embedded in base_ad_number. Labels are intentionally
# multi-valued and reflect selection rationale, not completed annotation.
SELECTION = [
    # 2019-2026 (15)
    dict(ad="2019-0011R2", cohort="2019-2026", family="A300", ata="53",
         strata="revised|complex_applicability|table_heavy",
         rationale="R2 A300 case with tabular scope and production-modification-conditioned applicability."),
    dict(ad="2019-0183", cohort="2019-2026", family="A350", ata="92",
         strata="simple",
         rationale="Two-page original AD with one modification action and one non-repetitive compliance rule."),
    dict(ad="2020-0028", cohort="2019-2026", family="A350", ata="78",
         strata="simple",
         rationale="Short original A350 AD used as a simple recent baseline."),
    dict(ad="2020-0085R1", cohort="2019-2026", family="A318-A321", ata="71",
         strata="revised|complex_applicability|table_heavy",
         rationale="R1 with structured supersedure and table-dependent engine applicability."),
    dict(ad="2021-0087", cohort="2019-2026", family="A380", ata="73",
         strata="simple",
         rationale="Short original A380 AD used as a simple recent baseline."),
    dict(ad="2021-0242", cohort="2019-2026", family="A318-A321", ata="53",
         strata="complex_applicability|table_heavy",
         rationale="Configuration-sensitive applicability and an explicit prior-AD relationship."),
    dict(ad="2022-0026", cohort="2019-2026", family="A318-A321", ata="25",
         strata="complex_applicability|table_heavy|long_document",
         rationale="Twelve-page AD with tables/appendix and two explicit superseded ADs."),
    dict(ad="2022-0197", cohort="2019-2026", family="A330/A340", ata="28",
         strata="complex_applicability|table_heavy|long_document",
         rationale="Long multi-family fuel-system AD with explicit supersedure."),
    dict(ad="2023-0093R1", cohort="2019-2026", family="A318-A321", ata="32|92",
         strata="revised|complex_applicability|table_heavy",
         rationale="R1 with two ATA chapters, tables, and a prior revised AD relationship."),
    dict(ad="2024-0038", cohort="2019-2026", family="A318-A321", ata="25",
         strata="complex_applicability|table_heavy|long_document|near_duplicate_cluster",
         rationale="First member of the complete three-publication recent near-duplicate component."),
    dict(ad="2024-0095", cohort="2019-2026", family="A330", ata="53",
         strata="complex_applicability|table_heavy|stc_conditioned",
         rationale="STC/configuration-conditioned applicability case."),
    dict(ad="2025-0068", cohort="2019-2026", family="A318-A321", ata="25",
         strata="complex_applicability|table_heavy|long_document|near_duplicate_cluster",
         rationale="First member of the recent high-similarity pair; explicitly supersedes 2024-0038."),
    dict(ad="2025-0008", cohort="2019-2026", family="A350", ata="27",
         strata="table_heavy",
         rationale="A350 case whose replacement timing depends on Table 1 and compound first/later logic."),
    dict(ad="2026-0017", cohort="2019-2026", family="A318-A321", ata="25",
         strata="complex_applicability|table_heavy|long_document|near_duplicate_cluster",
         rationale="Second member of the recent high-similarity pair; explicitly supersedes 2025-0068."),
    dict(ad="2026-0079", cohort="2019-2026", family="A318-A321", ata="23",
         strata="complex_applicability|stc_conditioned",
         rationale="Third-party approval-holder case with manufacturer wording 'Airbus, formerly Airbus Industrie'."),

    # 2006-2018 (15)
    dict(ad="2006-0047", cohort="2006-2018", family="A330", ata="25",
         strata="complex_applicability",
         rationale="Early-format widebody AD with repetitive/terminating-action logic."),
    dict(ad="2007-0022", cohort="2006-2018", family="A300-600ST", ata="24",
         strata="simple",
         rationale="Short early-format Beluga AD and negative/none relationship case."),
    dict(ad="2007-0278", cohort="2006-2018", family="A330/A340", ata="28",
         strata="corrected|complex_applicability",
         rationale="PDF-confirmed correction with explicit supersedure of 2006-0322."),
    dict(ad="2008-0012", cohort="2006-2018", family="A330/A340", ata="55",
         strata="complex_applicability",
         rationale="Part-number-dependent applicability and compound compliance without an AD-internal table."),
    dict(ad="2009-0025", cohort="2006-2018", family="A318-A321", ata="57",
         strata="corrected",
         rationale="PDF-confirmed correction with an explicit-none supersedure field."),
    dict(ad="2009-0141", cohort="2006-2018", family="A318-A321", ata="55",
         strata="complex_applicability|table_heavy|long_document",
         rationale="Eight-page table/appendix case later superseded by another selected AD."),
    dict(ad="2010-0164", cohort="2006-2018", family="A318-A321", ata="55",
         strata="complex_applicability|table_heavy|long_document",
         rationale="Seventeen-page table-heavy AD explicitly superseding selected AD 2009-0141."),
    dict(ad="2011-0112", cohort="2006-2018", family="A300", ata="27",
         strata="simple",
         rationale="Two-page original AD with one installation action and one non-repetitive compliance rule."),
    dict(ad="2012-0175R2", cohort="2006-2018", family="A318-A321", ata="27",
         strata="revised|complex_applicability|table_heavy",
         rationale="R2 flight-controls case whose threshold is in Table 1 and affected parts in Appendix 1."),
    dict(ad="2013-0234R2", cohort="2006-2018", family="A300/A310", ata="57",
         strata="revised|complex_applicability|table_heavy",
         rationale="R2 legacy-widebody case with exclusions and tabular scope."),
    dict(ad="2014-0062", cohort="2006-2018", family="A330", ata="78",
         strata="other",
         rationale="Short but non-simple case with conditional replacement, previous-action credit and installation constraint."),
    dict(ad="2015-0135R3", cohort="2006-2018", family="A318-A321", ata="34",
         strata="revised|complex_applicability|table_heavy|long_document",
         rationale="R3, eight-page avionics case with tables and mature revision history."),
    dict(ad="2016-0095", cohort="2006-2018", family="A380", ata="57",
         strata="complex_applicability|table_heavy|near_duplicate_cluster",
         rationale="First member of the older high-similarity pair."),
    dict(ad="2017-0013", cohort="2006-2018", family="A380", ata="57",
         strata="complex_applicability|table_heavy|near_duplicate_cluster",
         rationale="Second member of the older pair; explicitly supersedes selected AD 2016-0095."),
    dict(ad="2018-0108", cohort="2006-2018", family="A350", ata="52",
         strata="simple",
         rationale="Short original A350 AD used as a simple older baseline."),
]

DOUBLE_ANNOTATE = {
    "2019-0183", "2020-0085R1", "2023-0093R1", "2025-0068", "2026-0017",
    "2007-0278", "2009-0025", "2010-0164", "2016-0095", "2017-0013",
}


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, item: str) -> str:
        self.parent.setdefault(item, item)
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[b] = a


def truthy(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().eq("true")


def verified_selection_status(selected: pd.DataFrame) -> str:
    """Return a final status only when the source report proves all 30 PDFs."""

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
            item.get("expected_sha256") != row.file_sha256
            or item.get("actual_sha256") != row.file_sha256
            or int(item.get("actual_page_count") or 0) != int(row.page_count)
            or item.get("pdf_status")
            not in {"downloaded_verified", "resumed_verified", "reused_verified"}
            or item.get("page_text_status")
            not in {"extracted_verified", "reused_verified"}
        ):
            return "selected_pending_pdf_confirmation"
    return "selected_pdf_hash_verified"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    manifest = pd.read_csv(SOURCE / "corpus_manifest.csv", dtype=str, keep_default_na=False)
    near = pd.read_csv(SOURCE / "near_duplicate_candidates.csv", dtype=str, keep_default_na=False)
    provenance = pd.read_csv(DOWNLOADER_MANIFEST, dtype=str, keep_default_na=False)
    provenance = provenance.drop_duplicates("filename", keep="last")

    spec = pd.DataFrame(SELECTION).rename(columns={"ad": "ad_number"})
    assert len(spec) == 30 and spec.ad_number.nunique() == 30

    eligible = manifest[
        manifest.ad_number.ne("")
        & manifest.duplicate_of.eq("")
        & manifest.extraction_status.eq("ok")
        & ~truthy(manifest.needs_ocr)
    ].copy()
    eligible = eligible.sort_values("relative_path").drop_duplicates("logical_version_key", keep="first")

    selected = spec.merge(eligible, on="ad_number", how="left", validate="one_to_one", indicator=True)
    missing = selected.loc[selected._merge.ne("both"), "ad_number"].tolist()
    if missing:
        raise RuntimeError(f"Selected ADs missing from eligible corpus: {missing}")
    selected = selected.drop(columns="_merge")

    selected = selected.merge(
        provenance[["filename", "pdf_url", "detail_url", "drive_file_id"]],
        left_on="file_name", right_on="filename", how="left", validate="one_to_one"
    ).drop(columns="filename")
    if selected.drive_file_id.eq("").any():
        raise RuntimeError("Missing Drive provenance for: " + ", ".join(selected.loc[selected.drive_file_id.eq(""), "ad_number"]))

    uf = UnionFind()
    for row in near.itertuples(index=False):
        uf.union(row.ad_number_a, row.ad_number_b)
    groups: dict[str, list[str]] = defaultdict(list)
    for ad in set(near.ad_number_a) | set(near.ad_number_b):
        groups[uf.find(ad)].append(ad)
    cluster_by_ad: dict[str, str] = {}
    for members in groups.values():
        ordered = sorted(members)
        cluster_id = "near-" + "--".join(ordered)
        for ad in ordered:
            cluster_by_ad[ad] = cluster_id
    selected["near_duplicate_cluster"] = selected.ad_number.map(cluster_by_ad).fillna("")

    selected["base_year"] = selected.base_ad_number.str[:4].astype(int)
    selected["double_annotation"] = selected.ad_number.isin(DOUBLE_ANNOTATE)
    selected["annotator_a"] = "required"
    selected["annotator_b"] = selected.double_annotation.map({True: "required", False: "not_assigned"})
    selected["adjudication"] = selected.double_annotation.map({True: "required", False: "review_required"})
    selected["selection_frozen_on"] = FROZEN_ON
    selected["selection_status"] = verified_selection_status(selected)

    # Hard gates for the user-requested cohort split and corpus hygiene.
    assert selected.groupby("cohort").size().to_dict() == {"2006-2018": 15, "2019-2026": 15}
    assert selected.groupby("cohort").double_annotation.sum().to_dict() == {"2006-2018": 5, "2019-2026": 5}
    assert selected.logical_version_key.nunique() == 30
    assert selected.file_sha256.nunique() == 30
    assert selected.ad_number.ne("2007-0178").all()
    assert truthy(selected.needs_ocr).sum() == 0
    assert selected.duplicate_of.eq("").all()

    required_pairs = [
        {"2024-0038", "2025-0068", "2026-0017"},
        {"2016-0095", "2017-0013"},
    ]
    selected_ads = set(selected.ad_number)
    assert all(pair <= selected_ads for pair in required_pairs)
    assert {"2007-0278", "2009-0025"} <= set(selected.loc[truthy(selected.is_correction), "ad_number"])

    label_sets = selected.strata.str.split("|")
    strict_simple = selected.assign(_simple=label_sets.map(lambda values: "simple" in values))
    assert strict_simple.groupby("cohort")._simple.sum().to_dict() == {"2006-2018": 3, "2019-2026": 3}
    assert selected.assign(_revised=selected.revision_number.astype(int).gt(0)).groupby("cohort")._revised.sum().to_dict() == {"2006-2018": 3, "2019-2026": 3}
    covered_years = set(selected.base_year)
    assert covered_years == set(range(2006, 2027))
    ata_counter = Counter(chapter for values in selected.ata for chapter in values.split("|"))
    assert max(ata_counter.values()) <= 5

    columns = [
        "ad_number", "base_ad_number", "base_year", "cohort", "family", "ata", "strata", "rationale",
        "logical_version_key", "revision_number", "is_correction", "correction_date", "issue_date",
        "page_count", "file_name", "relative_path", "file_instance_id", "content_id", "file_sha256",
        "normalized_text_sha256", "drive_file_id", "pdf_url", "detail_url", "near_duplicate_cluster",
        "supersedes_ad_numbers", "double_annotation", "annotator_a", "annotator_b", "adjudication",
        "selection_status", "selection_frozen_on",
    ]
    selected = selected[columns].sort_values(["cohort", "base_year", "ad_number"], ascending=[False, True, True])
    selected.to_csv(OUTPUT / "pilot_selection.csv", index=False)
    (OUTPUT / "pilot_selection.json").write_text(
        json.dumps(selected.to_dict(orient="records"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    strata_counts = Counter(label for labels in selected.strata for label in labels.split("|"))
    family_counts = selected.family.value_counts().sort_index().to_dict()
    ata_counts = Counter(chapter for values in selected.ata for chapter in values.split("|"))
    year_counts = selected.groupby(["cohort", "base_year"]).size()

    rows = []
    for row in selected.itertuples(index=False):
        b = "yes" if row.double_annotation else "no"
        rows.append(f"| {row.ad_number} | {row.cohort} | {row.family} | {row.ata} | {row.strata} | {b} | {row.rationale} |")

    report = f"""# Step 3 pilot selection report

Frozen: {FROZEN_ON}  
Corpus snapshot: 1,809 PDFs / 1,809 logical publications  
Selection unit: one canonical PDF per `logical_version_key`

## Decision

The pilot contains exactly 30 EASA AD publications: 15 whose `base_ad_number` year is 2019-2026 and 15 whose year is 2006-2018. This is purposive test-set design, not a population-representative sample. Rare and failure-prone cases are deliberately oversampled.

The qualitative strata below are selection-screening labels. Each must be confirmed against the rendered PDF during annotation before the record can become gold.

## Frozen selection

| AD | Cohort | Airbus family | ATA | Screening strata | Double annotate | Selection rationale |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## Coverage summary

- Cohorts: {selected.groupby('cohort').size().to_dict()}
- Base-AD years: {dict((f'{cohort}:{year}', int(count)) for (cohort, year), count in year_counts.items())}
- Screening strata: {dict(sorted(strata_counts.items()))}
- Families: {family_counts}
- ATA chapters: {dict(sorted(ata_counts.items()))}
- Revised publications: {int((selected.revision_number.astype(int) > 0).sum())}
- PDF-confirmed corrected publications: {int(truthy(selected.is_correction).sum())}
- Long documents (screening label): {strata_counts['long_document']}
- Simple baselines (screening label): {strata_counts['simple']}
- Double-annotation assignments: {int(selected.double_annotation.sum())} (5 recent, 5 older)

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
"""
    (OUTPUT / "selection_report.md").write_text(report, encoding="utf-8")

    sha_lines = [f"{row.file_sha256}  {row.file_name}" for row in selected.itertuples(index=False)]
    (OUTPUT / "selected_sources.sha256").write_text("\n".join(sha_lines) + "\n", encoding="utf-8")

    print(f"Wrote {len(selected)} selected publications to {OUTPUT}")
    print("Cohorts:", selected.groupby("cohort").size().to_dict())
    print("Double annotations:", selected.groupby("cohort").double_annotation.sum().to_dict())
    print("Strata:", dict(sorted(strata_counts.items())))


if __name__ == "__main__":
    main()
