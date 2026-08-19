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
  X,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Toaster, toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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

type Turn = { id: string; question: string; result: AssistantResult };

function pageRange(item: { page_start: number; page_end: number }) {
  return item.page_start === item.page_end ? `${item.page_start}` : `${item.page_start}–${item.page_end}`;
}

function stageRank(stage: PipelineStage) {
  return { idle: -1, routing: 0, retrieving: 1, evidence: 2, generating: 3, complete: 4, error: -1 }[stage];
}

export function ConversationShell() {
  const [composer, setComposer] = useState("");
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [stage, setStage] = useState<PipelineStage>("idle");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [pendingEvidence, setPendingEvidence] = useState<Evidence[]>([]);
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);
  const [retrievalOnly, setRetrievalOnly] = useState(false);
  const [health, setHealth] = useState<Awaited<ReturnType<typeof getHealth>> | null>(null);
  const [contextAds, setContextAds] = useState<string[]>([]);
  const controller = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      try {
        const next = await getHealth();
        if (mounted) setHealth(next);
      } catch {
        if (mounted) setHealth(null);
      }
    };
    void poll();
    const timer = window.setInterval(poll, 2500);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns, pendingQuestion, stage]);

  const ready = health?.status === "ready";
  const busy = !!pendingQuestion && stage !== "idle" && stage !== "error";
  const latestEvidence = useMemo(() => {
    if (pendingEvidence.length) return pendingEvidence;
    return turns.at(-1)?.result.evidence ?? [];
  }, [pendingEvidence, turns]);
  const inspectorEvidence = selectedEvidence ?? latestEvidence[0] ?? null;

  async function submit(event?: FormEvent, override?: string) {
    event?.preventDefault();
    const question = (override ?? composer).trim();
    if (!question || !ready || busy) return;

    setComposer("");
    setPendingQuestion(question);
    setPendingEvidence([]);
    setSelectedEvidence(null);
    setStage("routing");
    controller.current = new AbortController();

    try {
      await streamQuestion(question, {
        retrievalOnly,
        contextAdNumbers: contextAds,
        signal: controller.current.signal,
        onStage: setStage,
        onEvidence: (items) => {
          setPendingEvidence(items);
          setSelectedEvidence(items[0] ?? null);
        },
        onAnswer: (result) => {
          const turn: Turn = {
            id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
            question,
            result,
          };
          setTurns((current) => [...current, turn]);
          setPendingEvidence([]);
          setSelectedEvidence(result.evidence[0] ?? null);
          setPendingQuestion(null);
          setStage("idle");
          if (result.status === "technical_error") {
            toast.warning("Hosted QA failed; source evidence remains available.");
          }
        },
      });
    } catch (error) {
      if ((error as Error).name === "AbortError") {
        setPendingQuestion(null);
        setPendingEvidence([]);
        setStage("idle");
        return;
      }
      setStage("error");
      toast.error((error as Error).message);
    }
  }

  function stop() {
    controller.current?.abort();
  }

  return (
    <main className="mx-auto min-h-screen max-w-[1540px] px-4 py-5 lg:px-8">
      <Toaster theme="dark" position="top-right" richColors />
      <Header health={health} />

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_430px]">
        <section className="flex min-h-[calc(100vh-130px)] flex-col overflow-hidden rounded-2xl border border-[#23384f] bg-[#0b1928]/90 shadow-2xl shadow-black/20 backdrop-blur">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#1d3146] px-5 py-3.5">
            <div className="flex items-center gap-2 text-xs text-[#9bb0c4]">
              <ShieldCheck className="size-4 text-emerald-400" />
              Frozen retrieval methodology · modern post-evaluation serving
            </div>
            <label className="flex items-center gap-2 text-xs text-[#8298ac]">
              <input
                type="checkbox"
                checked={retrievalOnly}
                onChange={(event) => setRetrievalOnly(event.target.checked)}
                className="accent-[#58a6ff]"
              />
              Retrieval only
            </label>
          </div>

          <div className="flex-1 overflow-y-auto px-5 py-6 sm:px-8">
            {turns.length === 0 && !pendingQuestion ? (
              <Welcome ready={ready} onAsk={(text) => void submit(undefined, text)} />
            ) : (
              <div className="mx-auto max-w-3xl space-y-8">
                {turns.map((turn) => (
                  <TurnView key={turn.id} turn={turn} onEvidence={setSelectedEvidence} />
                ))}

                {pendingQuestion && (
                  <div className="space-y-4">
                    <UserBubble>{pendingQuestion}</UserBubble>
                    <Pipeline stage={stage} evidenceCount={pendingEvidence.length} />
                  </div>
                )}
                {stage === "error" && pendingQuestion && (
                  <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
                    The request failed before a validated answer was returned. You can retry the question.
                  </div>
                )}
                <div ref={bottomRef} />
              </div>
            )}
          </div>

          <Composer
            value={composer}
            setValue={setComposer}
            ready={ready}
            busy={busy}
            contextAds={contextAds}
            setContextAds={setContextAds}
            onSubmit={submit}
            onStop={stop}
          />
        </section>

        <EvidenceInspector
          evidence={latestEvidence}
          selected={inspectorEvidence}
          onSelect={setSelectedEvidence}
          contextAds={contextAds}
          addContext={(ad) => setContextAds((current) => (current.includes(ad) ? current : [...current, ad]))}
        />
      </div>
    </main>
  );
}

function Header({ health }: { health: Awaited<ReturnType<typeof getHealth>> | null }) {
  const ready = health?.status === "ready";
  return (
    <header className="mb-5 flex items-center justify-between rounded-2xl border border-[#23384f] bg-[#0b1928]/92 px-5 py-4 shadow-2xl shadow-black/20 backdrop-blur">
      <div className="flex items-center gap-3">
        <div className="grid size-10 place-items-center rounded-xl border border-[#31506e] bg-[#10253a] text-[#70b7ff]">
          <Plane className="size-5" />
        </div>
        <div>
          <h1 className="text-base font-semibold tracking-tight text-white sm:text-lg">Airbus EASA AD Assistant</h1>
          <p className="text-xs text-[#8fa5ba]">Engineering document intelligence · evidence first</p>
        </div>
      </div>
      <div className="flex items-center gap-2 rounded-full border border-[#23384f] bg-[#091522] px-3 py-1.5 text-xs text-[#9bb0c4]">
        <span className={`size-2 rounded-full ${ready ? "bg-emerald-400" : "animate-pulse bg-amber-400"}`} />
        {ready ? `${health.document_count.toLocaleString()} docs · ${health.device.toUpperCase()}` : "Warming Qwen models"}
      </div>
    </header>
  );
}

function Welcome({ ready, onAsk }: { ready: boolean; onAsk: (text: string) => void }) {
  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col justify-center py-10">
      <div className="mb-8 text-center">
        <div className="mx-auto mb-4 grid size-14 place-items-center rounded-2xl border border-[#2b4966] bg-[#10263b] text-[#70b7ff]">
          <Radar className="size-7" />
        </div>
        <h2 className="text-2xl font-semibold tracking-tight text-white">Ask the Airworthiness Directive corpus</h2>
        <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-[#91a6ba]">
          Retrieve exact source passages and answer questions about applicability, compliance actions, lifecycle, references, and corpus-wide discovery.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {EXAMPLES.map(([label, text]) => (
          <button
            key={label}
            onClick={() => onAsk(text)}
            disabled={!ready}
            className="group rounded-xl border border-[#23384f] bg-[#0e1e2e] p-4 text-left transition hover:-translate-y-0.5 hover:border-[#3b6287] hover:bg-[#11253a] disabled:opacity-45"
          >
            <span className="mb-2 block text-xs font-semibold uppercase tracking-[.14em] text-[#58a6ff]">{label}</span>
            <span className="text-sm leading-5 text-[#c6d4e1] group-hover:text-white">{text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function TurnView({ turn, onEvidence }: { turn: Turn; onEvidence: (item: Evidence) => void }) {
  const result = turn.result;
  return (
    <div className="space-y-4">
      <UserBubble>{turn.question}</UserBubble>
      <article className="rounded-2xl border border-[#29445f] bg-[#0e2031] p-5 shadow-xl">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <Status status={result.status} />
          <span className="text-xs text-[#8499ad]">
            {String(result.route?.mode ?? "route")} · {(Number(result.timings.total_ms ?? 0) / 1000).toFixed(1)}s
          </span>
        </div>

        {result.answer ? (
          <div className="max-w-none text-[15px] leading-7 text-[#d8e3ed]">
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
            <div className="mb-2 text-[11px] font-semibold uppercase tracking-[.14em] text-[#8298ac]">Source citations</div>
            <div className="flex flex-wrap gap-2">
              {result.citations.map((citation) => {
                const source = result.evidence.find((item) => item.evidence_id === citation.evidence_id);
                return (
                  <Button
                    key={`${citation.evidence_id}-${citation.chunk_id ?? "citation"}`}
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => source && onEvidence(source)}
                  >
                    {citation.ad_number} · p.{pageRange(citation)} · {citation.evidence_id}
                  </Button>
                );
              })}
            </div>
          </div>
        )}
      </article>
    </div>
  );
}

function UserBubble({ children }: { children: React.ReactNode }) {
  return <div className="ml-auto max-w-[86%] rounded-2xl rounded-br-md bg-[#1b4f7f] px-4 py-3 text-sm leading-6 text-white shadow-lg">{children}</div>;
}

function Pipeline({ stage, evidenceCount }: { stage: PipelineStage; evidenceCount: number }) {
  if (stage === "idle" || stage === "complete") return null;
  return (
    <div className="rounded-xl border border-[#243e56] bg-[#0b1d2d] px-4 py-3">
      <div className="flex items-center justify-between gap-3 text-xs text-[#8fa6b9]">
        <span className="flex items-center gap-2"><LoaderCircle className="size-3.5 animate-spin text-[#58a6ff]" />Working through the evidence pipeline</span>
        {evidenceCount > 0 && <span>{evidenceCount} passages ready</span>}
      </div>
      <div className="mt-3 grid grid-cols-4 gap-2">
        {STAGES.map(([key, label], index) => {
          const active = stageRank(stage) >= index;
          return (
            <div key={key}>
              <div className={`h-1 rounded-full transition ${active ? "bg-[#58a6ff]" : "bg-[#21364a]"}`} />
              <div className={`mt-1.5 text-[10px] ${active ? "text-[#a9d3fb]" : "text-[#5f7588]"}`}>{label}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Composer({
  value,
  setValue,
  ready,
  busy,
  contextAds,
  setContextAds,
  onSubmit,
  onStop,
}: {
  value: string;
  setValue: (value: string) => void;
  ready: boolean;
  busy: boolean;
  contextAds: string[];
  setContextAds: React.Dispatch<React.SetStateAction<string[]>>;
  onSubmit: (event?: FormEvent) => Promise<void>;
  onStop: () => void;
}) {
  return (
    <form onSubmit={onSubmit} className="border-t border-[#1d3146] bg-[#091522]/94 p-4 sm:p-5">
      {contextAds.length > 0 && (
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <span className="text-[11px] uppercase tracking-[.12em] text-[#657d91]">Follow-up context</span>
          {contextAds.map((ad) => (
            <Badge key={ad}>
              {ad}
              <button type="button" className="ml-1" onClick={() => setContextAds((items) => items.filter((item) => item !== ad))} aria-label={`Remove ${ad} context`}>
                <X className="size-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
      <div className="flex items-end gap-3 rounded-2xl border border-[#2a435b] bg-[#0e1d2c] p-2 shadow-inner focus-within:border-[#4d7ca6]">
        <textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void onSubmit();
            }
          }}
          placeholder={ready ? "Ask about an EASA Airworthiness Directive…" : "Loading corpus and Qwen models…"}
          rows={2}
          disabled={!ready || busy}
          className="min-h-14 flex-1 resize-none bg-transparent px-3 py-2 text-sm leading-6 text-white outline-none placeholder:text-[#61778b] disabled:cursor-wait"
        />
        {busy ? (
          <Button type="button" variant="destructive" size="icon" onClick={onStop} title="Stop request"><CircleStop className="size-5" /></Button>
        ) : (
          <Button type="submit" size="icon" disabled={!ready || !value.trim()}><ArrowUp className="size-5" /></Button>
        )}
      </div>
      <p className="mt-2 text-center text-[11px] text-[#61778b]">Decision support only. The controlling EASA AD and approved maintenance data remain authoritative.</p>
    </form>
  );
}

function EvidenceInspector({
  evidence,
  selected,
  onSelect,
  contextAds,
  addContext,
}: {
  evidence: Evidence[];
  selected: Evidence | null;
  onSelect: (item: Evidence) => void;
  contextAds: string[];
  addContext: (ad: string) => void;
}) {
  return (
    <aside className="min-h-[calc(100vh-130px)] overflow-hidden rounded-2xl border border-[#23384f] bg-[#0b1928]/90 shadow-2xl shadow-black/20 backdrop-blur">
      <div className="flex items-center justify-between border-b border-[#1d3146] px-5 py-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-white"><BookOpenText className="size-4 text-[#70b7ff]" />Evidence inspector</div>
        <span className="text-xs text-[#71879c]">{evidence.length ? `${evidence.length} passages` : "No evidence"}</span>
      </div>

      {evidence.length ? (
        <div className="grid h-[calc(100vh-188px)] grid-rows-[auto_1fr]">
          <div className="flex gap-2 overflow-x-auto border-b border-[#1d3146] p-3">
            {evidence.map((item) => (
              <button
                key={item.evidence_id}
                onClick={() => onSelect(item)}
                className={`shrink-0 rounded-lg border px-3 py-2 text-left text-xs transition ${selected?.chunk_id === item.chunk_id ? "border-[#58a6ff] bg-[#173554] text-white" : "border-[#263e56] bg-[#0e1d2c] text-[#91a6ba] hover:border-[#3c617f]"}`}
              >
                <span className="block font-semibold">{item.evidence_id}</span>
                <span>{item.ad_number} · p.{pageRange(item)}</span>
              </button>
            ))}
          </div>
          {selected && (
            <div className="overflow-y-auto p-5">
              <div className="mb-5 grid grid-cols-2 gap-2 text-xs">
                <Metric icon={<FileSearch className="size-3.5" />} label="AD" value={selected.ad_number} />
                <Metric icon={<BookOpenText className="size-3.5" />} label="Page" value={pageRange(selected)} />
                <Metric icon={<Radar className="size-3.5" />} label="Section" value={selected.section} />
                <Metric icon={<Gauge className="size-3.5" />} label="E5-D rank" value={`#${selected.rank}`} />
              </div>
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-[.14em] text-[#6f879b]">Retrieved source passage</div>
              <div className="whitespace-pre-wrap rounded-xl border border-[#223b52] bg-[#081522] p-4 text-[13px] leading-6 text-[#c3d1de] shadow-inner">{selected.text}</div>
              <div className="mt-4 break-all text-[11px] leading-5 text-[#687e91]">Source: {selected.source_pdf}</div>
              {!contextAds.includes(selected.ad_number) && (
                <Button type="button" variant="secondary" size="sm" className="mt-4" onClick={() => addContext(selected.ad_number)}>
                  Use {selected.ad_number} for follow-up
                </Button>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="grid h-[calc(100vh-188px)] place-items-center p-8 text-center">
          <div>
            <BookOpenText className="mx-auto mb-3 size-7 text-[#49647d]" />
            <p className="text-sm font-medium text-[#9aafc1]">Source evidence appears here first.</p>
            <p className="mt-2 text-xs leading-5 text-[#667d91]">Inspect E5-D passages while the hosted answer is still being validated.</p>
          </div>
        </div>
      )}
    </aside>
  );
}

function Status({ status }: { status: AssistantResult["status"] }) {
  const variant = status === "answered" ? "success" : status === "technical_error" ? "danger" : "warning";
  return <Badge variant={variant}>{status.replaceAll("_", " ")}</Badge>;
}

function Structured({ title, values }: { title: string; values: string[] }) {
  if (!values.length) return null;
  return (
    <div className="mt-5">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-[.14em] text-[#8298ac]">{title}</h3>
      <ul className="space-y-2 text-sm leading-6 text-[#c8d5e1]">
        {values.map((value, index) => <li key={`${title}-${index}`} className="rounded-lg bg-[#0a1927] px-3 py-2">{value}</li>)}
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
