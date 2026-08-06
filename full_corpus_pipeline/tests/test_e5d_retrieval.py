import unittest

from full_corpus_pipeline.e5d_retrieval import (
    RERANKER_CANDIDATE_LIMIT,
    RERANKER_MODEL_NAME,
    RERANKER_MODEL_REVISION,
    apply_reranker_scores,
)


class E5DRerankerTests(unittest.TestCase):
    def test_reranker_reorders_without_changing_membership(self):
        candidates = [
            {"chunk_id": "a", "ad_number": "AD-1"},
            {"chunk_id": "b", "ad_number": "AD-2"},
            {"chunk_id": "c", "ad_number": "AD-3"},
        ]
        ranked = apply_reranker_scores(candidates, [0.1, 2.0, 1.0])
        self.assertEqual([item["chunk_id"] for item in ranked], ["b", "c", "a"])
        self.assertEqual({item["chunk_id"] for item in ranked}, {"a", "b", "c"})
        self.assertEqual(ranked[0]["pre_rerank_rank"], 2)
        self.assertEqual(ranked[0]["rerank_rank"], 1)

    def test_original_rank_breaks_score_ties(self):
        candidates = [
            {"chunk_id": "a", "ad_number": "AD-1"},
            {"chunk_id": "b", "ad_number": "AD-2"},
        ]
        ranked = apply_reranker_scores(candidates, [1.0, 1.0])
        self.assertEqual([item["chunk_id"] for item in ranked], ["a", "b"])

    def test_candidate_score_length_must_match(self):
        with self.assertRaises(ValueError):
            apply_reranker_scores([{"chunk_id": "a"}], [])

    def test_frozen_reranker_identity(self):
        self.assertEqual(RERANKER_MODEL_NAME, "Qwen/Qwen3-Reranker-0.6B")
        self.assertEqual(RERANKER_MODEL_REVISION, "e61197e")
        self.assertEqual(RERANKER_CANDIDATE_LIMIT, 20)


if __name__ == "__main__":
    unittest.main()
