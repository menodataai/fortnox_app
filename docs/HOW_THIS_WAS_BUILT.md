# How this was built (with an AI agent)

*The part of this repo that isn't about accounting. Fortnox Insights was
designed and written almost entirely by an AI coding agent (Claude Code),
directed by someone with no finance background — in roughly a week of
spare time (the design docs in this repo span 2026-07-29 to 2026-08-05). This
doc describes the working method, because the method is the transferable
part.*

## The starting point

I run an AI-consulting company. My accountant owns the books in Fortnox; I
could log in and see numbers, but not *understand* them — what drives costs,
what the balance sheet actually says, whether payroll was booked right. Hiring
a CFO at our size is absurd. So the question became: can an AI agent build
me a private analyst?

## Method: documents first, code second

The single biggest difference from "prompting an AI to write code" was that
most of the leverage came **before any code existed**:

1. **A feature spec written in conversation** ([FEATURES.md](FEATURES.md)).
   I described my situation; the agent drafted features; we argued; the doc
   converged. F1–F10 were designed before F1 was implemented. The spec is
   honest about constraints discovered along the way (no payroll API scope →
   reconstruct salaries from L-series ledger vouchers).

2. **Case studies as the quality bar.**
   Before building the AI assistant, I asked a real, hard question — "is our
   company car's bilförmån booked correctly?" — and worked it end-to-end with
   the agent: ledger evidence, current Skatteverket rules verified online,
   öre-exact arithmetic. The written-up session became the spec for what the
   assistant must be able to do, and later the eval that grades it. (The
   case-study documents trace my real books, so they stay local —
   `docs/CASE_STUDY_*.md` is gitignored — but the method transfers: your
   hardest real question makes the best spec.)

3. **Design proposals before risky builds** ([AI_DESIGN.md](AI_DESIGN.md) and
   the PROPOSAL_*.md docs). Framework choice, tool catalog, token budget,
   safety model — decided in a reviewable doc, then implemented.

4. **A grounding file for the AI** (`context/COMPANY_CONTEXT.md`, template in
   [../context/COMPANY_CONTEXT.example.md](../context/COMPANY_CONTEXT.example.md)).
   Verified company facts and known data-quality issues live in one curated
   doc the assistant must read, so it never re-derives them wrong.

## Architecture decisions an agent made well

- **Local SQLite mirror via SIE export.** Fortnox rate-limits hard, but one
  SIE file contains a year's entire ledger. A full sync is ~6–10 API calls;
  every screen and every AI answer runs on local data.
- **BAS ranges as the analytical backbone.** Swedish accounting's numbered
  chart of accounts means a readable P&L, cost recurrence detection and
  payroll reconstruction need zero manual tagging — it's all range arithmetic.
- **Read-only by construction, not by trust.** The AI's SQL tool gets a
  read-only SQLite connection (URI `mode=ro` + `query_only` + an authorizer
  that denies everything but SELECT). The Fortnox client isn't in its tool set
  at all. There is nothing to "trust" the model with.
- **Verification as a first-class step.** Tax rules are never answered from
  memory: a domain-allowlisted `web_search`/`fetch_page` pair checks
  Skatteverket et al., and a separate auditor agent (`verify_draft`)
  re-derives every computed number before an answer is finalized.
- **Tests that cost zero tokens.** The whole agent loop runs under Pydantic
  AI's `TestModel` in CI; the expensive real-model evals run manually, graded
  against the case studies (both live locally — they encode my real books).

## What I'd tell other non-developers-who-code-with-agents

- **Write the case study first.** One real, hard, worked example beats twenty
  feature ideas — it becomes spec, prompt material, and eval in one.
- **Make the agent argue in documents.** Code review is hard for a
  non-expert; design review in plain language is not.
- **Encode your domain constraints once** (the grounding file), then point
  every future session at it.
- **Let the agent own consistency chores** — double-entry demo data,
  OpenAPI-generated frontend types, sign conventions — the places humans
  make the boring mistakes.

---

*Built by [Keven (Qi Wang)](https://www.linkedin.com/in/kevenqiwang/).*
