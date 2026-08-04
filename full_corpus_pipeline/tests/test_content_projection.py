from __future__ import annotations

import json
import unittest
from pathlib import Path

from full_corpus_pipeline.content_projection import (
    FORBIDDEN_KEYS,
    forbidden_paths,
    project_record,
    validate_record,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads(
    (ROOT / "full_corpus_pipeline/content_record.schema.json").read_text(
        encoding="utf-8"
    )
)
EXAMPLE = (
    ROOT
    / "gold_releases/easa_airbus_ad_gold_v2/annotations/2007-0022__cdccd0ff024c4b72.annotation.json"
)


class ContentProjectionTests(unittest.TestCase):
    def test_projection_is_sparse_and_schema_valid(self) -> None:
        source = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        record, context = project_record(source, EXAMPLE)
        self.assertEqual([], context.warnings)
        self.assertEqual([], validate_record(record, SCHEMA))
        self.assertEqual([], forbidden_paths(record))
        self.assertEqual("2007-0022", record["ad_identity"]["ad_number"])
        self.assertNotIn("revision", record["ad_identity"])
        self.assertNotIn("classification", record)
        self.assertNotIn("source_document", record)
        self.assertNotIn("evidence_spans", record)
        self.assertIn("A300F4-608ST", record["applicability"][0]["text"])
        self.assertIn("action", record["required_actions"][0])
        self.assertNotIn("requirements", record)
        self.assertNotIn("unsafe_condition", record)
        self.assertNotIn("exceptions", record)
        self.assertNotIn("previous_action_credit", record)
        self.assertIn("reason", record)

    def test_missing_high_level_action_fails_closed(self) -> None:
        source = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        source["requirements"][0]["action_text"] = None
        with self.assertRaisesRegex(ValueError, "no high-level action text"):
            project_record(source, EXAMPLE)

    def test_forbidden_key_detection_is_recursive(self) -> None:
        value = {"required_actions": [{"action": "Inspect", "evidence_ids": []}]}
        self.assertIn("/required_actions/0/evidence_ids", forbidden_paths(value))
        self.assertIn("evidence_ids", FORBIDDEN_KEYS)

    def test_normalized_compliance_fields_are_rejected(self) -> None:
        source = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        record, _ = project_record(source, EXAMPLE)
        record["required_actions"][0]["conditions"] = ["unless previously accomplished"]
        errors = validate_record(record, SCHEMA)
        self.assertTrue(any("conditions" in error and "unexpected" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
