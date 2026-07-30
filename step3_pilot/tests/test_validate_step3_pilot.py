from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PILOT_DIR = Path(__file__).resolve().parents[1]
STEP2_DIR = PILOT_DIR.parent / "step2_ad_schema"
sys.path.insert(0, str(PILOT_DIR))

from validate_step3_pilot import (  # noqa: E402
    IMPORTANT_ASSERTED_VALUES,
    SUBSTANTIVE_SECTIONS,
    record_completion_errors,
    selection_membership_errors,
    validate_final_pilot,
)

class Step3PilotValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.example = json.loads(
            (STEP2_DIR / "examples" / "2007-0178.annotation.json").read_text(
                encoding="utf-8"
            )
        )

    def ready_record(self, double: bool = False) -> dict:
        record = copy.deepcopy(self.example)
        metadata = record["annotation_metadata"]
        metadata["creation_method"] = "manual"

        primary = {
            "annotator_id": "annotator-a",
            "role": "annotator",
            "started_at": "2026-07-22T00:00:00Z",
            "submitted_at": "2026-07-22T00:30:00Z",
        }
        if double:
            second = {
                "annotator_id": "annotator-b",
                "role": "annotator",
                "started_at": "2026-07-22T00:00:00Z",
                "submitted_at": "2026-07-22T00:35:00Z",
            }
            adjudicator = {
                "annotator_id": "adjudicator-c",
                "role": "adjudicator",
                "started_at": "2026-07-22T00:40:00Z",
                "submitted_at": "2026-07-22T00:55:00Z",
            }
            metadata["annotators"] = [primary, second, adjudicator]
            metadata["events"] = [
                {
                    "event_type": "created",
                    "actor_id": "annotator-a",
                    "timestamp": "2026-07-22T00:00:00Z",
                    "rationale": None,
                },
                {
                    "event_type": "submitted",
                    "actor_id": "annotator-a",
                    "timestamp": "2026-07-22T00:30:00Z",
                    "rationale": "Independent annotation A submitted.",
                },
                {
                    "event_type": "submitted",
                    "actor_id": "annotator-b",
                    "timestamp": "2026-07-22T00:35:00Z",
                    "rationale": "Independent annotation B submitted.",
                },
                {
                    "event_type": "adjudicated",
                    "actor_id": "adjudicator-c",
                    "timestamp": "2026-07-22T00:50:00Z",
                    "rationale": "A/B differences reviewed; final evidence-grounded value selected.",
                },
                {
                    "event_type": "approved",
                    "actor_id": "adjudicator-c",
                    "timestamp": "2026-07-22T00:55:00Z",
                    "rationale": "Gold record approved after adjudication.",
                },
            ]
        else:
            reviewer = {
                "annotator_id": "reviewer-b",
                "role": "reviewer",
                "started_at": "2026-07-22T00:35:00Z",
                "submitted_at": "2026-07-22T00:45:00Z",
            }
            metadata["annotators"] = [primary, reviewer]
            metadata["events"] = [
                {
                    "event_type": "created",
                    "actor_id": "annotator-a",
                    "timestamp": "2026-07-22T00:00:00Z",
                    "rationale": None,
                },
                {
                    "event_type": "submitted",
                    "actor_id": "annotator-a",
                    "timestamp": "2026-07-22T00:30:00Z",
                    "rationale": "Annotation A submitted.",
                },
                {
                    "event_type": "reviewed",
                    "actor_id": "reviewer-b",
                    "timestamp": "2026-07-22T00:42:00Z",
                    "rationale": "All substantive sections and evidence reviewed.",
                },
                {
                    "event_type": "approved",
                    "actor_id": "reviewer-b",
                    "timestamp": "2026-07-22T00:45:00Z",
                    "rationale": "Gold record approved.",
                },
            ]

        for assertion in record["field_assertions"]:
            if assertion.get("annotator_id"):
                assertion["annotator_id"] = "annotator-a"

        next_id = 100
        for pointer in SUBSTANTIVE_SECTIONS:
            value = self.pointer_get(record, pointer)
            record["field_assertions"].append(
                {
                    "assertion_id": f"AST-{next_id:03d}",
                    "field_path": pointer,
                    "value_state": "present" if value not in (None, []) else "absent_in_source",
                    "origin": "human_annotated",
                    "verification_status": "accepted",
                    "confidence": None,
                    "evidence_ids": ["EV-001"] if value not in (None, []) else [],
                    "annotator_id": "annotator-a",
                    "derivation_rule": None,
                    "input_field_paths": [],
                    "notes": "Step 3 section-completion assertion.",
                }
            )
            next_id += 1

        for pointer in IMPORTANT_ASSERTED_VALUES:
            value = self.pointer_get(record, pointer)
            if not value:
                continue
            record["field_assertions"].append(
                {
                    "assertion_id": f"AST-{next_id:03d}",
                    "field_path": pointer,
                    "value_state": "present",
                    "origin": "human_annotated",
                    "verification_status": "accepted",
                    "confidence": None,
                    "evidence_ids": ["EV-002"],
                    "annotator_id": "annotator-a",
                    "derivation_rule": None,
                    "input_field_paths": [],
                    "notes": "Step 3 normalized-list evidence assertion.",
                }
            )
            next_id += 1
        return record

    @staticmethod
    def pointer_get(record: dict, pointer: str):
        value = record
        for token in pointer[1:].split("/"):
            value = value[token]
        return value

    @staticmethod
    def selection_row(double: bool = False) -> dict:
        return {"ad_number": "2007-0178", "double_annotation": double}

    def test_complete_single_annotation_record_passes_step3_gate(self) -> None:
        self.assertEqual(
            record_completion_errors(self.ready_record(), self.selection_row()), []
        )

    def test_complete_double_annotation_record_passes_step3_gate(self) -> None:
        self.assertEqual(
            record_completion_errors(
                self.ready_record(double=True), self.selection_row(double=True)
            ),
            [],
        )

    def test_unreviewed_section_is_rejected(self) -> None:
        record = self.ready_record()
        assertion = next(
            item
            for item in record["field_assertions"]
            if item["field_path"] == "/requirements"
        )
        assertion["verification_status"] = "unreviewed"
        errors = record_completion_errors(record, self.selection_row())
        self.assertTrue(any("/requirements: missing accepted/corrected" in item for item in errors))
        self.assertTrue(any("final pilot assertions must be accepted" in item for item in errors))

    def test_missing_evidence_on_populated_item_is_rejected(self) -> None:
        record = self.ready_record()
        record["requirements"][0]["evidence_ids"] = []
        errors = record_completion_errors(record, self.selection_row())
        self.assertTrue(
            any("/requirements/0/evidence_ids: populated important item" in item for item in errors)
        )

    def test_missing_normalized_list_assertion_is_rejected(self) -> None:
        record = self.ready_record()
        record["field_assertions"] = [
            item
            for item in record["field_assertions"]
            if item["field_path"] != "/publication/type_model_designations"
        ]
        errors = record_completion_errors(record, self.selection_row())
        self.assertTrue(
            any("/publication/type_model_designations: populated important value" in item for item in errors)
        )

    def test_double_annotation_requires_b_and_adjudicator(self) -> None:
        errors = record_completion_errors(
            self.ready_record(double=False), self.selection_row(double=True)
        )
        self.assertTrue(any("annotators A and B" in item for item in errors))
        self.assertTrue(any("requires an adjudicator" in item for item in errors))
        self.assertTrue(any("adjudicated event with rationale" in item for item in errors))

    def test_draft_and_gold_false_are_rejected(self) -> None:
        record = self.ready_record()
        record["annotation_metadata"]["record_status"] = "draft"
        record["benchmark_metadata"]["gold_record"] = False
        errors = record_completion_errors(record, self.selection_row())
        self.assertTrue(any("must be approved" in item for item in errors))
        self.assertTrue(any("gold_record=true" in item for item in errors))

    @staticmethod
    def membership_fixture():
        rows = []
        records = []
        for cohort, year in (("2019-2026", 2019), ("2006-2018", 2018)):
            for number in range(1, 16):
                ad = f"{year}-{number:04d}"
                file_id = f"{year:04d}{number:012d}"[-16:]
                content_id = f"{number:016x}"
                file_hash = f"{number:064x}"
                text_hash = f"{number + 100:064x}"
                file_name = f"{ad}.pdf"
                logical = f"{ad}|UNCORRECTED"
                row = {
                    "ad_number": ad,
                    "base_ad_number": ad,
                    "cohort": cohort,
                    "logical_version_key": logical,
                    "file_instance_id": file_id,
                    "content_id": content_id,
                    "file_name": file_name,
                    "relative_path": file_name,
                    "file_sha256": file_hash,
                    "normalized_text_sha256": text_hash,
                    "page_count": "2",
                    "near_duplicate_cluster": "",
                    "double_annotation": len(rows) < 10,
                }
                record = {
                    "ad_identity": {
                        "ad_number": ad,
                        "base_ad_number": ad,
                        "logical_version_key": logical,
                    },
                    "source_document": {
                        "file_instance_id": file_id,
                        "canonical_file_instance_id": file_id,
                        "content_id": content_id,
                        "file_name": file_name,
                        "relative_path": file_name,
                        "file_sha256": file_hash,
                        "normalized_text_sha256": text_hash,
                        "page_count": 2,
                        "near_duplicate_cluster": None,
                    },
                }
                rows.append(row)
                records.append((file_name + ".json", record))
        return records, rows

    def test_exact_frozen_membership_and_15_plus_15_pass(self) -> None:
        records, rows = self.membership_fixture()
        self.assertEqual(selection_membership_errors(records, rows), [])

    def test_wrong_15_plus_15_selection_is_rejected(self) -> None:
        records, rows = self.membership_fixture()
        rows[0]["cohort"] = "2006-2018"
        errors = selection_membership_errors(records, rows)
        self.assertTrue(any("selection cohort counts" in item for item in errors))

    def test_unselected_record_is_rejected(self) -> None:
        records, rows = self.membership_fixture()
        records[0][1]["ad_identity"]["ad_number"] = "2020-9999"
        errors = selection_membership_errors(records, rows)
        self.assertTrue(any("missing selected ADs" in item for item in errors))
        self.assertTrue(any("unselected ADs" in item for item in errors))

    def test_selection_source_provenance_mismatch_is_rejected(self) -> None:
        records, rows = self.membership_fixture()
        records[0][1]["source_document"]["file_sha256"] = "f" * 64
        errors = selection_membership_errors(records, rows)
        self.assertTrue(any("file_sha256: does not match frozen selection" in item for item in errors))

    def test_final_validator_still_runs_step2_strict_validation(self) -> None:
        record = self.ready_record()
        with (
            patch("validate_step3_pilot.structural_errors", return_value=[]),
            patch(
                "validate_step3_pilot.semantic_errors",
                return_value=["strict-gate sentinel"],
            ) as strict_check,
            patch("validate_step3_pilot.batch_semantic_errors", return_value=[]),
        ):
            errors = validate_final_pilot(
                [("record.json", record)], [self.selection_row()], {}
            )
        strict_check.assert_called_once_with(record, strict=True)
        self.assertTrue(
            any(
                "[step2-strict] strict-gate sentinel" in item
                for item in errors
            )
        )


if __name__ == "__main__":
    unittest.main()
