# Fortnox Insights — Architecture & Implementation Plan

*v1 — 2026-07-30*

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | **Python 3.12 + FastAPI** | async, typed, auto API docs; natural home for the later AI tool-layer |
| HTTP client | **httpx (async)** | Fortnox REST + OAuth |
| Data store | **SQLite** (stdlib `sqlite3`) | single-user local app; zero ops; SQL is the query language the AI assistant will later use |
| Frontend | **React 19 + Vite + TypeScript** | fast dev loop; the mock's design system carries over 1:1 |
| Routing | react-router | screen-per-URL, deep links to accounts |
| Charts | hand-rolled (divs/SVG) | tiny, matches the validated design-system specs; no chart-lib bloat |
| AI (phase 2) | Pydantic AI + OpenRouter, tool-use over the mirror | grounded, read-only, model-switchable — see [AI_DESIGN.md](AI_DESIGN.md) |

## Stack decision: stay on Python (Node.js considered & rejected, 2026-07-30)

A switch to a Node/TypeScript backend (Next.js or Hono + Vite) was considered
to get "one app, one language". Decision: **keep the Python backend.**

- The rewrite would target exactly the code that is done and *validated
  against real data*: the SIE parser (encoding quirks), the OAuth flow with
  single-use rotating refresh tokens, the sync engine, and the analytics
  module whose numbers were verified at öre precision in the bilförmån case
  study. Re-verifying all of that buys no new user value.
- It would still be a client + server logically — the browser can't hold OAuth
  secrets, run sync, or own SQLite. Node unifies the language, not the
  architecture.
- The AI layer (F8) is the next big chunk of code; Pydantic AI (Python) is the
  chosen framework there.

The two real pains of the split get cheap Python-side fixes instead
(implemented alongside F8 step 1):

1. **Single-app packaging** — FastAPI serves the built frontend: mount
   `frontend/dist` via `StaticFiles` (with an SPA fallback to `index.html`).
   One process, one port in production; the Vite dev server + proxy remains
   the dev-time setup.
2. **Shared types** — stop hand-mirroring API shapes in
   `frontend/src/types.ts`: generate them from FastAPI's OpenAPI schema with
   `openapi-typescript` (npm script, e.g. `npm run gen:types` →
   `src/api-types.d.ts`), run whenever backend response models change.

Revisit only if the project's center of gravity moves to TypeScript for other
reasons; the least-bad time to port would have been before F8 — after F8 the
cost roughly doubles.

## System shape

```
Browser (React SPA, :5173)
   │  /api/* /auth/*  (Vite dev proxy)
   ▼
FastAPI backend (:8000)
   ├─ auth/        OAuth2 flow, token store (tokens.json, auto-refresh)
   ├─ sync/        Fortnox → SQLite mirror  ← the only code that talks to Fortnox
   ├─ analytics/   P&L, dashboard, account drill-down — SQL over the mirror
   └─ (phase 2) ai/  Claude tool-use loop over the same analytics functions
        ▼
   SQLite mirror (backend/data/mirror.db)
```

**Principles**: the app never writes to Fortnox; all reads go through the local
mirror (fast, rate-limit-safe, and later the AI's grounding); every number in
the UI is traceable to a voucher.

## Sync strategy (the key design decision)

Fortnox allows 25 requests / 5 s. Instead of paging through vouchers
(hundreds of calls), we fetch the **SIE type-4 export** — Sweden's standard
accounting interchange format — which contains, in **one request per
financial year**: every account with opening/closing balances, every voucher,
and every transaction. A full sync is therefore ~6–10 API calls:

1. `GET /financialyears` → year list
2. `GET /sie/4?financialyear=N` per year (current + previous) → parsed into
   `accounts`, `vouchers`, `transactions` tables
3. `GET /invoices` (paged) → `invoices` table (AR detail the ledger lacks)
4. `GET /supplierinvoices` (paged) → `supplier_invoices`
5. `GET /companyinformation` → company profile

Sync runs automatically after OAuth connect and on demand (`POST /api/sync`);
a status endpoint lets the UI show progress. Requests are throttled to stay
politely under the rate limit.

## Data model (SQLite)

```
meta               key/value: last_sync, company info json
financial_years    id, from_date, to_date
accounts           (year_id, number) → description, ib, ub
vouchers           (year_id, series, number) → date, description
transactions       year_id, series, voucher_number, account, date, description,
                   amount  (SIE convention: debit > 0, credit < 0)
invoices           document_number → customer, dates, total, balance, …
supplier_invoices  given_number → supplier, dates, total, balance, …
```

`bas.py` maps account numbers to BAS classes with English names
(3xxx revenue · 4xxx direct costs · 5–6xxx other external · 70–76xx personnel
· 77xx depreciation · 8xxx financial) plus per-account plain-language
descriptions. All analytics derive from this mapping — no manual tagging.

## API surface (phase 1)

| Endpoint | Purpose |
|---|---|
| `GET /auth/login · /auth/callback · /auth/status · POST /auth/logout` | OAuth |
| `POST /api/sync` · `GET /api/sync/status` | mirror refresh + progress |
| `GET /api/dashboard/summary?year=` | tiles, monthly rev/cost series, attention list |
| `GET /api/pnl?year=` | P&L groups → accounts, monthly + YTD |
| `GET /api/accounts/{number}?year=` | account detail: stats, monthly, transactions |
| `GET /api/vouchers/{series}/{number}?year=` | full double-entry voucher |
| `GET /api/invoices` | invoice list (from mirror) |

## Implementation phases

1. **Data foundation** *(now)* — SIE parser, sync engine, mirror schema,
   BAS mapping, analytics module, API endpoints.
2. **Core screens** *(now)* — app shell in the mock's design; Overview, P&L
   with expandable groups, Account Explorer with voucher modal; connect +
   sync flow.
3. Cost structure · Clients & invoices · Payroll screens (mirror queries exist
   by then; mostly frontend).
4. Year projection + tax calendar.
5. AI assistant (chat drawer, Claude tool-use over analytics) → AI agent.

## Security notes

- Tokens in `backend/data/tokens.json` (gitignored); refresh tokens rotate on
  every use, saved atomically.
- The Fortnox client only implements GET — the app cannot write to Fortnox.
- `.env` is gitignored; never committed.
