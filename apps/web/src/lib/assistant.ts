import type { components } from "@/generated/api";
import { API_BASE, api } from "@/lib/api";

export type Evidence = components["schemas"]["EvidenceRow"];
export type Health = components["schemas"]["HealthResponse"];
type ApiAssistantResult = components["schemas"]["QueryResponse"];

export type AssistantResult = Omit<
  ApiAssistantResult,
  "answer" | "conditions" | "compliance_time" | "exceptions" | "citations" | "evidence" | "technical_error"
> & {
  answer: string | null;
  conditions: string[];
  compliance_time: string[];
  exceptions: string[];
  citations: components["schemas"]["Citation"][];
  evidence: Evidence[];
  technical_error?: { type: string; message: string } | null;
};

export type PipelineStage = "idle" | "routing" | "retrieving" | "evidence" | "generating" | "complete" | "error";

export async function streamQuestion(
  question: string,
  options: {
    requestId?: string;
    retrievalOnly: boolean;
    contextAdNumbers: string[];
    signal: AbortSignal;
    onStage: (stage: PipelineStage) => void;
    onEvidence: (evidence: Evidence[], meta: Record<string, unknown>) => void;
    onAnswer: (answer: AssistantResult) => void;
  },
) {
  const requestId = options.requestId ?? crypto.randomUUID();
  options.onStage("routing");
  const response = await fetch(`${API_BASE}/api/v1/query/stream`, {
    method: "POST",
    headers: { "content-type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({
      request_id: requestId,
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
  const cancelReader = () => {
    void reader.cancel().catch(() => undefined);
  };
  options.signal.addEventListener("abort", cancelReader, { once: true });

  try {
    while (true) {
      if (options.signal.aborted) throw new DOMException("Request stopped", "AbortError");
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
        if (!data || options.signal.aborted) continue;
        const payload = JSON.parse(data);
        if (event === "route.completed" || event === "retrieval.started") options.onStage("retrieving");
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
    if (options.signal.aborted) throw new DOMException("Request stopped", "AbortError");
  } finally {
    options.signal.removeEventListener("abort", cancelReader);
    reader.releaseLock();
  }
}

export async function cancelQuestion(requestId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/query/${encodeURIComponent(requestId)}/cancel`, {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Assistant cancellation returned HTTP ${response.status}`);
  }
}

export async function getHealth(): Promise<Health> {
  const { data } = await api.GET("/api/v1/health", {
    cache: "no-store",
  });
  if (!data) {
    throw new Error("Health check returned no data");
  }
  return data;
}
