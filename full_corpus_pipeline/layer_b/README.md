# Layer B — Verified Original-PDF Retrieval

Publication labels: E1 = legacy E4; E2-A–D = legacy E5-A–D. Artifact names, question IDs and code excerpts retain their original labels. See [experiment label mapping](../../docs/EXPERIMENT_LABELS.md).

Layer B owns verified page text and the frozen engineering-aware retrieval pipeline that supplies authoritative original-PDF evidence to Layer C.

## Why the implementation files remain at the package root

The page-text, E0/E1, and E2-D retrieval implementations are frozen thesis artifacts. Their recorded source paths and behavior are preserved rather than rewritten solely for folder cleanup. This folder is the canonical navigation index for Layer B.

## Page-text source layer

- `../extract_page_text.py`
- `../apply_page_text_overrides.py`
- `../page_text_visual_overrides.json`
- `../document_io.py` — shared source-document I/O used by page extraction and ingestion

Verified source version: `page-text-v1.1`.

## E0/E1 retrieval experiment

- `../retrieval.py`
- `../build_retrieval_experiments.py`
- `../evaluate_retrieval_experiments.py`
- `../diagnose_retrieval_evaluation.py`
- `../encode_queries_worker.py`
- `../faiss_search_worker.py`
- `../rerank_candidates_worker.py`

Frozen E0/E1 build/evaluation: `rag-index-build-v1.2` / `retrieval-eval-v1.3`.

## E2 engineering-aware retrieval

### Routing and lexical base

- `../e5_query_router.py`
- `../e5_retrieval.py`
- `../e5b_retrieval.py`
- `../evaluate_e5a_development.py`
- `../evaluate_e5b_development.py`

### Qwen candidate generation

- `../build_e5c_dense_embeddings.py`
- `../e5c_encode_queries_worker.py`
- `../e5c_retrieval.py`
- `../evaluate_e5c_development.py`

### Frozen E2-D reranking

- `../e5d_retrieval.py`
- `../e5d_rerank_worker.py`
- `../evaluate_e5d_development.py`

### E2 benchmark support

- `../prepare_e5_benchmark_families.py`
- `../prepare_e5_authoring_packets.py`
- `../promote_e5_development_questions.py`
- `../validate_e5_draft_questions.py`
- `../validate_e5_questions.py`

## Frozen boundary

The primary Layer B configuration is E2-D. Do not change routing, chunking, E2-C candidate generation, embedding/reranker revisions, RRF/depth settings, reranker instruction, candidate limit 20, or final evidence depth 5 from Layer C outcomes.

Machine-readable lock:

`../../evaluation_sets/easa_airbus_ad_e5_benchmark_v1/retrieval_freeze.json`

Layer B ends at the frozen top-5 evidence set. Answer generation belongs to Layer C.
