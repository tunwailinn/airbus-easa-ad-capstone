import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from full_corpus_pipeline.permanent_ingest import _append_index


class PermanentIngestIndexRuntimeTests(unittest.TestCase):
    def test_research_faiss_backend_uses_process_isolated_append(self):
        with tempfile.TemporaryDirectory() as temporary:
            index_dir = Path(temporary)
            (index_dir / "index_config.json").write_text(
                json.dumps(
                    {
                        "dense_backend": "sentence_transformers",
                        "dense_index_backend": "faiss_index_flat_ip",
                        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                    }
                ),
                encoding="utf-8",
            )
            with patch(
                "full_corpus_pipeline.permanent_ingest.append_chunks_process_isolated",
                return_value={"append_mode": "process_isolated_sentence_transformer_plus_faiss"},
            ) as isolated:
                result = _append_index(index_dir, [object()], allow_dense_fallback=False)
            isolated.assert_called_once()
            self.assertEqual(
                result["append_mode"],
                "process_isolated_sentence_transformer_plus_faiss",
            )

    def test_nonresearch_backend_requires_explicit_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            index_dir = Path(temporary)
            (index_dir / "index_config.json").write_text(
                json.dumps(
                    {
                        "dense_backend": "hashing_fallback",
                        "dense_index_backend": "numpy_inner_product",
                        "embedding_model": "fallback",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "allow-dense-fallback"):
                _append_index(index_dir, [object()], allow_dense_fallback=False)


if __name__ == "__main__":
    unittest.main()
