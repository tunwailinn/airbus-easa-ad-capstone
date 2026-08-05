import unittest

from full_corpus_pipeline.evaluate_e5a_development import (
    relevance_rank,
    route_matches_declared,
    source_rank,
    summarize,
)


class E5AEvaluationTests(unittest.TestCase):
    def test_relevance_requires_source_and_reference_page(self):
        question = {
            "target_ad_number": "2020-0001",
            "reference_pages": [2],
        }
        candidates = [
            {"ad_number": "2020-0001", "page_start": 1, "page_end": 1},
            {"ad_number": "2021-0002", "page_start": 2, "page_end": 2},
            {"ad_number": "2020-0001", "page_start": 2, "page_end": 3},
        ]
        self.assertEqual(source_rank(candidates, question), 1)
        self.assertEqual(relevance_rank(candidates, question), 3)

    def test_summary_separates_top5_from_candidate_recall20(self):
        rows = [
            {"rank_at_20": 1, "source_rank_at_20": 1},
            {"rank_at_20": 7, "source_rank_at_20": 2},
            {"rank_at_20": None, "source_rank_at_20": 12},
        ]
        metrics = summarize(rows)
        self.assertAlmostEqual(metrics["recall_at_1"], 1 / 3)
        self.assertAlmostEqual(metrics["recall_at_5"], 1 / 3)
        self.assertAlmostEqual(metrics["candidate_source_and_page_recall_at_20"], 2 / 3)
        self.assertEqual(metrics["candidate_source_recall_at_20"], 1.0)
        self.assertAlmostEqual(metrics["mrr_at_5"], 1 / 3)

    def test_known_document_route_check_requires_target(self):
        question = {
            "query_mode": "known_document",
            "target_ad_number": "2024-0147R1",
        }
        self.assertTrue(
            route_matches_declared(
                question,
                {"mode": "known_document", "ad_numbers": ["2024-0147R1"]},
            )
        )
        self.assertFalse(
            route_matches_declared(
                question,
                {"mode": "known_document", "ad_numbers": ["2014-0209"]},
            )
        )

    def test_discovery_route_check(self):
        question = {
            "query_mode": "discovery",
            "target_ad_number": "2013-0250R2",
        }
        self.assertTrue(
            route_matches_declared(question, {"mode": "discovery", "ad_numbers": []})
        )
        self.assertFalse(
            route_matches_declared(
                question,
                {"mode": "known_document", "ad_numbers": ["2013-0250R1"]},
            )
        )


if __name__ == "__main__":
    unittest.main()
