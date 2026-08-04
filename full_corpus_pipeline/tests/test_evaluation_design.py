import unittest

from full_corpus_pipeline.freeze_evaluation_design import choose_test


class EvaluationDesignTests(unittest.TestCase):
    def test_deterministic_grouped_split(self):
        records = [
            {
                "base_ad_number": f"2026-{index:04d}",
                "file_instance_id": f"id-{index:02d}",
                "features": {"revised" if index % 4 == 0 else "original", "table" if index % 5 == 0 else "plain"},
            }
            for index in range(50)
        ]
        first = choose_test(records, count=20, seed=42)
        second = choose_test(records, count=20, seed=42)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 20)

    def test_rejects_multiple_versions_in_one_gold_family(self):
        records = [
            {"base_ad_number": "2026-0001", "file_instance_id": "a", "features": {"original"}},
            {"base_ad_number": "2026-0001", "file_instance_id": "b", "features": {"revised"}},
        ]
        with self.assertRaisesRegex(ValueError, "more than one record"):
            choose_test(records, count=1, seed=42)


if __name__ == "__main__":
    unittest.main()
