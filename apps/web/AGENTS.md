<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# Web App Agent Guide

This guide applies to `apps/web`. The repository-root `AGENTS.md` still applies; this file adds web-specific instructions. If the two guides conflict, follow the stricter project safety rule and the current user request.

## Product boundary

- This is the user-facing Airbus EASA Airworthiness Directive assistant, built with Next.js 16, React 19, TypeScript, and Tailwind CSS 4.
- Treat frontend work as post-evaluation engineering. Do not change, retune, or reinterpret the frozen parser, E5-D retrieval, hosted-QA settings, benchmark records, or locked results from this app.
- Original PDF passages are authoritative for detailed compliance interpretation. Preserve source, page, section, chunk, and evidence identifiers from the API through the UI.
- Keep retrieval failures, hosted-QA/status failures, and provider or transport failures visibly distinct. Do not turn missing evidence or technical errors into confident answers.
- Preserve retrieval-only behavior and the ability to inspect evidence even when hosted answer generation fails.

## Source map

- `src/app/page.tsx`: app entry point.
- `src/components/conversation-shell.tsx`: active conversation workspace, request lifecycle, evidence inspector, passage parsing, resizing, and cancellation UI.
- `src/app/globals.css`: global design tokens, responsive layout, and component styling.
- `src/lib/assistant.ts`: streaming SSE client and cancellation request.
- `src/lib/api.ts`: typed OpenAPI client and `NEXT_PUBLIC_ASSISTANT_API_URL` resolution.
- `src/generated/api.d.ts`: generated API types; do not hand-edit.
- `src/components/*.test.tsx`: Vitest and Testing Library coverage.
- `tests/e2e/shell.spec.ts`: Playwright browser coverage.

`src/components/assistant-shell.tsx` is a legacy/superseded shell unless a current import proves otherwise. Do not update both shells speculatively.

## UI and interaction rules

- Preserve the evidence-first regulatory workspace rather than turning it into a generic chatbot.
- Keep working interaction modes intact unless the request explicitly changes them: normal QA, retrieval-only, AD context, streaming progress, citation-to-evidence selection, inspector resizing, stop/cancel, and follow-up turns.
- Render evidence content as source material. Do not silently rewrite compliance conditions, intervals, exceptions, terminating actions, or applicability wording.
- A citation must resolve to its matching evidence record when one is supplied. Keep citation controls disabled or otherwise honest when the target evidence is unavailable.
- Maintain keyboard, focus, semantic-role, and accessible-name behavior when changing controls or layout. The evidence resize separator must remain keyboard operable.
- Keep responsive behavior usable at desktop and narrow widths; verify long AD identifiers, long passages, empty states, loading states, failures, and multiple evidence tabs.
- Reuse the current visual language and CSS variables. Avoid broad redesigns when the request targets one surface.
- Do not add analytics, remote fonts, trackers, or new network services without explicit approval.

## API contract

- The default backend is `http://127.0.0.1:8000`; override it with `NEXT_PUBLIC_ASSISTANT_API_URL` as shown in `.env.example`.
- The streaming endpoint emits route, retrieval, evidence, generation, and answer events. Preserve the ordering where evidence can appear before the final answer.
- Abort the local stream and send the backend cancellation request with the same request ID. Cancellation is not an error state and should not discard already retrieved evidence.
- Preserve the API status vocabulary, including `answered`, `insufficient_evidence`, `conflicting_evidence`, `retrieval_only`, and `technical_error`.
- When the backend OpenAPI schema changes, run the backend locally and regenerate types with `pnpm --dir apps/web generate:api`. Review the generated diff together with the backend contract change.

## Implementation conventions

- Prefer server components by default; add `"use client"` only where browser state, effects, or event handlers require it.
- Keep transport and response normalization in `src/lib`, not embedded throughout presentation components.
- Extend generated OpenAPI types with narrow frontend adapters instead of duplicating the backend schema by hand.
- Use the `@/` alias for app imports and existing utilities/components before adding dependencies.
- Avoid hydration mismatches: guard browser-only APIs and provide stable server snapshots for external stores.
- Do not weaken TypeScript, ESLint, or accessibility checks to make a change pass.

## Validation

Run the smallest relevant checks during iteration, then the full web gate for a material change:

```bash
pnpm --dir apps/web typecheck
pnpm --dir apps/web lint
pnpm --dir apps/web test
pnpm --dir apps/web test:e2e
pnpm --dir apps/web build
```

- Add or update unit tests for parsing, state transitions, cancellation, resizing, and conditional rendering.
- Use Playwright for critical user flows and layout/interaction regressions. Scope repeated text with semantic roles, labels, or exact text; in particular, target the inspector by its complementary landmark and the passage by `Retrieved source passage`.
- E2E uses `http://127.0.0.1:3000` and starts the Next.js dev server automatically. Backend-dependent flows require the assistant API separately on port 8000.
- Also run `git diff --check`. If an API contract changed, run the corresponding backend contract tests from the repository root.

## Change discipline

- Preserve unrelated modified and untracked files. Stage only the files in the requested web change.
- Do not commit generated build output such as `.next/`, Playwright `test-results/`, or local environment files.
- Do not commit, push, deploy, or regenerate the production/index corpus unless the user explicitly requests that separate action.
- Update web-facing documentation and tests when behavior changes materially, but do not rewrite frozen evaluation documentation or benchmark outcomes.
