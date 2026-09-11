# Conference Paper Status

Last updated: 11 September 2026

## Scope

This workstream is for the **conference paper** and is separate from the university final seminar report.

The current priority is to write and refine the **Methodology** section first. The paper is based on the frozen research/evaluation record and must not retroactively change the benchmark methodology or scores.

## Current paper structure

The working paper covers:

1. Introduction and problem motivation;
2. Contributions and research gap;
3. Methodology;
4. Experimental design;
5. Results;
6. Discussion;
7. Limitations and responsible use;
8. Conclusion;
9. References.

The working draft also includes quantitative figures for the major result groups rather than relying only on prose/tables.

## Methodology points to preserve

### 1. Lifecycle-aware corpus preparation

Airworthiness Directive identity, revision, correction and supersedure relationships are established deterministically before answer generation. Lifecycle normalization is not inferred by the answer model.

### 2. Source-faithful evidence

Source-derived evidence must be a contiguous passage locatable in the declared original PDF page. Only harmless whitespace, line-break and line-end hyphenation normalization is permitted. Evidence is therefore an audit layer, not a model-generated summary.

### 3. Query routing

The methodology distinguishes known-document questions from corpus-wide discovery questions. Known-document routing may use the explicit AD identifier to establish document scope, while the identifier is removed from passage-ranking text to reduce identifier leakage. Discovery questions do not receive a target AD identifier.

### 4. Frozen retrieval stack

The evaluated retrieval stack uses the frozen E5-C/E5-D methodology, including BM25 and Qwen dense retrieval where applicable, followed by Qwen reranking and top-five evidence selection.

The evaluated model revisions are fixed to:

```text
Qwen/Qwen3-Embedding-0.6B@97b0c61
Qwen/Qwen3-Reranker-0.6B@e61197e
```

### 5. Evidence-grounded generation

Layer C receives the retrieved evidence rather than independently searching the corpus. Final responses are schema- and evidence-validated before being accepted as answers. If the available evidence does not support a requested detail, the system should abstain rather than fabricate it.

### 6. Explicit follow-up context

The live assistant permits one explicitly selected AD context for follow-up questions. Unrestricted chat history is not silently injected into the frozen retrieval path.

This is a post-evaluation serving/UX capability and must not be presented as a change to the frozen E5 evaluation protocol.

## Frozen quantitative results

The paper must preserve these distinctions:

| Result category | Frozen value | Interpretation |
|---|---:|---|
| E5 final semantic accuracy | **38/40 = 95.0%** | Main end-to-end research result |
| E5-D Recall@5 | **35/36 = 97.22%** | Main retrieval result |
| Unseen U7 outcome | **13 PASS / 1 semantic FAIL / 1 technical failure** | Separate post-ingestion generalization result |
| Warm-serving latency reduction | **77.26%** | Post-evaluation engineering/serving result |

The 77.26% serving figure must not replace either frozen research benchmark.

The later 84.49% hardening revalidation is an incidental regression check and is not the canonical serving-performance result.

## Visuals

The paper working draft contains quantitative figures for:

- Layer A extraction/source-fidelity results;
- frozen E5 final retrieval and semantic results;
- frozen-final versus unseen generalization;
- post-evaluation serving latency.

Figure QA requirement:

- legends must remain outside the plotting area when they would obscure data;
- value labels must have clear padding from axes/borders;
- captions must remain attached to their figures;
- figures must not imply that serving/demo acceptance is research accuracy.

## Review and authoring boundary

The conference paper should remain faithful to the frozen experiment record. Do not silently:

- retune retrieval using final-test failures;
- rewrite gold evidence to improve scores;
- combine unseen results with the primary benchmark;
- describe eight demo scenarios as 100% research accuracy;
- describe the serving optimization as a new research benchmark;
- imply that the assistant is an autonomous maintenance authority.

The assistant remains a decision-support research prototype. Original regulatory documents remain authoritative, and referenced approved maintenance data must still be consulted when required.

## Current status

**Methodology drafting: in progress.**

The paper visual draft has been updated with chart layout corrections, including moving the Fig. 4 legend outside the plotting area. The latest local working files are maintained separately from the repository implementation freeze.
