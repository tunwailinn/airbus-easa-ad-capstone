import { afterEach, describe, expect, it, vi } from "vitest";

import { normalizeContextAdNumbers, streamQuestion } from "@/lib/assistant";

function mockSseResponse(frames: string[]) {
  const encoder = new TextEncoder();
  const values = frames.map((frame) => encoder.encode(frame));
  let index = 0;
  const reader = {
    read: vi.fn(async () => {
      if (index >= values.length) return { done: true, value: undefined };
      const value = values[index++];
      return { done: false, value };
    }),
    cancel: vi.fn(async () => undefined),
    releaseLock: vi.fn(),
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({
      ok: true,
      status: 200,
      body: { getReader: () => reader },
    })),
  );
  return reader;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("normalizeContextAdNumbers", () => {
  it("keeps only the most recently selected explicit AD", () => {
    expect(normalizeContextAdNumbers([])).toEqual([]);
    expect(normalizeContextAdNumbers(["2011-0041R1"])).toEqual(["2011-0041R1"]);
    expect(normalizeContextAdNumbers(["2008-0008", "2011-0041R1"])).toEqual(["2011-0041R1"]);
  });
});

describe("streamQuestion", () => {
  it("fails clearly if the SSE stream closes without a validated final answer", async () => {
    mockSseResponse([
      "event: request.started\ndata: {\"request_id\":\"request-123\"}\n\n",
      "event: retrieval.started\ndata: {}\n\n",
    ]);

    await expect(
      streamQuestion("What does this AD require?", {
        requestId: "request-123",
        retrievalOnly: false,
        contextAdNumbers: [],
        signal: new AbortController().signal,
        onStage: vi.fn(),
        onEvidence: vi.fn(),
        onAnswer: vi.fn(),
      }),
    ).rejects.toThrow("Assistant stream ended before a validated final answer was received.");
  });

  it("resolves after answer.completed and sends only one follow-up AD", async () => {
    mockSseResponse([
      "event: answer.completed\ndata: {\"status\":\"answered\",\"answer\":\"Done\",\"evidence\":[],\"citations\":[],\"conditions\":[],\"compliance_time\":[],\"exceptions\":[],\"route\":{},\"timings\":{},\"runtime\":{},\"assistant_version\":\"test\",\"question\":\"q\"}\n\n",
    ]);
    const onAnswer = vi.fn();

    await streamQuestion("q", {
      requestId: "request-456",
      retrievalOnly: false,
      contextAdNumbers: ["2008-0008", "2011-0041R1"],
      signal: new AbortController().signal,
      onStage: vi.fn(),
      onEvidence: vi.fn(),
      onAnswer,
    });

    expect(onAnswer).toHaveBeenCalledOnce();
    const fetchMock = vi.mocked(fetch);
    const [, init] = fetchMock.mock.calls[0];
    const body = JSON.parse(String(init?.body));
    expect(body.context_ad_numbers).toEqual(["2011-0041R1"]);
  });
});
