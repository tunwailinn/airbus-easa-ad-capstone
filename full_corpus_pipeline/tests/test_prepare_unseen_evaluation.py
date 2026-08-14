from __future__ import annotations

import unittest

import pandas as pd

from full_corpus_pipeline.prepare_unseen_evaluation import EXPECTED_STRATA, validate_selection


class PrepareUnseenEvaluationTests(unittest.TestCase):
    def make_frames(self):
        strata = sorted(EXPECTED_STRATA)
        selection_rows = []
        manifest_rows = []
        for index, stratum in enumerate(strata, 1):
            ad = f"2020-{index:04d}"
            file_id = f"file{index}"
            common = {
                "ad_number": ad,
                "base_ad_number": ad,
                "file_instance_id": file_id,
                "relative_path": f"{ad}.pdf",
                "file_sha256": f"hash{index}",
                "page_count": index + 1,
                "revision_number": 0,
                "is_correction": stratum == "corrected",
            }
            selection_rows.append({"stratum": stratum, **common})
            manifest_rows.append({**common, "issue_date": "2020-01-01"})
        return pd.DataFrame(selection_rows), pd.DataFrame(manifest_rows)

    def test_locked_five_case_selection_matches_manifest(self):
        selection, manifest = self.make_frames()
        merged = validate_selection(selection, manifest)
        self.assertEqual(len(merged), 5)
        self.assertEqual(set(merged["stratum"]), EXPECTED_STRATA)

    def test_rejects_manifest_hash_mismatch(self):
        selection, manifest = self.make_frames()
        manifest.loc[0, "file_sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "file_sha256"):
            validate_selection(selection, manifest)

    def test_rejects_missing_stratum(self):
        selection, manifest = self.make_frames()
        selection = selection.iloc[:4].copy()
        with self.assertRaisesRegex(ValueError, "exactly five"):
            validate_selection(selection, manifest)


if __name__ == "__main__":
    unittest.main()
