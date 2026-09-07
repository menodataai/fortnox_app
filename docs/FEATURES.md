# Fortnox Insights — Feature Design

*Draft v1 — 2026-07-29. For discussion; UX/UI design follows from this.*

## Who this is for

A small Swedish AB (one or two people) selling consulting services.
- Accounting is outsourced to a third-party accountant who manages Fortnox
  (bookkeeping + payslips).
- The owner invoices clients via Fortnox Faktura (often just a few active
  clients).
- The owner has limited financial/Swedish-tax background and wants to
  **understand** the numbers, not manage them.

## Design principles

1. **Read-only by design.** Fortnox scopes always grant read+write — there is no
   read-only scope — so the app enforces read-only itself: it never creates,
   updates, or deletes anything in Fortnox. The accountant owns the books.
2. **Explain everything.** Every number, account name, and Swedish term
   (moms, arbetsgivaravgift, preliminärskatt, resultaträkning…) gets a
   plain-language explanation. The reader is smart but not an accountant.
3. **Local data mirror.** Fortnox rate-limits to 25 requests / 5 s. The app
   syncs data (SIE export + invoices + vouchers) into a local SQLite database
   on demand / nightly, and all analysis + AI reasoning runs against the mirror.
   This also gives the future LLM features fast, cheap, complete grounding.
4. **Not tax advice.** Projections and tax estimates are labeled as estimates
   with "confirm with your accountant" affordances.

## What the Fortnox API gives us

| Data | API resource | Used for |
|---|---|---|
| General ledger (all transactions) | Vouchers, SIE export, Accounts, Financial Years | P&L, cost structure, cash, projections |
| Chart of accounts w/ balances | Accounts (per financial year) | Account balances, BAS-class grouping |
| Client invoices (AR) | Invoices | Revenue, client view, overdue tracking |
| Supplier invoices (AP) | Supplier Invoices, Suppliers | Cost detail, upcoming payments |
| Payroll | Salary Transactions, Employees | Salary cost view (needs Lön license on API; fallback: read 7xxx accounts from ledger) |
| Company info | Company Information | Header, fiscal year |
| Change events | WebSockets (Invoices, Vouchers, …) | Later: live sync |

Swedish BAS chart of accounts structure is the analytical backbone:
`3xxx` revenue · `4xxx` direct costs · `5–6xxx` overhead · `7xxx` personnel ·
`8xxx` financial items. This maps mechanically to a readable P&L and cost
structure without any manual tagging.

## Features

### F1 — Overview dashboard (the "how are we doing" page)
- KPI tiles: revenue YTD, total costs YTD, profit (EBIT) YTD, cash in bank
  (1930-account balance), outstanding + overdue invoices.
- Monthly revenue vs. costs chart with profit line; compare to previous year.
- Attention list: overdue client invoices, supplier invoices due within 14
  days, unusual transactions (new large cost, month-over-month spikes).

### F2 — Profit & loss, readable (Resultaträkning för människor)
- P&L built from the ledger, grouped by BAS class, each line renamed to plain
  language ("Personnel costs — salaries, employer contributions, pension").
- Monthly columns, YTD, vs. last year.
- Drill-down: P&L line → accounts → individual vouchers/transactions, so
  "Other external costs, 34 500 kr" is two clicks from the actual receipts.

### F2b — Account Explorer ("what's behind this number?") ★ owner priority
*Motivation: the accountant's quarterly/yearly reports and balance sheet show a
number per account, but not what's in it. Every such number must be openable.*

- **Mirrored reports.** The app renders its own Balance sheet (balansräkning)
  and P&L for any period — year, quarter, month, or custom — matching the
  periods the accountant reports on, so any line in their PDF can be found here.
- **Three-level drill-down.** Report line → accounts behind it → transactions:
  1. *Report line* ("Övriga externa kostnader — 84 300 kr") expands to the BAS
     accounts that make it up, each with its share.
  2. *Account view* (e.g. `6540 IT-tjänster`): opening balance (IB), period
     movement, closing balance (UB); a mini bar chart of monthly activity; and
     the full transaction list — date, voucher number, description, supplier /
     counterparty where known, debit, credit, running balance.
  3. *Voucher view*: the complete double-entry voucher a transaction belongs
     to, all rows with their accounts, so you can see e.g. that one payment
     hit both a cost account and moms. Attachment (receipt/invoice image)
     shown when available via the archive connection.
- **Periodization chains.** Recurring accrual rows ("Periodisering av
  verifikation A57") are linked to their origin voucher and shown as a
  schedule: original amount, monthly slice, remaining balance on the
  17xx/29xx account, end date. Caution: the referenced voucher number may
  belong to a *previous year's* series (and the same number may be reused
  by an unrelated voucher in the current year), so the link must resolve
  by year + balance continuity, not by number alone.
- **Composition summary per account.** Above the transaction list: largest
  transactions, recurring vs. one-off split, top counterparties — so a year's
  total is understandable at a glance before reading rows.
- **Plain-language account descriptions.** Every BAS account gets a
  human explanation ("6540 IT-tjänster — software, cloud services, IT
  consultants you buy") shown inline; later the AI assistant answers
  free-form questions about any account or transaction.
- **Search across everything.** Free-text search over transaction descriptions
  and suppliers ("what did we pay to AWS this year?") regardless of account.
- *(Later, AI)* **Report reconciliation**: upload the accountant's PDF report
  and the assistant maps each line to app data and flags anything that
  doesn't match or deserves a question at the next accountant meeting.
  → promoted to F10 (report analyzer).

Data: entirely from the ledger mirror (SIE type 4 / vouchers + accounts +
financial years). Balance sheet needs IB/UB per account per financial year —
both available from the Accounts resource and the SIE file.

*Known mirror limitation (observed 2026-07-30):* transaction-level detail
exists only for recent years (currently 2025–2026); older financial years
have IB/UB balances but no vouchers. Features and AI answers must degrade
gracefully — reconstruct from balances where possible and say explicitly
which years lack detail. Worth investigating whether Fortnox can export
SIE detail for the older years too.

### F3 — Cost structure
- "Where does the money go": breakdown of costs by category with share-of-total.
- Recurring-cost detection: subscriptions, insurance, phone, accountant fees —
  anything appearing monthly/quarterly at a similar amount becomes a named
  recurring item with an annualized cost.
- Fixed vs. variable split → your monthly "burn rate" independent of billing.
- **Entity cost view (total cost of ownership).** "What does the company car
  cost per month?" answered by aggregating across accounts and counterparties:
  leasing (5615, incl. periodization rows), insurance (5612), charging/fuel
  (5611/5619), trängselskatt (5616), connectivity subscriptions,
  fordonsskatt, plus the employer-side AGA on the bilförmån. Grouping is by
  *entity* (the car), not by account — counterparty matching (the leasing
  company, the insurer, Transportstyrelsen) does the mapping. Same pattern later for
  other entities (an employee, a client, an insurance portfolio). Worked
  example with real numbers in `CASE_STUDY_BILFORMAN.md` (example 2;
  local/gitignored — it traces the author's real books).

### F4 — Revenue & clients
- Per-client invoice history, days-to-pay behavior, invoiced vs. paid.
- Client concentration: when most revenue comes from a single client this is
  the company's biggest risk — show revenue dependency explicitly.
- Billing cadence view: invoiced amount per month vs. your run-rate target.

### F5 — Full-year projection
- Baseline projection = YTD actuals + detected recurring costs + contracted /
  expected billing for remaining months.
- Adjustable assumptions: billed days or amount per month, salary levels,
  planned one-off costs.
- Outputs: projected year-end revenue, costs, profit before tax, corporate tax
  (bolagsskatt, 20.6 %), profit after tax. Clearly labeled as an estimate.
- Later: rough dividend-space (3:12 / K10) indicator — flagged "discuss with
  accountant".

### F6 — Payroll view
- Monthly salary cost per employee: gross salary → employer contributions
  (arbetsgivaravgifter) → pension → total employer cost, with an explainer of
  each step.
- Source: Salary API if the license allows; otherwise derived from 7xxx
  accounts in the ledger (works regardless of license).

### F7 — Tax & obligations calendar
- Derived timeline of what the company pays and when: moms (VAT) periods,
  arbetsgivaravgift + preliminärskatt monthly cycle, bolagsskatt.
- Each entry: what it is, roughly how it's computed, where it shows in the books.
- Amounts read from the ledger's tax accounts (26xx, 27xx, 1630/2518…) rather
  than computed from scratch — the accountant's numbers are the truth.

### F8 — AI financial assistant *(phase 2)* ★ owner priority
*Architecture & implementation design: [AI_DESIGN.md](AI_DESIGN.md).*

Free-text Q&A over the company's real data, built as an agentic tool-use loop:
the assistant understands the question, asks for clarification when it's
ambiguous, decides which data it needs, fetches it, and answers with the
numbers and their sources.

**Conversation flow**
1. *Understand* — parse intent: metric(s), period, entity (account, client,
   supplier, invoice…).
2. *Clarify when needed* — ambiguous questions get one short follow-up before
   any data is fetched ("Costs for Q2 — the whole company, or a specific
   category?"). Never guess silently on period or scope.
3. *Plan & fetch* — the model runs a tool-use loop against read-only data
   tools (see below), chaining calls as needed: a "why was March expensive?"
   question might fetch the monthly P&L, diff it against February, then pull
   transactions for the accounts that moved most.
4. *Answer* — plain language, numbers formatted, every figure traceable:
   answers cite the vouchers/invoices/accounts they came from, and the UI
   renders those citations as links into the Account Explorer (F2b).
   Swedish terms explained on first use. Tax-adjacent answers carry the
   "estimate — confirm with accountant" label.

**Question types the assistant must handle** (each validated against real
data — see the case study):
- *Verification* — "is this benefit/tax/charge correct?" → ledger evidence +
  online rule check + exact arithmetic + confirm/refute verdict (example 1).
- *Entity cost aggregation* — "what does X cost per month?" → collect across
  accounts and counterparties, separate cash cost / benefit / tax effect
  (example 2).
- *Explain this entry* — "what is this 2,666.67 posting?" → identify the
  bookkeeping construct (periodisering, accrual, reversal…), trace the
  reference chain to its origin (the row's description pointed to a voucher
  in an earlier year, outside the mirror's detail window), reconstruct
  the story from IB/UB balances when voucher detail is missing (an
  illustrative 96,000 kr first lease fee ÷ 36 months, verified against three
  year-end balances),
  and *teach* the concept in plain language: why accountants spread costs,
  what account 1720 is for, when the entry will end and what happens then
  (example 3). Answers must distinguish verified facts from balance-based
  reconstruction, and follow same-numbered voucher collisions across years
  correctly (2026's "A57" is an unrelated transaction).

**Data tools exposed to the model** (all read-only, all against the local
mirror first for speed and rate-limit safety; live Fortnox fetch only when
the mirror is stale):
- `query_ledger` — parameterized queries over accounts/vouchers/transactions
  (per period, per BAS class, text search on descriptions)
- `get_profit_and_loss` / `get_balance_sheet` — the same builders F2/F2b use
- `list_invoices` / `get_invoice` — AR, payment status, per client
- `list_supplier_invoices` — AP, upcoming payments
- `get_account_detail` / `get_voucher` — drill-down data
- `run_projection` — the F5 projection engine with assumption overrides
- `get_company_info`, `get_financial_years`
- `web_research` — search/fetch against authoritative Swedish sources
  (Skatteverket incl. rättslig vägledning, Riksgälden, regeringen.se,
  Bolagsverket) so answers can combine the company's real numbers with
  current rules and rates (prisbasbelopp, statslåneränta, förmånsregler,
  moms- and AGA-rates). Answers must cite the sources used.

**Validated reference case (2026-07-30).** A manual session proved the
concept end-to-end: a suspected over-reported bilförmån was checked by
querying the ledger mirror (per-employee payroll vouchers, AGA
reconciliation at öre precision), verifying the current rules online
(350 000 kr EV nedsättning, 2026 formula parameters, extrautrustning
treatment), reverse-engineering the registered nybilspris to the exact
öre, and delivering a confirm/refute verdict with month-by-month numbers
and follow-ups for the accountant. This is the quality bar for F8: real
ledger data + live rule verification + auditable arithmetic, read-only,
"discuss with your accountant" framing on conclusions.
Full worked examples — questions, answers, method, and the tool
requirements they imply — in
**`CASE_STUDY_BILFORMAN.md`** (local/gitignored): (1) the bilförmån
audit, (2) "what does the company car cost per month?" (entity cost
aggregation, F3), (3) "what is this monthly accrual?" (explain-an-
entry). Use them as design context and as test fixtures for F8.

The model never gets write access to anything, and never calls the Fortnox
API directly — only our backend's tool layer, which enforces read-only.

**UX**
- Chat panel available from every screen (side drawer), context-aware:
  opening it from an account page pre-loads that account as context
  ("Ask about 6540…").
- Shows its work: a collapsible trace of which data it fetched, so answers
  are auditable, not oracular.
- Suggested questions per screen for discoverability.
- Streaming responses; conversation history persisted locally.

**Also in this phase**
- Auto-generated monthly plain-language report: what happened, what changed,
  what needs attention.
- Built on Pydantic AI + OpenRouter (model-switchable tool use; see
  [AI_DESIGN.md](AI_DESIGN.md)).

### F9 — AI analysis agent *(phase 3)*
- Multi-step autonomous analyses: deep year-end projection with scenarios,
  anomaly investigation across the ledger, cost-saving review,
  "prepare me for the meeting with my accountant" briefings.

### F10 — Report analyzer *(phase 3)* ★ owner priority
*Grows out of the F2b "report reconciliation" bullet — promoted to a
first-class feature.*

Analyze the accountant's quarterly/yearly reports (and the app's own
mirrored reports for the same periods):

- **Highlights.** Pinpoint what matters in the period: biggest movements
  vs. previous period/year, margin changes, one-offs vs. recurring,
  items that deserve a question at the next accountant meeting.
- **Cross-checks.** Verify the numbers: report lines vs. the ledger
  mirror, AGA vs. 31.42 % × (wages + benefits), moms accounts vs.
  declared amounts, benefit values vs. current Skatteverket rules
  (using F8's `web_research`), balance-sheet ties (IB/UB continuity).
  Every discrepancy gets a severity, an explanation, and a drill-down
  link into F2b.
- **Q&A on the report.** The F8 chat runs with the report loaded as
  context, so "why is personnel cost up 12 %?" is answered from the
  underlying vouchers.
- Input: uploaded PDF from the accountant, or an app-generated period
  report. Output: plain-language summary + findings list; read-only,
  nothing filed or changed anywhere.
- The cross-check depth expected here is demonstrated in
  `CASE_STUDY_BILFORMAN.md` (benefit value vs. Skatteverket rules, AGA
  reconciliation, cross-year comparison).

## Suggested build order

1. **Data foundation**: sync layer (SIE + invoices + supplier invoices +
   vouchers → SQLite), BAS-class mapping. *Everything depends on this.*
2. F1 dashboard (upgrade current placeholder) + F2 P&L.
3. F3 cost structure + F4 revenue/clients.
4. F5 projection + F7 tax calendar.
5. F6 payroll.
6. F8 assistant (chat + data tools + web research) → F9 agent → F10 report
   analyzer.

## Open questions

- Does the Fortnox license include API access to Salary/Employees, or do we
  derive payroll from the ledger? (Easy to test once connected.)
- Projection inputs: is billing roughly "days × rate, monthly invoice" — and is
  there a contracted horizon we can encode?
- Language: UI in English with Swedish terms kept (moms, arbetsgivaravgift)
  and explained, or fully Swedish?
