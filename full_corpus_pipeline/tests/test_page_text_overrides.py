import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from full_corpus_pipeline.apply_page_text_overrides import apply_visual_overrides


class PageTextOverrideTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path]:
        page_dir = root / "page_text"
        pages_dir = page_dir / "pages"
        pages_dir.mkdir(parents=True)
        (page_dir / "failures.csv").write_text(
            "file_instance_id,ad_number,relative_path,error\n", encoding="utf-8"
        )
        pd.DataFrame(
            [
                {
                    "file_instance_id": "abc123",
                    "ad_number": "2011-0006",
                    "relative_path": "2011-0006.pdf",
                    "source_pdf_sha256": "hash123",
                    "page_count": 1,
                    "needs_ocr_page_count": 1,
                    "needs_ocr_pages": "1",
                    "page_text_file": "pages/2011-0006__abc123.pages.jsonl",
                    "status": "needs_ocr",
                }
            ]
        ).to_csv(page_dir / "page_manifest.csv", index=False)
        (page_dir / "page_extraction_audit.json").write_text(
            json.dumps(
                {
                    "page_text_version": "page-text-v1.0",
                    "selected_document_count": 1,
                    "successful_document_count": 1,
                    "failure_count": 0,
                    "needs_ocr_document_count": 1,
                    "needs_ocr_page_count": 1,
                    "ready_for_indexing": False,
                }
            ),
            encoding="utf-8",
        )
        (pages_dir / "2011-0006__abc123.pages.jsonl").write_text(
            json.dumps(
                {
                    "schema_version": "page-text-v1.0",
                    "file_instance_id": "abc123",
                    "ad_number": "2011-0006",
                    "source_pdf_sha256": "hash123",
                    "page": 1,
                    "text": "Appendix 1",
                    "needs_ocr": True,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        overrides = root / "overrides.json"
        overrides.write_text(
            json.dumps(
                {
                    "override_version": "test-v1",
                    "overrides": [
                        {
                            "override_id": "test-page-1",
                            "file_instance_id": "abc123",
                            "ad_number": "2011-0006",
                            "page": 1,
                            "source_pdf_sha256": "hash123",
                            "method": "visual_transcription",
                            "native_text_expected_contains": ["Appendix 1"],
                            "text": "Appendix 1\nOLD DESIGN\nNEW DESIGN",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return page_dir, overrides

    def test_verified_override_resolves_only_weak_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            page_dir, overrides = self._fixture(Path(tmp))
            audit = apply_visual_overrides(page_dir, overrides_path=overrides)
            self.assertTrue(audit["ready_for_indexing"])
            self.assertEqual(audit["needs_ocr_page_count"], 0)
            self.assertEqual(audit["native_needs_ocr_page_count"], 1)
            self.assertEqual(audit["visual_override_count"], 1)
            page_file = page_dir / "pages/2011-0006__abc123.pages.jsonl"
            page = json.loads(page_file.read_text(encoding="utf-8").strip())
            self.assertFalse(page["needs_ocr"])
            self.assertTrue(page["native_needs_ocr"])
            self.assertEqual(page["native_text"], "Appendix 1")
            self.assertEqual(page["text_source"], "visual_transcription_override")
            self.assertIn("OLD DESIGN", page["text"])
            self.assertTrue(
                (page_dir / "page_extraction_audit.json.native-v1.0.bak").exists()
            )
            self.assertTrue(
                page_file.with_name(page_file.name + ".native-v1.0.bak").exists()
            )

    def test_override_is_source_hash_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            page_dir, overrides = self._fixture(Path(tmp))
            payload = json.loads(overrides.read_text(encoding="utf-8"))
            payload["overrides"][0]["source_pdf_sha256"] = "wrong"
            overrides.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source hash mismatch"):
                apply_visual_overrides(page_dir, overrides_path=overrides)


if __name__ == "__main__":
    unittest.main()
