# Five-PDF Unseen Permanent-Ingestion Evaluation

Publication labels: E1 = legacy E4; E2-A–D = legacy E5-A–D. Artifact names, question IDs and code excerpts retain their original labels. See [experiment label mapping](EXPERIMENT_LABELS.md).

## Status — COMPLETE / PASS / LOCKED

U5/U6 isolated permanent ingestion is **complete, passed, and locked**:

- Ingestion success: **5/5**;
- Exact duplicate rejection without mutation: **5/5**;
- AD identity and parser version match: **5/5**;
- Exact deterministic record match against U1: **5/5**;
- Copied source SHA match: **5/5**;
- Isolated E1 chunk append match: **5/5**;
- Isolated E2-C dense row alignment: **5/5**;
- Frozen source indexes unchanged: **true**;
- Automatic safeguards pass: **true**.

Derivative growth:
```text
Documents: 1,786 → 1,791 (+5)
Chunks:    12,634 → 12,670 (+36)
```

Locked result artifact:
```text
evaluation_sets/unseen_incoming_5_v1/unseen_permanent_ingestion_result_lock.json
```

The authoritative temporary result remains unchanged (13 PASS / 1 FAIL / 1 technical failure). Permanent ingestion does not retrain models or modify the frozen research indexes.

## Purpose

Evaluate whether the five held-out PDFs can be admitted after the post-final temporary-document evaluation while preserving:

- source provenance;
- frozen deterministic extraction;
- duplicate rejection;
- revision-family lifecycle safeguards;
- correction/revision/supersedure signals;
- persistent section-index append behavior;
- E2-C Qwen dense-store row alignment;
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

The normal `data_incoming/` directory and frozen E1/E2-C source artifacts are fingerprinted before and after the run and must remain unchanged.

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

## E2-C compatibility

The frozen E2-C dense artifact is aligned by SHA-256 and chunk-order hash to the E1 `chunks.jsonl`. Appending only E1 chunks would intentionally make the frozen E2-C store stale and cause the E2-C validator to reject it.

For the isolated ingestion derivative only, each appended document is therefore encoded with the same frozen E2-C model:

```text
Qwen/Qwen3-Embedding-0.6B@97b0c61
```

using the same float32 L2-renormalization policy. The cloned E2-C `dense_embeddings.npy` and cloned metadata are extended and rebound to the cloned `chunks.jsonl` SHA-256 and chunk-ID order.

The original frozen E2-C artifact is never modified.

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
7. isolated E1 chunk-count append validation;
8. isolated E2-C dense row-count/SHA/order alignment validation;
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
- 5/5 isolated E1 append-count checks;
- 5/5 isolated E2-C alignment checks;
- 5/5 exact duplicate rejection with no mutation;
- 5/5 lifecycle decisions recorded;
- frozen E1 source unchanged;
- frozen E2-C source unchanged;
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

U7 must use the isolated post-ingestion E1/E2-C derivative and the frozen E2-D reranker/Layer C settings. It must not modify or replace the frozen E2 final benchmark artifacts.
