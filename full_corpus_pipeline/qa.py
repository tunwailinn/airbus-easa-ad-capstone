"""Corpus and temporary-document question answering with page citations."""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from full_corpus_pipeline.document_io import file_sha256, read_pdf_pages
from full_corpus_pipeline.hosted_gateway import HostedGateway
from full_corpus_pipeline.retrieval import HybridIndex, TOKEN_RE, chunk_pages


ANSWER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answer", "citations", "insufficient_information"],
    "properties": {
        "answer": {"type": "string"},
        "insufficient_information": {"type": "boolean"},
        "citations": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["source_pdf", "ad_number", "page"],
                "properties": {
                    "source_pdf": {"type": "string"}, "ad_number": {"type": "string"},
                    "page": {"type": "integer"}, "section": {"type": "string"},
                },
            },
        },
    },
}

ANSWER_PROMPT = """Answer only from the retrieved original Airworthiness
Directive chunks. For compliance questions, interpret the retrieved wording at
question time and preserve every material condition, exception, branch,
repetitive interval, terminating effect, and 'whichever occurs first/later'
relationship. Do not substitute machine-normalized structured fields for the PDF
passage. Do not calculate an aircraft-specific deadline without the required
aircraft history, and do not supply unstated Service Bulletin procedures. If the
chunks do not support the answer, set insufficient_information true and say what
is missing. Cite the source PDF, AD number, page, and section for each material
claim. Do not cite a source that does not support the answer."""


def extractive_answer(question: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {"answer": "Insufficient information was found in the selected document scope.", "citations": [], "insufficient_information": True}
    query_terms = set(TOKEN_RE.findall(question.lower()))
    candidates: list[tuple[float, str, dict[str, Any]]] = []
    for result in results:
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", result["text"]):
            terms = set(TOKEN_RE.findall(sentence.lower()))
            if not terms:
                continue
            score = len(query_terms & terms) / max(len(query_terms), 1)
            candidates.append((score, sentence.strip(), result))
    score, sentence, source = max(candidates, key=lambda item: item[0])
    if score == 0:
        return {"answer": "Insufficient information was found in the selected document scope.", "citations": [], "insufficient_information": True}
    citation = {
        "source_pdf": source["source_pdf"], "ad_number": source["ad_number"],
        "page": int(source["page_start"]), "section": source["section"],
    }
    return {"answer": sentence, "citations": [citation], "insufficient_information": False}


def answer_question(
    index: HybridIndex, question: str, *, hosted: bool = False,
    model: str = "configured-by-gateway", operational_only: bool = False,
    ad_number: str | None = None,
) -> dict[str, Any]:
    results = index.search(question, limit=5, operational_only=operational_only, ad_number=ad_number)
    if not results:
        return {
            "answer": "Insufficient information was found in the selected document scope.",
            "citations": [],
            "insufficient_information": True,
        }
    if not hosted:
        return extractive_answer(question, results)
    context = "\n\n".join(
        f"[SOURCE {item['source_pdf']} | AD {item['ad_number']} | PAGE {item['page_start']} | SECTION {item['section']}]\n{item['text']}"
        for item in results
    )
    response = HostedGateway().generate(
        model=model, system_prompt=ANSWER_PROMPT + f"\n\nQuestion: {question}",
        document_text=context, schema=ANSWER_SCHEMA, temperature=0.0,
        request_metadata={"operation": "qa", "retrieved_chunk_ids": [item["chunk_id"] for item in results]},
    )
    errors = list(Draft202012Validator(ANSWER_SCHEMA).iter_errors(response.output))
    if errors:
        raise ValueError("hosted QA output is invalid: " + "; ".join(error.message for error in errors[:5]))
    allowed_citations = {
        (item["source_pdf"], item["ad_number"], page)
        for item in results
        for page in range(int(item["page_start"]), int(item["page_end"]) + 1)
    }
    for citation in response.output.get("citations", []):
        key = (citation["source_pdf"], citation["ad_number"], int(citation["page"]))
        if key not in allowed_citations:
            raise ValueError(f"hosted QA cited a page that was not retrieved: {key}")
    return response.output


class TemporaryDocumentQA:
    """Session-scoped PDF index that is deleted explicitly or on context exit."""

    def __init__(self, pdf_path: Path, *, allow_dense_fallback: bool = True):
        self.pdf_path = Path(pdf_path)
        self._temporary = tempfile.TemporaryDirectory(prefix="ad-temporary-qa-")
        pages = read_pdf_pages(self.pdf_path)
        if any(page["needs_ocr"] for page in pages):
            self.clear()
            raise ValueError("uploaded PDF requires OCR; create an OCR derivative before QA")
        text = "\n".join(page["text"] for page in pages)
        match = re.search(r"\b((?:19|20)\d{2}-\d{4}(?:R\d+)?)\b", text, re.I)
        ad_number = match.group(1).upper() if match else "UNIDENTIFIED-AD"
        file_id = file_sha256(self.pdf_path)[:16]
        chunks = chunk_pages(
            pages, file_instance_id=file_id, ad_number=ad_number,
            source_pdf=self.pdf_path.name, lifecycle_status="temporary",
        )
        self.index = HybridIndex(Path(self._temporary.name) / "index")
        self.index.build(chunks, allow_dense_fallback=allow_dense_fallback)

    def ask(self, question: str, *, hosted: bool = False, model: str = "configured-by-gateway") -> dict[str, Any]:
        return answer_question(self.index, question, hosted=hosted, model=model)

    def clear(self) -> None:
        if getattr(self, "_temporary", None) is not None:
            self._temporary.cleanup()
            self._temporary = None

    def __enter__(self) -> "TemporaryDocumentQA":
        return self

    def __exit__(self, *_: Any) -> None:
        self.clear()
