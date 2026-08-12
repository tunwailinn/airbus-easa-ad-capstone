import json
import unittest

from full_corpus_pipeline.layer_c.providers.deepseek import (
    DEEPSEEK_MODEL,
    DeepSeekProvider,
)


class DeepSeekProviderTests(unittest.TestCase):
    def provider(self):
        return DeepSeekProvider(
            api_key="test-key",
            reasoning_effort="high",
            thinking_enabled=True,
            max_tokens=4096,
        )

    def test_request_uses_v4_pro_thinking_and_json_output(self):
        payload = self.provider().build_request_payload(
            model=DEEPSEEK_MODEL,
            system_prompt="Return JSON only.",
            document_text="Question and evidence",
            schema={"type": "object", "properties": {"status": {"type": "string"}}},
        )
        self.assertEqual(payload["model"], "deepseek-v4-pro")
        self.assertEqual(payload["thinking"], {"type": "enabled"})
        self.assertEqual(payload["reasoning_effort"], "high")
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["max_tokens"], 4096)
        self.assertNotIn("temperature", payload)
        self.assertIn("JSON RESPONSE CONTRACT", payload["messages"][0]["content"])

    def test_parse_response_discards_reasoning_content(self):
        provider_response = {
            "id": "request-123",
            "model": "deepseek-v4-pro",
            "choices": [
                {
                    "message": {
                        "reasoning_content": "private reasoning that must not be persisted",
                        "content": json.dumps(
                            {
                                "status": "answered",
                                "answer": "Do the inspection.",
                                "conditions": [],
                                "compliance_time": [],
                                "exceptions": [],
                                "evidence_ids": ["EV1"],
                                "reason_for_abstention": None,
                            }
                        ),
                    }
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
        }
        parsed = self.provider().parse_response(provider_response)
        self.assertEqual(parsed.request_id, "request-123")
        self.assertEqual(parsed.output["status"], "answered")
        rendered = json.dumps({"output": parsed.output, "usage": parsed.usage})
        self.assertNotIn("private reasoning", rendered)

    def test_empty_json_output_is_rejected(self):
        provider_response = {
            "choices": [{"message": {"reasoning_content": "reasoning", "content": ""}}]
        }
        with self.assertRaisesRegex(ValueError, "empty final content"):
            self.provider().parse_response(provider_response)

    def test_provider_rejects_non_v4_pro_model(self):
        with self.assertRaisesRegex(ValueError, "locked to"):
            self.provider().build_request_payload(
                model="deepseek-v4-flash",
                system_prompt="Return JSON only.",
                document_text="Question and evidence",
                schema={"type": "object"},
            )


if __name__ == "__main__":
    unittest.main()
