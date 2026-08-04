import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from full_corpus_pipeline.retrieval import HybridIndex, TOKEN_RE, chunk_pages


class FakeDenseEncoder:
    """Deterministic pure-NumPy encoder for retrieval unit tests."""

    def __init__(self, model_name: str, *, allow_fallback: bool = True):
        self.model_name = model_name
        self.backend = "hashing_fallback"

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), 256), dtype="float32")
        for row, text in enumerate(texts):
            for token in TOKEN_RE.findall(text.casefold()):
                digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
                vectors[row, int.from_bytes(digest, "little") % vectors.shape[1]] += 1.0
            norm = float(np.linalg.norm(vectors[row]))
            if norm:
                vectors[row] /= norm
        return vectors


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
            with patch("full_corpus_pipeline.retrieval.DenseEncoder", FakeDenseEncoder):
                index.build(
                    chunks,
                    embedding_model="test-fake",
                    allow_dense_fallback=True,
                )
            results = index.search("When must the elevator be inspected?", limit=1)
            self.assertEqual(results[0]["source_pdf"], "sample.pdf")
            self.assertEqual(results[0]["page_start"], 2)

    def test_chunks_never_mix_documents(self):
        first = chunk_pages([{"page": 1, "text": "Reason\nOne condition."}], file_instance_id="a", ad_number="1", source_pdf="a.pdf", minimum_tokens=1)
        second = chunk_pages([{"page": 1, "text": "Reason\nAnother condition."}], file_instance_id="b", ad_number="2", source_pdf="b.pdf", minimum_tokens=1)
        self.assertEqual({chunk.file_instance_id for chunk in first + second}, {"a", "b"})


if __name__ == "__main__":
    unittest.main()
