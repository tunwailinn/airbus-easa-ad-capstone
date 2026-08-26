from __future__ import annotations

import asyncio
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
import time
from typing import Any

import numpy as np

from full_corpus_pipeline.assistant.runtime import DEFAULT_DENSE_DIR, DEFAULT_INDEX
from full_corpus_pipeline.build_e5c_dense_embeddings import (
    MODEL_NAME as EMBEDDING_MODEL_NAME,
    MODEL_REVISION as EMBEDDING_MODEL_REVISION,
    choose_device,
    normalize_rows_float32,
)
from full_corpus_pipeline.e5_query_router import route_query
from full_corpus_pipeline.e5c_retrieval import DenseEvidenceAssemblyRetriever
from full_corpus_pipeline.e5d_retrieval import (
    RERANKER_CANDIDATE_LIMIT,
    RERANKER_INSTRUCTION,
    RERANKER_MODEL_NAME,
    RERANKER_MODEL_REVISION,
    apply_reranker_scores,
)
from full_corpus_pipeline.layer_c.hosted_qa import Evidence, call_hosted_qa


ASSISTANT_VERSION = "aviation-document-assistant-v2.0"


class RetrievalCancelled(RuntimeError):
    """Raised at a safe boundary when a live retrieval request has been stopped."""


class _LRU:
    def __init__(self, limit: int = 128):
        self.limit = limit
        self._items: OrderedDict[str, Any] = OrderedDict()

    def get(self, key: str) -> Any | None:
        value = self._items.get(key)
        if value is not None:
            self._items.move_to_end(key)
        return value

    def put(self, key: str, value: Any) -> None:
        self._items[key] = value
        self._items.move_to_end(key)
        while len(self._items) > self.limit:
            self._items.popitem(last=False)


class WarmInferenceService:
    """Persistent E5-C/E5-D inference using the exact pinned research models."""

    def __init__(
        self,
        *,
        index_dir: Path = DEFAULT_INDEX,
        dense_dir: Path = DEFAULT_DENSE_DIR,
        device: str = "auto",
        ml_concurrency: int = 1,
    ) -> None:
        self.index_dir = Path(index_dir)
        self.dense_dir = Path(dense_dir)
        self.device = choose_device(device)
        self._semaphore = asyncio.Semaphore(max(1, int(ml_concurrency)))
        self._embedding_cache = _LRU(128)
        self._retrieval_cache = _LRU(64)
        self.retriever: DenseEvidenceAssemblyRetriever | None = None
        self.embedding_model: Any | None = None
        self.reranker: Any | None = None

    def load(self) -> None:
        from sentence_transformers import CrossEncoder, SentenceTransformer

        self.retriever = DenseEvidenceAssemblyRetriever(self.index_dir, self.dense_dir)
        self.embedding_model = SentenceTransformer(
            EMBEDDING_MODEL_NAME,
            revision=EMBEDDING_MODEL_REVISION,
            device=self.device,
        )
        self.reranker = CrossEncoder(
            RERANKER_MODEL_NAME,
            revision=RERANKER_MODEL_REVISION,
            device=self.device,
            prompts={"aviation": RERANKER_INSTRUCTION},
            default_prompt_name="aviation",
        )
        self._encode_sync("warmup")
        self.reranker.predict([("warmup", "warmup")], batch_size=1, show_progress_bar=False)

    @property
    def ready(self) -> bool:
        return self.retriever is not None and self.embedding_model is not None and self.reranker is not None

    @property
    def corpus_stats(self) -> dict[str, int]:
        if not self.retriever:
            return {"document_count": 0, "chunk_count": 0}
        chunks = self.retriever.index.chunks
        return {
            "document_count": len({str(chunk.file_instance_id) for chunk in chunks}),
            "chunk_count": len(chunks),
        }

    @staticmethod
    def _copy_payload(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            **payload,
            "route_errors": list(payload.get("route_errors", [])),
            "evidence": [dict(item) for item in payload.get("evidence", [])],
            "_evidence_objects": list(payload.get("_evidence_objects", [])),
            "timings": dict(payload.get("timings", {})),
        }

    @staticmethod
    def _raise_if_cancelled(is_cancelled: Callable[[], bool] | None) -> None:
        if is_cancelled is not None and is_cancelled():
            raise RetrievalCancelled("live retrieval was stopped")

    def _encode_sync(self, question: str) -> np.ndarray:
        if self.embedding_model is None:
            raise RuntimeError("embedding model is not loaded")
        cached = self._embedding_cache.get(question)
        if cached is not None:
            return cached.copy()
        vectors = self.embedding_model.encode(
            [question],
            prompt_name="query",
            batch_size=1,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        vectors = np.asarray(vectors, dtype="float32")
        vectors, _, _ = normalize_rows_float32(vectors, label="live query embedding")
        vector = vectors[0]
        self._embedding_cache.put(question, vector.copy())
        return vector

    def _retrieve_sync(
        self,
        question: str,
        context_ad_numbers: tuple[str, ...],
        is_cancelled: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        if not self.retriever or self.reranker is None:
            raise RuntimeError("warm inference service is not loaded")

        self._raise_if_cancelled(is_cancelled)
        route = route_query(question)
        effective_question = question
        if route.mode == "discovery" and context_ad_numbers:
            effective_question = f"{question} Context AD: {context_ad_numbers[0]}"
            route = route_query(effective_question)

        self._raise_if_cancelled(is_cancelled)
        cache_key = effective_question
        cached = self._retrieval_cache.get(cache_key)
        if cached is not None:
            self._raise_if_cancelled(is_cancelled)
            return self._copy_payload(cached)

        t0 = time.perf_counter()
        query_vector = None
        embedding_ms = 0.0
        if route.mode == "discovery":
            self._raise_if_cancelled(is_cancelled)
            e0 = time.perf_counter()
            query_vector = self._encode_sync(effective_question)
            embedding_ms = (time.perf_counter() - e0) * 1000
            self._raise_if_cancelled(is_cancelled)

        c0 = time.perf_counter()
        result = self.retriever.retrieve(effective_question, query_vector)
        candidates = list(result.get("candidates", []))[:RERANKER_CANDIDATE_LIMIT]
        candidate_ms = (time.perf_counter() - c0) * 1000
        self._raise_if_cancelled(is_cancelled)

        r0 = time.perf_counter()
        if candidates:
            pairs = [(effective_question, str(item["text"])) for item in candidates]
            scores = self.reranker.predict(pairs, batch_size=2, show_progress_bar=False)
            reranked = apply_reranker_scores(candidates, np.asarray(scores).reshape(-1).tolist())
        else:
            reranked = []
        rerank_ms = (time.perf_counter() - r0) * 1000
        self._raise_if_cancelled(is_cancelled)

        evidence_rows: list[dict[str, Any]] = []
        evidence_objects: list[Evidence] = []
        for rank, item in enumerate(reranked[:5], 1):
            row = {
                "evidence_id": f"EV{rank}",
                "rank": rank,
                "chunk_id": str(item["chunk_id"]),
                "ad_number": str(item["ad_number"]),
                "source_pdf": str(item["source_pdf"]),
                "page_start": int(item["page_start"]),
                "page_end": int(item["page_end"]),
                "section": str(item["section"]),
                "text": str(item["text"]),
                "reranker_score": float(item["reranker_score"]),
                "pre_rerank_rank": int(item["pre_rerank_rank"]),
            }
            evidence_rows.append(row)
            evidence_objects.append(Evidence.from_dict(row))

        self._raise_if_cancelled(is_cancelled)
        payload = {
            "question": question,
            "effective_question": effective_question,
            "route": result.get("route", route.to_dict()),
            "route_errors": result.get("route_errors", []),
            "evidence": evidence_rows,
            "_evidence_objects": evidence_objects,
            "timings": {
                "query_embedding_ms": embedding_ms,
                "candidate_generation_ms": candidate_ms,
                "reranking_ms": rerank_ms,
                "retrieval_total_ms": (time.perf_counter() - t0) * 1000,
            },
        }
        self._retrieval_cache.put(cache_key, self._copy_payload(payload))
        return self._copy_payload(payload)

    async def retrieve(
        self,
        question: str,
        context_ad_numbers: list[str],
        *,
        cancel_event: asyncio.Event | None = None,
    ) -> dict[str, Any]:
        async with self._semaphore:
            return await asyncio.to_thread(
                self._retrieve_sync,
                question.strip(),
                tuple(context_ad_numbers),
                cancel_event.is_set if cancel_event is not None else None,
            )

    async def answer(self, question: str, context_ad_numbers: list[str], retrieval_only: bool) -> dict[str, Any]:
        total_start = time.perf_counter()
        retrieval = self._copy_payload(await self.retrieve(question, context_ad_numbers))
        evidence = retrieval.pop("_evidence_objects")
        timings = dict(retrieval["timings"])

        if retrieval_only:
            hosted = {
                "status": "retrieval_only",
                "answer": None,
                "conditions": [],
                "compliance_time": [],
                "exceptions": [],
                "reason_for_abstention": "Hosted Layer C was intentionally skipped.",
                "citations": [],
            }
            timings["hosted_qa_ms"] = 0.0
        elif not evidence:
            hosted = {
                "status": "insufficient_evidence",
                "answer": None,
                "conditions": [],
                "compliance_time": [],
                "exceptions": [],
                "reason_for_abstention": "No E5-D evidence passages were retrieved.",
                "citations": [],
            }
            timings["hosted_qa_ms"] = 0.0
        else:
            h0 = time.perf_counter()
            try:
                hosted = await asyncio.to_thread(
                    call_hosted_qa,
                    question,
                    evidence,
                    reasoning_effort="high",
                    max_tokens=4096,
                    request_metadata={"live_assistant": True, "assistant_version": ASSISTANT_VERSION},
                )
            except Exception as exc:
                hosted = {
                    "status": "technical_error",
                    "answer": None,
                    "conditions": [],
                    "compliance_time": [],
                    "exceptions": [],
                    "reason_for_abstention": "Hosted QA did not return a valid structured response.",
                    "citations": [],
                    "technical_error": {"type": type(exc).__name__, "message": str(exc)},
                }
            timings["hosted_qa_ms"] = (time.perf_counter() - h0) * 1000

        timings.setdefault("routing_ms", 0.0)
        timings["total_ms"] = (time.perf_counter() - total_start) * 1000
        return {
            "assistant_version": ASSISTANT_VERSION,
            "question": question,
            "route": retrieval["route"],
            "evidence": retrieval["evidence"],
            "timings": timings,
            "runtime": {
                "device": self.device,
                "embedding_model": EMBEDDING_MODEL_NAME,
                "embedding_revision": EMBEDDING_MODEL_REVISION,
                "reranker_model": RERANKER_MODEL_NAME,
                "reranker_revision": RERANKER_MODEL_REVISION,
                "corpus": self.corpus_stats,
            },
            **hosted,
        }
