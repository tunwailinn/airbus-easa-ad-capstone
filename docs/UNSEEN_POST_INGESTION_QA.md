# U7 — Five-PDF Unseen Post-Ingestion E5-D + Layer C Evaluation

## Status

Implementation ready as of 18 August 2026.

U7 begins after:

- U0/U1 source validation and preparation — complete;
- U2 human-reviewed 15-question unseen set — locked;
- U3/U4 temporary-document QA — human approved and locked;
- U5/U6 isolated permanent-ingestion safeguards — automatic safeguards passed and locked.

The frozen 40-question E5 final benchmark remains authoritative and unchanged.

## U5/U6 result entering U7

The isolated permanent-ingestion run completed with:

- 5/5 ingestion success;
- 5/5 AD identity match;
- 5/5 frozen parser-version match;
- 5/5 deterministic record equality with U1 preparation;
- 5/5 copied-source SHA-256 match;
- 5/5 isolated E4 append checks;
- 5/5 isolated E5-C alignment checks;
- 5/5 exact duplicate rejections with no mutation;
- frozen E4 source unchanged;
- frozen E5-C source unchanged;
- normal `data_incoming/` unchanged;
- automatic safeguards pass: `true`.

The isolated derivative grew from 12,634 to 12,670 section chunks, adding 36 chunks for the five PDFs. The isolated E5-C Qwen dense store also contains 12,670 aligned rows.

Committed result lock:

```text
evaluation_sets/unseen_incoming_5_v1/unseen_permanent_ingestion_result_lock.json
```

Validator:

```text
full_corpus_pipeline/layer_c/validate_unseen_permanent_ingestion_result.py
```

## Interpretation boundary from U5/U6

Deterministic record equality means permanent ingestion reproduced the frozen U1 extraction exactly. It does **not** mean every structured field is semantically perfect.

AI-assisted inspection of the lifecycle review packet shows over-broad `revision_statement` captures in at least AD `2008-0008` and AD `2026-0084`. This is a pre-existing Layer A extraction limitation exposed by the unseen set, not an ingestion regression. U7 does not use that field for answering maintenance questions; it retrieves from original PDF-derived chunks.

The lifecycle engine remains revision-family based. Cross-family supersedure and correction statements are preserved in content records but are not silently promoted into lifecycle edges after observing held-out outcomes.

## Frozen-chunk compatibility gate

The U5/U6 append path historically called the generic section chunker, while the accepted E4 research build uses the stricter `rag-index-build-v1.2` whitespace-delimited section chunker.

Before U7, the validator reconstructs all five newly ingested PDFs with:

```text
full_corpus_pipeline.build_retrieval_experiments.strict_section_chunk_pages
```

and compares the expected chunks against the isolated derivative for exact:

- chunk count;
- chunk ID;
- page span;
- section;
- text;
- lifecycle status;
- source PDF value.

The diagnostic is written to:

```text
data_processed/evaluations/unseen_5/permanent_ingestion/
e5_chunk_policy_compatibility.json
```

If all five match exactly, U7 is allowed.

If any document differs, the U5/U6 result remains preserved as a technical-safeguard result, but U7 is blocked. An explicitly labelled E5-compatible derivative must then be built; the original U5/U6 output is not silently overwritten.

## U7 retrieval condition

U7 uses the same 15 human-reviewed unseen questions without editing their text or references.

Their original `query_mode=temporary_document` value remains provenance from U3. After permanent ingestion, actual routing is determined from the question text by the frozen E5 query router:

- a question containing an AD identifier may route as known-document;
- an identifier-free question routes through corpus-wide discovery;
- multi-document routing is preserved if the text contains multiple AD identifiers.

No target AD identifier is injected into a discovery question.

Candidate generation uses the isolated post-ingestion derivative with the frozen E5-C algorithm:

```text
BM25 / E5 evidence assembly
+ Qwen/Qwen3-Embedding-0.6B@97b0c61
→ fixed top-20 candidate pool
```

The fixed pool is reranked with:

```text
Qwen/Qwen3-Reranker-0.6B@e61197e
```

using the frozen instruction:

> Given an aviation airworthiness-directive maintenance query, rank passages by how directly and completely they answer the query. Preserve exact applicability, compliance thresholds, timing, exceptions, identifiers, lifecycle statements, and referenced publications.

Only reranked top-5 evidence is supplied to Layer C.

## U7 Layer C condition

Hosted configuration remains frozen:

```text
provider: DeepSeek official direct API
adapter: deepseek-direct-v1.1
model: deepseek-v4-pro
thinking: enabled
reasoning_effort: high
max_tokens: 4096
prompt: e5-hosted-qa-prompt-v1.0-dev
contract: e5-hosted-qa-contract-v1.0
semantic retry: prohibited
```

The model sees only:

- the question text;
- top-5 evidence passages.

Private fields such as target AD, reference pages, source quotations and reference answer remain outside the prompt and are joined only by the offline evaluator.

## U7 runner

```text
full_corpus_pipeline/layer_c/run_unseen_post_ingestion_qa.py
```

Default output:

```text
data_processed/evaluations/unseen_5/post_ingestion_primary/
├── run_manifest.json
├── retrieval_report.json
├── evidence_packs.jsonl
├── responses.jsonl
├── failures.jsonl
└── run_summary.json
```

The runner refuses to overwrite an existing U7 primary run.

No automatic retry is performed. A provider/transport failure, if any, is preserved. Any later exact transport retry must be separately audited and cannot rewrite the first-pass result.

## Offline evaluator

```text
full_corpus_pipeline/layer_c/evaluate_unseen_post_ingestion_qa.py
```

Outputs:

```text
data_processed/evaluations/unseen_5/post_ingestion_primary/evaluation/
├── automatic_evaluation.json
├── reference_quote_containment_diagnostic.json
├── human_review.csv
└── review_packet.md
```

Automatic metrics include:

- E5-D Recall@1/3/5, MRR@5 and nDCG@5 on 14 answerable questions;
- source recall and source+page recall;
- actual post-ingestion route-mode counts;
- reference-page any Recall@5;
- full-reference-page coverage@5;
- exact approved-quote containment diagnostics;
- hosted request success;
- answerability/status accuracy;
- reference-page citation hit rate;
- target-AD citation hit rate.

Exact quote containment remains a passage-support diagnostic and does not replace the page-level retrieval metrics.

## Human review

After U7 finishes, every successful hosted answer must be reviewed against the human-approved reference and source evidence for:

- answer correctness;
- requested-scope completeness;
- material conditions;
- compliance-time completeness;
- exceptions;
- citation support;
- unsupported claims.

Do not fail an answer merely for omitting a fact the question did not request.

Failure attribution remains stage-specific:

- post-ingestion candidate generation;
- E5-D passage selection;
- Layer C generation/status;
- provider/transport.

## Reporting boundary

U7 is a post-final unseen generalization condition. Its results must not:

- replace the frozen 95.0% E5 final result;
- replace the locked U3/U4 temporary result;
- retune the parser, E5-C, E5-D, prompt, model settings or evidence depth;
- modify frozen E5 benchmark artifacts.

After U7 human review is locked, proceed to U8 final unseen-generalization reporting.
