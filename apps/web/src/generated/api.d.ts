// Seeded from the FastAPI Pydantic contract. Regenerate with `pnpm --dir apps/web generate:api`
// whenever the backend schema changes.
export interface paths {
  "/api/v1/health": {
    get: operations["health_api_v1_health_get"];
  };
  "/api/v1/meta": {
    get: operations["meta_api_v1_meta_get"];
  };
  "/api/v1/query": {
    post: operations["query_api_v1_query_post"];
  };
  "/api/v1/query/stream": {
    post: operations["query_stream_api_v1_query_stream_post"];
  };
}

export interface components {
  schemas: {
    QueryRequest: {
      question: string;
      retrieval_only?: boolean;
      context_ad_numbers?: string[];
    };
    EvidenceRow: {
      evidence_id: string;
      rank: number;
      chunk_id: string;
      ad_number: string;
      source_pdf: string;
      page_start: number;
      page_end: number;
      section: string;
      text: string;
      reranker_score: number;
      pre_rerank_rank: number;
    };
    Citation: {
      evidence_id: string;
      chunk_id?: string | null;
      ad_number: string;
      source_pdf: string;
      page_start: number;
      page_end: number;
      section: string;
    };
    Timings: {
      routing_ms?: number;
      query_embedding_ms?: number;
      candidate_generation_ms?: number;
      reranking_ms?: number;
      retrieval_total_ms?: number;
      hosted_qa_ms?: number;
      total_ms?: number;
    };
    QueryResponse: {
      assistant_version: string;
      status: "answered" | "insufficient_evidence" | "conflicting_evidence" | "retrieval_only" | "technical_error";
      question: string;
      route: Record<string, unknown>;
      answer?: string | null;
      conditions?: string[];
      compliance_time?: string[];
      exceptions?: string[];
      reason_for_abstention?: string | null;
      citations?: components["schemas"]["Citation"][];
      evidence?: components["schemas"]["EvidenceRow"][];
      timings: components["schemas"]["Timings"];
      runtime?: Record<string, unknown>;
      technical_error?: Record<string, unknown> | null;
    };
    HealthResponse: {
      status: "starting" | "ready" | "error";
      assistant_version: string;
      embedding_model_loaded: boolean;
      reranker_loaded: boolean;
      device: string;
      document_count: number;
      chunk_count: number;
    };
  };
}

export interface operations {
  health_api_v1_health_get: {
    responses: { 200: { content: { "application/json": components["schemas"]["HealthResponse"] } } };
  };
  meta_api_v1_meta_get: {
    responses: { 200: { content: { "application/json": Record<string, unknown> } } };
  };
  query_api_v1_query_post: {
    requestBody: { content: { "application/json": components["schemas"]["QueryRequest"] } };
    responses: { 200: { content: { "application/json": components["schemas"]["QueryResponse"] } } };
  };
  query_stream_api_v1_query_stream_post: {
    requestBody: { content: { "application/json": components["schemas"]["QueryRequest"] } };
    responses: { 200: { content: { "text/event-stream": string } } };
  };
}
