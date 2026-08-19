"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowUp,
  BookOpenText,
  CircleStop,
  FileSearch,
  Gauge,
  LoaderCircle,
  Plane,
  Radar,
  ShieldCheck,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast, Toaster } from "sonner";

import {
  type AssistantResult,
  type Evidence,
  type PipelineStage,
  getHealth,
  streamQuestion,
} from "@/lib/assistant";

const EXAMPLES = [
  ["Applicability", "Which A310 models are affected by EASA AD 2008-0008?"],
  ["Compliance", "For EASA AD 2011-0041R1, what actions had to be completed within 3 days after 14 March 2011?"],
  ["Discovery", "Which Airbus directive requires reporting inspection results including no findings within 30 days after each inspection?"],
  ["Lifecycle", "Which earlier directive does EASA AD 2011-0041R1 revise?"],
] as const;

const STAGES: Array<[PipelineStage, string]> = [
  ["routing", "Route"],
  ["retrieving", "Retrieve"],
  ["evidence", "Evidence"],
  ["generating", "Answer"],
];

function pages(item: { page_start: number; page_end: number }) {
  return item.page_start === item.page_end ? `${item.page_start}` : `${item.page_start}–${item.page_end}`;
}

function rank(stage: PipelineStage) {
  return { idle: -1, routing: 0, retrieving: 1, evidence: 2, generating: 3, complete: 4, error: -1 }[stage];
}

export function AssistantShell() {
  const [question, setQuestion] = useState("");
  const [stage, setStage] = useState<PipelineStage>("idle");
  const [result, setResult] = useState<AssistantResult | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [selectedEvidence, setSelectedEvidence] = useState<string | null>(null);
  const [retrievalOnly, setRetrievalOnly] = useState(false);
  const [health, setHealth] = useState<Awaited<ReturnType<typeof getHealth>> | null>(null);
  const [contextAds, setContextAds] = useState<string[]>([]);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const value = await getHealth();
        if (active) setHealth(value);
      } catch {
        if (active) setHealth(null);
      }
    };
    poll();
    const timer = window.setInterval(poll, 2500);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  const ready = health?.status === "ready";
  const busy = stage !== "idle" && stage !== "complete" && stage !== "error";
  const selected = evidence.find((item) => item.evidence_id === selectedEvidence) ?? evidence[0] ?? null;
  const routeMode = String((result?.route ?? {})["mode"] ?? "");

  const totalMs = useMemo(() => result?.timings?.total_ms ?? 0, [result]);

  async function submit(event?: FormEvent, override?: string) {
    event?.preventDefault();
    const value = (override ?? question).trim();
    if (!value || !ready || busy) return;

    setQuestion(value);
    setResult(null);
    setEvidence([]);
    setSelectedEvidence(null);
    setStage("routing");
    controller.current = new AbortController();

    try {
      await streamQuestion(value, {
        retrievalOnly,
        contextAdNumbers: contextAds,
        signal: controller.current.signal,
        onStage: setStage,
        onEvidence: (items) => {
          setEvidence(items);
          setSelectedEvidence(items[0]?.evidence_id ?? null);
        },
        onAnswer: (answer) => {
          setResult(answer);
          if (answer.status === "technical_error") {
            toast.warning("Hosted QA failed, but retrieved evidence is still available.");
          }
        },
      });
    } catch (error) {
      if ((error as Error).name !== "AbortError") {
        setStage("error");
        toast.error((error as Error).message);
      } else {
        setStage("idle");
      }
    }
  }

  function stop() {
    controller.current?.abort();
  }

  return (
    <main className="mx-auto min-h-screen max-w-[1500px] px-4 py-5 lg:px-8">
      <Toaster theme="dark" position="top-right" richColors />

      <header className="mb-5 flex items-center justify-between rounded-2xl border border-[#23384f] bg-[#0b1928]/90 px-5 py-4 shadow-2xl shadow-black/20 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-xl border border-[#31506e] bg-[#10253a] text-[#70b7ff]">
            <Plane className="size-5" />
          </div>
          <div>
            <h1 className="text-base font-semibold tracking-tight text-white sm:text-lg">Airbus EASA AD Assistant</h1>
            <p className="text-xs text-[#8fa5ba]">Evidence-grounded maintenance document intelligence</p>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-[#23384f] bg-[#091522] px-3 py-1.5 text-xs text-[#9bb0c4]">
          <span className={`size-2 rounded-full ${ready ? "bg-emerald-400" : "bg-amber-400"}`} />
          {ready ? `${health?.document_count.toLocaleString()} documents · ${health?.device.toUpperCase()}` : "Loading models"}
        </div>
      </header>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_420px]">
        <section className="flex min-h-[calc(100vh-130px)] flex-col overflow-hidden rounded-2xl border border-[#23384f] bg-[#0b1928]/88 shadow-2xl shadow-black/20">
          <div className="border-b border-[#1d3146] px-5 py-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm text-[#a9bacb]">
                <ShieldCheck className="size-4 text-emerald-400" />
                Frozen E5-C → E5-D → Layer C serving path
              </div>
              <label className="flex items-center gap-2 text-xs text-[#8fa5ba]">
                <input
                  type="checkbox"
                  checked={retrievalOnly}
                  onChange={(e) => setRetrievalOnly(e.target.checked)}
                  className="accent-[#58a6ff]"
                />
                Retrieval only
              </label>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-5 py-6 sm:px-8">
            {!result && stage === "idle" && evidence.length === 0 ? (
              <div className="mx-auto flex h-full max-w-3xl flex-col justify-center py-10">
                <div className="mb-8 text-center">
                  <div className="mx-auto mb-4 grid size-14 place-items-center rounded-2xl border border-[#2b4966] bg-[#10263b] text-[#70b7ff]">
                    <Radar className="size-7" />
                  </div>
                  <h2 className="text-2xl font-semibold tracking-tight text-white">Ask the AD corpus</h2>
                  <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-[#91a6ba]">
                    Ask about applicability, compliance actions, lifecycle statements, reference publications, or discover the relevant directive from maintenance language.
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {EXAMPLES.map(([label, text]) => (
                    <button
                      key={label}
                      onClick={() => submit(undefined, text)}
                      disabled={!ready}
                      className="group rounded-xl border border-[#23384f] bg-[#0e1e2e] p-4 text-left transition hover:-translate-y-0.5 hover:border-[#3b6287] hover:bg-[#11253a] disabled:opacity-50"
                    >
                      <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.14em] text-[#58a6ff]">{label}</span>
                      <span className="text-sm leading-5 text-[#c6d4e1] group-hover:text-white">{text}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="mx-auto max-w-3xl space-y-6">
                <div className="ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-[#1b4f7f] px-4 py-3 text-sm leading-6 text-white shadow-lg">
                  {question}
                </div>

                <Pipeline stage={stage} />

                {result && (
                  <article className="rounded-2xl border border-[#29445f] bg-[#0e2031] p-5 shadow-xl">
                    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                      <Status status={result.status} />
                      <span className="text-xs text-[#8499ad]">
                        {routeMode || "route"}{totalMs ? ` · ${(totalMs / 1000).toFixed(1)}s` : ""}
                      </span>
                    </div>

                    {result.answer ? (
                      <div className="prose prose-invert max-w-none text-[15px] leading-7 text-[#d8e3ed]">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.answer}</ReactMarkdown>
                      </div>
                    ) : result.reason_for_abstention ? (
                      <p className="text-sm leading-6 text-[#b8c7d5]">{result.reason_for_abstention}</p>
                    ) : null}

                    <Structured title="Conditions" values={result.conditions} />
                    <Structured title="Compliance time" values={result.compliance_time} />
                    <Structured title="Exceptions" values={result.exceptions} />

                    {result.citations.length > 0 && (
                      <div className="mt-5 border-t border-[#22384d] pt-4">
                        <p className="mb-2 text-xs font-semibold uppercase tracking-[.14em] text-[#8298ac]">Sources used</p>
                        <div className="flex flex-wrap gap-2">
                          {result.citations.map((citation) => (
                            <button
                              key={`${citation.evidence_id}-${citation.chunk_id}`}
                              onClick={() => setSelectedEvidence(citation.evidence_id)}
                              className="rounded-full border border-[#315271] bg-[#12283c] px-3 py-1.5 text-xs text-[#b9d7f5] transition hover:border-[#58a6ff] hover:text-white"
                            >
                              {citation.ad_number} · p.{pages(citation)} · {citation.evidence_id}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </article>
                )}
              </div>
            )}
          </div>

          <form onSubmit={submit} className="border-t border-[#1d3146] bg-[#091522]/92 p-4 sm:p-5">
            {contextAds.length > 0 && (
              <div className="mb-2 flex gap-2">
                {contextAds.map((ad) => (
                  <button key={ad} type="button" onClick={() => setContextAds((items) => items.filter((x) => x !== ad))} className="rounded-full bg-[#17314a] px-3 py-1 text-xs text-[#b6d2eb]">
                    {ad} ×
                  </button>
                ))}
              </div>
            )}
            <div className="flex items-end gap-3 rounded-2xl border border-[#2a435b] bg-[#0e1d2c] p-2 shadow-inner focus-within:border-[#4d7ca6]">
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void submit();
                  }
                }}
                placeholder={ready ? "Ask about an EASA Airworthiness Directive…" : "Loading corpus and Qwen models…"}
                rows={2}
                disabled={!ready}
                className="min-h-14 flex-1 resize-none bg-transparent px-3 py-2 text-sm leading-6 text-white outline-none placeholder:text-[#61778b] disabled:cursor-wait"
              />
              {busy ? (
                <button type="button" onClick={stop} className="grid size-10 place-items-center rounded-xl bg-[#37242a] text-[#ff948e] transition hover:bg-[#492a30]" title="Stop request">
                  <CircleStop className="size-5" />
                </button>
              ) : (
                <button type="submit" disabled={!ready || !question.trim()} className="grid size-10 place-items-center rounded-xl bg-[#2f81f7] text-white transition hover:bg-[#4a91f8] disabled:opacity-35">
                  <ArrowUp className="size-5" />
                </button>
              )}
            </div>
            <p className="mt-2 text-center text-[11px] text-[#61778b]">
              Engineering decision support only. Controlling EASA AD and approved maintenance data remain authoritative.
            </p>
          </form>
        </section>

        <aside className="min-h-[calc(100vh-130px)] overflow-hidden rounded-2xl border border-[#23384f] bg-[#0b1928]/88 shadow-2xl shadow-black/20">
          <div className="flex items-center justify-between border-b border-[#1d3146] px-5 py-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <BookOpenText className="size-4 text-[#70b7ff]" /> Evidence inspector
            </div>
            <span className="text-xs text-[#71879c]">{evidence.length ? `${evidence.length} passages` : "No evidence"}</span>
          </div>

          {evidence.length ? (
            <div className="grid h-[calc(100vh-188px)] grid-rows-[auto_1fr]">
              <div className="flex gap-2 overflow-x-auto border-b border-[#1d3146] p-3">
                {evidence.map((item) => (
                  <button
                    key={item.evidence_id}
                    onClick={() => setSelectedEvidence(item.evidence_id)}
                    className={`shrink-0 rounded-lg border px-3 py-2 text-left text-xs transition ${selected?.evidence_id === item.evidence_id ? "border-[#58a6ff] bg-[#173554] text-white" : "border-[#263e56] bg-[#0e1d2c] text-[#91a6ba] hover:border-[#3c617f]"}`}
                  >
                    <span className="block font-semibold">{item.evidence_id}</span>
                    <span>{item.ad_number} · p.{pages(item)}</span>
                  </button>
                ))}
              </div>
              {selected && (
                <div className="overflow-y-auto p-5">
                  <div className="mb-5 grid grid-cols-2 gap-2 text-xs">
                    <Metric icon={<FileSearch className="size-3.5" />} label="AD" value={selected.ad_number} />
                    <Metric icon={<BookOpenText className="size-3.5" />} label="Page" value={pages(selected)} />
                    <Metric icon={<Radar className="size-3.5" />} label="Section" value={selected.section} />
                    <Metric icon={<Gauge className="size-3.5" />} label="E5-D rank" value={`#${selected.rank}`} />
                  </div>
                  <div className="mb-2 text-[11px] font-semibold uppercase tracking-[.14em] text-[#6f879b]">Retrieved source passage</div>
                  <div className="whitespace-pre-wrap rounded-xl border border-[#223b52] bg-[#081522] p-4 text-[13px] leading-6 text-[#c3d1de] shadow-inner">
                    {selected.text}
                  </div>
                  <div className="mt-4 text-[11px] leading-5 text-[#687e91]">Source: {selected.source_pdf}</div>
                  {!contextAds.includes(selected.ad_number) && (
                    <button onClick={() => setContextAds((items) => [...items, selected.ad_number])} className="mt-4 rounded-lg border border-[#315271] bg-[#10263a] px-3 py-2 text-xs text-[#b8d7f4] hover:border-[#58a6ff]">
                      Use {selected.ad_number} as follow-up context
                    </button>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="grid h-[calc(100vh-188px)] place-items-center p-8 text-center">
              <div>
                <BookOpenText className="mx-auto mb-3 size-7 text-[#49647d]" />
                <p className="text-sm font-medium text-[#9aafc1]">Source evidence will appear here first.</p>
                <p className="mt-2 text-xs leading-5 text-[#667d91]">You can inspect top-ranked AD passages while Layer C finishes generating the validated answer.</p>
              </div>
            </div>
          )}
        </aside>
      </div>
    </main>
  );
}

function Pipeline({ stage }: { stage: PipelineStage }) {
  if (stage === "idle" || stage === "complete") return null;
  return (
    <div className="rounded-xl border border-[#243e56] bg-[#0b1d2d] px-4 py-3">
      <div className="flex items-center gap-2 text-xs text-[#8fa6b9]">
        <LoaderCircle className="size-3.5 animate-spin text-[#58a6ff]" /> Processing query
      </div>
      <div className="mt-3 grid grid-cols-4 gap-2">
        {STAGES.map(([key, label], index) => {
          const active = rank(stage) >= index;
          return (
            <div key={key}>
              <div className={`h-1 rounded-full ${active ? "bg-[#58a6ff]" : "bg-[#21364a]"}`} />
              <div className={`mt-1.5 text-[10px] ${active ? "text-[#a9d3fb]" : "text-[#5f7588]"}`}>{label}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Status({ status }: { status: AssistantResult["status"] }) {
  const styles = status === "answered" ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" : status === "technical_error" ? "border-red-500/30 bg-red-500/10 text-red-300" : "border-amber-500/30 bg-amber-500/10 text-amber-200";
  return <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${styles}`}>{status.replaceAll("_", " ")}</span>;
}

function Structured({ title, values }: { title: string; values: string[] }) {
  if (!values?.length) return null;
  return (
    <div className="mt-5">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-[.14em] text-[#8298ac]">{title}</h3>
      <ul className="space-y-2 text-sm leading-6 text-[#c8d5e1]">
        {values.map((value, index) => <li key={index} className="rounded-lg bg-[#0a1927] px-3 py-2">{value}</li>)}
      </ul>
    </div>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[#223b52] bg-[#0d1e2d] p-3">
      <div className="mb-1 flex items-center gap-1.5 text-[#698298]">{icon}{label}</div>
      <div className="truncate font-medium text-[#c5d5e3]" title={value}>{value}</div>
    </div>
  );
}
