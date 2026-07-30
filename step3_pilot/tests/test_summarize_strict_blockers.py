from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PILOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PILOT_DIR))

from summarize_strict_blockers import (  # noqa: E402
    EXPECTED_HUMAN_GATE,
    PRE_HUMAN_BLOCKER,
    build_summary,
    classify_finding,
    parse_error,
)


class StrictBlockerSummaryTests(unittest.TestCase):
    def test_expected_human_gate_is_review_ready(self) -> None:
        error = (
            "/tmp/2026-0001.annotation.json:[step3] "
            "/annotation_metadata/record_status: final pilot record must be approved"
        )
        source = {
            "passed": False,
            "record_count": 1,
            "selection_count": 1,
            "errors": [error],
        }
        raw = json.dumps(source).encode("utf-8")
        summary = build_summary(Path("synthetic.json"), source, raw)
        self.assertTrue(summary["ready_for_human_review"])
        self.assertEqual(summary["expected_human_gate_count"], 1)
        self.assertEqual(summary["pre_human_blocker_count"], 0)

    def test_evidence_and_compliance_are_pre_human(self) -> None:
        evidence = classify_finding(
            "step3", "/field_assertions/7/evidence_ids: populated assertion requires evidence"
        )
        compliance = classify_finding(
            "step2-strict",
            "$.requirements[5].compliance_rules: required for approval",
        )
        self.assertEqual(evidence[:2], (PRE_HUMAN_BLOCKER, "evidence_grounding"))
        self.assertEqual(
            compliance[:2], (PRE_HUMAN_BLOCKER, "compliance_completeness")
        )

    def test_unresolved_value_is_pre_human(self) -> None:
        finding = classify_finding(
            "step3",
            "/field_assertions/9/origin: unclear/conflicting gold values require adjudication",
        )
        self.assertEqual(finding[0], PRE_HUMAN_BLOCKER)

    def test_double_annotation_provenance_is_a_human_gate(self) -> None:
        finding = classify_finding(
            "step3",
            "/annotation_metadata/annotators: selected double annotation requires an adjudicator",
        )
        self.assertEqual(finding[0], EXPECTED_HUMAN_GATE)

    def test_unknown_findings_fail_closed(self) -> None:
        self.assertEqual(
            classify_finding("step3", "new validator rule")[0], PRE_HUMAN_BLOCKER
        )
        parsed = parse_error("not a recognized validator error")
        self.assertEqual(parsed.blocker_class, PRE_HUMAN_BLOCKER)


if __name__ == "__main__":
    unittest.main()
