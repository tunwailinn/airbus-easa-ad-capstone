import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const assistantMocks = vi.hoisted(() => ({
  cancelQuestion: vi.fn(),
  getHealth: vi.fn(),
  streamQuestion: vi.fn(),
}));

import type { AssistantResult, Evidence } from "@/lib/assistant";

vi.mock("@/lib/assistant", () => assistantMocks);

import { ConversationShell, evidenceWidthStore, parsePassage } from "@/components/conversation-shell";

describe("parsePassage", () => {
  it("groups split regulatory fields and clause continuations into readable blocks", () => {
    const blocks = parsePassage([
      "Type Approval Holder’s Name :",
      "AIRBUS SAS",
      "Applicability:",
      "AIRBUS A310-221 and A310-222 aircraft,",
      "all serial numbers.",
      "Reason(s):",
      "Cracks were found in the lower pylon spar.",
      "Required Action(s)",
      "and Compliance",
      "Time(s):",
      "(1) Perform an eddy current inspection",
      "within the stated threshold.",
      "Ref. Publications:",
      "AIRBUS Service Bulletin A310-54-2016.",
    ].join("\n"));

    expect(blocks).toEqual([
      { type: "field", prefix: "Type Approval Holder’s Name", content: "AIRBUS SAS", fieldLevel: "metadata" },
      { type: "field", prefix: "Applicability", content: "AIRBUS A310-221 and A310-222 aircraft, all serial numbers.", fieldLevel: "section" },
      { type: "field", prefix: "Reason(s)", content: "Cracks were found in the lower pylon spar.", fieldLevel: "section" },
      { type: "field", prefix: "Required Action(s) and Compliance Time(s)", content: "", fieldLevel: "section" },
      { type: "clause", prefix: "(1)", content: "Perform an eddy current inspection within the stated threshold." },
      { type: "field", prefix: "Ref. Publications", content: "AIRBUS Service Bulletin A310-54-2016.", fieldLevel: "section" },
    ]);
  });
});

describe("ConversationShell", () => {
  beforeEach(() => {
    localStorage.clear();
    evidenceWidthStore.resetForTesting();
    Object.defineProperty(HTMLElement.prototype, "scrollTo", {
      configurable: true,
      value: vi.fn(),
    });
    assistantMocks.getHealth.mockResolvedValue({
      status: "ready",
      document_count: 1791,
      device: "cpu",
    });
    assistantMocks.streamQuestion.mockReset();
    assistantMocks.cancelQuestion.mockResolvedValue(undefined);
  });

  afterEach(() => {
    cleanup();
    localStorage.clear();
    evidenceWidthStore.resetForTesting();
    vi.clearAllMocks();
  });

  it("stops an active request immediately and restores the question", async () => {
    let requestSignal: AbortSignal | undefined;
    assistantMocks.streamQuestion.mockImplementation(
      (_question: string, options: { signal: AbortSignal }) =>
        new Promise<void>((_resolve, reject) => {
          requestSignal = options.signal;
          options.signal.addEventListener(
            "abort",
            () => reject(new DOMException("Request stopped", "AbortError")),
            { once: true },
          );
        }),
    );

    render(<ConversationShell />);

    const example = screen.getByRole("button", { name: /01.*Applicability/i });
    await waitFor(() => expect(example).toBeEnabled());
    fireEvent.click(example);

    const stopButton = await screen.findByRole("button", { name: "Stop request" });
    const composer = screen.getByRole("textbox", { name: "Ask the Airbus EASA AD corpus" });
    expect(composer).toBeEnabled();
    fireEvent.click(stopButton);

    expect(requestSignal?.aborted).toBe(true);
    expect(assistantMocks.cancelQuestion).toHaveBeenCalledOnce();
    expect(assistantMocks.cancelQuestion).toHaveBeenCalledWith(expect.any(String));
    await waitFor(() => {
      expect(composer).toBeEnabled();
      expect(composer).toHaveValue(
        "Which A310 models are affected by EASA AD 2008-0008?",
      );
    });
    expect(screen.queryByRole("button", { name: "Stop request" })).not.toBeInTheDocument();
  });

  it("renders a resizable separator with proper ARIA attributes", async () => {
    render(<ConversationShell />);
    const separator = screen.getByRole("separator", { name: "Resize evidence inspector" });
    expect(separator).toBeInTheDocument();
    expect(separator).toHaveAttribute("aria-orientation", "vertical");
    expect(separator).toHaveAttribute("aria-valuenow", "420");
    expect(separator).toHaveAttribute("aria-valuemin", "280");
  });

  it("supports keyboard resizing with arrow keys, home, end, and enter reset", async () => {
    render(<ConversationShell />);
    const separator = screen.getByRole("separator", { name: "Resize evidence inspector" });

    // ArrowLeft expands evidence width (+24)
    fireEvent.keyDown(separator, { key: "ArrowLeft" });
    expect(separator).toHaveAttribute("aria-valuenow", "444");

    // ArrowRight contracts evidence width (-24)
    fireEvent.keyDown(separator, { key: "ArrowRight" });
    expect(separator).toHaveAttribute("aria-valuenow", "420");

    // Home snaps to minimum evidence width (280)
    fireEvent.keyDown(separator, { key: "Home" });
    expect(separator).toHaveAttribute("aria-valuenow", "280");

    // "Reset width" button appears when width is not default
    const resetButton = screen.getByRole("button", { name: "Reset panel width to default" });
    expect(resetButton).toBeInTheDocument();

    // Clicking reset width restores default 420
    fireEvent.click(resetButton);
    expect(separator).toHaveAttribute("aria-valuenow", "420");
    expect(screen.queryByRole("button", { name: "Reset panel width to default" })).not.toBeInTheDocument();

    // Enter key resets width to default
    fireEvent.keyDown(separator, { key: "ArrowLeft" });
    expect(separator).toHaveAttribute("aria-valuenow", "444");
    fireEvent.keyDown(separator, { key: "Enter" });
    expect(separator).toHaveAttribute("aria-valuenow", "420");
  });

  it("resizes dynamically via pointer drag", async () => {
    const { container } = render(<ConversationShell />);
    const workspaceGrid = container.querySelector(".workspace-grid") as HTMLElement;
    const separator = screen.getByRole("separator", { name: "Resize evidence inspector" });

    vi.spyOn(workspaceGrid, "getBoundingClientRect").mockReturnValue({
      width: 1200,
      right: 1200,
      left: 0,
      top: 0,
      bottom: 800,
      height: 800,
      x: 0,
      y: 0,
      toJSON: () => {},
    });

    fireEvent.pointerDown(separator, { button: 0, clientX: 780, pointerId: 1 });
    fireEvent.pointerMove(separator, { clientX: 700, pointerId: 1 });
    expect(separator).toHaveAttribute("aria-valuenow", "500");

    fireEvent.pointerUp(separator, { pointerId: 1 });
    expect(separator).toHaveAttribute("aria-valuenow", "500");
  });

  it("resets width on double-click of the separator", async () => {
    render(<ConversationShell />);
    const separator = screen.getByRole("separator", { name: "Resize evidence inspector" });

    fireEvent.keyDown(separator, { key: "ArrowLeft" });
    expect(separator).toHaveAttribute("aria-valuenow", "444");

    fireEvent.doubleClick(separator);
    expect(separator).toHaveAttribute("aria-valuenow", "420");
  });

  it("renders rich formatted passage with font cycling, mode toggle, and copy action", async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: { writeText: writeTextMock },
    });

    assistantMocks.streamQuestion.mockImplementation(
      (_question: string, options: { onEvidence?: (items: Evidence[]) => void; onAnswer?: (result: AssistantResult) => void }) => {
        const testEvidence: Evidence[] = [
          {
            evidence_id: "E5D-001",
            chunk_id: "chk-1",
            ad_number: "2024-0001",
            page_start: 2,
            page_end: 2,
            section: "Requirements",
            rank: 1,
            pre_rerank_rank: 1,
            reranker_score: 0.95,
            source_pdf: "2024-0001.pdf",
            text: "Required Action(s):\n(1) Accomplish detailed inspection.\nNote 1: Refer to service bulletin.",
          },
        ];
        options.onEvidence?.(testEvidence);
        options.onAnswer?.({
          assistant_version: "1.0.0",
          question: "Test question",
          answer: "Answer text",
          reason_for_abstention: null,
          status: "answered",
          route: { mode: "known_ad", requested_ad_numbers: ["2024-0001"], discovery_query: null },
          citations: [
            {
              evidence_id: "E5D-001",
              chunk_id: "chk-1",
              ad_number: "2024-0001",
              source_pdf: "2024-0001.pdf",
              section: "Requirements",
              page_start: 2,
              page_end: 2,
            },
          ],
          conditions: [],
          compliance_time: [],
          exceptions: [],
          evidence: testEvidence,
          timings: {
            routing_ms: 10,
            query_embedding_ms: 20,
            candidate_generation_ms: 30,
            reranking_ms: 40,
            retrieval_total_ms: 100,
            hosted_qa_ms: 400,
            total_ms: 500,
          },
        });
        return Promise.resolve();
      },
    );

    const { container } = render(<ConversationShell />);
    const example = screen.getByRole("button", { name: /01.*Applicability/i });
    await waitFor(() => expect(example).toBeEnabled());
    fireEvent.click(example);

    // Wait for evidence passage to render
    await screen.findByText("Formatted Reader");
    expect(screen.getByText("Retrieved section")).toBeInTheDocument();
    expect(screen.getAllByText("Requirements")).toHaveLength(2);
    expect(screen.getByText("Required Action(s)")).toBeInTheDocument();
    expect(screen.getByText("(1)")).toBeInTheDocument();
    expect(screen.getByText("Accomplish detailed inspection.")).toBeInTheDocument();
    expect(screen.getByText("Note 1:")).toBeInTheDocument();

    // Test font size cycling
    const fontButton = screen.getByRole("button", { name: /change font size/i });
    expect(fontButton).toHaveTextContent("MD");
    fireEvent.click(fontButton);
    expect(fontButton).toHaveTextContent("LG");
    fireEvent.click(fontButton);
    expect(fontButton).toHaveTextContent("SM");
    fireEvent.click(fontButton);
    expect(fontButton).toHaveTextContent("MD");

    // Test view mode toggle (Raw vs Formatted)
    const modeButton = screen.getByRole("button", { name: "Toggle view mode" });
    fireEvent.click(modeButton);
    expect(screen.getByText("Verbatim Source")).toBeInTheDocument();
    const preElement = container.querySelector("pre.passage-raw");
    expect(preElement).toBeInTheDocument();
    expect(preElement).toHaveTextContent("Required Action(s):");

    // Toggle back to Reader
    fireEvent.click(modeButton);
    expect(screen.getByText("Formatted Reader")).toBeInTheDocument();

    // Test copy passage
    const copyButton = screen.getByRole("button", { name: "Copy passage text" });
    fireEvent.click(copyButton);
    expect(writeTextMock).toHaveBeenCalledWith("Required Action(s):\n(1) Accomplish detailed inspection.\nNote 1: Refer to service bulletin.");
    expect(await screen.findByText("Copied")).toBeInTheDocument();
  });
});
