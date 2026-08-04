#!/usr/bin/env python3
"""Section-aware hybrid retrieval for permanent and temporary AD indexes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from full_corpus_pipeline.document_io import read_page_jsonl


ROOT = Path(__file__).resolve().parents[1]
HEADING_RE = re.compile(
    r"^(?:airworthiness directive|applicability|definitions?|reason|required action(?:\(s\))?"
    r"(?: and compliance time(?:\(s\))?)?|compliance|ref\.? publications?|remarks?|contacts?|"
    r"supersedure|subject|effective date)\s*:?$",
    re.I,
)
TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9./-]*")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    file_instance_id: str
    ad_number: str
    source_pdf: str
    page_start: int
    page_end: int
    section: str
    text: str
    lifecycle_status: str = "historical"


def token_count(text: str) -> int:
    return len(TOKEN_RE.findall(text))


def make_chunk_id(file_instance_id: str, page: int, section: str, text: str) -> str:
    value = f"{file_instance_id}|{page}|{section}|{text}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()[:24]


def section_blocks(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    current_section = "Document"
    for page in pages:
        page_number = int(page["page"])
        paragraphs = re.split(r"\n\s*\n|(?<=\.)\s*\n", str(page.get("text", "")))
        buffer: list[str] = []
        for paragraph in paragraphs:
            cleaned = re.sub(r"[ \t]+", " ", paragraph).strip()
            if not cleaned:
                continue
            first_line = cleaned.splitlines()[0].strip()
            if HEADING_RE.match(first_line):
                if buffer:
                    blocks.append({"page": page_number, "section": current_section, "text": "\n".join(buffer)})
                    buffer = []
                current_section = first_line.rstrip(":")
                remainder = "\n".join(cleaned.splitlines()[1:]).strip()
                if remainder:
                    buffer.append(remainder)
            else:
                buffer.append(cleaned)
        if buffer:
            blocks.append({"page": page_number, "section": current_section, "text": "\n".join(buffer)})
    return blocks


def chunk_pages(
    pages: list[dict[str, Any]], *, file_instance_id: str, ad_number: str,
    source_pdf: str, lifecycle_status: str = "historical", minimum_tokens: int = 250,
    maximum_tokens: int = 450,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    pending: list[dict[str, Any]] = []
    pending_tokens = 0

    def flush() -> None:
        nonlocal pending, pending_tokens
        if not pending:
            return
        text = "\n\n".join(item["text"] for item in pending)
        first = pending[0]
        last = pending[-1]
        chunks.append(
            Chunk(
                chunk_id=make_chunk_id(file_instance_id, first["page"], first["section"], text),
                file_instance_id=file_instance_id,
                ad_number=ad_number,
                source_pdf=source_pdf,
                page_start=int(first["page"]),
                page_end=int(last["page"]),
                section=first["section"],
                text=text,
                lifecycle_status=lifecycle_status,
            )
        )
        pending = []
        pending_tokens = 0

    for block in section_blocks(pages):
        words = TOKEN_RE.findall(block["text"])
        if len(words) > maximum_tokens:
            flush()
            raw_words = block["text"].split()
            for offset in range(0, len(raw_words), maximum_tokens):
                part = " ".join(raw_words[offset : offset + maximum_tokens])
                pending = [{**block, "text": part}]
                pending_tokens = token_count(part)
                flush()
            continue
        if pending and (block["section"] != pending[-1]["section"] or pending_tokens + len(words) > maximum_tokens):
            flush()
        pending.append(block)
        pending_tokens += len(words)
        if pending_tokens >= minimum_tokens:
            flush()
    flush()
    return chunks


def flat_chunk_pages(
    pages: list[dict[str, Any]], *, file_instance_id: str, ad_number: str,
    source_pdf: str, lifecycle_status: str = "historical", chunk_tokens: int = 350,
) -> list[Chunk]:
    """Dense-only baseline chunks with no section reconstruction."""
    chunks = []
    for page in pages:
        words = str(page.get("text", "")).split()
        for offset in range(0, len(words), chunk_tokens):
            text = " ".join(words[offset : offset + chunk_tokens]).strip()
            if not text:
                continue
            chunks.append(
                Chunk(
                    chunk_id=make_chunk_id(file_instance_id, int(page["page"]), "Flat", text),
                    file_instance_id=file_instance_id, ad_number=ad_number,
                    source_pdf=source_pdf, page_start=int(page["page"]),
                    page_end=int(page["page"]), section="Flat", text=text,
                    lifecycle_status=lifecycle_status,
                )
            )
    return chunks


class DenseEncoder:
    """Local embedding backend; uses sentence-transformers when installed."""

    def __init__(self, model_name: str, *, allow_fallback: bool = True):
        self.model_name = model_name
        self.backend = "sentence_transformers"
        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(model_name)
        except ImportError:
            if not allow_fallback:
                raise RuntimeError("install sentence-transformers for the configured dense retrieval")
            from sklearn.feature_extraction.text import HashingVectorizer

            self.backend = "hashing_fallback"
            self.model = HashingVectorizer(n_features=2048, alternate_sign=False, norm="l2", ngram_range=(1, 2))

    def encode(self, texts: list[str]) -> np.ndarray:
        if self.backend == "sentence_transformers":
            return np.asarray(self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False), dtype="float32")
        return self.model.transform(texts).toarray().astype("float32")


class HybridIndex:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.sqlite_path = self.directory / "sparse.sqlite"
        self.chunk_path = self.directory / "chunks.jsonl"
        self.embedding_path = self.directory / "dense_embeddings.npy"
        self.faiss_path = self.directory / "dense.faiss"
        self.config_path = self.directory / "index_config.json"
        self._chunks: list[Chunk] | None = None
        self._embeddings: np.ndarray | None = None
        self._encoder: DenseEncoder | None = None
        self._reranker: Any | None = None

    @property
    def chunks(self) -> list[Chunk]:
        if self._chunks is None:
            with self.chunk_path.open(encoding="utf-8") as handle:
                self._chunks = [Chunk(**json.loads(line)) for line in handle if line.strip()]
        return self._chunks

    def build(
        self, chunks: list[Chunk], *, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        allow_dense_fallback: bool = True,
    ) -> dict[str, Any]:
        if self.directory.exists() and any(self.directory.iterdir()):
            raise ValueError(f"refusing to overwrite non-empty index: {self.directory}")
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.chunk_path.open("w", encoding="utf-8") as handle:
            for chunk in chunks:
                handle.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")
        connection = sqlite3.connect(self.sqlite_path)
        try:
            connection.execute(
                "CREATE VIRTUAL TABLE chunks USING fts5(chunk_id UNINDEXED, ad_number, source_pdf UNINDEXED, "
                "page_start UNINDEXED, page_end UNINDEXED, section, text, lifecycle_status UNINDEXED)"
            )
            connection.executemany(
                "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [(c.chunk_id, c.ad_number, c.source_pdf, c.page_start, c.page_end, c.section, c.text, c.lifecycle_status) for c in chunks],
            )
            connection.commit()
        finally:
            connection.close()
        encoder = DenseEncoder(embedding_model, allow_fallback=allow_dense_fallback)
        embeddings = encoder.encode([chunk.text for chunk in chunks])
        np.save(self.embedding_path, embeddings)
        dense_index_backend = "numpy_inner_product"
        try:
            import faiss

            faiss_index = faiss.IndexFlatIP(embeddings.shape[1])
            faiss_index.add(np.ascontiguousarray(embeddings))
            faiss.write_index(faiss_index, str(self.faiss_path))
            dense_index_backend = "faiss_index_flat_ip"
        except ImportError:
            if not allow_dense_fallback:
                raise RuntimeError("install faiss-cpu for the configured dense index")
        config = {
            "chunk_count": len(chunks), "embedding_model": embedding_model,
            "dense_backend": encoder.backend, "dense_index_backend": dense_index_backend,
            "sparse_backend": "sqlite_fts5_bm25",
            "fusion": "reciprocal_rank_fusion",
            "reranker_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
            "reranker": "local_cross_encoder_or_lexical_fallback",
        }
        self.config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        self._chunks, self._embeddings, self._encoder = chunks, embeddings, encoder
        return config

    def add_chunks(self, chunks: list[Chunk]) -> dict[str, Any]:
        """Append new-document chunks to both sparse and dense indexes."""
        if not chunks:
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        existing_ids = {chunk.chunk_id for chunk in self.chunks}
        if any(chunk.chunk_id in existing_ids for chunk in chunks):
            raise ValueError("duplicate chunk ID during permanent ingestion")
        with self.chunk_path.open("a", encoding="utf-8") as handle:
            for chunk in chunks:
                handle.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")
        connection = sqlite3.connect(self.sqlite_path)
        try:
            connection.executemany(
                "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [(c.chunk_id, c.ad_number, c.source_pdf, c.page_start, c.page_end, c.section, c.text, c.lifecycle_status) for c in chunks],
            )
            connection.commit()
        finally:
            connection.close()
        self._ensure_dense()
        new_embeddings = self._encoder.encode([chunk.text for chunk in chunks])
        self._embeddings = np.vstack([self._embeddings, new_embeddings])
        np.save(self.embedding_path, self._embeddings)
        if self.faiss_path.exists():
            import faiss

            index = faiss.read_index(str(self.faiss_path))
            index.add(np.ascontiguousarray(new_embeddings))
            faiss.write_index(index, str(self.faiss_path))
        self._chunks.extend(chunks)
        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        config["chunk_count"] = len(self._chunks)
        self.config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        return config

    def _ensure_dense(self) -> None:
        if self._embeddings is None:
            self._embeddings = np.load(self.embedding_path)
        if self._encoder is None:
            config = json.loads(self.config_path.read_text(encoding="utf-8"))
            self._encoder = DenseEncoder(config["embedding_model"], allow_fallback=True)

    def sparse_search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        terms = [term for term in TOKEN_RE.findall(query.lower()) if len(term) > 1]
        if not terms:
            return []
        fts_query = " OR ".join(f'"{term.replace(chr(34), "")}"' for term in terms[:20])
        connection = sqlite3.connect(self.sqlite_path)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                "SELECT chunk_id, bm25(chunks) AS score FROM chunks WHERE chunks MATCH ? ORDER BY score LIMIT ?",
                (fts_query, limit),
            ).fetchall()
        finally:
            connection.close()
        return [{"chunk_id": row["chunk_id"], "score": -float(row["score"])} for row in rows]

    def dense_search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        self._ensure_dense()
        query_vector = self._encoder.encode([query])[0]
        if self.faiss_path.exists():
            import faiss

            index = faiss.read_index(str(self.faiss_path))
            scores, indexes = index.search(np.ascontiguousarray(query_vector.reshape(1, -1)), limit)
            return [
                {"chunk_id": self.chunks[int(index_value)].chunk_id, "score": float(score)}
                for score, index_value in zip(scores[0], indexes[0])
                if index_value >= 0
            ]
        scores = self._embeddings @ query_vector
        indexes = np.argsort(-scores)[:limit]
        return [{"chunk_id": self.chunks[int(index)].chunk_id, "score": float(scores[index])} for index in indexes]

    def search(
        self, query: str, *, limit: int = 5, candidate_limit: int = 20,
        operational_only: bool = False, ad_number: str | None = None,
    ) -> list[dict[str, Any]]:
        sparse = self.sparse_search(query, candidate_limit)
        dense = self.dense_search(query, candidate_limit)
        rrf: dict[str, float] = {}
        for ranking in (sparse, dense):
            for rank, item in enumerate(ranking, 1):
                rrf[item["chunk_id"]] = rrf.get(item["chunk_id"], 0.0) + 1.0 / (60 + rank)
        by_id = {chunk.chunk_id: chunk for chunk in self.chunks}
        query_terms = set(TOKEN_RE.findall(query.lower()))
        results = []
        for chunk_id, score in rrf.items():
            chunk = by_id[chunk_id]
            if operational_only and chunk.lifecycle_status != "operational":
                continue
            if ad_number and chunk.ad_number.casefold() != ad_number.casefold():
                continue
            chunk_terms = set(TOKEN_RE.findall(chunk.text.lower()))
            lexical_overlap = len(query_terms & chunk_terms) / max(len(query_terms), 1)
            results.append({**asdict(chunk), "retrieval_score": score, "lexical_overlap": lexical_overlap})
        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        if config.get("dense_backend") == "sentence_transformers" and results:
            try:
                if self._reranker is None:
                    from sentence_transformers import CrossEncoder

                    self._reranker = CrossEncoder(config["reranker_model"])
                scores = self._reranker.predict([(query, item["text"]) for item in results])
                for item, rerank_score in zip(results, scores):
                    item["rerank_score"] = float(rerank_score)
            except Exception:
                for item in results:
                    item["rerank_score"] = item["retrieval_score"] + 0.01 * item["lexical_overlap"]
        else:
            for item in results:
                item["rerank_score"] = item["retrieval_score"] + 0.01 * item["lexical_overlap"]
        return sorted(results, key=lambda item: (-item["rerank_score"], item["chunk_id"]))[:limit]

    def search_dense_only(
        self, query: str, *, limit: int = 5, operational_only: bool = False,
        ad_number: str | None = None,
    ) -> list[dict[str, Any]]:
        by_id = {chunk.chunk_id: chunk for chunk in self.chunks}
        output = []
        for item in self.dense_search(query, max(limit * 10, 20)):
            chunk = by_id[item["chunk_id"]]
            if operational_only and chunk.lifecycle_status != "operational":
                continue
            if ad_number and chunk.ad_number.casefold() != ad_number.casefold():
                continue
            output.append({**asdict(chunk), "retrieval_score": item["score"], "rerank_score": item["score"]})
            if len(output) == limit:
                break
        return output


def build_chunks_from_directory(
    page_text_dir: Path, manifest_rows: Iterable[dict[str, Any]], *, chunking: str = "section"
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for row in manifest_rows:
        file_id = str(row["file_instance_id"])
        candidates = list(page_text_dir.glob(f"*{file_id}*.jsonl"))
        if len(candidates) != 1:
            raise ValueError(f"expected one page-text JSONL for {file_id}, found {len(candidates)}")
        pages = read_page_jsonl(candidates[0])
        chunker = chunk_pages if chunking == "section" else flat_chunk_pages
        chunks.extend(
            chunker(
                pages, file_instance_id=file_id, ad_number=str(row["ad_number"]),
                source_pdf=str(row["relative_path"]),
                lifecycle_status="operational" if bool(row.get("is_latest_version")) else "historical",
            )
        )
    return chunks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page-text-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--exclude-selection", type=Path)
    parser.add_argument("--embedding-model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--allow-dense-fallback", action="store_true")
    parser.add_argument("--chunking", choices=("section", "flat"), default="section")
    return parser.parse_args()


def main() -> int:
    import pandas as pd

    args = parse_args()
    manifest = pd.read_parquet(args.manifest) if args.manifest.suffix == ".parquet" else pd.read_csv(args.manifest)
    if args.exclude_selection:
        excluded = pd.read_csv(args.exclude_selection)
        manifest = manifest[~manifest["file_instance_id"].isin(excluded["file_instance_id"])]
    chunks = build_chunks_from_directory(
        args.page_text_dir, manifest.to_dict(orient="records"), chunking=args.chunking
    )
    config = HybridIndex(args.output_dir).build(
        chunks, embedding_model=args.embedding_model, allow_dense_fallback=args.allow_dense_fallback
    )
    pd.DataFrame([asdict(chunk) for chunk in chunks]).to_parquet(
        args.output_dir / "chunk_manifest.parquet", index=False
    )
    print(json.dumps(config, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
