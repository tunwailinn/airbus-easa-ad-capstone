# Airbus EASA AD Capstone — Documentation Catalog

Publication labels: E1 = legacy E4; E2-A–D = legacy E5-A–D. Artifact names, question IDs and code excerpts retain their original labels. See [experiment label mapping](EXPERIMENT_LABELS.md).

This directory contains the complete technical, experimental, and operational documentation for the **Airbus S.A.S. EASA Airworthiness Directive (AD) Automation and RAG Capstone**.

All core research benchmarks (Layer A deterministic extraction, Layer B E2-D retrieval, Layer C hosted QA, and the five-PDF unseen generalization experiment) are **frozen and locked**. Subsequent engineering work covers the user-facing assistant runtime and demo freeze.

---

## Quick Navigation

```text
docs/
├── Master Project Status & Governance
├── Layer A & Layer B Pipelines
├── Layer C Hosted QA & Benchmark Results
├── Five-Document Unseen Generalization Experiment (U0–U8)
└── Post-Evaluation Assistant & Demo Freeze
```

---

## 1. Master Project Status & Governance

High-level project status, architectural decision logs, and experimental boundaries:

- [`PROJECT_STATUS.md`](PROJECT_STATUS.md) — **Authoritative master project status**: comprehensive positions across Layer A extraction, Layer B retrieval, Layer C QA (38/40 = 95.0%), unseen generalization (U0–U8), and post-evaluation assistant demo freeze.
- [`DECISIONS.md`](DECISIONS.md) — **Project decisions log**: stable record of methodological decisions D01–D65 and dated change log entries through demo freeze.
- [`BENCHMARK_DESIGN.md`](BENCHMARK_DESIGN.md) — **Benchmark methodology & dataset design**: layer-separated evaluation principles, split definitions, frozen criteria, and evaluation boundaries.
- [`CLOUD_WORKFLOW.md`](CLOUD_WORKFLOW.md) — **Cloud & data workflow**: data storage boundaries between versioned GitHub code and external/large derivatives (Google Drive / local storage).

---

## 2. Layer A & Layer B Pipelines

Deterministic extraction, page-level PDF source text, and retrieval pipelines:

- [`PAGE_TEXT_PIPELINE.md`](PAGE_TEXT_PIPELINE.md) — **Page-preserving PDF text pipeline (`page-text-v1.1`)**: extraction of 6,002 verified operational pages across 1,786 strict-scope documents, visual override audit (`2011-0006`), and indexing gates.
- [`RETRIEVAL_BUILD_STATUS.md`](RETRIEVAL_BUILD_STATUS.md) — **Historical E0/E1 retrieval build & evaluation status**: frozen comparison between E0 flat dense-only and E1 section-aware hybrid retrieval, FAISS backend validation, and process isolation.
- [`E5_ENGINEERING_AWARE_RETRIEVAL.md`](E5_ENGINEERING_AWARE_RETRIEVAL.md) — **E2 engineering-aware retrieval methodology**: design of deterministic known-document routing, section-aware passage retrieval, and discovery mode.

---

## 3. Layer C Hosted QA & Benchmark Results

Hosted evidence-grounded QA, evaluation records, and oracle diagnostics:

- [`E5_STATUS.md`](E5_STATUS.md) — **E2 status & progress record**: developmental progression through E2-D retrieval, hosted-QA freeze, final 40-question benchmark, unseen evaluation, and assistant demo freeze.
- [`E5_DEVELOPMENT_REVIEW_AUDIT.md`](E5_DEVELOPMENT_REVIEW_AUDIT.md) — **Development question audit**: human review audit of the 60 E2 development questions against source authoring packets.
- [`LAYER_C_HOSTED_QA.md`](LAYER_C_HOSTED_QA.md) — **Hosted evidence-grounded QA specification**: DeepSeek V4 Pro configuration, reasoning effort, prompt engineering, and response contract schema.
- [`HOSTED_LLM_GATEWAY.md`](HOSTED_LLM_GATEWAY.md) — **Hosted LLM gateway specification**: legacy/optional centralized gateway documentation.
- [`LAYER_C_DEVELOPMENT_EVALUATION.md`](LAYER_C_DEVELOPMENT_EVALUATION.md) — **60-question development evaluation report**: baseline results, error attribution (E5D-017, E5D-030), and transport retry audit.
- [`LAYER_C_ORACLE_EVIDENCE.md`](LAYER_C_ORACLE_EVIDENCE.md) — **Development oracle evidence pack**: reference-evidence diagnostic packaging for development questions.
- [`LAYER_C_ORACLE_EVALUATION.md`](LAYER_C_ORACLE_EVALUATION.md) — **Development oracle evaluation**: diagnostic analysis separating retrieval misses from generation limits.
- [`LAYER_C_FINAL_BENCHMARK.md`](LAYER_C_FINAL_BENCHMARK.md) — **One-time final benchmark execution**: immutable configuration and automated metrics for the 40-question final benchmark.
- [`LAYER_C_FINAL_EVALUATION.md`](LAYER_C_FINAL_EVALUATION.md) — **Authoritative final benchmark report**: human semantic evaluation (**38/40 = 95.0% PASS**), failure attribution (E5F-011, E5F-021), and final oracle diagnostic.

---

## 4. Five-Document Unseen Generalization Experiment (U0–U8)

Evaluation of five held-out strata PDFs (corrected, revised, supersedure, long document, simple original):

- [`UNSEEN_DOCUMENT_EVALUATION.md`](UNSEEN_DOCUMENT_EVALUATION.md) — **Canonical unseen evaluation document**: comprehensive protocol and findings across stages U0 through U8.
- [`UNSEEN_TEMPORARY_QA_FIRST_PASS.md`](UNSEEN_TEMPORARY_QA_FIRST_PASS.md) — **Temporary unseen QA first-pass record (U3/U4)**: first-pass metrics, passage selection diagnostic on `U5Q-010`, and provider error on `U5Q-011`.
- [`UNSEEN_PERMANENT_INGESTION.md`](UNSEEN_PERMANENT_INGESTION.md) — **Isolated permanent ingestion (U5/U6)**: technical safeguard validation (5/5 pass), exact duplicate rejection, and index expansion to 1,791 documents / 12,670 chunks.
- [`UNSEEN_POST_INGESTION_QA.md`](UNSEEN_POST_INGESTION_QA.md) — **Post-ingestion evaluation (U7)**: execution and human review of post-ingestion E2-D retrieval (14/14 = 100% Recall@5) and Layer C QA.
- [`U8_FINAL_UNSEEN_GENERALIZATION_REPORT.md`](U8_FINAL_UNSEEN_GENERALIZATION_REPORT.md) — **Final unseen generalization report (U8)**: authoritative executive summary and locked completion report.

---

## 5. Post-Evaluation Assistant & Demo Freeze

User-facing software engineering, serving optimization, reliability hardening, and live validation:

- [`ASSISTANT_STATUS.md`](ASSISTANT_STATUS.md) — **Master assistant demo status**: baseline freeze checkpoint (commit `88f96d5`), warm-serving metrics, and live validation acceptance.
- [`ASSISTANT_MODERNIZATION.md`](ASSISTANT_MODERNIZATION.md) — **FastAPI + Next.js modernization**: warm model caching on Apple MPS, reducing median retrieval latency by 77.26% (26.87 s to 6.11 s) with 10/10 exact top-5 evidence match.
- [`ASSISTANT_INTEGRATION.md`](ASSISTANT_INTEGRATION.md) — **Assistant serving integration**: serving snapshot creation (`data_processed/serving/assistant_v1/`), CLI interface, and fallback prototype.
- [`ASSISTANT_DEMO_FREEZE_HARDENING.md`](ASSISTANT_DEMO_FREEZE_HARDENING.md) — **Demo reliability hardening**: single-AD follow-up context, SSE completion check, and stage-safe cancellation checkpoints.
- [`ASSISTANT_FINAL_DEMO_VALIDATION.md`](ASSISTANT_FINAL_DEMO_VALIDATION.md) — **Demo validation checklist**: freeze acceptance criteria and execution logs.
- [`D1_D8_FINAL_LIVE_DEMO_VALIDATION.md`](D1_D8_FINAL_LIVE_DEMO_VALIDATION.md) — **Executed live demo validation**: manual browser test records for scenarios D1 through D8 (all PASS).

### Machine-Readable Demo Artifacts:
- [`ASSISTANT_WARM_SERVING_ACCEPTANCE.json`](ASSISTANT_WARM_SERVING_ACCEPTANCE.json) — Warm serving latency and top-5 compatibility benchmark data.
- [`ASSISTANT_HARDENING_REVALIDATION.json`](ASSISTANT_HARDENING_REVALIDATION.json) — Post-hardening regression revalidation data.
- [`ASSISTANT_DEMO_SHOWCASE_QUESTIONS.json`](ASSISTANT_DEMO_SHOWCASE_QUESTIONS.json) — Validated showcase questions for live demonstrations.

---

## Authority & Governance Hierarchy

When consulting project documentation, follow the precedence order established in [`AGENTS.md`](../AGENTS.md):

1. Current user instructions;
2. Root [`AGENTS.md`](../AGENTS.md);
3. Machine-readable locks (`final_lock.json`, `unseen_final_generalization_lock.json`, etc.);
4. Canonical reports: [`U8_FINAL_UNSEEN_GENERALIZATION_REPORT.md`](U8_FINAL_UNSEEN_GENERALIZATION_REPORT.md), [`UNSEEN_DOCUMENT_EVALUATION.md`](UNSEEN_DOCUMENT_EVALUATION.md), [`E5_STATUS.md`](E5_STATUS.md), [`LAYER_C_FINAL_EVALUATION.md`](LAYER_C_FINAL_EVALUATION.md), [`PROJECT_STATUS.md`](PROJECT_STATUS.md);
5. Active decisions: [`DECISIONS.md`](DECISIONS.md);
6. Benchmark specification: [`BENCHMARK_DESIGN.md`](BENCHMARK_DESIGN.md).
