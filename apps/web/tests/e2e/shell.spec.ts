import { expect, test } from "@playwright/test";

const API_ORIGIN = "http://127.0.0.1:8000";
const WEB_ORIGIN = "http://127.0.0.1:3000";

function corsHeaders(contentType = "application/json") {
  return {
    "Access-Control-Allow-Origin": WEB_ORIGIN,
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "content-type,accept",
    "Content-Type": contentType,
  };
}

test.beforeEach(async ({ page }) => {
  await page.route(`${API_ORIGIN}/api/v1/health`, async (route) => {
    await route.fulfill({
      status: 200,
      headers: corsHeaders(),
      body: JSON.stringify({
        status: "ready",
        assistant_version: "aviation-document-assistant-v2.0",
        embedding_model_loaded: true,
        reranker_loaded: true,
        device: "mps",
        document_count: 1791,
        chunk_count: 12670,
      }),
    });
  });
});

test("renders the aviation assistant shell and evidence inspector", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Airbus EASA AD Assistant" })).toBeVisible();
  await expect(page.getByText("Evidence inspector")).toBeVisible();
  await expect(page.getByRole("heading", { name: /Ask with precision/i })).toBeVisible();
  await expect(page.getByLabel("Evidence inspector")).toBeVisible();
  await expect(page.getByRole("separator", { name: "Resize evidence inspector" })).toBeVisible();
  await expect(page.getByLabel("Ask the Airbus EASA AD corpus")).toBeVisible();
  await expect(page.getByText(/controlling EASA AD/i)).toBeVisible();
  await expect(page.getByText(/1,791 documents/i)).toBeVisible();
});

test("shows retrieved evidence before a validated mocked answer", async ({ page }) => {
  const evidence = {
    evidence_id: "EV1",
    rank: 1,
    chunk_id: "chunk-2011-0041r1-2",
    ad_number: "2011-0041R1",
    source_pdf: "EASA_AD_2011-0041R1.pdf",
    page_start: 2,
    page_end: 2,
    section: "Required Action(s) and Compliance Time(s)",
    text: "Required Action(s):\n(1) Install ATQC V11 L50 and activate ETC No. 0038.",
    reranker_score: 0.98,
    pre_rerank_rank: 1,
  };

  await page.route(`${API_ORIGIN}/api/v1/query/stream`, async (route) => {
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: corsHeaders() });
      return;
    }

    const result = {
      assistant_version: "aviation-document-assistant-v2.0",
      status: "answered",
      question: "For EASA AD 2011-0041R1, what actions had to be completed within 3 days after 14 March 2011?",
      route: { mode: "known_document" },
      answer: "Complete both required actions within 3 days after 14 March 2011.",
      conditions: [],
      compliance_time: ["Within 3 days after 14 March 2011"],
      exceptions: [],
      reason_for_abstention: null,
      citations: [
        {
          evidence_id: "EV1",
          chunk_id: evidence.chunk_id,
          ad_number: evidence.ad_number,
          source_pdf: evidence.source_pdf,
          page_start: 2,
          page_end: 2,
          section: evidence.section,
        },
      ],
      evidence: [evidence],
      timings: {
        routing_ms: 1,
        query_embedding_ms: 0,
        candidate_generation_ms: 20,
        reranking_ms: 30,
        retrieval_total_ms: 50,
        hosted_qa_ms: 120,
        total_ms: 170,
      },
      runtime: { device: "mps", corpus: { document_count: 1791, chunk_count: 12670 } },
    };

    const body = [
      `event: request.started\ndata: ${JSON.stringify({ request_id: "e2e-request" })}\n\n`,
      `event: route.completed\ndata: ${JSON.stringify({ route: result.route })}\n\n`,
      "event: retrieval.started\ndata: {}\n\n",
      `event: evidence.ready\ndata: ${JSON.stringify({ evidence: [evidence], timings: result.timings, runtime: result.runtime })}\n\n`,
      "event: generation.started\ndata: {}\n\n",
      `event: answer.completed\ndata: ${JSON.stringify(result)}\n\n`,
      `event: request.completed\ndata: ${JSON.stringify({ status: "answered" })}\n\n`,
    ].join("");

    await route.fulfill({
      status: 200,
      headers: corsHeaders("text/event-stream"),
      body,
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: /02.*Compliance/i }).click();

  await expect(page.getByText("Complete both required actions within 3 days after 14 March 2011.")).toBeVisible();
  await expect(page.getByText("Required Action(s)")).toBeVisible();
  await expect(page.getByText("2011-0041R1").first()).toBeVisible();
  await expect(page.getByText("Within 3 days after 14 March 2011")).toBeVisible();
});

test("Stop restores the active question and calls the cancellation endpoint", async ({ page }) => {
  let cancellationCalled = false;

  await page.route(`${API_ORIGIN}/api/v1/query/stream`, async (route) => {
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: corsHeaders() });
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 600));
    try {
      await route.fulfill({
        status: 200,
        headers: corsHeaders("text/event-stream"),
        body: "event: retrieval.started\ndata: {}\n\n",
      });
    } catch {
      // The browser intentionally aborted the request after Stop was pressed.
    }
  });

  await page.route(`${API_ORIGIN}/api/v1/query/*/cancel`, async (route) => {
    cancellationCalled = true;
    await route.fulfill({
      status: 200,
      headers: corsHeaders(),
      body: JSON.stringify({ request_id: "browser-request", status: "cancelling" }),
    });
  });

  await page.goto("/");
  const example = page.getByRole("button", { name: /01.*Applicability/i });
  await expect(example).toBeEnabled();
  await example.click();

  await page.getByRole("button", { name: "Stop request" }).click();

  const composer = page.getByRole("textbox", { name: "Ask the Airbus EASA AD corpus" });
  await expect(composer).toHaveValue("Which A310 models are affected by EASA AD 2008-0008?");
  await expect(page.getByRole("button", { name: "Stop request" })).toHaveCount(0);
  await expect.poll(() => cancellationCalled).toBe(true);
});
