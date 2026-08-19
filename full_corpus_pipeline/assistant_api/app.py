from __future__ import annotations

from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import time
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from full_corpus_pipeline.assistant.runtime import DEFAULT_DENSE_DIR, DEFAULT_INDEX
from full_corpus_pipeline.assistant_api.schemas import HealthResponse, QueryRequest, QueryResponse
from full_corpus_pipeline.assistant_api.services import ASSISTANT_VERSION, WarmInferenceService


SERVICE: WarmInferenceService | None = None
STARTUP_ERROR: str | None = None


def _service() -> WarmInferenceService:
    if SERVICE is None or not SERVICE.ready:
        raise RuntimeError(STARTUP_ERROR or "assistant service is not ready")
    return SERVICE


@asynccontextmanager
async def lifespan(app: FastAPI):
    global SERVICE, STARTUP_ERROR
    index = Path(os.environ.get("ASSISTANT_INDEX_PATH", str(DEFAULT_INDEX)))
    dense = Path(os.environ.get("ASSISTANT_DENSE_PATH", str(DEFAULT_DENSE_DIR)))
    device = os.environ.get("ASSISTANT_DEVICE", "auto")
    concurrency = int(os.environ.get("ASSISTANT_ML_CONCURRENCY", "1"))
    candidate = WarmInferenceService(
        index_dir=index,
        dense_dir=dense,
        device=device,
        ml_concurrency=concurrency,
    )
    try:
        candidate.load()
        SERVICE = candidate
        STARTUP_ERROR = None
    except Exception as exc:
        STARTUP_ERROR = f"{type(exc).__name__}: {exc}"
        raise
    yield
    SERVICE = None


app = FastAPI(
    title="Airbus EASA AD Assistant API",
    version="2.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    service = SERVICE
    stats = service.corpus_stats if service and service.ready else {"document_count": 0, "chunk_count": 0}
    return HealthResponse(
        status="ready" if service and service.ready else ("error" if STARTUP_ERROR else "starting"),
        assistant_version=ASSISTANT_VERSION,
        embedding_model_loaded=bool(service and service.embedding_model is not None),
        reranker_loaded=bool(service and service.reranker is not None),
        device=service.device if service else os.environ.get("ASSISTANT_DEVICE", "auto"),
        document_count=stats["document_count"],
        chunk_count=stats["chunk_count"],
    )


@app.get("/api/v1/meta")
async def meta() -> dict:
    service = _service()
    return {
        "assistant_version": ASSISTANT_VERSION,
        "corpus": service.corpus_stats,
        "device": service.device,
        "architecture": {
            "candidate_generation": "Frozen E5-C",
            "reranking": "Frozen E5-D",
            "evidence_depth": 5,
            "hosted_qa": "Frozen Layer C contract / DeepSeek V4 Pro",
        },
        "reporting_boundary": "Post-evaluation serving layer; frozen E5 and unseen results are unchanged.",
    }


@app.post("/api/v1/query", response_model=QueryResponse)
async def query(payload: QueryRequest) -> QueryResponse:
    result = await _service().answer(
        payload.question,
        payload.context_ad_numbers,
        payload.retrieval_only,
    )
    return QueryResponse.model_validate(result)


def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")


@app.post("/api/v1/query/stream")
async def query_stream(payload: QueryRequest, request: Request) -> StreamingResponse:
    service = _service()

    async def events() -> AsyncIterator[bytes]:
        started = time.perf_counter()
        yield _sse("request.started", {"assistant_version": ASSISTANT_VERSION})
        yield _sse("route.started", {})

        retrieval = await service.retrieve(payload.question, payload.context_ad_numbers)
        evidence_objects = retrieval.pop("_evidence_objects")
        yield _sse("route.completed", {"route": retrieval["route"]})
        yield _sse(
            "evidence.ready",
            {
                "evidence": retrieval["evidence"],
                "timings": retrieval["timings"],
                "runtime": {
                    "device": service.device,
                    "corpus": service.corpus_stats,
                },
            },
        )
        if await request.is_disconnected():
            return

        if payload.retrieval_only:
            result = await service.answer(payload.question, payload.context_ad_numbers, True)
            yield _sse("answer.completed", result)
            return

        yield _sse("generation.started", {})
        # Final Layer C JSON remains hidden until it passes the frozen response contract.
        result = await service.answer(payload.question, payload.context_ad_numbers, False)
        if await request.is_disconnected():
            return
        result["timings"]["total_ms"] = (time.perf_counter() - started) * 1000
        yield _sse("answer.completed", result)
        yield _sse("request.completed", {"status": result["status"]})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def main() -> None:
    import uvicorn

    uvicorn.run(
        "full_corpus_pipeline.assistant_api.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        workers=1,
    )


if __name__ == "__main__":
    main()
