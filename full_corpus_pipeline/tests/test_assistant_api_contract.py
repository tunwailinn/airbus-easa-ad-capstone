from __future__ import annotations

import asyncio
import unittest

from pydantic import ValidationError

from full_corpus_pipeline.assistant_api.app import ACTIVE_REQUESTS, cancel_query
from full_corpus_pipeline.assistant_api.deepseek_stream import (
    HostedGenerationCancelled,
    _iter_lines_until_cancel,
)
from full_corpus_pipeline.assistant_api.schemas import QueryRequest, QueryResponse, Timings
from full_corpus_pipeline.assistant_api.services import RetrievalCancelled, WarmInferenceService


class AssistantApiContractTests(unittest.TestCase):
    def test_query_request_defaults_are_safe(self) -> None:
        request = QueryRequest(question="What does AD 2011-0041R1 require?")
        self.assertIsNone(request.request_id)
        self.assertFalse(request.retrieval_only)
        self.assertEqual(request.context_ad_numbers, [])

    def test_query_request_accepts_browser_request_id(self) -> None:
        request = QueryRequest(
            request_id="browser-request_123",
            question="What does AD 2011-0041R1 require?",
        )
        self.assertEqual(request.request_id, "browser-request_123")

    def test_query_request_allows_one_explicit_follow_up_ad(self) -> None:
        request = QueryRequest(
            question="What happens after that inspection?",
            context_ad_numbers=["2011-0041R1"],
        )
        self.assertEqual(request.context_ad_numbers, ["2011-0041R1"])

    def test_query_request_rejects_multi_document_follow_up_scope(self) -> None:
        with self.assertRaises(ValidationError):
            QueryRequest(
                question="Compare the next actions.",
                context_ad_numbers=["2011-0041R1", "2008-0008"],
            )

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

    def test_retrieval_cancellation_checkpoint_raises_before_next_stage(self) -> None:
        with self.assertRaises(RetrievalCancelled):
            WarmInferenceService._raise_if_cancelled(lambda: True)
        WarmInferenceService._raise_if_cancelled(lambda: False)
        WarmInferenceService._raise_if_cancelled(None)


class AssistantCancellationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self) -> None:
        ACTIVE_REQUESTS.clear()

    async def test_cancel_endpoint_signals_active_request(self) -> None:
        cancel_event = asyncio.Event()
        ACTIVE_REQUESTS["browser-request_123"] = cancel_event

        response = await cancel_query("browser-request_123")

        self.assertTrue(cancel_event.is_set())
        self.assertEqual(response, {"request_id": "browser-request_123", "status": "cancelling"})

    async def test_provider_line_wait_is_interrupted_by_stop_signal(self) -> None:
        provider_closed = asyncio.Event()

        async def blocked_provider_lines():
            try:
                await asyncio.Event().wait()
                yield "unreachable"
            finally:
                provider_closed.set()

        cancel_event = asyncio.Event()

        async def consume() -> None:
            async for _line in _iter_lines_until_cancel(blocked_provider_lines(), cancel_event):
                self.fail("The blocked provider should not yield after cancellation")

        task = asyncio.create_task(consume())
        await asyncio.sleep(0)
        cancel_event.set()

        with self.assertRaises(HostedGenerationCancelled):
            await asyncio.wait_for(task, timeout=0.5)
        self.assertTrue(provider_closed.is_set())


if __name__ == "__main__":
    unittest.main()
