import unittest

from full_corpus_pipeline.evaluate_retrieval_experiments import (
    paired_comparison,
    relevance_rank,
    source_rank,
    summarize,
)


class RetrievalExperimentEvaluationTests(unittest.TestCase):
    def test_source_and_page_rank(self):
        question = {
            "target_ad_number": "2026-0001",
            "reference_pages": [2],
        }
        results = [
            {
                "ad_number": "2026-0001",
                "page_start": 1,
                "page_end": 1,
            },
            {
                "ad_number": "2026-0001",
                "page_start": 2,
                "page_end": 2,
            },
        ]
        self.assertEqual(source_rank(results, question), 1)
        self.assertEqual(relevance_rank(results, question), 2)

    def test_summary_metrics(self):
        rows = [
            {"rank": 1, "source_rank": 1},
            {"rank": 3, "source_rank": 2},
            {"rank": None, "source_rank": None},
        ]
        metrics = summarize(rows)
        self.assertAlmostEqual(metrics["recall_at_1"], 1 / 3)
        self.assertAlmostEqual(metrics["recall_at_3"], 2 / 3)
        self.assertAlmostEqual(metrics["recall_at_5"], 2 / 3)
        self.assertAlmostEqual(metrics["correct_source_at_5"], 2 / 3)
        self.assertAlmostEqual(metrics["correct_source_and_page_at_5"], 2 / 3)

    def test_paired_comparison(self):
        e0 = [
            {"question_id": "Q1", "rank": 3},
            {"question_id": "Q2", "rank": 1},
            {"question_id": "Q3", "rank": None},
        ]
        e4 = [
            {"question_id": "Q1", "rank": 1},
            {"question_id": "Q2", "rank": 2},
            {"question_id": "Q3", "rank": None},
        ]
        result = paired_comparison(e0, e4)
        self.assertEqual(result["e4_better_rank_count"], 1)
        self.assertEqual(result["e0_better_rank_count"], 1)
        self.assertEqual(result["tie_count"], 1)


if __name__ == "__main__":
    unittest.main()
