#!/usr/bin/env python3
"""Dependency-light local web UI for the Airbus EASA AD assistant."""

from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import Any

from full_corpus_pipeline.assistant.runtime import (
    AssistantRuntimeConfig,
    AviationDocumentAssistant,
    DEFAULT_DENSE_DIR,
    DEFAULT_INDEX,
)


HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Airbus EASA AD Assistant</title>
<style>
:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#172033;background:#f4f6f8}
body{margin:0}main{max-width:980px;margin:0 auto;padding:32px 20px 56px}
header{margin-bottom:22px}h1{margin:0 0 8px;font-size:30px}p{line-height:1.55}
.card{background:#fff;border:1px solid #dce2e8;border-radius:14px;padding:18px;margin:16px 0;box-shadow:0 5px 18px rgba(20,40,70,.04)}
textarea{width:100%;box-sizing:border-box;min-height:120px;padding:14px;border:1px solid #b8c2cc;border-radius:10px;font:inherit;resize:vertical}
.controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:12px}
button{border:0;border-radius:9px;padding:10px 16px;font:inherit;font-weight:650;background:#163b65;color:#fff;cursor:pointer}
button:disabled{opacity:.55;cursor:not-allowed}.muted{color:#5d6875;font-size:14px}.status{font-weight:700}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}.metric{background:#f7f9fb;border-radius:9px;padding:10px}
.evidence{border-top:1px solid #e6ebef;padding-top:12px;margin-top:12px}.evidence pre{white-space:pre-wrap;font:inherit;font-size:14px;line-height:1.45;background:#f7f9fb;padding:12px;border-radius:8px}
ul{padding-left:22px}.error{color:#a32626}.ok{color:#17653a}.warn{color:#8b5c00}
code{background:#eef2f5;padding:2px 5px;border-radius:5px}
</style>
</head>
<body>
<main>
<header>
<h1>Airbus EASA AD Assistant</h1>
<p class="muted">Evidence-grounded assistant for Airbus S.A.S. Airworthiness Directives issued by EASA. Original AD passages remain authoritative.</p>
</header>
<section class="card">
<label for="q"><strong>Ask a maintenance-document question</strong></label>
<textarea id="q" placeholder="Example: For EASA AD 2011-0041R1, what actions were required within 3 days after 14 March 2011?"></textarea>
<div class="controls">
<button id="ask">Ask assistant</button>
<label><input id="retrievalOnly" type="checkbox"> Retrieval only (skip DeepSeek)</label>
<span id="busy" class="muted"></span>
</div>
</section>
<section id="result" hidden></section>
<section class="card">
<strong>Safety boundary</strong>
<p class="muted">This tool supports document retrieval and interpretation. It does not make an aircraft-specific legal compliance determination or replace the controlling EASA AD and approved maintenance data.</p>
</section>
</main>
<script>
const ask=document.getElementById('ask'),q=document.getElementById('q'),out=document.getElementById('result'),busy=document.getElementById('busy');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function list(title,items){if(!items||!items.length)return'';return `<h3>${esc(title)}</h3><ul>${items.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`}
function page(c){return c.page_start===c.page_end?c.page_start:`${c.page_start}-${c.page_end}`}
function render(r){
 const status=r.status||'unknown';
 const klass=status==='answered'?'ok':status==='technical_error'?'error':'warn';
 const citations=(r.citations||[]).map(c=>`<li><strong>${esc(c.ad_number)}</strong> · p.${esc(page(c))} · ${esc(c.section)} · ${esc(c.evidence_id)}</li>`).join('');
 const ev=((r.retrieval||{}).evidence||[]).map(e=>`<div class="evidence"><strong>${esc(e.evidence_id)} · ${esc(e.ad_number)} · p.${esc(page(e))} · ${esc(e.section)}</strong><pre>${esc(e.text)}</pre></div>`).join('');
 const corpus=((r.retrieval||{}).runtime||{}).corpus||{};
 return `<div class="card">
  <div class="grid">
   <div class="metric"><span class="muted">Status</span><br><span class="status ${klass}">${esc(status)}</span></div>
   <div class="metric"><span class="muted">Route</span><br><strong>${esc((r.route||{}).mode||'unknown')}</strong></div>
   <div class="metric"><span class="muted">Corpus</span><br><strong>${esc(corpus.document_count||'?')} docs / ${esc(corpus.chunk_count||'?')} chunks</strong></div>
  </div>
  ${r.answer?`<h2>Answer</h2><p>${esc(r.answer)}</p>`:''}
  ${list('Conditions',r.conditions)}${list('Compliance time',r.compliance_time)}${list('Exceptions',r.exceptions)}
  ${r.reason_for_abstention?`<h3>Reason</h3><p>${esc(r.reason_for_abstention)}</p>`:''}
  ${r.technical_error?`<p class="error"><strong>${esc(r.technical_error.type)}:</strong> ${esc(r.technical_error.message)}</p>`:''}
  ${citations?`<h3>Citations</h3><ul>${citations}</ul>`:''}
 </div>
 <div class="card"><h2>Retrieved evidence</h2>${ev||'<p class="muted">No evidence returned.</p>'}</div>`;
}
ask.onclick=async()=>{
 const question=q.value.trim(); if(!question)return;
 ask.disabled=true;busy.textContent='Running E5-D retrieval and QA…';out.hidden=true;
 try{
   const resp=await fetch('/api/query',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({question,retrieval_only:document.getElementById('retrievalOnly').checked})});
   const data=await resp.json();
   if(!resp.ok) throw new Error(data.error||`HTTP ${resp.status}`);
   out.innerHTML=render(data);out.hidden=false;
 }catch(e){out.innerHTML=`<div class="card error"><strong>Request failed:</strong> ${esc(e.message)}</div>`;out.hidden=false}
 finally{ask.disabled=false;busy.textContent=''}
};
</script>
</body></html>
"""


class AssistantHandler(BaseHTTPRequestHandler):
    assistant: AviationDocumentAssistant

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/":
            body = HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/health":
            self._json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "assistant_version": "aviation-document-assistant-v1.0",
                    "corpus": self.assistant.corpus_stats,
                },
            )
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/api/query":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 64_000:
                raise ValueError("invalid request size")
            payload = json.loads(self.rfile.read(length))
            question = str(payload.get("question", "")).strip()
            if not question:
                raise ValueError("question is required")
            if len(question) > 4_000:
                raise ValueError("question is too long")
            result = self.assistant.answer(
                question,
                retrieval_only=bool(payload.get("retrieval_only", False)),
            )
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except Exception as exc:
            self._json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"{type(exc).__name__}: {exc}"},
            )
            return
        self._json(HTTPStatus.OK, result)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[web] {self.address_string()} - {fmt % args}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--dense-dir", type=Path, default=DEFAULT_DENSE_DIR)
    parser.add_argument("--query-device", default="auto")
    parser.add_argument("--reranker-device", default="auto")
    parser.add_argument("--reranker-batch-size", type=int, default=2)
    args = parser.parse_args()

    assistant = AviationDocumentAssistant(
        AssistantRuntimeConfig(
            index_dir=args.index,
            dense_dir=args.dense_dir,
            query_device=args.query_device,
            reranker_device=args.reranker_device,
            reranker_batch_size=args.reranker_batch_size,
        )
    )
    AssistantHandler.assistant = assistant
    server = ThreadingHTTPServer((args.host, args.port), AssistantHandler)
    print(
        f"Airbus EASA AD Assistant: http://{args.host}:{args.port} "
        f"({assistant.corpus_stats['document_count']} docs / "
        f"{assistant.corpus_stats['chunk_count']} chunks)"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
