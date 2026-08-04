#!/usr/bin/env python3
"""Streamlit prototype for corpus search and uploaded-AD QA."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

from full_corpus_pipeline.permanent_ingest import ingest_pdf
from full_corpus_pipeline.qa import TemporaryDocumentQA, answer_question
from full_corpus_pipeline.retrieval import HybridIndex


ROOT = Path(__file__).resolve().parents[1]


def render_answer(st, answer: dict) -> None:
    if answer.get("insufficient_information"):
        st.warning(answer.get("answer", "Insufficient information."))
    else:
        st.markdown(answer.get("answer", ""))
    for citation in answer.get("citations", []):
        st.caption(
            f"Source: {citation['source_pdf']} · AD {citation['ad_number']} · "
            f"page {citation['page']} · {citation.get('section', 'section not labelled')}"
        )


def load_records(record_dir: Path) -> dict[str, dict]:
    records = {}
    if record_dir.exists():
        for path in sorted(record_dir.glob("*.json")):
            value = json.loads(path.read_text(encoding="utf-8"))
            records[value["ad_identity"]["ad_number"]] = value
    return records


def clear_temporary(st) -> None:
    qa = st.session_state.pop("temporary_qa", None)
    if qa:
        qa.clear()
    upload_dir = st.session_state.pop("upload_dir", None)
    if upload_dir:
        shutil.rmtree(upload_dir, ignore_errors=True)
    st.session_state.pop("upload_hash", None)


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Airbus AD Intelligence", page_icon="✈", layout="wide")
    st.markdown(
        """
        <style>
        :root { --ink:#102a43; --sky:#2f80ed; --paper:#f4f7fb; --signal:#ffb000; }
        .stApp { background: radial-gradient(circle at 85% 0%, #dcecff 0, transparent 30%), var(--paper); }
        [data-testid="stHeader"] { background: transparent; }
        .hero { padding: 1.6rem 1.8rem; border:1px solid #c8d8eb; border-radius:18px;
                background:linear-gradient(115deg,#0d2847,#174d7d); color:white; margin-bottom:1rem; }
        .hero h1 { font-family: Georgia, serif; letter-spacing:-.025em; margin:0 0 .3rem; }
        .hero p { margin:0; color:#d8e9f8; max-width:65rem; }
        .snapshot { border-left:4px solid var(--signal); padding:.7rem 1rem; background:#fff7df;
                    border-radius:0 10px 10px 0; color:#594000; margin:.7rem 0 1.2rem; }
        div[data-testid="stJson"] { border:1px solid #d6e0eb; border-radius:12px; }
        </style>
        <div class="hero"><h1>Airbus AD Intelligence</h1>
        <p>Structured regulatory content, hybrid retrieval, and page-cited answers for engineering review.</p></div>
        <div class="snapshot"><b>Frozen-snapshot warning:</b> answers reflect the stored corpus snapshot and do not establish current legal status or aircraft-specific compliance.</div>
        """,
        unsafe_allow_html=True,
    )

    index_dir = Path(os.environ.get("AD_INDEX_DIR", ROOT / "indexes/corpus_v1"))
    record_dir = Path(os.environ.get("AD_RECORD_DIR", ROOT / "data_processed/extracted_records"))
    hosted = st.sidebar.toggle("LLM compliance interpretation", value=True)
    model = st.sidebar.text_input("Gateway model", value="configured-by-gateway")
    st.sidebar.caption(
        "Retrieval is local. LLM interpretation uses retrieved original-PDF passages and does not retrain a model. "
        "Turning it off enables an extractive diagnostic only, not the v3 QA system."
    )

    corpus_tab, upload_tab = st.tabs(["Search Corpus", "Upload AD"])
    with corpus_tab:
        left, right = st.columns([1.1, 0.9], gap="large")
        with left:
            st.subheader("Ask the permanent corpus")
            question = st.text_area("Question", placeholder="Which AD requires inspection of the affected bracket, and by when?", height=100)
            operational_only = st.toggle("Operational snapshot only", value=True)
            if st.button("Search and answer", type="primary", use_container_width=True):
                if not index_dir.exists():
                    st.error(f"Corpus index is not built: {index_dir}")
                elif not question.strip():
                    st.warning("Enter a question.")
                else:
                    with st.spinner("Retrieving AD sections…"):
                        answer = answer_question(HybridIndex(index_dir), question, hosted=hosted, model=model, operational_only=operational_only)
                    render_answer(st, answer)
        with right:
            st.subheader("AD content record")
            st.caption("Complex compliance timing and conditions are answered from retrieved PDF passages, not pre-structured fields.")
            records = load_records(record_dir)
            selection = st.selectbox("AD number", ["Select an AD"] + sorted(records))
            if selection != "Select an AD":
                st.json(records[selection], expanded=2)
            elif not records:
                st.info("Canonical content records have not been promoted yet.")

    with upload_tab:
        st.subheader("Ask an unseen PDF without retraining")
        upload = st.file_uploader("Upload one EASA AD PDF", type=["pdf"])
        if upload is not None:
            upload_bytes = upload.getvalue()
            upload_hash = __import__("hashlib").sha256(upload_bytes).hexdigest()
            if st.session_state.get("upload_hash") != upload_hash:
                clear_temporary(st)
                directory = Path(tempfile.mkdtemp(prefix="ad-upload-ui-"))
                path = directory / upload.name
                path.write_bytes(upload_bytes)
                try:
                    st.session_state["temporary_qa"] = TemporaryDocumentQA(path)
                except Exception:
                    shutil.rmtree(directory, ignore_errors=True)
                    raise
                st.session_state["upload_dir"] = str(directory)
                st.session_state["upload_hash"] = upload_hash
            temporary = st.session_state["temporary_qa"]
            question = st.text_input("Question about this PDF", placeholder="What aircraft models are affected?")
            ask_col, clear_col = st.columns(2)
            if ask_col.button("Ask temporary document", type="primary", use_container_width=True) and question:
                render_answer(st, temporary.ask(question, hosted=hosted, model=model))
            if clear_col.button("Clear Document", use_container_width=True):
                clear_temporary(st)
                st.rerun()
            st.divider()
            st.markdown("#### Permanent ingestion")
            confirm = st.checkbox("I understand this will append the PDF, extract a record, and update both retrieval indexes.")
            if st.button("Add to Corpus", disabled=not confirm, use_container_width=True):
                with st.spinner("Checking duplicate, extracting, and indexing…"):
                    result = ingest_pdf(
                        Path(st.session_state["upload_dir"]) / upload.name,
                        store_dir=Path(os.environ.get("AD_INCOMING_DIR", ROOT / "data_incoming")),
                        index_dir=index_dir, model=model,
                    )
                st.success(f"Added AD {result['ad_number']} without model retraining.")
                if not result["lifecycle"]["operational_selection"]:
                    st.warning("Lifecycle relationship is ambiguous; operational snapshot selection was not changed.")


if __name__ == "__main__":
    main()
