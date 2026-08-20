"use client";

import { FormEvent, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import {
  ArrowUp,
  BookOpenText,
  Check,
  CircleStop,
  Code,
  Copy,
  Eye,
  FileSearch,
  FileText,
  Gauge,
  LoaderCircle,
  Plane,
  Plus,
  Radar,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Type,
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
  cancelQuestion,
  getHealth,
  streamQuestion,
} from "@/lib/assistant";

const EXAMPLES = [
  { index: "01", label: "Applicability", text: "Which A310 models are affected by EASA AD 2008-0008?" },
  { index: "02", label: "Compliance", text: "For EASA AD 2011-0041R1, what actions had to be completed within 3 days after 14 March 2011?" },
  { index: "03", label: "Discovery", text: "Which Airbus directive requires reporting inspection results including no findings within 30 days after each inspection?" },
  { index: "04", label: "Lifecycle", text: "Which earlier directive does EASA AD 2011-0041R1 revise?" },
] as const;

const STAGES: Array<[PipelineStage, string, string]> = [
  ["routing", "Route", "Identify scope"],
  ["retrieving", "Retrieve", "Search corpus"],
  ["evidence", "Evidence", "Verify passages"],
  ["generating", "Answer", "Compose brief"],
];

type Turn = { id: string; question: string; result: AssistantResult };

const DEFAULT_EVIDENCE_WIDTH = 420;
const MIN_EVIDENCE_WIDTH = 280;
const MIN_CONVERSATION_WIDTH = 380;
const SPLITTER_WIDTH = 10;
const STORAGE_KEY = "easa_ad_evidence_width";

const widthListeners = new Set<() => void>();
let memoryWidth: number | null = null;

function emitWidthChange() {
  widthListeners.forEach((listener) => listener());
}

export const evidenceWidthStore = {
  subscribe(listener: () => void) {
    widthListeners.add(listener);
    return () => {
      widthListeners.delete(listener);
    };
  },
  getSnapshot(): number {
    if (memoryWidth !== null) return memoryWidth;
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
          const parsed = parseFloat(saved);
          if (!Number.isNaN(parsed) && parsed >= MIN_EVIDENCE_WIDTH) {
            memoryWidth = parsed;
            return memoryWidth;
          }
        }
      } catch {
        // ignore
      }
    }
    return DEFAULT_EVIDENCE_WIDTH;
  },
  getServerSnapshot(): number {
    return DEFAULT_EVIDENCE_WIDTH;
  },
  setWidth(width: number) {
    memoryWidth = width;
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem(STORAGE_KEY, String(width));
      } catch {
        // ignore
      }
    }
    emitWidthChange();
  },
  resetForTesting() {
    memoryWidth = null;
  },
};

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
  const evidenceWidth = useSyncExternalStore(
    evidenceWidthStore.subscribe,
    evidenceWidthStore.getSnapshot,
    evidenceWidthStore.getServerSnapshot,
  );
  const setEvidenceWidth = evidenceWidthStore.setWidth;
  const [isResizing, setIsResizing] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const isResizingRef = useRef(false);
  const activeRequest = useRef<{ controller: AbortController; requestId: string } | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

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
    if (!pendingQuestion && turns.length === 0) return;
    const container = scrollRef.current;
    container?.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
  }, [turns, pendingQuestion, stage]);

  const ready = health?.status === "ready";
  const busy = !!pendingQuestion && stage !== "idle" && stage !== "error";
  const latestEvidence = useMemo(() => {
    if (pendingEvidence.length) return pendingEvidence;
    return turns.at(-1)?.result.evidence ?? [];
  }, [pendingEvidence, turns]);
  const inspectorEvidence = selectedEvidence ?? latestEvidence[0] ?? null;

  const clampEvidenceWidth = (rawWidth: number, containerWidth?: number): number => {
    const currentContainerWidth = containerWidth || containerRef.current?.getBoundingClientRect().width || 1200;
    const maxAvailable = Math.max(MIN_EVIDENCE_WIDTH, currentContainerWidth - MIN_CONVERSATION_WIDTH - SPLITTER_WIDTH);
    return Math.min(Math.max(Math.round(rawWidth), MIN_EVIDENCE_WIDTH), maxAvailable);
  };

  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    event.preventDefault();
    if (typeof event.currentTarget.setPointerCapture === "function") {
      event.currentTarget.setPointerCapture(event.pointerId);
    }
    isResizingRef.current = true;
    setIsResizing(true);
  };

  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!isResizingRef.current || !containerRef.current) return;
    const containerRect = containerRef.current.getBoundingClientRect();
    const rawWidth = containerRect.right - event.clientX;
    const clamped = clampEvidenceWidth(rawWidth, containerRect.width);
    setEvidenceWidth(clamped);
  };

  const handlePointerUp = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!isResizingRef.current) return;
    isResizingRef.current = false;
    setIsResizing(false);
    try {
      if (typeof event.currentTarget.releasePointerCapture === "function") {
        event.currentTarget.releasePointerCapture(event.pointerId);
      }
    } catch {
      // ignore
    }
    try {
      localStorage.setItem(STORAGE_KEY, String(evidenceWidth));
    } catch {
      // ignore
    }
  };

  const resetEvidenceWidth = () => {
    setEvidenceWidth(DEFAULT_EVIDENCE_WIDTH);
    try {
      localStorage.setItem(STORAGE_KEY, String(DEFAULT_EVIDENCE_WIDTH));
    } catch {
      // ignore
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    const STEP = 24;
    let newWidth: number | null = null;
    const containerWidth = containerRef.current?.getBoundingClientRect().width || 1200;
    const maxAvailable = Math.max(MIN_EVIDENCE_WIDTH, containerWidth - MIN_CONVERSATION_WIDTH - SPLITTER_WIDTH);

    switch (event.key) {
      case "ArrowLeft":
      case "ArrowUp":
        newWidth = clampEvidenceWidth(evidenceWidth + STEP, containerWidth);
        break;
      case "ArrowRight":
      case "ArrowDown":
        newWidth = clampEvidenceWidth(evidenceWidth - STEP, containerWidth);
        break;
      case "Home":
        newWidth = MIN_EVIDENCE_WIDTH;
        break;
      case "End":
        newWidth = maxAvailable;
        break;
      case "Enter":
      case " ":
        newWidth = DEFAULT_EVIDENCE_WIDTH;
        break;
    }

    if (newWidth !== null) {
      event.preventDefault();
      setEvidenceWidth(newWidth);
      try {
        localStorage.setItem(STORAGE_KEY, String(newWidth));
      } catch {
        // ignore
      }
    }
  };

  async function submit(event?: FormEvent, override?: string) {
    event?.preventDefault();
    const question = (override ?? composer).trim();
    if (!question || !ready || busy) return;

    setComposer("");
    setPendingQuestion(question);
    setPendingEvidence([]);
    setSelectedEvidence(null);
    setStage("routing");
    const requestController = new AbortController();
    const requestId = crypto.randomUUID();
    activeRequest.current = { controller: requestController, requestId };

    try {
      await streamQuestion(question, {
        requestId,
        retrievalOnly,
        contextAdNumbers: contextAds,
        signal: requestController.signal,
        onStage: (nextStage) => {
          if (!requestController.signal.aborted) setStage(nextStage);
        },
        onEvidence: (items) => {
          if (requestController.signal.aborted) return;
          setPendingEvidence(items);
          setSelectedEvidence(items[0] ?? null);
        },
        onAnswer: (result) => {
          if (requestController.signal.aborted) return;
          const turn: Turn = { id: `${Date.now()}-${Math.random().toString(16).slice(2)}`, question, result };
          setTurns((current) => [...current, turn]);
          setPendingEvidence([]);
          setSelectedEvidence(result.evidence[0] ?? null);
          setPendingQuestion(null);
          setStage("idle");
          if (result.status === "technical_error") toast.warning("Hosted QA failed; source evidence remains available.");
        },
      });
    } catch (error) {
      if ((error as Error).name === "AbortError") {
        setComposer((current) => current || question);
        setPendingQuestion(null);
        setPendingEvidence([]);
        setStage("idle");
        return;
      }
      setComposer(question);
      setPendingQuestion(null);
      setStage("error");
      toast.error((error as Error).message);
    } finally {
      if (activeRequest.current?.controller === requestController) activeRequest.current = null;
    }
  }

  function stopRequest() {
    if (!pendingQuestion) return;
    const stoppedQuestion = pendingQuestion;
    const request = activeRequest.current;
    activeRequest.current = null;
    if (request) {
      void cancelQuestion(request.requestId).catch((error: Error) => {
        toast.error(`${error.message}. The browser stream was still closed.`);
      });
      request.controller.abort();
    }
    setComposer((current) => current || stoppedQuestion);
    setPendingQuestion(null);
    setPendingEvidence([]);
    setStage("idle");
    toast.info("Request stopped. Your question is ready to edit or send again.");
  }

  function resetWorkspace() {
    setTurns([]);
    setComposer("");
    setPendingQuestion(null);
    setPendingEvidence([]);
    setSelectedEvidence(null);
    setContextAds([]);
    setStage("idle");
  }

  return (
    <main className="app-frame">
      <Toaster theme="dark" position="top-right" richColors />
      <Header health={health} />

      <div
        ref={containerRef}
        suppressHydrationWarning
        className={`workspace-grid ${isResizing ? "is-resizing" : ""}`}
        style={{ "--evidence-width": `${evidenceWidth}px` } as React.CSSProperties}
      >
        <section className="conversation-panel" aria-label="Assistant workspace">
          <div className="workspace-toolbar">
            <div className="method-lock">
              <ShieldCheck aria-hidden="true" />
              <span><strong>Method locked</strong> E5-D retrieval · Layer C response</span>
            </div>
            <div className="toolbar-actions">
              {turns.length > 0 && (
                <button type="button" className="quiet-action" onClick={resetWorkspace}>
                  <RotateCcw aria-hidden="true" /> New inquiry
                </button>
              )}
              <label className="mode-switch">
                <span>Evidence only</span>
                <input type="checkbox" checked={retrievalOnly} onChange={(event) => setRetrievalOnly(event.target.checked)} />
                <span className="switch-track" aria-hidden="true"><span /></span>
              </label>
            </div>
          </div>

          <div ref={scrollRef} className="conversation-scroll" aria-live="polite">
            {turns.length === 0 && !pendingQuestion ? (
              <Welcome ready={ready} documentCount={health?.document_count} onAsk={(text) => void submit(undefined, text)} />
            ) : (
              <div className="turn-stack">
                {turns.map((turn, index) => (
                  <TurnView key={turn.id} turn={turn} turnNumber={index + 1} onEvidence={setSelectedEvidence} />
                ))}

                {pendingQuestion && (
                  <div className="turn-block">
                    <UserQuery question={pendingQuestion} />
                    <Pipeline stage={stage} evidenceCount={pendingEvidence.length} />
                  </div>
                )}
                {stage === "error" && (
                  <div className="request-error" role="alert">
                    The request stopped before a validated answer was returned. Your question is back in the inquiry field.
                  </div>
                )}
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
            onStop={stopRequest}
          />
        </section>

        <div
          role="separator"
          aria-orientation="vertical"
          aria-valuenow={Math.round(evidenceWidth)}
          aria-valuemin={MIN_EVIDENCE_WIDTH}
          aria-valuemax={1200}
          aria-label="Resize evidence inspector"
          tabIndex={0}
          className={`workspace-splitter ${isResizing ? "is-resizing" : ""}`}
          title="Drag to resize evidence inspector · Double-click to reset (420px) · Left/Right arrows to adjust"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          onDoubleClick={resetEvidenceWidth}
          onKeyDown={handleKeyDown}
        />

        <EvidenceInspector
          evidence={latestEvidence}
          selected={inspectorEvidence}
          onSelect={setSelectedEvidence}
          contextAds={contextAds}
          addContext={(ad) => setContextAds((current) => (current.includes(ad) ? current : [...current, ad]))}
          evidenceWidth={evidenceWidth}
          onResetWidth={resetEvidenceWidth}
        />
      </div>
    </main>
  );
}

function Header({ health }: { health: Awaited<ReturnType<typeof getHealth>> | null }) {
  const ready = health?.status === "ready";
  return (
    <header className="masthead">
      <div className="brand-lockup">
        <div className="brand-mark" aria-hidden="true"><Plane /><span>AD</span></div>
        <div>
          <p className="eyebrow">Regulatory intelligence workspace</p>
          <h1>Airbus EASA AD Assistant</h1>
        </div>
      </div>

      <div className="system-cluster">
        <div className="system-note"><span>Source-grounded</span><span>Post-evaluation serving</span></div>
        <div className={`health-card ${ready ? "is-ready" : "is-warming"}`}>
          <span className="health-light" />
          <div>
            <strong>{ready ? "Corpus online" : "Models warming"}</strong>
            <span>{ready ? `${health.document_count.toLocaleString()} documents · ${health.device.toUpperCase()}` : "Preparing Qwen retrieval"}</span>
          </div>
        </div>
      </div>
    </header>
  );
}

function Welcome({ ready, documentCount, onAsk }: { ready: boolean; documentCount?: number; onAsk: (text: string) => void }) {
  return (
    <div className="welcome-state">
      <div className="welcome-copy">
        <div className="welcome-kicker"><Radar aria-hidden="true" /> Evidence before inference</div>
        <h2>Ask with precision.<br /><em>Verify at the source.</em></h2>
        <p>
          Interrogate the Airbus Airworthiness Directive corpus for applicability, compliance actions,
          lifecycle history, reference publications, and cross-document discovery.
        </p>
        <div className="capability-row" aria-label="Assistant capabilities">
          <span><Check aria-hidden="true" /> {documentCount ? documentCount.toLocaleString() : "Validated"} documents</span>
          <span><Check aria-hidden="true" /> Top-5 evidence</span>
          <span><Check aria-hidden="true" /> Page provenance</span>
        </div>
      </div>

      <div className="example-deck">
        <div className="example-heading"><span>Start from a flight-line question</span><span>04 prompts</span></div>
        <div className="example-grid">
          {EXAMPLES.map((example) => (
            <button key={example.index} type="button" onClick={() => onAsk(example.text)} disabled={!ready} className="example-card">
              <span className="example-index">{example.index}</span>
              <span className="example-content">
                <span className="example-label">{example.label}</span>
                <span className="example-text">{example.text}</span>
              </span>
              <ArrowUp className="example-arrow" aria-hidden="true" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function TurnView({ turn, turnNumber, onEvidence }: { turn: Turn; turnNumber: number; onEvidence: (item: Evidence) => void }) {
  const result = turn.result;
  const totalSeconds = Number(result.timings.total_ms ?? 0) / 1000;
  return (
    <div className="turn-block">
      <UserQuery question={turn.question} />
      <article className="answer-brief">
        <div className="brief-body">
          <header className="brief-header">
            <div>
              <p className="brief-kicker"><span>Brief {String(turnNumber).padStart(2, "0")}</span><Sparkles aria-hidden="true" /> Evidence-grounded response</p>
              <h2>Response brief</h2>
            </div>
            <div className="brief-meta">
              <Status status={result.status} />
              <span>{String(result.route?.mode ?? "route").replaceAll("_", " ")}</span>
              {totalSeconds > 0 && <span>{totalSeconds.toFixed(1)}s</span>}
            </div>
          </header>

          {result.answer ? (
            <div className="answer-copy"><ReactMarkdown remarkPlugins={[remarkGfm]}>{result.answer}</ReactMarkdown></div>
          ) : result.reason_for_abstention ? (
            <div className="abstention-note">
              <strong>
                {result.status === "retrieval_only"
                  ? "Evidence retrieval complete"
                  : result.status === "technical_error"
                    ? "Answer service unavailable"
                    : "No validated answer returned"}
              </strong>
              <p>{result.reason_for_abstention}</p>
            </div>
          ) : null}

          <div className="structured-grid">
            <Structured title="Conditions" values={result.conditions} />
            <Structured title="Compliance time" values={result.compliance_time} />
            <Structured title="Exceptions" values={result.exceptions} />
          </div>

          {result.citations.length > 0 && (
            <div className="citation-block">
              <div className="section-label"><span>Sources cited</span><span>{result.citations.length.toString().padStart(2, "0")}</span></div>
              <div className="citation-list">
                {result.citations.map((citation, index) => {
                  const source = result.evidence.find((item) => item.evidence_id === citation.evidence_id);
                  return (
                    <button
                      key={`${citation.evidence_id}-${citation.chunk_id ?? "citation"}`}
                      type="button"
                      className="citation-chip"
                      onClick={() => source && onEvidence(source)}
                      disabled={!source}
                    >
                      <span>{String(index + 1).padStart(2, "0")}</span>
                      <strong>{citation.ad_number}</strong>
                      <small>p.{pageRange(citation)} · {citation.evidence_id}</small>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </article>
    </div>
  );
}

function UserQuery({ question }: { question: string }) {
  return <div className="user-query"><span>Inquiry</span><p>{question}</p></div>;
}

function Pipeline({ stage, evidenceCount }: { stage: PipelineStage; evidenceCount: number }) {
  if (stage === "idle" || stage === "complete") return null;
  return (
    <div className="pipeline-card" role="status">
      <div className="pipeline-heading">
        <span><LoaderCircle className="spin" aria-hidden="true" /> Building an auditable response</span>
        <span>{evidenceCount > 0 ? `${evidenceCount} passages retrieved` : "Working"}</span>
      </div>
      <div className="pipeline-steps">
        {STAGES.map(([key, label, detail], index) => {
          const active = stageRank(stage) >= index;
          const current = stageRank(stage) === index;
          return (
            <div key={key} className={`pipeline-step ${active ? "is-active" : ""} ${current ? "is-current" : ""}`}>
              <span className="step-number">0{index + 1}</span>
              <span><strong>{label}</strong><small>{detail}</small></span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Composer({ value, setValue, ready, busy, contextAds, setContextAds, onSubmit, onStop }: {
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
    <form onSubmit={onSubmit} className="composer-shell">
      {contextAds.length > 0 && (
        <div className="context-row">
          <span>Follow-up scope</span>
          {contextAds.map((ad) => (
            <Badge key={ad}>
              {ad}
              <button type="button" onClick={() => setContextAds((items) => items.filter((item) => item !== ad))} aria-label={`Remove ${ad} context`}>
                <X aria-hidden="true" />
              </button>
            </Badge>
          ))}
        </div>
      )}

      <div className="composer-label"><span>New inquiry</span><span>Enter to send · Shift + Enter for a new line</span></div>
      <div className="composer-field">
        <textarea
          aria-label="Ask the Airbus EASA AD corpus"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void onSubmit();
            }
          }}
          placeholder={ready ? "Ask about an AD, requirement, threshold, or lifecycle relationship…" : "Loading corpus and Qwen models…"}
          rows={2}
          disabled={!ready}
          aria-busy={busy}
        />
        {busy ? (
          <Button type="button" variant="destructive" size="icon" onClick={onStop} title="Stop request" aria-label="Stop request"><CircleStop /></Button>
        ) : (
          <Button type="submit" size="icon" disabled={!ready || !value.trim()} aria-label="Send inquiry"><ArrowUp /></Button>
        )}
      </div>
      <p className="safety-note"><ShieldCheck aria-hidden="true" /> Decision support only. The controlling EASA AD and approved maintenance data remain authoritative.</p>
    </form>
  );
}

function EvidenceInspector({ evidence, selected, onSelect, contextAds, addContext, evidenceWidth, onResetWidth }: {
  evidence: Evidence[];
  selected: Evidence | null;
  onSelect: (item: Evidence) => void;
  contextAds: string[];
  addContext: (ad: string) => void;
  evidenceWidth?: number;
  onResetWidth?: () => void;
}) {
  return (
    <aside className="evidence-panel" aria-label="Evidence inspector">
      <header className="evidence-header">
        <div><p>Source ledger</p><h2><BookOpenText aria-hidden="true" /> Evidence inspector</h2></div>
        <div className="evidence-header-actions">
          {evidenceWidth !== undefined && evidenceWidth !== DEFAULT_EVIDENCE_WIDTH && onResetWidth && (
            <button
              type="button"
              onClick={onResetWidth}
              className="evidence-reset-button"
              title="Reset panel width to default (420px)"
              aria-label="Reset panel width to default"
            >
              Reset width
            </button>
          )}
          <span className="evidence-count">{evidence.length ? `${evidence.length} passages` : "Standing by"}</span>
        </div>
      </header>

      {evidence.length ? (
        <div className="evidence-content">
          <div className="evidence-tabs" aria-label="Retrieved passages">
            {evidence.map((item, index) => (
              <button
                key={item.evidence_id}
                type="button"
                onClick={() => onSelect(item)}
                className={selected?.chunk_id === item.chunk_id ? "is-selected" : ""}
              >
                <span className="tab-rank">{String(index + 1).padStart(2, "0")}</span>
                <span><strong>{item.ad_number}</strong><small>p.{pageRange(item)} · {item.section}</small></span>
              </button>
            ))}
          </div>

          {selected && (
            <div className="evidence-record">
              <div className="record-meta">
                <Metric icon={<FileSearch />} label="Directive" value={selected.ad_number} />
                <Metric icon={<BookOpenText />} label="Page" value={pageRange(selected)} />
                <Metric icon={<Radar />} label="Section" value={selected.section} />
                <Metric icon={<Gauge />} label="E5-D rank" value={`#${selected.rank}`} />
              </div>

              <PassageViewer
                passage={selected.text}
                evidenceId={selected.evidence_id}
                sourcePdf={selected.source_pdf}
                section={selected.section}
              />

              {!contextAds.includes(selected.ad_number) ? (
                <Button type="button" variant="secondary" className="context-button" onClick={() => addContext(selected.ad_number)}>
                  <Plus aria-hidden="true" /> Use {selected.ad_number} for follow-up
                </Button>
              ) : (
                <div className="context-confirmation"><Check aria-hidden="true" /> Added to follow-up scope</div>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="evidence-empty">
          <div className="empty-radar" aria-hidden="true"><span /><Radar /></div>
          <p>Evidence will arrive here first.</p>
          <span>Every response stays traceable to an AD, page, section, and retrieved passage.</span>
          <div className="empty-sequence" aria-hidden="true"><span>Route</span><i /><span>Retrieve</span><i /><span>Verify</span></div>
        </div>
      )}
    </aside>
  );
}

function Status({ status }: { status: AssistantResult["status"] }) {
  const variant = status === "answered" ? "success" : status === "technical_error" ? "danger" : status === "retrieval_only" ? "default" : "warning";
  return <Badge variant={variant}>{status.replaceAll("_", " ")}</Badge>;
}

function Structured({ title, values }: { title: string; values: string[] }) {
  if (!values.length) return null;
  return (
    <section className="structured-section">
      <h3>{title}</h3>
      <ul>{values.map((value, index) => <li key={`${title}-${index}`}>{value}</li>)}</ul>
    </section>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="record-metric"><span>{icon}{label}</span><strong title={value}>{value}</strong></div>;
}

type FontSize = "sm" | "md" | "lg";
type ViewMode = "formatted" | "raw";

type BlockType = "field" | "heading" | "clause" | "note" | "table_header" | "paragraph";

interface ParsedBlock {
  type: BlockType;
  prefix?: string;
  content: string;
  fieldLevel?: "section" | "metadata";
}

const PASSAGE_FIELDS: Array<{ pattern: string; level: "section" | "metadata"; continues?: boolean }> = [
  { pattern: "Required Action\\(s\\)(?: and Compliance Time\\(s\\))?", level: "section" },
  { pattern: "Compliance Time\\(s\\)", level: "section" },
  { pattern: "Applicability", level: "section" },
  { pattern: "Reason(?:\\(s\\))?(?: for Revision)?", level: "section" },
  { pattern: "Definitions", level: "section" },
  { pattern: "Effective Date", level: "section" },
  { pattern: "Ref\\. Publications", level: "section" },
  { pattern: "Remarks", level: "section" },
  { pattern: "Correction", level: "section" },
  { pattern: "Type Approval Holder(?:’|')s Name", level: "metadata" },
  { pattern: "Type\\/Model designation\\(s\\)?", level: "metadata" },
  { pattern: "Type\\/model designations?", level: "metadata" },
  { pattern: "TCDS Number", level: "metadata" },
  { pattern: "Foreign AD", level: "metadata" },
  { pattern: "Supersedure(?:\\/Revision)?", level: "metadata" },
  { pattern: "Manufacturer\\(s\\)?", level: "metadata" },
  { pattern: "AD No\\.?", level: "metadata", continues: false },
  { pattern: "Date", level: "metadata", continues: false },
];

function passageFieldAt(lines: string[], start: number): {
  consumed: number;
  label: string;
  content: string;
  level: "section" | "metadata";
  continues: boolean;
} | null {
  const available = Math.min(3, lines.length - start);

  for (let consumed = available; consumed >= 1; consumed -= 1) {
    const candidateLines = lines.slice(start, start + consumed).map((line) => line.trim());
    if (candidateLines.some((line) => !line)) continue;
    if (consumed > 1 && candidateLines.slice(0, -1).some((line) => line.includes(":"))) continue;

    const candidate = candidateLines.join(" ").replace(/\s+/g, " ").trim();
    for (const field of PASSAGE_FIELDS) {
      const withColon = candidate.match(new RegExp(`^(${field.pattern})\\s*:\\s*(.*)$`, "i"));
      const withoutColon = candidate.match(new RegExp(`^(${field.pattern})\\s*$`, "i"));
      const match = withColon ?? withoutColon;
      if (!match) continue;
      return {
        consumed,
        label: match[1].replace(/\s+/g, " ").trim(),
        content: withColon?.[2]?.trim() ?? "",
        level: field.level,
        continues: field.continues ?? true,
      };
    }
  }

  return null;
}

export function parsePassage(text: string): ParsedBlock[] {
  const lines = text.split(/\r?\n/);
  const blocks: ParsedBlock[] = [];
  let currentParagraph: string[] = [];
  let activeStructuredBlock: ParsedBlock | null = null;

  const flushParagraph = () => {
    if (currentParagraph.length > 0) {
      const combined = currentParagraph.join(" ").trim();
      if (combined) {
        blocks.push({ type: "paragraph", content: combined });
      }
      currentParagraph = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    if (!line) {
      flushParagraph();
      activeStructuredBlock = null;
      continue;
    }

    const field = passageFieldAt(lines, i);
    if (field) {
      flushParagraph();
      const block: ParsedBlock = {
        type: "field",
        prefix: field.label,
        content: field.content,
        fieldLevel: field.level,
      };
      blocks.push(block);
      activeStructuredBlock = field.continues ? block : null;
      i += field.consumed - 1;
      continue;
    }

    // Check for Note
    const noteMatch = line.match(/^((?:Note(?:\s+\d+)?|Reminder):\s*)(.*)$/i);
    if (noteMatch) {
      flushParagraph();
      const block: ParsedBlock = {
        type: "note",
        prefix: noteMatch[1].trim(),
        content: noteMatch[2].trim(),
      };
      blocks.push(block);
      activeStructuredBlock = block;
      continue;
    }

    // Check for Table Header / Table title
    const tableMatch = line.match(/^(Table\s+\d+[^:]*:\s*|Table\s+\d+\s*[-–]\s*.*)$/i);
    if (tableMatch) {
      flushParagraph();
      blocks.push({
        type: "table_header",
        content: line,
      });
      activeStructuredBlock = null;
      continue;
    }

    // Check for Main Headings (e.g. "Applicability:", "Required Action(s)...:", "Reason:", "Definitions:")
    const headingMatch = line.match(/^(Applicability|Reason|Definitions|Required Action\(s\)(?: and Compliance Time\(s\))?|Compliance Time\(s\)|Ref\. Publications|Remarks|Supersedure|Correction):\s*(.*)$/i);
    if (headingMatch) {
      flushParagraph();
      const block: ParsedBlock = {
        type: "heading",
        prefix: headingMatch[1] + ":",
        content: headingMatch[2].trim(),
      };
      blocks.push(block);
      activeStructuredBlock = block;
      continue;
    }

    // Check for Clause markers like (1), (1.1), (2), (a), (b), (i)
    const clauseMatch = line.match(/^(\((?:\d+(?:\.\d+)*|[a-z]|[ivx]+)\))\s+(.*)$/i);
    if (clauseMatch) {
      flushParagraph();
      const block: ParsedBlock = {
        type: "clause",
        prefix: clauseMatch[1],
        content: clauseMatch[2].trim(),
      };
      blocks.push(block);
      activeStructuredBlock = block;
      continue;
    }

    if (activeStructuredBlock) {
      activeStructuredBlock.content = `${activeStructuredBlock.content} ${line}`.trim();
    } else {
      currentParagraph.push(line);
    }
  }

  flushParagraph();
  return blocks;
}

function PassageViewer({ passage, evidenceId, sourcePdf, section }: {
  passage: string;
  evidenceId: string;
  sourcePdf: string;
  section: string;
}) {
  const [fontSize, setFontSize] = useState<FontSize>("md");
  const [viewMode, setViewMode] = useState<ViewMode>("formatted");
  const [copied, setCopied] = useState(false);

  const blocks = useMemo(() => parsePassage(passage), [passage]);

  const copyPassage = async () => {
    try {
      await navigator.clipboard.writeText(passage);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      toast.success("Passage copied to clipboard");
    } catch {
      toast.error("Failed to copy passage");
    }
  };

  const cycleFontSize = () => {
    setFontSize((current) => (current === "sm" ? "md" : current === "md" ? "lg" : "sm"));
  };

  return (
    <div className="passage-card" aria-label="Retrieved source passage">
      <div className="passage-toolbar">
        <div className="passage-toolbar-left">
          <span className="passage-badge"><FileText aria-hidden="true" /> {evidenceId}</span>
          <span className="passage-mode-label">{viewMode === "formatted" ? "Formatted Reader" : "Verbatim Source"}</span>
        </div>
        <div className="passage-toolbar-right">
          <button
            type="button"
            onClick={cycleFontSize}
            className="passage-tool-button"
            title={`Font size: ${fontSize.toUpperCase()} (Click to cycle S/M/L)`}
            aria-label={`Change font size, currently ${fontSize}`}
          >
            <Type aria-hidden="true" />
            <span>{fontSize.toUpperCase()}</span>
          </button>
          <button
            type="button"
            onClick={() => setViewMode((m) => (m === "formatted" ? "raw" : "formatted"))}
            className={`passage-tool-button ${viewMode === "raw" ? "is-active" : ""}`}
            title={viewMode === "formatted" ? "Switch to Verbatim Raw text" : "Switch to Formatted Reader"}
            aria-label="Toggle view mode"
          >
            {viewMode === "formatted" ? <Code aria-hidden="true" /> : <Eye aria-hidden="true" />}
            <span>{viewMode === "formatted" ? "Raw" : "Reader"}</span>
          </button>
          <button
            type="button"
            onClick={copyPassage}
            className={`passage-tool-button ${copied ? "is-active" : ""}`}
            title="Copy passage text"
            aria-label="Copy passage text"
          >
            {copied ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}
            <span>{copied ? "Copied" : "Copy"}</span>
          </button>
        </div>
      </div>

      <div className="passage-section-context">
        <span>Retrieved section</span>
        <strong>{section || "Document"}</strong>
      </div>

      {viewMode === "raw" ? (
        <pre className="passage-raw">{passage}</pre>
      ) : (
        <div className={`passage-body size-${fontSize}`}>
          {blocks.map((block, index) => {
            if (block.type === "field") {
              return (
                <div key={index} className={`passage-field is-${block.fieldLevel ?? "metadata"}`}>
                  <div className="passage-field-label">{block.prefix}</div>
                  {block.content && <div className="passage-field-content">{block.content}</div>}
                </div>
              );
            }
            if (block.type === "heading") {
              return (
                <div key={index} className="passage-heading-block">
                  <div className="passage-heading-title">{block.prefix}</div>
                  {block.content && <p className="passage-heading-content">{block.content}</p>}
                </div>
              );
            }
            if (block.type === "clause") {
              return (
                <div key={index} className="passage-clause">
                  <span className="passage-clause-badge">{block.prefix}</span>
                  <div className="passage-clause-content">{block.content}</div>
                </div>
              );
            }
            if (block.type === "note") {
              return (
                <div key={index} className="passage-note">
                  <span className="passage-note-label">{block.prefix}</span>
                  <p>{block.content}</p>
                </div>
              );
            }
            if (block.type === "table_header") {
              return (
                <div key={index} className="passage-table-header">
                  {block.content}
                </div>
              );
            }
            return (
              <p key={index} className="passage-paragraph">
                {block.content}
              </p>
            );
          })}
        </div>
      )}

      <div className="passage-provenance">
        <span title={sourcePdf}><FileText aria-hidden="true" /> {sourcePdf}</span>
        <span>Verified E5-D source</span>
      </div>
    </div>
  );
}
