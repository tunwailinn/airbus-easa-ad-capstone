# Five-PDF Unseen Permanent-Ingestion Evaluation

## Status

U5/U6 implementation is ready. This stage begins only after the locked U3/U4 temporary-document result validates.

The authoritative temporary result remains:

- 13 semantic PASS;
- 1 semantic FAIL (`U5Q-010`, Layer B temporary passage selection);
- 1 persistent provider/transport failure (`U5Q-011`);
- 13/14 = 92.86% semantic accuracy among successful hosted responses;
- 13/15 = 86.67% strict first-pass end-to-end success.

U5/U6 does not change those values.

## Purpose

Evaluate whether the five held-out PDFs can be admitted after the post-final temporary-document evaluation while preserving:

- source provenance;
- frozen deterministic extraction;
- duplicate rejection;
- revision-family lifecycle safeguards;
- correction/revision/supersedure signals;
- persistent section-index append behavior;
- E5-C Qwen dense-store row alignment;
- frozen-source-index immutability.

No hosted QA is called in U5/U6 and no model is retrained.

## Isolation boundary

The evaluator clones these read-only frozen artifacts:

```text
data_processed/indexes/rag_v1_2/e4_section_hybrid/
data_processed/indexes/e5c_qwen3_embedding_0_6b/
```

into:

```text
data_processed/evaluations/unseen_5/permanent_ingestion/isolated_index/
```

Incoming records are written only to:

```text
data_processed/evaluations/unseen_5/permanent_ingestion/isolated_store/
```

The normal `data_incoming/` directory and frozen E4/E5-C source artifacts are fingerprinted before and after the run and must remain unchanged.

## Held-out manifest handling

`permanent_ingest.py` excludes the five frozen held-out `file_instance_id` values from the active physical-manifest view when deciding whether a PDF is already ingested. This prevents the evaluation PDFs from being falsely treated as existing operational records merely because they were retained in the immutable physical snapshot.

After a held-out PDF is admitted to the isolated incoming store, its SHA-256 is added to the incoming extraction manifest. Re-ingesting the exact same PDF must then be rejected before extraction, lifecycle mutation, or index mutation.

## Runtime hardening before U5

The existing `HybridIndex.add_chunks()` path loaded SentenceTransformers/PyTorch and FAISS in one process. The project has already observed native macOS/ARM segmentation faults from that process combination during retrieval evaluation.

Before U5, the permanent append path was therefore hardened using the same accepted runtime principle:

1. SentenceTransformer chunk encoding runs in an isolated child process that never imports FAISS.
2. FAISS append runs in a separate child process that never imports PyTorch/SentenceTransformers.
3. The parent process stages SQLite FTS rows, `chunks.jsonl`, NumPy embeddings, index config, and chunk manifest updates.

This is a process-boundary/runtime correction only. It does not change:

- chunk text;
- chunk IDs;
- MiniLM embedding model;
- normalized-vector semantics;
- FAISS `IndexFlatIP` behavior;
- SQLite FTS/BM25 content;
- lifecycle policy.

## E5-C compatibility

The frozen E5-C dense artifact is aligned by SHA-256 and chunk-order hash to the E4 `chunks.jsonl`. Appending only E4 chunks would intentionally make the frozen E5-C store stale and cause the E5-C validator to reject it.

For the isolated ingestion derivative only, each appended document is therefore encoded with the same frozen E5-C model:

```text
Qwen/Qwen3-Embedding-0.6B@97b0c61
```

using the same float32 L2-renormalization policy. The cloned E5-C `dense_embeddings.npy` and cloned metadata are extended and rebound to the cloned `chunks.jsonl` SHA-256 and chunk-ID order.

The original frozen E5-C artifact is never modified.

## U5/U6 evaluator

Implementation:

```text
full_corpus_pipeline/evaluate_unseen_permanent_ingestion.py
```

Supporting runtime modules:

```text
full_corpus_pipeline/faiss_add_worker.py
full_corpus_pipeline/isolated_index_append.py
full_corpus_pipeline/encode_e5c_chunks_worker.py
full_corpus_pipeline/e5c_dense_append.py
```

Permanent ingestion integration:

```text
full_corpus_pipeline/permanent_ingest.py
```

Regression test:

```text
full_corpus_pipeline/tests/test_permanent_ingest_index_runtime.py
```

## Per-document checks

For each of the five frozen PDFs, the evaluator performs:

1. source SHA-256 validation against `selection.csv`;
2. permanent ingest into the isolated store;
3. AD identity and parser-version validation;
4. exact deterministic-record comparison against the U1 preparation packet;
5. copied-source SHA-256 validation;
6. lifecycle decision capture;
7. isolated E4 chunk-count append validation;
8. isolated E5-C dense row-count/SHA/order alignment validation;
9. exact duplicate re-ingestion attempt;
10. verification that the duplicate attempt caused no extraction/lifecycle/index mutation.

## Lifecycle reporting boundary

The current lifecycle engine is revision-family based. It can classify:

- new family;
- higher revision;
- ambiguous same-version upload;
- ambiguous version order.

Correction and cross-family supersedure signals are preserved in the deterministic extracted content record, but they are not silently promoted into revision-family operational-selection decisions.

U5/U6 reports those outcomes as observed safeguards/limitations. It does not tune lifecycle logic after seeing held-out outcomes.

## Automatic pass gate

`automatic_safeguards_pass` requires all of the following:

- 5/5 ingestion success;
- 5/5 AD identity match;
- 5/5 frozen parser version match;
- 5/5 deterministic record equality with U1 preparation;
- 5/5 copied source SHA match;
- 5/5 isolated E4 append-count checks;
- 5/5 isolated E5-C alignment checks;
- 5/5 exact duplicate rejection with no mutation;
- 5/5 lifecycle decisions recorded;
- frozen E4 source unchanged;
- frozen E5-C source unchanged;
- normal `data_incoming/` unchanged.

Ambiguous lifecycle decisions do not automatically fail this gate; they are surfaced for explicit review because ambiguity handling is itself a safety behavior.

## Outputs

The evaluator writes:

```text
data_processed/evaluations/unseen_5/permanent_ingestion/
├── run_manifest.json
├── permanent_ingestion_summary.json
├── ingestion_events.jsonl
├── lifecycle_review_packet.md
├── isolated_store/
└── isolated_index/
    ├── e4_section_hybrid/
    └── e5c_qwen3_embedding_0_6b/
```

## Next stage

After U5/U6 outputs are preserved and reviewed:

```text
U7 post-ingestion E5-D retrieval + citation verification
→ U8 final unseen-generalization report
```

U7 must use the isolated post-ingestion E4/E5-C derivative and the frozen E5-D reranker/Layer C settings. It must not modify or replace the frozen E5 final benchmark artifacts.
