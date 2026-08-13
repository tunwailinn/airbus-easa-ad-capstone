from __future__ import annotations

import unittest

from full_corpus_pipeline.layer_c.build_hosted_qa_freeze import validate_selected_run


class LayerCHostedQAFreezeTests(unittest.TestCase):
    def base_summary(self) -> dict:
        return {
            "provider": "deepseek",
            "provider_version": "deepseek-direct-v1.1",
            "model": "deepseek-v4-pro",
            "hosted_qa_runner_version": "e5-hosted-qa-runner-v1.1",
            "prompt_version": "e5-hosted-qa-prompt-v1.0-dev",
            "thinking": "enabled",
            "reasoning_effort": "high",
            "max_tokens": 4096,
            "temperature": None,
            "selected_question_count": 60,
        }

    def test_retrieved_condition_accepts_declared_configuration(self) -> None:
        summary = self.base_summary()
        validate_selected_run(summary, expected_condition="retrieved_e5d_top5", expected_count=60)

    def test_oracle_condition_requires_explicit_marker(self) -> None:
        summary = self.base_summary()
        summary["evidence_condition"] = "oracle_reference_evidence"
        validate_selected_run(summary, expected_condition="oracle_reference_evidence", expected_count=60)

    def test_reasoning_effort_drift_is_rejected(self) -> None:
        summary = self.base_summary()
        summary["reasoning_effort"] = "max"
        with self.assertRaisesRegex(ValueError, "reasoning_effort=high"):
            validate_selected_run(summary, expected_condition="retrieved_e5d_top5", expected_count=60)

    def test_evidence_condition_drift_is_rejected(self) -> None:
        summary = self.base_summary()
        summary["evidence_condition"] = "oracle_reference_evidence"
        with self.assertRaisesRegex(ValueError, "unexpected evidence condition"):
            validate_selected_run(summary, expected_condition="retrieved_e5d_top5", expected_count=60)


if __name__ == "__main__":
    unittest.main()
