"""Tool catalog for the assistant. Two layers:

Layer 1 — structured tools wrapping analytics.py: the same code paths the UI
screens use, so chat answers and screens can never disagree.
Layer 2 — power tools: query_ledger (guarded SELECT), calculate (exact
decimal arithmetic), run_python (sandboxed script over a read-only mirror),
read_reference (project knowledge docs), verify_draft (independent auditor),
web_search / fetch_page (allowlisted Swedish sources).

Everything is read-only; the Fortnox client is not reachable from here — with
one deliberate, narrow exception: `trigger_sync` kicks the existing local
sync (no parameters, returns only a status dict; no Fortnox payloads reach the
model)."""

from urllib.parse import urlparse

from pydantic_ai import ModelRetry, RunContext, UsageLimitExceeded

from .. import analytics
from ..analytics import NeedsSyncError
from . import calc, ledger_sql, reference, sandbox, verify, web
from .agent import AssistantDeps, agent

MAX_TXNS_IN_TOOL_OUTPUT = 100


def _needs_sync_guard(fn, *args):
    try:
        return fn(*args)
    except NeedsSyncError:
        raise ModelRetry(
            "The local mirror is empty — tell the user to run a sync from the UI first."
        ) from None


# ── Layer 1: structured tools (same code paths as the UI) ─────


@agent.tool_plain
def get_financial_years() -> list[dict]:
    """List all mirrored financial years. Years with has_transaction_detail=false
    have only opening/closing balances (IB/UB) — no vouchers; answers about
    those years must be reconstructed from balances and say so."""
    return _needs_sync_guard(analytics.financial_years)


@agent.tool_plain
def get_company_info() -> dict:
    """Company profile from Fortnox (name, org number, fiscal year info)."""
    from .. import db

    with db.session() as conn:
        return {
            "company": db.get_meta_json(conn, "company", {}),
            "last_sync": db.get_meta(conn, "last_sync"),
        }


@agent.tool_plain
def get_profit_and_loss(year: int | None = None) -> dict:
    """P&L for a financial year (default: current), grouped by BAS class with
    per-account and per-month breakdowns. Display signs: revenue and costs
    both read positive."""
    return _needs_sync_guard(analytics.pnl, year)


@agent.tool_plain
def get_balance_sheet(year: int | None = None, to_date: str | None = None) -> dict:
    """Balansräkning: IB, movement and UB per balance account. to_date
    (YYYY-MM-DD) gives a mid-period sheet. Liability side reads positive.
    For balances-only years, stored year-end UB is used and to_date is ignored."""
    return _needs_sync_guard(analytics.balance_sheet, year, to_date)


@agent.tool_plain
def get_account_detail(number: int, year: int | None = None) -> dict:
    """One account's story for a year: IB/UB or period total, monthly
    activity, and the transaction list (capped — use query_ledger for more).
    Display signs already flipped for readability."""
    detail = _needs_sync_guard(analytics.account_detail, number, year)
    if len(detail["transactions"]) > MAX_TXNS_IN_TOOL_OUTPUT:
        detail["transactions"] = detail["transactions"][:MAX_TXNS_IN_TOOL_OUTPUT]
        detail["transactions_truncated"] = True
    return detail


@agent.tool_plain
def get_voucher(series: str, number: int, year: int | None = None) -> dict:
    """The complete double-entry voucher: every row with account, debit and
    credit. Voucher numbers restart per year — pass the right year."""
    return _needs_sync_guard(analytics.voucher_detail, series, number, year)


@agent.tool_plain
def get_cost_structure(year: int | None = None) -> dict:
    """Cost breakdown by category with shares, detected recurring costs
    (subscriptions etc.) with frequency and monthly amount, burn rate,
    runway, and one-off outliers."""
    return _needs_sync_guard(analytics.cost_structure, year)


@agent.tool_plain
def get_clients_overview(year: int | None = None) -> dict:
    """Per-client invoicing: totals, share of revenue (concentration risk),
    days-to-pay behaviour, outstanding balances, and the year's invoices."""
    return _needs_sync_guard(analytics.clients_overview, year)


@agent.tool_plain
def get_payroll(year: int | None = None) -> dict:
    """Payroll cost derived from 7xxx ledger accounts: gross, employer
    contributions, pension, other — monthly and totals. For per-employee
    detail query the L-series vouchers with query_ledger."""
    return _needs_sync_guard(analytics.payroll, year)


@agent.tool_plain
def get_projection(year: int | None = None) -> dict:
    """Baseline full-year projection inputs: actuals to date plus default
    monthly run-rates. Apply assumption overrides yourself with calculate;
    bolagsskatt rate included (tax_rate)."""
    return _needs_sync_guard(analytics.projection_baseline, year)


@agent.tool_plain
def list_invoices() -> list[dict]:
    """All client invoices (AR) from the mirror, newest first: customer,
    dates, total, open balance."""
    return _needs_sync_guard(analytics.invoices_list)


@agent.tool_plain
def get_assets() -> dict:
    """Fixed-asset register (Anläggningsregister): every asset itemized —
    description, acquisition value & purchase date, depreciation method and
    schedule (start/end), accumulated depreciation and current book value —
    plus fleet totals. This is the itemized detail BEHIND the 12xx balance-sheet
    accounts and the 78xx depreciation P&L rows; prefer it for any
    depreciation/avskrivning question instead of inferring from the ledger.
    Supplier is not a direct field — it is only recoverable when an asset was
    booked from a supplier invoice (asset_history.supplier_invoice > 0). If
    `status.state` is 'unavailable' the company lacks the register license; if
    'not_synced', run a sync first."""
    return analytics.assets_overview()


@agent.tool_plain
def get_asset(number: str) -> dict:
    """One asset's full record plus its complete event history — the original
    acquisition and every scheduled depreciation posting, each with the linked
    ledger voucher (series/number/year) so you can tie it back to the books.
    `number` is the asset's Number from get_assets."""
    detail = analytics.asset_detail(number)
    if detail is None:
        raise ModelRetry(
            f"No asset numbered {number!r} in the register. Call get_assets to "
            "list valid asset numbers."
        )
    return detail


@agent.tool_plain
def list_supplier_invoices() -> list[dict]:
    """All supplier invoices (AP) from the mirror: supplier, dates, total,
    open balance."""
    from .. import db

    with db.session() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM supplier_invoices ORDER BY invoice_date DESC"
        )]


# ── Layer 2: power tools ───────────────────────────────────────
#
# query_ledger / calculate / run_python are shared with the verifier agent
# (change 2), so they're defined as plain functions and registered on BOTH
# agents at the bottom of this module. web/reference/sync/verify tools are
# main-agent-only.


def query_ledger(sql: str, params: list | None = None) -> dict:
    # Fresh read-only connection per call: tools may run concurrently on
    # different threads, and sqlite3 handles must never be shared across them.
    from .. import db

    conn = db.connect_readonly()
    try:
        return ledger_sql.run_query(conn, sql, params)
    except ValueError as e:
        raise ModelRetry(str(e)) from None
    finally:
        conn.close()


# Docstrings can't interpolate the schema doc, so the description is passed
# explicitly at registration instead.
QUERY_LEDGER_DESC = (
    "Run one read-only SELECT over the mirror database. Use for anything the "
    "structured tools don't cover: per-voucher payroll rows, text search, "
    "custom aggregations, cross-year comparison.\n\n"
    "Results are capped at 200 rows ({columns, rows, truncated}) — aggregate "
    "in SQL rather than paging. Positional parameters via `params` and `?`.\n\n"
    + ledger_sql.SCHEMA_DOC
)


def calculate(expression: str) -> str:
    """Exact decimal arithmetic for one-liners — use for a single computation
    that carries a conclusion; never do mental arithmetic for verdicts.
    Allowed: numbers, + - * /, parentheses, round(x, n), abs(x). Example:
    calculate("round(88000 * 0.3142, 2)") -> "27649.6". For anything with more
    than two steps (pivots, tax brackets, reconciliations) use run_python."""
    try:
        return calc.calculate(expression)
    except ValueError as e:
        raise ModelRetry(str(e)) from None


def run_python(script: str) -> dict:
    """Run a short Python script in a sandbox with read-only access to the
    mirror database. Use for anything beyond one-line arithmetic: pivot
    tables (e.g. month x category cost matrices), tax computations with
    brackets, iterative reconciliation. Available in the script's namespace:
      q(sql, params=()) -> list of tuples (read-only SELECT on the mirror)
      qd(sql, params=()) -> list of dicts
      db -> the sqlite3 connection; D -> decimal.Decimal
    Standard library only (json, statistics, datetime, collections, math...).
    No network, no filesystem writes that persist, 10s CPU limit. print() your
    results — stdout is returned. On errors the traceback comes back: fix and
    retry."""
    return sandbox.run(script)


@agent.tool_plain
def read_reference(name: str | None = None, search: str | None = None) -> dict:
    """Read the project's reference docs (prior audits and case studies with
    VERIFIED findings — e.g. correct bilförmån basis, known misbookings — plus
    the company-context and Swedish-tax reference grounding docs). Call with no
    args to list available docs with one-line summaries. Pass name to read one
    (optionally search=<regex> to return only matching sections). Check here
    before re-deriving anything a prior audit already settled."""
    if name is None:
        return {"docs": reference.list_docs()}
    try:
        return reference.read_doc(name, search)
    except ValueError as e:
        raise ModelRetry(str(e)) from None


@agent.tool_plain
async def trigger_sync() -> dict:
    """Refresh the local mirror from Fortnox (same as the UI's sync button).
    Use when the user asks for the latest data, or when last_sync predates
    today and the question concerns current state. Takes ~10-30s. Returns the
    sync result including last_sync and per-entity counts. This only refreshes
    the local read-only mirror — it never writes to Fortnox."""
    import asyncio

    from .. import sync
    from ..config import settings

    if settings.demo_mode:
        return {"status": "done", "error": None, "counts": {},
                "last_sync": "demo mode — the mirror is a static demo dataset"}
    if sync.state.get("status") == "running":
        # A sync (UI or a prior call) is already in flight — wait it out
        # instead of starting another; sync.run() would no-op via its lock.
        for _ in range(90):
            await asyncio.sleep(1)
            if sync.state.get("status") != "running":
                break
    else:
        await sync.run()  # runs to completion; no-ops via its lock if racing
    return {k: sync.state.get(k) for k in ("status", "error", "counts", "last_sync")}


@agent.tool
async def verify_draft(ctx: RunContext[AssistantDeps], question: str, draft: str) -> dict:
    """MANDATORY before finalizing any answer that contains computed numbers
    (totals, tax effects, projections, comparisons). Pass the user's question
    and your draft answer (or a compressed list of every numeric claim + how
    you derived it). An independent auditor re-derives the numbers and returns
    findings; fix every 'wrong'/'incoherent' finding before you answer, and
    mention material corrections."""
    # A failing/over-budget verifier must NOT abort the user's answer — it's a
    # safety net, not a gate. Degrade to an explicit "verification incomplete"
    # signal the main agent can relay, instead of letting the exception bubble
    # up through the stream (which reads as a hard failure to the user).
    try:
        result = await verify.verifier.run(
            f"QUESTION:\n{question}\n\nDRAFT:\n{draft}",
            model=verify.build_model_for_verifier(),
            deps=ctx.deps,
            usage_limits=verify.VERIFIER_LIMITS,
        )
        return result.output.model_dump()
    except UsageLimitExceeded as e:
        return {
            "findings": [],
            "ok": None,
            "error": (
                f"Verification incomplete — the auditor hit its budget ({e}). "
                "Proceed, but re-check the headline numbers yourself and tell "
                "the user the independent check was only partial."
            ),
        }
    except Exception as e:  # never let the verifier take down the answer
        return {
            "findings": [],
            "ok": None,
            "error": (
                f"Verification could not run ({type(e).__name__}: {e}). "
                "Proceed, but tell the user the independent check didn't complete."
            ),
        }


@agent.tool
async def web_search(ctx: RunContext[AssistantDeps], query: str, max_results: int = 5) -> list[dict]:
    """Search authoritative Swedish sources (Skatteverket, Riksgälden,
    regeringen.se, Bolagsverket, riksdagen.se, lagen.nu, BFN...) for current
    rules and rates. Use before any tax parameter becomes load-bearing.
    Returns [{title, url, snippet}]; follow up with fetch_page for full text."""
    try:
        results = await web.tavily_search(query, max_results)
    except Exception as e:
        raise ModelRetry(f"Search failed: {e}") from None
    for r in results:
        host = (urlparse(r["url"]).hostname or "").lower()
        if host:
            ctx.deps.seen_domains.add(host)
    return results


@agent.tool
async def fetch_page(ctx: RunContext[AssistantDeps], url: str) -> str:
    """Fetch one page from an allowlisted (or previously-searched) domain and
    return its readable text. Cite it as [source:URL] when used."""
    try:
        return await web.fetch_page_text(url, ctx.deps.seen_domains)
    except ValueError as e:
        raise ModelRetry(str(e)) from None
    except Exception as e:
        raise ModelRetry(f"Fetch failed: {e}") from None


# ── Shared power tools: registered on BOTH the main agent and the verifier ──
# The verifier re-derives numbers with exactly these three (change 2). Same
# underlying functions, registered on each agent so neither can drift.
for _a in (agent, verify.verifier):
    _a.tool_plain(calculate)
    _a.tool_plain(run_python)
    _a.tool_plain(query_ledger, description=QUERY_LEDGER_DESC)
