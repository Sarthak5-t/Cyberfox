# Cyberfox — Web Development Domain

> **Domain owners:** Web Dev team members (fork & PR workflow — see `CONTRIBUTING.md`).
> This document describes everything in the Cyberfox codebase that concerns the **web frontend, terminal UI, and the HTTP/WebSocket backend that serves them**. It is implementation-specific and references real files so you can navigate quickly.

---

## 1. Domain Overview

The web domain covers every layer that a human operator touches or that renders Cyberfox's state to a screen:

| Layer | Location | Purpose |
|---|---|---|
| Dashboard SPA | `web/` | React 19 + Vite 8 single-page app (the "Cyberfox Dashboard"). |
| Terminal UI | `ui-tui/` | Ink/React-based interactive CLI dashboard (`cyberfox tui`). |
| Dashboard backend | `cyberfox_cli/web_server.py` | FastAPI server exposing ~213 REST + WebSocket routes. |
| Auth plugin | `plugins/dashboard_auth/` | Loopback-token + OAuth-cookie auth for the dashboard. |
| Docs site | `website/` | Docusaurus documentation site (published separately). |
| Theming | `web/src/themes/` | 8 built-in themes incl. the cyberpunk preset. |
| i18n | `web/src/i18n/` | 17 locales with a typed key system. |

Everything in this domain is **presentation + transport**. It does *not* implement agent logic — it calls the agent core (see `ai_ml.md`) and the Ares plugin (see `cybersec.md`) through the backend API.

---

## 2. Tech Stack

| Concern | Choice |
|---|---|
| SPA framework | React **19**, TypeScript, Vite **8** |
| Styling | Plain CSS + CSS variables (theme tokens); no Tailwind |
| Terminal UI | Ink **6** + React (same component model as the SPA) |
| Backend | FastAPI (Python 3.11+) with Uvicorn |
| Realtime | WebSocket (chat streaming, PTY) + Server-Sent Events |
| i18n | Custom typed dictionary (`types.ts` + per-locale `*.ts`) |
| Docs site | Docusaurus |

Package manifests: `web/package.json`, `web/vite.config.ts`, `web/tsconfig.app.json`.

---

## 3. Architecture (3-tier)

```
┌─────────────────────────┐         ┌──────────────────────────┐        ┌────────────────────────┐
│  Dashboard SPA (web/)   │  REST/  │  FastAPI backend         │  CLI/   │  Agent core            │
│  React 19 + Vite 8      │◀───────▶│  cyberfox_cli/           │◀──────▶│  run_agent.py + agent/ │
│  WebSocket / WS-PTY     │  WS/    │  web_server.py (~213 rt) │  Py     │  Ares plugin           │
└─────────────────────────┘  SSE    └──────────────────────────┘        └────────────────────────┘
        │                                                                      ▲
        │  Ink/React                                                            │
        ▼                                                                      │
┌─────────────────────────┐                                                    │
│  ui-tui/ terminal UI    │────────── same backend API ────────────────────────┘
└─────────────────────────┘
```

- The SPA and the TUI are **two clients of the same backend**. Neither contains agent logic.
- The backend (`web_server.py`) is a thin orchestration layer: it validates input, calls into the agent runtime / plugins, and serializes results to JSON or streams them over WebSocket.
- Local dev: `venv/bin/python -m cyberfox_cli.main dashboard --skip-build --no-open` serves on **port 9119**.

---

## 4. Detailed Implementation

### 4.1 Dashboard SPA — `web/`

Entry points:
- `web/index.html` — HTML shell. The favicon is suppressed via `<link rel="icon" href="data:,">` (deliberate; do not re-add a binary favicon).
- `web/src/main.tsx` — React root bootstrap.
- `web/src/App.tsx` — **router + sidebar nav + global layout**. This is the most important file for web contributors:
  - Top-level `<Routes>` maps paths → page components.
  - Sidebar uses **collapsible groups** (Core / Intelligence / Integrations / Admin).
  - Profile UI is intentionally **removed from the router** — `ProfilesPage.tsx` and `ProfileBuilderPage.tsx` still exist on disk but are NOT routed (profile system is hidden per product decision). Do not re-add them.
  - Pages registry lives in `web/src/pages/`.

Pages (`web/src/pages/`):
`AnalyticsPage, ChannelsPage, ChatPage, ConfigPage, CronPage, DocsPage, EnvPage, FilesPage, LogsPage, McpPage, ModelsPage, PairingPage, PluginsPage, ProfileBuilderPage, ProfilesPage, SessionsPage, SkillsPage, SystemPage, WebhooksPage`.

Supporting dirs under `web/src/`:
- `components/` — shared UI components.
- `contexts/` — React contexts (auth, settings, runtime state).
- `hooks/` — custom hooks (data fetching, websocket).
- `lib/` — API client, helpers.
- `themes/` — see §4.4.
- `i18n/` — see §4.5.
- `plugins/` — SPA-side plugin mounts (e.g. dashboard widgets).

**Sessions page readability overhaul** (recent work, keep this standard):
`web/src/pages/SessionsPage.tsx` — stats bar uses icon+label, titles `text-base`, metadata uses icons, source-colored badges, desktop action labels, overview card hover + `line-clamp`, toolbar stacks on mobile. Match this density/contrast bar when editing other pages.

### 4.2 Backend — `cyberfox_cli/web_server.py`

- Single FastAPI `app` with ~213 `@app.*` / `@router.*` route decorators.
- Responsibilities:
  - **Static + SPA shell** serving the built dashboard.
  - **REST API groups:** sessions, messages, models, config, plugins, skills, cron, logs, system, mcp, channels, files, env, webhooks, pairing, analytics, docs.
  - **WebSocket endpoints:** chat streaming (token-by-token) and a **PTY bridge** so the terminal experience is mirrored in the browser.
  - **Server-Sent Events** for push (status phrases, background task progress).
- The server imports the agent runtime lazily (avoids importing heavy ML deps at import time for pure static serving).
- Config consumed: `cyberfox_cli/config.py` (see `ai_ml.md` for config schema; web only reads display/runtime flags).

### 4.3 Terminal UI — `ui-tui/`

- Ink 6 + React. Mirrors dashboard functionality in the terminal.
- **ASCII banner was intentionally removed** from `ui-tui/src/components/appLayout.tsx` (and the CLI banner in `cyberfox_cli/banner.py`). Do not re-add branding banners.
- Talks to the same backend API as the SPA (or runs embedded when launched via `cyberfox tui`).

### 4.4 Theming — `web/src/themes/`

Files:
- `presets.ts` — **8 theme presets** as token objects (colors, radius, shadows). The active cyberpunk preset uses `cyan #00ffcc` on `dark #0a0a0f`, `border-radius: 0`, and glow utilities.
- `context.tsx` — React theme context/provider.
- `types.ts` — `Theme` type.
- `index.ts` — re-exports + registry.
- `fonts.ts` — font loading.

Glow + scrollbar styling lives in `web/src/index.css` (utility classes + `::-webkit-scrollbar`). When adding a theme, add a token object to `presets.ts` and register it in `index.ts`; no component changes required.

### 4.5 i18n — `web/src/i18n/`

- `types.ts` — master `TranslationKey` type (single source of truth for keys).
- `en.ts` — English baseline (must contain every key).
- 16 other locales: `af, de, es, fr, ga, hu, it, ja, ko, pt, ru, tr, uk, zh-hant, zh, plus es` (17 total incl. en).
- `context.tsx` — locale context/provider + `useI18n()` hook.
- `index.ts` — locale registry.

**Rule:** any new user-facing string MUST be added to `types.ts` and `en.ts` first, then translated. The SessionsPage uses keys like `sessions.*` — follow the same namespacing.

### 4.6 Auth — `plugins/dashboard_auth/`

- Provides loopback-token auth for local single-user dashboards AND an OAuth-cookie flow for shared deployments.
- The backend enforces it; the SPA stores the token in a context (`web/src/contexts/`).
- Do not weaken the auth check in `web_server.py` — it is the only thing standing between a LAN dashboard and remote control of the agent.

### 4.7 Docs site — `website/`

- Docusaurus project. Builds/publishes the user docs separately from the app.
- Note: the old top-level `docs/` folder was **removed** (backed up to `/home/sarthak/Downloads/docs`). The Docusaurus `website/` is the supported docs surface now.

---

## 5. Key Files Reference

| Path | What to touch |
|---|---|
| `web/src/App.tsx` | Routes, sidebar, layout |
| `web/src/pages/*Page.tsx` | Individual dashboard screens |
| `web/src/themes/presets.ts` | Theme tokens (8 presets) |
| `web/src/index.css` | Global/glow/scrollbar styles |
| `web/src/i18n/{types,en}.ts` | Translation keys |
| `cyberfox_cli/web_server.py` | Backend API (~213 routes) |
| `ui-tui/src/components/appLayout.tsx` | Terminal UI layout (banner removed) |
| `plugins/dashboard_auth/` | Dashboard auth |
| `website/` | Docusaurus docs |

---

## 6. How Web Dev Members Should Work

1. **Fork** the repo, branch `web/<feature>` (see `CONTRIBUTING.md`).
2. Run the dashboard locally: `venv/bin/python -m cyberfox_cli.main dashboard --skip-build --no-open` → http://localhost:9119.
3. **Adding a page:** create `web/src/pages/FooPage.tsx`, register route + sidebar entry in `web/src/App.tsx`, add `foo.*` i18n keys.
4. **Adding a theme:** token object in `presets.ts` + registry in `index.ts`.
5. **Adding a backend route:** add to `cyberfox_cli/web_server.py`; keep agent logic out — call existing runtime functions.
6. **Tests:** `web/` uses Vitest (`vitest.config.ts`). Lint via `eslint.config.js`.
7. **PR:** target `main` (protected — requires review). Never push directly to `main`.

### Conventions to preserve
- No binary favicon (use `data:,`).
- No ASCII/banner branding in TUI or CLI.
- Profile UI stays unrouted.
- Every string is i18n-keyed.
- Cyberpunk is the default visual language: `#00ffcc` / `#0a0a0f`, square corners, glow.
