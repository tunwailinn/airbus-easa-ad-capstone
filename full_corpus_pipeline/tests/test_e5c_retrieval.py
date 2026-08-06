import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from full_corpus_pipeline.build_e5c_dense_embeddings import (
    BUILD_VERSION,
    MODEL_NAME,
    MODEL_REVISION,
    normalize_rows_float32,
)
from full_corpus_pipeline.e5c_retrieval import (
    DenseDocumentCandidate,
    DenseEvidenceAssemblyRetriever,
    QwenDenseStore,
    _top_indexes,
    sha256_file,
)


class E5CDenseRetrievalTests(unittest.TestCase):
    def test_float32_renormalization_corrects_small_mps_like_norm_drift(self):
        vectors = np.asarray(
            [
                [0.9980479, 0.0],
                [0.0, 1.0038435],
            ],
            dtype="float32",
        )
        normalized, raw_norms, post_norms = normalize_rows_float32(
            vectors,
            label="test vectors",
        )
        self.assertAlmostEqual(float(raw_norms.min()), 0.9980479, places=6)
        self.assertAlmostEqual(float(raw_norms.max()), 1.0038435, places=6)
        self.assertTrue(np.allclose(post_norms, 1.0, atol=1e-6, rtol=1e-6))
        self.assertTrue(
            np.allclose(
                normalized,
                np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype="float32"),
                atol=1e-6,
            )
        )

    def test_top_indexes_orders_descending(self):
        scores = np.asarray([0.1, 0.9, 0.4, 0.8], dtype="float32")
        self.assertEqual(_top_indexes(scores, 3).tolist(), [1, 3, 2])

    def test_document_rrf_rewards_agreement_between_lexical_and_dense(self):
        lexical = [
            SimpleNamespace(ad_number="AD-A"),
            SimpleNamespace(ad_number="AD-B"),
            SimpleNamespace(ad_number="AD-C"),
        ]
        dense = [
            DenseDocumentCandidate("AD-C", 1, 1, 0.1, 1),
            DenseDocumentCandidate("AD-A", 2, 2, 0.09, 1),
            DenseDocumentCandidate("AD-D", 3, 3, 0.08, 1),
        ]
        fused = DenseEvidenceAssemblyRetriever._fuse_document_rankings(lexical, dense)
        self.assertEqual(fused[0]["ad_number"], "AD-A")
        self.assertEqual(fused[0]["lexical_document_rank"], 1)
        self.assertEqual(fused[0]["dense_document_rank"], 2)

    def test_dense_store_validates_row_alignment_and_searches_without_faiss(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            chunk_path = temp_dir / "chunks.jsonl"
            chunk_path.write_text(
                json.dumps({"chunk_id": "c1"}) + "\n" + json.dumps({"chunk_id": "c2"}) + "\n",
                encoding="utf-8",
            )
            chunks = [
                SimpleNamespace(chunk_id="c1", ad_number="AD-1"),
                SimpleNamespace(chunk_id="c2", ad_number="AD-2"),
            ]
            embeddings = np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype="float32")
            np.save(temp_dir / "dense_embeddings.npy", embeddings)
            chunk_id_sha = hashlib.sha256(b"c1\nc2").hexdigest()
            metadata = {
                "build_version": BUILD_VERSION,
                "model": MODEL_NAME,
                "model_revision": MODEL_REVISION,
                "normalized": True,
                "chunk_source_sha256": sha256_file(chunk_path),
                "chunk_id_order_sha256": chunk_id_sha,
                "embedding_dimension": 2,
            }
            (temp_dir / "metadata.json").write_text(
                json.dumps(metadata),
                encoding="utf-8",
            )
            store = QwenDenseStore(temp_dir, chunk_path=chunk_path, chunks=chunks)
            result = store.search(np.asarray([1.0, 0.0], dtype="float32"), limit=2)
            self.assertEqual(result[0]["chunk_id"], "c1")
            self.assertGreater(result[0]["score"], result[1]["score"])


if __name__ == "__main__":
    unittest.main()
