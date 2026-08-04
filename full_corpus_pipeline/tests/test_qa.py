import tempfile
import unittest
from pathlib import Path

from full_corpus_pipeline.qa import answer_question
from full_corpus_pipeline.retrieval import HybridIndex, chunk_pages


class QATests(unittest.TestCase):
    def test_answer_has_page_citation(self):
        chunks = chunk_pages(
            [{"page": 3, "text": "Compliance\nInspect the bracket before 500 flight cycles."}],
            file_instance_id="x", ad_number="2026-0001", source_pdf="ad.pdf",
            minimum_tokens=1, maximum_tokens=100,
        )
        with tempfile.TemporaryDirectory() as temporary:
            index = HybridIndex(Path(temporary) / "index")
            index.build(chunks, embedding_model="fallback", allow_dense_fallback=True)
            answer = answer_question(index, "When must the bracket be inspected?")
            self.assertFalse(answer["insufficient_information"])
            self.assertEqual(answer["citations"][0]["page"], 3)

    def test_abstains_when_no_terms_match(self):
        chunks = chunk_pages(
            [{"page": 1, "text": "Applicability\nAirbus A320 aeroplanes."}],
            file_instance_id="x", ad_number="2026-0001", source_pdf="ad.pdf",
            minimum_tokens=1, maximum_tokens=100,
        )
        with tempfile.TemporaryDirectory() as temporary:
            index = HybridIndex(Path(temporary) / "index")
            index.build(chunks, embedding_model="fallback", allow_dense_fallback=True)
            answer = answer_question(index, "What torque is used on the banana connector?")
            self.assertTrue(answer["insufficient_information"])


if __name__ == "__main__":
    unittest.main()
