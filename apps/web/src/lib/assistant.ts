export type Evidence = {
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

export type AssistantResult = {
  assistant_version: string;
  status: "answered" | "insufficient_evidence" | "conflicting_evidence" | "retrieval_only" | "technical_error";
  question: string;
  route: Record<string, unknown>;
  answer: string | null;
  conditions: string[];
  compliance_time: string[];
  exceptions: string[];
  reason_for_abstention?: string | null;
  citations: Array<{
    evidence_id: string;
    chunk_id?: string | null;
    ad_number: string;
    source_pdf: string;
    page_start: number;
    page_end: number;
    section: string;
  }>;
  evidence: Evidence[];
  timings: Record<string, number>;
  runtime: Record<string, unknown>;
  technical_error?: { type: string; message: string } | null;
};

export type PipelineStage = "idle" | "routing" | "retrieving" | "evidence" | "generating" | "complete" | "error";

const API = process.env.NEXT_PUBLIC_ASSISTANT_API_URL ?? "http://127.0.0.1:8000";

export async function streamQuestion(
  question: string,
  options: {
    retrievalOnly: boolean;
    contextAdNumbers: string[];
    signal: AbortSignal;
    onStage: (stage: PipelineStage) => void;
    onEvidence: (evidence: Evidence[], meta: Record<string, unknown>) => void;
    onAnswer: (answer: AssistantResult) => void;
  },
) {
  options.onStage("routing");
  const response = await fetch(`${API}/api/v1/query/stream`, {
    method: "POST",
    headers: { "content-type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({
      question,
      retrieval_only: options.retrievalOnly,
      context_ad_numbers: options.contextAdNumbers,
    }),
    signal: options.signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(`Assistant API returned HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      let event = "message";
      let data = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (!data) continue;
      const payload = JSON.parse(data);
      if (event === "route.completed") options.onStage("retrieving");
      if (event === "evidence.ready") {
        options.onStage("evidence");
        options.onEvidence(payload.evidence ?? [], payload);
      }
      if (event === "generation.started") options.onStage("generating");
      if (event === "answer.completed") {
        options.onStage("complete");
        options.onAnswer(payload as AssistantResult);
      }
    }
  }
}

export async function getHealth() {
  const response = await fetch(`${API}/api/v1/health`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Health check failed: ${response.status}`);
  return response.json() as Promise<{
    status: "starting" | "ready" | "error";
    assistant_version: string;
    embedding_model_loaded: boolean;
    reranker_loaded: boolean;
    device: string;
    document_count: number;
    chunk_count: number;
  }>;
}
