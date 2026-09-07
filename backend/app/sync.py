"""Fortnox → SQLite mirror sync.

A full sync is only ~6–10 API calls thanks to the SIE export (one file per
financial year contains the entire ledger). Sync state is kept in-process so
the UI can poll progress; only one sync runs at a time.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

import httpx

from . import db, sie
from .fortnox.client import fortnox

# Assets is a licensed module: without the license Fortnox returns 403, without
# the scope 400. Either way we skip the step rather than fail the whole sync.
_ASSET_SKIP_STATUS = {400, 403}

log = logging.getLogger("sync")

state: dict = {"status": "idle", "step": "", "error": None, "counts": {}, "last_sync": None}
_lock = asyncio.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def run() -> None:
    if _lock.locked():
        return
    async with _lock:
        state.update(status="running", step="starting", error=None, counts={})
        try:
            await _sync_all()
            with db.session() as conn:
                db.set_meta(conn, "last_sync", _now())
            state.update(status="done", step="", last_sync=_now())
        except Exception as exc:  # surface any failure to the UI
            log.exception("sync failed")
            detail = str(exc)
            body = getattr(getattr(exc, "response", None), "text", "")
            if body:
                detail = f"{detail} — Fortnox says: {body[:300]}"
            state.update(status="error", error=detail)


async def _sync_all() -> None:
    counts = state["counts"]

    state["step"] = "company information"
    company = (await fortnox.get("/companyinformation"))["CompanyInformation"]
    with db.session() as conn:
        db.set_meta(conn, "company", json.dumps(company))

    state["step"] = "financial years"
    years = (await fortnox.get("/financialyears"))["FinancialYears"]
    with db.session() as conn:
        conn.execute("DELETE FROM financial_years")
        for y in years:
            conn.execute(
                "INSERT OR REPLACE INTO financial_years (id, from_date, to_date) VALUES (?,?,?)",
                (y["Id"], y["FromDate"], y["ToDate"]),
            )
    counts["financial_years"] = len(years)

    # Ledger: newest two financial years cover every current screen
    for y in sorted(years, key=lambda y: y["FromDate"], reverse=True)[:2]:
        state["step"] = f"ledger {y['FromDate'][:4]}"
        data = await fortnox.get_bytes("/sie/4", {"financialyear": y["Id"]})
        parsed = sie.parse(data)
        _store_ledger(y["Id"], parsed)
        counts[f"vouchers_{y['FromDate'][:4]}"] = len(parsed.vouchers)

    state["step"] = "invoices"
    invoices = await _fetch_all("/invoices", "Invoices")
    with db.session() as conn:
        conn.execute("DELETE FROM invoices")
        for inv in invoices:
            conn.execute(
                "INSERT OR REPLACE INTO invoices (document_number, customer_number,"
                " customer_name, invoice_date, due_date, final_pay_date, total,"
                " balance, currency, cancelled) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    str(inv.get("DocumentNumber")),
                    inv.get("CustomerNumber"),
                    inv.get("CustomerName"),
                    inv.get("InvoiceDate"),
                    inv.get("DueDate"),
                    inv.get("FinalPayDate"),
                    float(inv.get("Total") or 0),
                    float(inv.get("Balance") or 0),
                    inv.get("Currency") or "SEK",
                    1 if inv.get("Cancelled") else 0,
                ),
            )
    counts["invoices"] = len(invoices)

    state["step"] = "supplier invoices"
    sup = await _fetch_all("/supplierinvoices", "SupplierInvoices")
    with db.session() as conn:
        conn.execute("DELETE FROM supplier_invoices")
        for s in sup:
            conn.execute(
                "INSERT OR REPLACE INTO supplier_invoices (given_number, supplier_name,"
                " invoice_date, due_date, total, balance, currency, cancelled)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (
                    str(s.get("GivenNumber")),
                    s.get("SupplierName"),
                    s.get("InvoiceDate"),
                    s.get("DueDate"),
                    float(s.get("Total") or 0),
                    float(s.get("Balance") or 0),
                    s.get("Currency") or "SEK",
                    1 if s.get("Cancelled") in (True, "true", 1) else 0,
                ),
            )
    counts["supplier_invoices"] = len(sup)

    state["step"] = "assets"
    await _sync_assets(counts)


async def _sync_assets(counts: dict) -> None:
    """Mirror the fixed-asset register (Anläggningsregister). Skipped gracefully
    when the company lacks the license/scope so it never breaks a sync."""
    try:
        types = (await fortnox.asset_types()).get("Types", [])
        summaries = await _fetch_all("/assets/", "Assets")
        # The list view omits depreciation method, notes and the event history;
        # fetch each asset's detail for the full record.
        details = [await fortnox.asset(a["Number"]) for a in summaries]
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in _ASSET_SKIP_STATUS:
            reason = exc.response.text[:200]
            log.warning("asset register unavailable (%s) — skipping: %s",
                        exc.response.status_code, reason)
            with db.session() as conn:
                db.set_meta(conn, "assets_status", json.dumps(
                    {"state": "unavailable", "http": exc.response.status_code,
                     "reason": reason}))
            counts["assets"] = 0
            return
        raise

    history_rows = 0
    with db.session() as conn:
        conn.execute("DELETE FROM asset_types")
        conn.execute("DELETE FROM assets")
        conn.execute("DELETE FROM asset_history")

        for t in types:
            conn.execute(
                "INSERT OR REPLACE INTO asset_types (id, number, description, type, notes)"
                " VALUES (?,?,?,?,?)",
                (t.get("Id"), t.get("Number"), t.get("Description"),
                 t.get("Type"), t.get("Notes") or ""),
            )

        for a in details:
            conn.execute(
                "INSERT OR REPLACE INTO assets (number, id, description, status, type_id,"
                " type_name, acquisition_value, acquisition_date, acquisition_start,"
                " depreciation_method, depreciation_final, depreciated_to,"
                " depreciate_to_residual_value, manual_ob, notes, reference, brand,"
                " cost_center, project, asset_group, placement, room, department,"
                " insured_with, insured_number)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    str(a.get("Number")),
                    a.get("Id"),
                    a.get("Description") or "",
                    a.get("Status") or "",
                    a.get("TypeId"),
                    a.get("Type") or "",
                    float(a.get("AcquisitionValue") or 0),
                    a.get("AcquisitionDate"),
                    a.get("AcquisitionStart"),
                    a.get("DepreciationMethod"),
                    a.get("DepreciationFinal"),
                    a.get("DepreciatedTo"),
                    float(a.get("DepreciateToResidualValue") or 0),
                    float(a.get("ManualOb") or 0),
                    a.get("Notes") or "",
                    a.get("Reference") or "",
                    a.get("Brand") or "",
                    a.get("CostCenter") or "",
                    a.get("Project") or "",
                    a.get("Group") or "",
                    a.get("Placement") or "",
                    a.get("Room") or "",
                    a.get("Department") or "",
                    a.get("InsuredWith") or "",
                    a.get("InsuredNumber") or "",
                ),
            )
            for h in a.get("History") or []:
                conn.execute(
                    "INSERT INTO asset_history (asset_number, history_id, date, event_id,"
                    " amount, user_name, notes, voucher_series, voucher_number,"
                    " voucher_year, supplier_invoice) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        str(a.get("Number")),
                        h.get("Id"),
                        h.get("Date"),
                        h.get("EventId"),
                        float(h.get("Amount") or 0),
                        h.get("UserName") or "",
                        h.get("Notes") or "",
                        h.get("VoucherSeries"),
                        h.get("VoucherNumber"),
                        h.get("VoucherYear"),
                        int(h.get("SupplierInvoice") or 0),
                    ),
                )
                history_rows += 1

        db.set_meta(conn, "assets_status", json.dumps(
            {"state": "ok", "count": len(details)}))

    counts["assets"] = len(details)
    counts["asset_history"] = history_rows


def _store_ledger(year_id: int, parsed: sie.ParsedSIE) -> None:
    with db.session() as conn:
        conn.execute("DELETE FROM accounts WHERE year_id = ?", (year_id,))
        conn.execute("DELETE FROM vouchers WHERE year_id = ?", (year_id,))
        conn.execute("DELETE FROM transactions WHERE year_id = ?", (year_id,))

        seen: set[int] = set(parsed.accounts)
        seen.update(parsed.ib, parsed.ub, parsed.res)
        for acct in seen:
            conn.execute(
                "INSERT INTO accounts (year_id, number, description, ib, ub) VALUES (?,?,?,?,?)",
                (
                    year_id,
                    acct,
                    parsed.accounts.get(acct, ""),
                    parsed.ib.get(acct, 0.0),
                    # P&L accounts have no #UB; #RES is their period balance
                    parsed.ub.get(acct, parsed.res.get(acct, 0.0)),
                ),
            )

        for ver in parsed.vouchers:
            conn.execute(
                "INSERT OR REPLACE INTO vouchers (year_id, series, number, date, description)"
                " VALUES (?,?,?,?,?)",
                (year_id, ver.series, ver.number, ver.date, ver.text),
            )
            for t in ver.trans:
                conn.execute(
                    "INSERT INTO transactions (year_id, series, voucher_number, account,"
                    " date, description, amount) VALUES (?,?,?,?,?,?,?)",
                    (
                        year_id,
                        ver.series,
                        ver.number,
                        t.account,
                        t.date or ver.date,
                        t.text or ver.text,
                        t.amount,
                    ),
                )


async def _fetch_all(path: str, key: str) -> list[dict]:
    results: list[dict] = []
    page = 1
    while page <= 20:
        data = await fortnox.get(path, {"page": page, "limit": 500})
        results.extend(data.get(key, []))
        meta = data.get("MetaInformation", {})
        if page >= int(meta.get("@TotalPages") or 1):
            break
        page += 1
    return results
