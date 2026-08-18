#!/usr/bin/env python3
"""Post-evaluation serving runtime for the Airbus EASA AD assistant.

This module reuses the frozen E5-C candidate generator, pinned E5-D reranker,
and frozen Layer C response contract without importing benchmark labels or
evaluation answers into the live query path.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

import numpy as np

from full_corpus_pipeline.build_e5c_dense_embeddings import (
    MODEL_NAME as EMBEDDING_MODEL_NAME,
    MODEL_REVISION as EMBEDDING_MODEL_REVISION,
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


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SERVING_ROOT = ROOT / "data_processed/serving/assistant_v1"
DEFAULT_INDEX = DEFAULT_SERVING_ROOT / "e4_section_hybrid"
DEFAULT_DENSE_DIR = DEFAULT_SERVING_ROOT / "e5c_qwen3_embedding_0_6b"
DEFAULT_EVIDENCE_DEPTH = 5
LIVE_QUERY_ID = "LIVE"


@dataclass(frozen=True)
class AssistantRuntimeConfig:
    index_dir: Path = DEFAULT_INDEX
    dense_dir: Path = DEFAULT_DENSE_DIR
    query_device: str = "auto"
    query_batch_size: int = 1
    reranker_device: str = "auto"
    reranker_batch_size: int = 2
    evidence_depth: int = DEFAULT_EVIDENCE_DEPTH


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _encode_live_query(
    question: str,
    *,
    device: str,
    batch_size: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Encode one discovery query in the existing isolated Qwen worker."""
    with tempfile.TemporaryDirectory(prefix="assistant_query_") as temp_value:
        temp_dir = Path(temp_value)
        input_path = temp_dir / "query.jsonl"
        output_path = temp_dir / "query.npy"
        metadata_path = temp_dir / "metadata.json"
        input_path.write_text(
            json.dumps(
                {"question_id": LIVE_QUERY_ID, "question": question},
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                "-m",
                "full_corpus_pipeline.e5c_encode_queries_worker",
                "--input",
                str(input_path),
                "--output",
                str(output_path),
                "--metadata-output",
                str(metadata_path),
                "--device",
                device,
                "--batch-size",
                str(batch_size),
            ],
            cwd=ROOT,
            check=True,
        )
        vectors = np.load(output_path)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    if vectors.shape[0] != 1:
        raise ValueError(f"expected one live query vector, found shape {vectors.shape}")
    ids = [str(item) for item in metadata.get("question_ids", [])]
    if ids != [LIVE_QUERY_ID]:
        raise ValueError(f"live query embedding ID mismatch: {ids}")
    if metadata.get("model") != EMBEDDING_MODEL_NAME:
        raise ValueError("live query used unexpected Qwen embedding model")
    if metadata.get("model_revision") != EMBEDDING_MODEL_REVISION:
        raise ValueError("live query used unexpected Qwen embedding revision")
    return np.asarray(vectors[0], dtype="float32"), metadata


def _rerank_live_candidates(
    question: str,
    candidates: list[dict[str, Any]],
    *,
    device: str,
    batch_size: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Rerank the fixed E5-C candidate set in the pinned isolated worker."""
    if not candidates:
        return [], {
            "model": RERANKER_MODEL_NAME,
            "model_revision": RERANKER_MODEL_REVISION,
            "instruction": RERANKER_INSTRUCTION,
            "candidate_count": 0,
        }

    rows = [
        {
            "question_id": LIVE_QUERY_ID,
            "candidate_position": position,
            "chunk_id": str(candidate["chunk_id"]),
            "question": question,
            "text": str(candidate["text"]),
        }
        for position, candidate in enumerate(candidates, 1)
    ]

    with tempfile.TemporaryDirectory(prefix="assistant_rerank_") as temp_value:
        temp_dir = Path(temp_value)
        input_path = temp_dir / "pairs.jsonl"
        output_path = temp_dir / "scores.jsonl"
        metadata_path = temp_dir / "metadata.json"
        with input_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

        subprocess.run(
            [
                sys.executable,
                "-m",
                "full_corpus_pipeline.e5d_rerank_worker",
                "--input",
                str(input_path),
                "--output",
                str(output_path),
                "--metadata-output",
                str(metadata_path),
                "--device",
                device,
                "--batch-size",
                str(batch_size),
            ],
            cwd=ROOT,
            check=True,
        )
        scored = _load_jsonl(output_path)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    if metadata.get("model") != RERANKER_MODEL_NAME:
        raise ValueError("live query used unexpected reranker model")
    if metadata.get("model_revision") != RERANKER_MODEL_REVISION:
        raise ValueError("live query used unexpected reranker revision")
    if metadata.get("instruction") != RERANKER_INSTRUCTION:
        raise ValueError("live query used unexpected reranker instruction")

    score_map = {
        (
            str(row["question_id"]),
            int(row["candidate_position"]),
            str(row["chunk_id"]),
        ): float(row["score"])
        for row in scored
    }
    expected = {
        (LIVE_QUERY_ID, position, str(candidate["chunk_id"]))
        for position, candidate in enumerate(candidates, 1)
    }
    if set(score_map) != expected:
        raise ValueError("live reranker output membership differs from E5-C candidates")

    scores = [
        score_map[(LIVE_QUERY_ID, position, str(candidate["chunk_id"]))]
        for position, candidate in enumerate(candidates, 1)
    ]
    return apply_reranker_scores(candidates, scores), metadata


def build_live_evidence(
    reranked: list[dict[str, Any]],
    *,
    depth: int = DEFAULT_EVIDENCE_DEPTH,
) -> tuple[list[Evidence], list[dict[str, Any]]]:
    """Convert top E5-D passages into Layer C evidence and serializable rows."""
    if depth <= 0:
        raise ValueError("evidence depth must be positive")

    evidence: list[Evidence] = []
    rows: list[dict[str, Any]] = []
    for rank, item in enumerate(reranked[:depth], 1):
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
        rows.append(row)
        evidence.append(Evidence.from_dict(row))
    return evidence, rows


class AviationDocumentAssistant:
    """Reusable live-query service over a prepared post-evaluation serving snapshot."""

    def __init__(self, config: AssistantRuntimeConfig | None = None):
        self.config = config or AssistantRuntimeConfig()
        if not self.config.index_dir.is_dir():
            raise FileNotFoundError(
                f"missing assistant serving index: {self.config.index_dir}. "
                "Run `python -m full_corpus_pipeline.assistant.prepare_serving_snapshot` first."
            )
        if not self.config.dense_dir.is_dir():
            raise FileNotFoundError(
                f"missing assistant serving dense store: {self.config.dense_dir}. "
                "Run `python -m full_corpus_pipeline.assistant.prepare_serving_snapshot` first."
            )
        self.retriever = DenseEvidenceAssemblyRetriever(
            self.config.index_dir,
            self.config.dense_dir,
        )

    @property
    def corpus_stats(self) -> dict[str, int]:
        chunks = self.retriever.index.chunks
        return {
            "document_count": len({str(chunk.file_instance_id) for chunk in chunks}),
            "chunk_count": len(chunks),
        }

    def retrieve(self, question: str) -> dict[str, Any]:
        question = question.strip()
        if not question:
            raise ValueError("question must not be empty")

        route = route_query(question)
        query_vector = None
        query_meta: dict[str, Any] | None = None
        if route.mode == "discovery":
            query_vector, query_meta = _encode_live_query(
                question,
                device=self.config.query_device,
                batch_size=self.config.query_batch_size,
            )

        result = self.retriever.retrieve(question, query_vector)
        candidates = list(result.get("candidates", []))[:RERANKER_CANDIDATE_LIMIT]
        reranked, reranker_meta = _rerank_live_candidates(
            question,
            candidates,
            device=self.config.reranker_device,
            batch_size=self.config.reranker_batch_size,
        )
        evidence, evidence_rows = build_live_evidence(
            reranked,
            depth=self.config.evidence_depth,
        )
        return {
            "question": question,
            "route": result.get("route", route.to_dict()),
            "route_errors": list(result.get("route_errors", [])),
            "ranking_query": result.get("ranking_query"),
            "candidate_count": len(candidates),
            "evidence_depth": len(evidence_rows),
            "evidence": evidence_rows,
            "_evidence_objects": evidence,
            "runtime": {
                "candidate_generation": "E5-C",
                "reranker": "E5-D",
                "embedding_model": (
                    query_meta.get("model") if query_meta else EMBEDDING_MODEL_NAME
                ),
                "embedding_revision": EMBEDDING_MODEL_REVISION,
                "reranker_model": reranker_meta.get("model"),
                "reranker_revision": reranker_meta.get("model_revision"),
                "corpus": self.corpus_stats,
            },
        }

    def answer(
        self,
        question: str,
        *,
        retrieval_only: bool = False,
    ) -> dict[str, Any]:
        retrieval = self.retrieve(question)
        evidence_objects = retrieval.pop("_evidence_objects")

        base = {
            "assistant_version": "aviation-document-assistant-v1.0",
            "question": retrieval["question"],
            "route": retrieval["route"],
            "route_errors": retrieval["route_errors"],
            "retrieval": {
                key: value
                for key, value in retrieval.items()
                if key not in {"question", "route", "route_errors"}
            },
            "safety": {
                "source_authority": (
                    "Original EASA AD passages remain authoritative for maintenance interpretation."
                ),
                "decision_boundary": (
                    "This assistant does not make aircraft-specific legal compliance determinations."
                ),
            },
        }

        if retrieval_only:
            return {
                **base,
                "status": "retrieval_only",
                "answer": None,
                "conditions": [],
                "compliance_time": [],
                "exceptions": [],
                "reason_for_abstention": (
                    "Hosted Layer C was intentionally skipped; inspect the retrieved evidence."
                ),
                "citations": [],
            }

        if not evidence_objects:
            return {
                **base,
                "status": "insufficient_evidence",
                "answer": None,
                "conditions": [],
                "compliance_time": [],
                "exceptions": [],
                "reason_for_abstention": "No E5-D evidence passages were retrieved.",
                "citations": [],
            }

        try:
            hosted = call_hosted_qa(
                retrieval["question"],
                evidence_objects,
                reasoning_effort="high",
                max_tokens=4096,
                request_metadata={
                    "live_assistant": True,
                    "assistant_version": "aviation-document-assistant-v1.0",
                    "route_mode": str(retrieval["route"].get("mode", "")),
                },
            )
        except Exception as exc:
            return {
                **base,
                "status": "technical_error",
                "answer": None,
                "conditions": [],
                "compliance_time": [],
                "exceptions": [],
                "reason_for_abstention": (
                    "Hosted QA did not return a valid structured response. "
                    "The retrieved evidence is still available below."
                ),
                "citations": [],
                "technical_error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            }

        return {
            **base,
            **hosted,
        }
