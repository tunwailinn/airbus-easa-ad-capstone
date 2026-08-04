import unittest
import tempfile
from pathlib import Path

import pandas as pd

from full_corpus_pipeline.lifecycle import decide_lifecycle
from full_corpus_pipeline.permanent_ingest import known_hashes


class LifecycleTests(unittest.TestCase):
    def test_higher_revision_can_be_operational(self):
        result = decide_lifecycle("2026-0001R2", [{"base_ad_number": "2026-0001", "ad_number": "2026-0001R1", "revision_number": 1}])
        self.assertTrue(result.operational_selection)
        self.assertEqual(result.relationship_status, "higher_revision")

    def test_same_version_conflict_stays_non_operational(self):
        result = decide_lifecycle("2026-0001R1", [{"base_ad_number": "2026-0001", "ad_number": "2026-0001R1", "revision_number": 1}])
        self.assertFalse(result.operational_selection)
        self.assertEqual(result.relationship_status, "ambiguous_same_version")

    def test_held_out_hash_is_not_active_until_ingested(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            corpus = root / "corpus.parquet"
            selection = root / "held.csv"
            incoming = root / "incoming.parquet"
            pd.DataFrame(
                [
                    {"file_instance_id": "active", "file_sha256": "hash-active"},
                    {"file_instance_id": "held", "file_sha256": "hash-held"},
                ]
            ).to_parquet(corpus, index=False)
            pd.DataFrame([{"file_instance_id": "held"}]).to_csv(selection, index=False)
            self.assertEqual(known_hashes(corpus, incoming, selection), {"hash-active"})
            pd.DataFrame([{"source_pdf_sha256": "hash-held"}]).to_parquet(incoming, index=False)
            self.assertEqual(known_hashes(corpus, incoming, selection), {"hash-active", "hash-held"})


if __name__ == "__main__":
    unittest.main()
