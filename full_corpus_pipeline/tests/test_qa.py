import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from full_corpus_pipeline.qa import answer_question
from full_corpus_pipeline.retrieval import HybridIndex, TOKEN_RE, chunk_pages


class FakeDenseEncoder:
    """Deterministic pure-NumPy encoder for retrieval/QA unit tests."""

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


class QATests(unittest.TestCase):
    def test_answer_has_page_citation(self):
        chunks = chunk_pages(
            [{"page": 3, "text": "Compliance\nInspect the bracket before 500 flight cycles."}],
            file_instance_id="x", ad_number="2026-0001", source_pdf="ad.pdf",
            minimum_tokens=1, maximum_tokens=100,
        )
        with tempfile.TemporaryDirectory() as temporary:
            index = HybridIndex(Path(temporary) / "index")
            with patch("full_corpus_pipeline.retrieval.DenseEncoder", FakeDenseEncoder):
                index.build(chunks, embedding_model="test-fake", allow_dense_fallback=True)
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
            with patch("full_corpus_pipeline.retrieval.DenseEncoder", FakeDenseEncoder):
                index.build(chunks, embedding_model="test-fake", allow_dense_fallback=True)
            answer = answer_question(index, "What torque is used on the banana connector?")
            self.assertTrue(answer["insufficient_information"])


if __name__ == "__main__":
    unittest.main()
