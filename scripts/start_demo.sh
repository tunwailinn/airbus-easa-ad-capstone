#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${ASSISTANT_PYTHON:-.venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Assistant Python executable not found or not executable: $PYTHON_BIN" >&2
  echo "Create .venv, or set ASSISTANT_PYTHON to an existing project Python executable." >&2
  exit 1
fi
if ! command -v pnpm >/dev/null 2>&1; then
  echo "pnpm is required. Install Node.js 20.9+ and pnpm first." >&2
  exit 1
fi
if [[ ! -d "data_processed/serving/assistant_v1/e4_section_hybrid" ]]; then
  echo "Serving snapshot missing. Running validated snapshot preparation..."
  "$PYTHON_BIN" -m full_corpus_pipeline.assistant.prepare_serving_snapshot
fi
if [[ ! -d "apps/web/node_modules" ]]; then
  echo "Installing frontend dependencies..."
  pnpm install
fi

cleanup() {
  [[ -n "${API_PID:-}" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "${WEB_PID:-}" ]] && kill "$WEB_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting warm FastAPI backend on http://127.0.0.1:8000"
"$PYTHON_BIN" -m full_corpus_pipeline.assistant_api.app &
API_PID=$!

printf "Waiting for Qwen models to warm"
for _ in $(seq 1 180); do
  if curl -fsS http://127.0.0.1:8000/api/v1/health 2>/dev/null | grep -q '"status":"ready"\|"status": "ready"'; then
    echo
    break
  fi
  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo
    echo "Backend exited during startup." >&2
    exit 1
  fi
  printf "."
  sleep 2
done

if ! curl -fsS http://127.0.0.1:8000/api/v1/health | grep -q '"status":"ready"\|"status": "ready"'; then
  echo "Backend did not become ready." >&2
  exit 1
fi

echo "Starting Next.js frontend on http://127.0.0.1:3000"
(
  cd apps/web
  NEXT_PUBLIC_ASSISTANT_API_URL="${NEXT_PUBLIC_ASSISTANT_API_URL:-http://127.0.0.1:8000}" pnpm dev --hostname 127.0.0.1
) &
WEB_PID=$!

echo
echo "Demo ready: http://127.0.0.1:3000"
echo "Press Ctrl+C to stop both services."
wait "$WEB_PID"
