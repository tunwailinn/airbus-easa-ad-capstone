# Experiment label mapping

The paper and documentation prose use consecutive experiment labels. This is an editorial rename only; methods, datasets, results and frozen artifacts are unchanged.

| Publication label | Original artifact label | Experiment |
| --- | --- | --- |
| E0 | E0 | Historical flat dense baseline |
| E1 | E4 | Historical section-aware hybrid retrieval with MiniLM reranking |
| E2-A | E5-A | Deterministic routing and lexical retrieval |
| E2-B | E5-B | Two-stage sparse discovery and evidence assembly |
| E2-C | E5-C | Qwen3 dense document and passage fusion |
| E2-D | E5-D | Qwen3 reranking of the fixed top-20 candidate pool |
| E2 final benchmark | E5 final benchmark | Separate frozen final evaluation of the selected E2-D system |

## Traceability

Frozen code, result files, question IDs, configuration identifiers and evaluation locks retain their original names. For example, `E5F-021` is still the final-test question ID, and `data_processed/evaluations/e5/e5d_development_evaluation.json` remains the E2-D development result source. Existing documentation filenames, including `E5_STATUS.md`, are unchanged. Literal code and artifact excerpts may therefore contain E4/E5 labels.

E1/E2 here identify experiments; evidence citation identifiers such as `E1` in a response are a separate namespace.

## Evaluation boundaries

E0 and E1 were evaluated on the same 44 answerable QA-v2 questions. E2-A–D share 54 answerable development questions out of 60 total. The E2 final benchmark contains 36 answerable retrieval questions out of 40 total, with 35/36 Recall@5 and 38/40 strict semantic accuracy. The five-PDF unseen study remains separate. Renaming does not make comparisons across these question sets controlled ablations and does not imply that additional experiments were run.
