import tempfile
import unittest
from pathlib import Path

from full_corpus_pipeline.retrieval import HybridIndex, chunk_pages


class RetrievalTests(unittest.TestCase):
    def test_hybrid_search_returns_source_and_page(self):
        pages = [
            {"page": 1, "text": "Applicability\nAirbus A320-214 aeroplanes, all serial numbers."},
            {"page": 2, "text": "Required Actions and Compliance Times\nInspect the elevator before 500 flight cycles."},
        ]
        chunks = chunk_pages(
            pages, file_instance_id="abc", ad_number="2026-0001", source_pdf="sample.pdf",
            minimum_tokens=1, maximum_tokens=100,
        )
        with tempfile.TemporaryDirectory() as temporary:
            index = HybridIndex(Path(temporary) / "index")
            index.build(chunks, embedding_model="unused-in-fallback", allow_dense_fallback=True)
            results = index.search("When must the elevator be inspected?", limit=1)
            self.assertEqual(results[0]["source_pdf"], "sample.pdf")
            self.assertEqual(results[0]["page_start"], 2)

    def test_chunks_never_mix_documents(self):
        first = chunk_pages([{"page": 1, "text": "Reason\nOne condition."}], file_instance_id="a", ad_number="1", source_pdf="a.pdf", minimum_tokens=1)
        second = chunk_pages([{"page": 1, "text": "Reason\nAnother condition."}], file_instance_id="b", ad_number="2", source_pdf="b.pdf", minimum_tokens=1)
        self.assertEqual({chunk.file_instance_id for chunk in first + second}, {"a", "b"})


if __name__ == "__main__":
    unittest.main()
