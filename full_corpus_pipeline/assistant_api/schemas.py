from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    request_id: str | None = Field(default=None, min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    question: str = Field(min_length=1, max_length=4000)
    retrieval_only: bool = False
    context_ad_numbers: list[str] = Field(default_factory=list, max_length=8)


class EvidenceRow(BaseModel):
    evidence_id: str
    rank: int
    chunk_id: str
    ad_number: str
    source_pdf: str
    page_start: int
    page_end: int
    section: str
    text: str
    reranker_score: float
    pre_rerank_rank: int


class Citation(BaseModel):
    evidence_id: str
    chunk_id: str | None = None
    ad_number: str
    source_pdf: str
    page_start: int
    page_end: int
    section: str


class Timings(BaseModel):
    routing_ms: float = 0
    query_embedding_ms: float = 0
    candidate_generation_ms: float = 0
    reranking_ms: float = 0
    retrieval_total_ms: float = 0
    hosted_qa_ms: float = 0
    total_ms: float = 0


class QueryResponse(BaseModel):
    assistant_version: str
    status: Literal[
        "answered",
        "insufficient_evidence",
        "conflicting_evidence",
        "retrieval_only",
        "technical_error",
    ]
    question: str
    route: dict
    answer: str | None = None
    conditions: list[str] = Field(default_factory=list)
    compliance_time: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    reason_for_abstention: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    evidence: list[EvidenceRow] = Field(default_factory=list)
    timings: Timings
    runtime: dict = Field(default_factory=dict)
    technical_error: dict | None = None


class HealthResponse(BaseModel):
    status: Literal["starting", "ready", "error"]
    assistant_version: str
    embedding_model_loaded: bool
    reranker_loaded: bool
    device: str
    document_count: int
    chunk_count: int
