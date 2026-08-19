from __future__ import annotations

import unittest

from full_corpus_pipeline.assistant_api.schemas import QueryRequest, QueryResponse, Timings
from full_corpus_pipeline.assistant_api.services import WarmInferenceService


class AssistantApiContractTests(unittest.TestCase):
    def test_query_request_defaults_are_safe(self) -> None:
        request = QueryRequest(question="What does AD 2011-0041R1 require?")
        self.assertFalse(request.retrieval_only)
        self.assertEqual(request.context_ad_numbers, [])

    def test_query_response_accepts_retrieval_only_contract(self) -> None:
        response = QueryResponse(
            assistant_version="aviation-document-assistant-v2.0",
            status="retrieval_only",
            question="test",
            route={"mode": "known_document"},
            answer=None,
            conditions=[],
            compliance_time=[],
            exceptions=[],
            reason_for_abstention="Hosted Layer C was intentionally skipped.",
            citations=[],
            evidence=[],
            timings=Timings(),
            runtime={},
        )
        self.assertEqual(response.status, "retrieval_only")

    def test_cached_retrieval_payload_is_copied_before_mutation(self) -> None:
        source = {
            "route_errors": ["a"],
            "evidence": [{"evidence_id": "EV1"}],
            "_evidence_objects": [object()],
            "timings": {"retrieval_total_ms": 1.0},
        }
        copied = WarmInferenceService._copy_payload(source)
        copied["route_errors"].append("b")
        copied["evidence"][0]["evidence_id"] = "changed"
        copied["timings"]["retrieval_total_ms"] = 2.0
        self.assertEqual(source["route_errors"], ["a"])
        self.assertEqual(source["evidence"][0]["evidence_id"], "EV1")
        self.assertEqual(source["timings"]["retrieval_total_ms"], 1.0)


if __name__ == "__main__":
    unittest.main()
