import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const assistantMocks = vi.hoisted(() => ({
  cancelQuestion: vi.fn(),
  getHealth: vi.fn(),
  streamQuestion: vi.fn(),
}));

import type { AssistantResult, Evidence } from "@/lib/assistant";

vi.mock("@/lib/assistant", () => assistantMocks);

import { ConversationShell, evidenceWidthStore } from "@/components/conversation-shell";

const evidence: Evidence[] = [
  {
    evidence_id: "EV1",
    chunk_id: "chunk-a",
    ad_number: "2008-0008",
    page_start: 1,
    page_end: 1,
    section: "Applicability",
    rank: 1,
    pre_rerank_rank: 1,
    reranker_score: 0.99,
    source_pdf: "2008-0008.pdf",
    text: "Applicability:\nAIRBUS A310 aircraft.",
  },
  {
    evidence_id: "EV2",
    chunk_id: "chunk-b",
    ad_number: "2011-0041R1",
    page_start: 2,
    page_end: 2,
    section: "Required Action(s)",
    rank: 2,
    pre_rerank_rank: 2,
    reranker_score: 0.95,
    source_pdf: "2011-0041R1.pdf",
    text: "Required Action(s):\nPerform the stated action.",
  },
];

const result: AssistantResult = {
  assistant_version: "aviation-document-assistant-v2.0",
  status: "answered",
  question: "demo",
  route: { mode: "known_document" },
  answer: "Demo answer",
  conditions: [],
  compliance_time: [],
  exceptions: [],
  reason_for_abstention: null,
  citations: [],
  evidence,
  timings: {
    routing_ms: 0,
    query_embedding_ms: 0,
    candidate_generation_ms: 0,
    reranking_ms: 0,
    retrieval_total_ms: 0,
    hosted_qa_ms: 0,
    total_ms: 1,
  },
  runtime: {},
};

describe("single-document follow-up scope", () => {
  beforeEach(() => {
    localStorage.clear();
    evidenceWidthStore.resetForTesting();
    Object.defineProperty(HTMLElement.prototype, "scrollTo", {
      configurable: true,
      value: vi.fn(),
    });
    assistantMocks.getHealth.mockResolvedValue({
      status: "ready",
      assistant_version: "aviation-document-assistant-v2.0",
      embedding_model_loaded: true,
      reranker_loaded: true,
      document_count: 1791,
      chunk_count: 12670,
      device: "mps",
    });
    assistantMocks.streamQuestion.mockImplementation(
      (_question: string, options: { onEvidence?: (items: Evidence[]) => void; onAnswer?: (answer: AssistantResult) => void }) => {
        options.onEvidence?.(evidence);
        options.onAnswer?.(result);
        return Promise.resolve();
      },
    );
    assistantMocks.cancelQuestion.mockResolvedValue(undefined);
  });

  afterEach(() => {
    cleanup();
    localStorage.clear();
    evidenceWidthStore.resetForTesting();
    vi.clearAllMocks();
  });

  it("replaces the previous AD when a new follow-up context is selected", async () => {
    render(<ConversationShell />);

    const example = screen.getByRole("button", { name: /01.*Applicability/i });
    await waitFor(() => expect(example).toBeEnabled());
    fireEvent.click(example);

    const firstContext = await screen.findByRole("button", { name: "Use 2008-0008 for follow-up" });
    fireEvent.click(firstContext);
    expect(screen.getByRole("button", { name: "Remove 2008-0008 context" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /02.*2011-0041R1/i }));
    const secondContext = screen.getByRole("button", { name: "Use 2011-0041R1 for follow-up" });
    fireEvent.click(secondContext);

    expect(screen.getByRole("button", { name: "Remove 2011-0041R1 context" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remove 2008-0008 context" })).not.toBeInTheDocument();
  });
});
