from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_DIR))

from validate_annotations import (  # noqa: E402
    batch_semantic_errors,
    load_schema,
    semantic_errors,
    structural_errors,
    validate_record,
)


class AnnotationValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_schema(PACKAGE_DIR / "easa_airbus_ad_annotation.schema.json")
        cls.example = json.loads(
            (PACKAGE_DIR / "examples" / "2007-0178.annotation.json").read_text(
                encoding="utf-8"
            )
        )

    def correction_pair(self):
        original = copy.deepcopy(self.example)
        corrected = copy.deepcopy(self.example)
        corrected_source_id = "2222222222222222"
        corrected["record_id"] = f"adann-{corrected_source_id}"
        corrected["source_document"]["file_instance_id"] = corrected_source_id
        corrected["source_document"]["canonical_file_instance_id"] = (
            corrected_source_id
        )
        corrected["source_document"]["content_id"] = corrected_source_id
        for span in corrected["evidence_spans"]:
            span["source_file_instance_id"] = corrected_source_id
        corrected["ad_identity"]["is_correction"] = True
        corrected["ad_identity"]["correction_date"] = {
            "state": "present",
            "value": "2007-06-25",
            "raw_text": "Corrected: 25 June 2007",
            "evidence_ids": ["EV-001"],
        }
        corrected["ad_identity"]["logical_version_key"] = (
            "2007-0178|original|corrected:2007-06-25"
        )
        corrected["relationships"] = [
            {
                "relationship_id": "REL-001",
                "relationship_type": "corrects",
                "target_ad_number": "2007-0178",
                "target_record_id": original["record_id"],
                "target_logical_version_key": original["ad_identity"][
                    "logical_version_key"
                ],
                "source": "correction_notice",
                "verification_status": "annotator_verified",
                "manually_verified": True,
                "raw_text": "Corrected: 25 June 2007",
                "evidence_ids": ["EV-001"],
            }
        ]
        return original, corrected

    def test_approved_example_passes_strict_validation(self) -> None:
        self.assertEqual(structural_errors(self.example, self.schema), [])
        self.assertEqual(semantic_errors(self.example, strict=True), [])

    def test_orphan_evidence_reference_is_rejected(self) -> None:
        record = copy.deepcopy(self.example)
        record["requirements"][0]["evidence_ids"] = ["EV-999"]
        errors = semantic_errors(record, strict=True)
        self.assertTrue(any("unresolved evidence ID 'EV-999'" in item for item in errors))

    def test_unverified_relationship_is_rejected_for_approved_record(self) -> None:
        record = copy.deepcopy(self.example)
        relationship = record["relationships"][0]
        relationship["verification_status"] = "candidate"
        relationship["manually_verified"] = False
        errors = semantic_errors(record, strict=True)
        self.assertTrue(any("approved records cannot retain 'candidate'" in item for item in errors))

    def test_historical_reference_cannot_be_promoted_to_supersedure(self) -> None:
        record = copy.deepcopy(self.example)
        record["relationships"][0]["relationship_type"] = "supersedes"
        errors = semantic_errors(record, strict=True)
        self.assertTrue(any("historical_reference source must use" in item for item in errors))
        self.assertTrue(any("supersedure_statement.state=explicit_none" in item for item in errors))

    def test_broken_requirement_reference_is_rejected(self) -> None:
        record = copy.deepcopy(self.example)
        record["requirements"][0]["follow_on_requirement_ids"] = ["REQ-999"]
        errors = semantic_errors(record, strict=True)
        self.assertTrue(any("unresolved ID 'REQ-999'" in item for item in errors))

    def test_revision_number_must_match_ad_number(self) -> None:
        record = copy.deepcopy(self.example)
        record["ad_identity"]["revision_number"] = 2
        errors = semantic_errors(record, strict=True)
        self.assertTrue(any("revision_number: inconsistent" in item for item in errors))

    def test_same_number_correction_uses_a_distinct_record_target(self) -> None:
        original, corrected = self.correction_pair()
        self.assertEqual(structural_errors(corrected, self.schema), [])
        self.assertEqual(semantic_errors(corrected, strict=True), [])
        self.assertEqual(
            batch_semantic_errors(
                [("original.json", original), ("corrected.json", corrected)]
            ),
            [],
        )

    def test_correction_must_target_the_same_ad_number(self) -> None:
        _, corrected = self.correction_pair()
        corrected["relationships"][0]["target_ad_number"] = "2008-0001"
        errors = semantic_errors(corrected, strict=True)
        self.assertTrue(any("correction relationships must target" in item for item in errors))

    def test_orphan_correction_record_target_is_rejected_in_batch(self) -> None:
        original, corrected = self.correction_pair()
        corrected["relationships"][0]["target_record_id"] = (
            "adann-0000000000000001"
        )
        errors = batch_semantic_errors(
            [("original.json", original), ("corrected.json", corrected)]
        )
        self.assertTrue(any("unresolved batch target" in item for item in errors))

    def test_correction_target_fields_must_resolve_to_one_record(self) -> None:
        original, corrected = self.correction_pair()
        corrected["relationships"][0]["target_logical_version_key"] = corrected[
            "ad_identity"
        ]["logical_version_key"]
        errors = batch_semantic_errors(
            [("original.json", original), ("corrected.json", corrected)]
        )
        self.assertTrue(any("resolve to different records" in item for item in errors))

    def test_malformed_array_item_returns_schema_error_without_crashing(self) -> None:
        record = copy.deepcopy(self.example)
        record["requirements"] = ["not-an-object"]
        errors = validate_record(record, self.schema, strict=True)
        self.assertTrue(errors)
        self.assertTrue(any("requirements" in item for item in errors))

    def test_terminating_action_requires_a_target_requirement(self) -> None:
        record = copy.deepcopy(self.example)
        terminating = record["requirements"][0]["terminating_action"]
        terminating.update(
            {
                "state": "present",
                "present": True,
                "scope": "full",
                "action_text": "This action terminates the inspection requirement.",
                "terminates_requirement_ids": [],
                "evidence_ids": ["EV-005"],
            }
        )
        errors = semantic_errors(record, strict=True)
        self.assertTrue(any("at least one target requirement" in item for item in errors))

    def test_terminating_action_cannot_target_its_own_requirement(self) -> None:
        record = copy.deepcopy(self.example)
        terminating = record["requirements"][0]["terminating_action"]
        terminating.update(
            {
                "state": "present",
                "present": True,
                "scope": "full",
                "action_text": "This action terminates a repetitive requirement.",
                "terminates_requirement_ids": ["REQ-001"],
                "evidence_ids": ["EV-005"],
            }
        )
        errors = semantic_errors(record, strict=True)
        self.assertTrue(any("cannot target its own enclosing requirement" in item for item in errors))

    def test_strict_mode_requires_relationship_evidence(self) -> None:
        record = copy.deepcopy(self.example)
        record["relationships"][0]["evidence_ids"] = []
        errors = semantic_errors(record, strict=True)
        self.assertTrue(
            any("$.relationships[0].evidence_ids: required for approval" in item for item in errors)
        )

    def test_family_split_leakage_is_rejected_across_records(self) -> None:
        first = copy.deepcopy(self.example)
        second = copy.deepcopy(self.example)
        first["benchmark_metadata"]["split"] = "train"
        second["benchmark_metadata"]["split"] = "test"
        errors = batch_semantic_errors([("first.json", first), ("second.json", second)])
        self.assertTrue(any("base_ad_number:2007-0178" in item for item in errors))

    def test_near_duplicate_split_leakage_is_rejected_across_families(self) -> None:
        first = copy.deepcopy(self.example)
        second = copy.deepcopy(self.example)
        first["benchmark_metadata"]["split"] = "train"
        second["benchmark_metadata"]["split"] = "test"
        first["source_document"]["near_duplicate_cluster"] = "ND-001"
        second["source_document"]["near_duplicate_cluster"] = "ND-001"
        second["ad_identity"]["base_ad_number"] = "2008-0001"
        second["source_document"]["content_id"] = "1111111111111111"
        errors = batch_semantic_errors([("first.json", first), ("second.json", second)])
        self.assertTrue(any("near_duplicate:ND-001" in item for item in errors))

    def test_annotator_cannot_approve_their_own_record(self) -> None:
        record = copy.deepcopy(self.example)
        record["annotation_metadata"]["annotators"][1]["annotator_id"] = (
            "annotator-demo"
        )
        record["annotation_metadata"]["events"][1]["actor_id"] = "annotator-demo"
        errors = semantic_errors(record, strict=True)
        self.assertTrue(any("duplicate annotator_id" in item for item in errors))
        self.assertTrue(any("approved event must be performed" in item for item in errors))

    def test_controlled_vocabularies_match_schema(self) -> None:
        vocab = json.loads(
            (PACKAGE_DIR / "controlled_vocabularies.json").read_text(encoding="utf-8")
        )
        defs = self.schema["$defs"]
        self.assertEqual(
            set(vocab["action_types"]),
            set(defs["requirement"]["properties"]["action_types"]["items"]["enum"]),
        )
        self.assertEqual(
            set(vocab["compliance_logic"]),
            set(defs["compliance_rule"]["properties"]["logic"]["enum"]),
        )
        self.assertEqual(
            set(vocab["compliance_units"]),
            set(defs["compliance_limit"]["properties"]["unit"]["enum"]),
        )
        self.assertEqual(
            set(vocab["relationship_types"]),
            set(defs["relationship"]["properties"]["relationship_type"]["enum"]),
        )
        self.assertEqual(set(vocab["field_states"]), set(defs["field_state"]["enum"]))
        self.assertEqual(
            set(vocab["quality_flags"]),
            set(defs["annotation_metadata"]["properties"]["quality_flags"]["items"]["enum"]),
        )


if __name__ == "__main__":
    unittest.main()
