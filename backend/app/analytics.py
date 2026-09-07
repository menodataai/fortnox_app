"""Read-only analytics over the SQLite mirror. Every function here is also a
future AI-assistant tool — keep signatures simple and outputs JSON-friendly."""

import json
from datetime import date, timedelta

from . import bas, db


class NeedsSyncError(Exception):
    """The mirror is empty — run a sync first."""


# ── Period helpers ─────────────────────────────────────────────


def _financial_year(conn, year: int | None) -> dict:
    rows = [dict(r) for r in conn.execute(
        "SELECT id, from_date, to_date FROM financial_years ORDER BY from_date DESC"
    )]
    if not rows:
        raise NeedsSyncError
    today = date.today().isoformat()
    if year is None:
        for r in rows:
            if r["from_date"] <= today <= r["to_date"]:
                return r
        return rows[0]
    for r in rows:
        if r["from_date"][:4] == str(year):
            return r
    raise NeedsSyncError


def _months(fy: dict) -> list[str]:
    out = []
    y, m = int(fy["from_date"][:4]), int(fy["from_date"][5:7])
    end = fy["to_date"][:7]
    while True:
        label = f"{y:04d}-{m:02d}"
        out.append(label)
        if label >= end or len(out) >= 24:
            break
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def _account_name(number: int, description: str) -> str:
    return bas.explain(number) or description or f"Account {number}"


# ── P&L ────────────────────────────────────────────────────────


def _pnl_data(conn, fy: dict) -> dict:
    """Per-group, per-account, per-month sums for one financial year."""
    months = _months(fy)
    midx = {m: i for i, m in enumerate(months)}
    rows = conn.execute(
        "SELECT t.account, substr(t.date,1,7) AS month, SUM(t.amount) AS amt,"
        "       COALESCE(a.description,'') AS description "
        "FROM transactions t "
        "LEFT JOIN accounts a ON a.year_id = t.year_id AND a.number = t.account "
        "WHERE t.year_id = ? AND t.account BETWEEN 3000 AND 8999 "
        "GROUP BY t.account, month",
        (fy["id"],),
    ).fetchall()

    groups: dict[str, dict] = {}
    for r in rows:
        g = bas.pnl_group_for(r["account"])
        if g is None or r["month"] not in midx:
            continue
        entry = groups.setdefault(
            g.key,
            {"key": g.key, "name": g.name, "sign": g.sign,
             "monthly": [0.0] * len(months), "accounts": {}},
        )
        display = g.sign * r["amt"]
        entry["monthly"][midx[r["month"]]] += display
        acc = entry["accounts"].setdefault(
            r["account"],
            {"number": r["account"],
             "name": _account_name(r["account"], r["description"]),
             "monthly": [0.0] * len(months), "total": 0.0},
        )
        acc["monthly"][midx[r["month"]]] += display
        acc["total"] += display

    ordered = []
    for g in bas.PNL_GROUPS:
        if g.key not in groups:
            continue
        entry = groups[g.key]
        entry["total"] = round(sum(entry["monthly"]), 2)
        entry["monthly"] = [round(v, 2) for v in entry["monthly"]]
        entry["accounts"] = sorted(
            (
                {**a, "total": round(a["total"], 2),
                 "monthly": [round(v, 2) for v in a["monthly"]]}
                for a in entry["accounts"].values()
            ),
            key=lambda a: -abs(a["total"]),
        )
        del entry["sign"]
        ordered.append(entry)

    def total(key: str) -> float:
        return next((g["total"] for g in ordered if g["key"] == key), 0.0)

    revenue = total("revenue")
    op_costs = sum(total(k) for k in ("direct", "external", "personnel", "depreciation", "other_op"))
    financial_net = total("financial")
    profit_monthly = [0.0] * len(months)
    for g in ordered:
        s = 1 if g["key"] in ("revenue", "financial") else -1
        if g["key"] == "tax":
            continue
        for i, v in enumerate(g["monthly"]):
            profit_monthly[i] += s * v

    return {
        "year": int(fy["from_date"][:4]),
        "from_date": fy["from_date"],
        "to_date": fy["to_date"],
        "months": months,
        "groups": ordered,
        "revenue_total": round(revenue, 2),
        "costs_total": round(op_costs, 2),
        "financial_net": round(financial_net, 2),
        "profit_before_tax": round(revenue - op_costs + financial_net, 2),
        "profit_monthly": [round(v, 2) for v in profit_monthly],
    }


def pnl(year: int | None = None) -> dict:
    with db.session() as conn:
        fy = _financial_year(conn, year)
        return _pnl_data(conn, fy)


# ── Dashboard ──────────────────────────────────────────────────


def _cash(conn, fy: dict) -> float:
    row = conn.execute(
        "SELECT COALESCE((SELECT SUM(ib) FROM accounts"
        "   WHERE year_id = ? AND number BETWEEN 1900 AND 1999), 0)"
        " + COALESCE((SELECT SUM(amount) FROM transactions"
        "   WHERE year_id = ? AND account BETWEEN 1900 AND 1999), 0) AS cash",
        (fy["id"], fy["id"]),
    ).fetchone()
    return round(row["cash"], 2)


def _elapsed(months: list[str]) -> int:
    now = date.today().isoformat()[:7]
    return sum(1 for m in months if m <= now)


def dashboard_summary(year: int | None = None) -> dict:
    today = date.today().isoformat()
    soon = (date.today() + timedelta(days=14)).isoformat()
    with db.session() as conn:
        fy = _financial_year(conn, year)
        p = _pnl_data(conn, fy)

        cash = _cash(conn, fy)

        open_invoices = [dict(r) for r in conn.execute(
            "SELECT * FROM invoices WHERE cancelled = 0 AND balance > 0 ORDER BY due_date"
        )]
        overdue = [i for i in open_invoices if (i["due_date"] or "9999") < today]
        supplier_due = [dict(r) for r in conn.execute(
            "SELECT * FROM supplier_invoices WHERE cancelled = 0 AND balance > 0"
            " AND due_date <= ? ORDER BY due_date",
            (soon,),
        )]

        attention = []
        for i in overdue:
            attention.append({
                "level": "critical",
                "title": f"Invoice #{i['document_number']} · {i['customer_name']} · {i['balance']:,.0f} kr",
                "detail": f"Overdue — was due {i['due_date']}",
            })
        for i in open_invoices:
            if i not in overdue:
                attention.append({
                    "level": "info",
                    "title": f"Invoice #{i['document_number']} · {i['customer_name']} · {i['balance']:,.0f} kr",
                    "detail": f"Sent {i['invoice_date']}, due {i['due_date']}",
                })
        for s in supplier_due:
            attention.append({
                "level": "warning",
                "title": f"Supplier invoice · {s['supplier_name']} · {s['balance']:,.0f} kr",
                "detail": f"Due {s['due_date']}",
            })

        monthly = {
            "months": p["months"],
            "revenue": p["months"] and next(
                (g["monthly"] for g in p["groups"] if g["key"] == "revenue"),
                [0.0] * len(p["months"]),
            ),
            "costs": [0.0] * len(p["months"]),
        }
        for g in p["groups"]:
            if g["key"] in ("direct", "external", "personnel", "depreciation", "other_op"):
                monthly["costs"] = [
                    round(a + b, 2) for a, b in zip(monthly["costs"], g["monthly"])
                ]

        company = db.get_meta_json(conn, "company", {})
        return {
            "year": p["year"],
            "company_name": company.get("CompanyName", ""),
            "currency": "SEK",
            "revenue_ytd": p["revenue_total"],
            "costs_ytd": p["costs_total"],
            "profit_ytd": p["profit_before_tax"],
            "cash": cash,
            "outstanding_total": round(sum(i["balance"] for i in open_invoices), 2),
            "outstanding_count": len(open_invoices),
            "overdue_total": round(sum(i["balance"] for i in overdue), 2),
            "overdue_count": len(overdue),
            "monthly": monthly,
            "attention": attention[:8],
            "last_sync": db.get_meta(conn, "last_sync"),
        }


# ── Account explorer ───────────────────────────────────────────


def account_detail(number: int, year: int | None = None) -> dict:
    with db.session() as conn:
        fy = _financial_year(conn, year)
        acct = conn.execute(
            "SELECT * FROM accounts WHERE year_id = ? AND number = ?",
            (fy["id"], number),
        ).fetchone()

        rows = conn.execute(
            "SELECT series, voucher_number, account, date, description, amount"
            " FROM transactions WHERE year_id = ? AND account = ? ORDER BY date, id",
            (fy["id"], number),
        ).fetchall()

        g = bas.pnl_group_for(number)
        sign = g.sign if g else 1
        is_balance = number < 3000
        ib = float(acct["ib"]) if acct else 0.0

        months = _months(fy)
        monthly = [0.0] * len(months)
        midx = {m: i for i, m in enumerate(months)}

        txns = []
        running = ib if is_balance else 0.0
        for r in rows:
            running += r["amount"]
            m = r["date"][:7]
            if m in midx:
                monthly[midx[m]] += sign * r["amount"]
            txns.append({
                "date": r["date"],
                "series": r["series"],
                "voucher_number": r["voucher_number"],
                "description": r["description"],
                "amount": round(sign * r["amount"], 2) if not is_balance else round(r["amount"], 2),
                "running": round(running if is_balance else sign * running, 2),
            })
        txns.reverse()  # newest first

        movement = round(sum(r["amount"] for r in rows), 2)
        active_months = [v for v in monthly if abs(v) > 0.005] or [0]
        return {
            "year": int(fy["from_date"][:4]),
            "number": number,
            "name": (acct["description"] if acct else "") or f"Account {number}",
            "explain": bas.explain(number),
            "group": g.name if g else ("Assets" if number < 2000 else "Equity & liabilities"),
            "is_balance_account": is_balance,
            "ib": round(ib, 2),
            "ub": round(ib + movement, 2) if is_balance else None,
            "period_total": round(sign * movement, 2) if not is_balance else movement,
            "monthly_average": round(sum(active_months) / len(active_months), 2),
            "months": months,
            "monthly": [round(v, 2) for v in monthly],
            "transaction_count": len(txns),
            "transactions": txns,
        }


def voucher_detail(series: str, number: int, year: int | None = None) -> dict:
    with db.session() as conn:
        fy = _financial_year(conn, year)
        ver = conn.execute(
            "SELECT * FROM vouchers WHERE year_id = ? AND series = ? AND number = ?",
            (fy["id"], series, number),
        ).fetchone()
        rows = conn.execute(
            "SELECT t.*, COALESCE(a.description,'') AS acct_desc FROM transactions t"
            " LEFT JOIN accounts a ON a.year_id = t.year_id AND a.number = t.account"
            " WHERE t.year_id = ? AND t.series = ? AND t.voucher_number = ?"
            " ORDER BY t.id",
            (fy["id"], series, number),
        ).fetchall()
        return {
            "series": series,
            "number": number,
            "date": ver["date"] if ver else (rows[0]["date"] if rows else ""),
            "description": ver["description"] if ver else "",
            "rows": [
                {
                    "account": r["account"],
                    "name": _account_name(r["account"], r["acct_desc"]),
                    "debit": round(r["amount"], 2) if r["amount"] > 0 else None,
                    "credit": round(-r["amount"], 2) if r["amount"] < 0 else None,
                }
                for r in rows
            ],
        }


# ── Cost structure ─────────────────────────────────────────────

COST_KEYS = ("direct", "external", "personnel", "depreciation", "other_op")


def _classify_recurrence(monthly: list[float], elapsed: int) -> dict | None:
    """Detect monthly/quarterly recurring spend from an account's monthly totals."""
    if elapsed < 3:
        return None
    vals = monthly[:elapsed]
    active_idx = [i for i, v in enumerate(vals) if abs(v) > 1]
    active = [vals[i] for i in active_idx]
    if len(active) >= max(3, round(0.7 * elapsed)):
        med = sorted(active)[len(active) // 2]
        first = active[0]
        last = active[-1]
        trend = (last - first) / abs(first) if abs(first) > 1 else 0.0
        return {"frequency": "Monthly", "per_month": round(med, 2), "trend": round(trend, 3)}
    if (
        len(active_idx) >= 2
        and elapsed >= 5
        and all(2 <= b - a <= 4 for a, b in zip(active_idx, active_idx[1:]))
    ):
        return {"frequency": "Quarterly", "per_month": round(sum(active) / elapsed, 2), "trend": 0.0}
    return None


def cost_structure(year: int | None = None) -> dict:
    with db.session() as conn:
        fy = _financial_year(conn, year)
        p = _pnl_data(conn, fy)
        elapsed = max(1, _elapsed(p["months"]))
        cost_groups = [g for g in p["groups"] if g["key"] in COST_KEYS]
        total_costs = round(sum(g["total"] for g in cost_groups), 2)

        # Categories: personnel as one block, every other cost account on its own
        categories: list[dict] = []
        recurring: list[dict] = []
        personnel = next((g for g in cost_groups if g["key"] == "personnel"), None)
        if personnel and personnel["total"]:
            categories.append({
                "label": "Personnel — salaries, employer tax, pension",
                "account": None,
                "total": personnel["total"],
            })
            info = _classify_recurrence(personnel["monthly"], elapsed)
            if info:
                recurring.append({
                    "label": "Salaries + employer tax + pension",
                    "account": "70xx–76xx", **info,
                })
        for g in cost_groups:
            if g["key"] == "personnel":
                continue
            for a in g["accounts"]:
                if abs(a["total"]) < 1:
                    continue
                categories.append({"label": a["name"], "account": a["number"], "total": a["total"]})
                info = _classify_recurrence(a["monthly"], elapsed)
                if info and info["per_month"] > 10:
                    recurring.append({"label": a["name"], "account": a["number"], **info})
        categories.sort(key=lambda c: -c["total"])
        if len(categories) > 12:
            rest = categories[12:]
            categories = categories[:12] + [{
                "label": f"Other ({len(rest)} smaller accounts)",
                "account": None,
                "total": round(sum(c["total"] for c in rest), 2),
            }]
        for c in categories:
            c["share"] = round(c["total"] / total_costs, 4) if total_costs else 0

        # One-off outliers: cost transactions well above their account's norm
        oneoffs: list[dict] = []
        rows = conn.execute(
            "SELECT account, date, description, amount, series, voucher_number"
            " FROM transactions WHERE year_id = ? AND account BETWEEN 4000 AND 7999"
            " AND amount > 4000 ORDER BY amount DESC LIMIT 200",
            (fy["id"],),
        ).fetchall()
        medians: dict[int, float] = {}
        for r in conn.execute(
            "SELECT account, amount FROM transactions"
            " WHERE year_id = ? AND account BETWEEN 4000 AND 7999 AND amount > 0",
            (fy["id"],),
        ):
            medians.setdefault(r["account"], []).append(r["amount"])  # type: ignore[arg-type]
        medians = {k: sorted(v)[len(v) // 2] for k, v in medians.items()}
        for r in rows:
            med = medians.get(r["account"], 0)
            if 7000 <= r["account"] <= 7699:
                continue  # salaries are recurring by nature
            if r["amount"] >= max(8000, 3 * med):
                oneoffs.append({
                    "date": r["date"], "account": r["account"],
                    "description": r["description"], "amount": round(r["amount"], 2),
                    "series": r["series"], "voucher_number": r["voucher_number"],
                })
        oneoffs = oneoffs[:6]

        burn = round(sum(r["per_month"] for r in recurring), 2)
        recurring.sort(key=lambda r: -r["per_month"])
        cash = _cash(conn, fy)
        return {
            "year": p["year"],
            "months": p["months"],
            "elapsed_months": elapsed,
            "total_costs": total_costs,
            "monthly_costs": [
                round(sum(g["monthly"][i] for g in cost_groups), 2)
                for i in range(len(p["months"]))
            ],
            "categories": categories,
            "recurring": recurring,
            "burn_per_month": burn,
            "cash": cash,
            "runway_months": round(cash / burn, 1) if burn > 0 else None,
            "oneoff_total": round(sum(o["amount"] for o in oneoffs), 2),
            "oneoffs": oneoffs,
        }


# ── Clients & invoices ─────────────────────────────────────────


def clients_overview(year: int | None = None) -> dict:
    today = date.today().isoformat()
    with db.session() as conn:
        fy = _financial_year(conn, year)
        invs = [dict(r) for r in conn.execute(
            "SELECT * FROM invoices WHERE cancelled = 0 ORDER BY invoice_date DESC"
        )]
        fy_invs = [i for i in invs if fy["from_date"] <= (i["invoice_date"] or "") <= fy["to_date"]]
        total_fy = round(sum(i["total"] for i in fy_invs), 2)

        by_client: dict[str, dict] = {}
        for i in invs:
            c = by_client.setdefault(i["customer_name"] or "Unknown", {
                "name": i["customer_name"] or "Unknown",
                "invoiced_fy": 0.0, "count_fy": 0, "outstanding": 0.0,
                "pay_days": [], "last_invoice_date": i["invoice_date"],
                "last_invoice_number": i["document_number"], "invoiced_alltime": 0.0,
            })
            c["invoiced_alltime"] += i["total"]
            if i in fy_invs:
                c["invoiced_fy"] += i["total"]
                c["count_fy"] += 1
            c["outstanding"] += max(0.0, i["balance"])
            if i["final_pay_date"] and i["invoice_date"]:
                d0 = date.fromisoformat(i["invoice_date"][:10])
                d1 = date.fromisoformat(i["final_pay_date"][:10])
                c["pay_days"].append((d1 - d0).days)

        clients = []
        for c in by_client.values():
            clients.append({
                "name": c["name"],
                "invoiced_fy": round(c["invoiced_fy"], 2),
                "invoiced_alltime": round(c["invoiced_alltime"], 2),
                "count_fy": c["count_fy"],
                "outstanding": round(c["outstanding"], 2),
                "share_fy": round(c["invoiced_fy"] / total_fy, 4) if total_fy else 0,
                "avg_days_to_pay": round(sum(c["pay_days"]) / len(c["pay_days"]))
                if c["pay_days"] else None,
                "last_invoice_date": c["last_invoice_date"],
                "last_invoice_number": c["last_invoice_number"],
                "active": c["invoiced_fy"] > 0,
            })
        clients.sort(key=lambda c: (-c["invoiced_fy"], -c["invoiced_alltime"]))

        open_fy = [i for i in invs if i["balance"] > 0]
        all_days = [d for c in by_client.values() for d in c["pay_days"]]
        top_share = clients[0]["share_fy"] if clients else 0

        def status(i: dict) -> str:
            if i["balance"] <= 0:
                return "paid"
            return "overdue" if (i["due_date"] or "9999") < today else "open"

        return {
            "year": int(fy["from_date"][:4]),
            "invoiced_total": total_fy,
            "invoice_count": len(fy_invs),
            "outstanding_total": round(sum(i["balance"] for i in open_fy), 2),
            "outstanding_count": len(open_fy),
            "avg_days_to_pay": round(sum(all_days) / len(all_days)) if all_days else None,
            "active_clients": sum(1 for c in clients if c["active"]),
            "top_client_share": top_share,
            "clients": clients,
            "invoices": [{**i, "status": status(i)} for i in fy_invs],
        }


# ── Payroll ────────────────────────────────────────────────────

PAYROLL_BUCKETS = [
    ("gross", "Gross salaries", 7000, 7399),
    ("pension", "Occupational pension (tjänstepension)", 7400, 7499),
    ("social", "Employer contributions & payroll taxes", 7500, 7599),
    ("other", "Other personnel costs", 7600, 7699),
]


def payroll(year: int | None = None) -> dict:
    with db.session() as conn:
        fy = _financial_year(conn, year)
        months = _months(fy)
        midx = {m: i for i, m in enumerate(months)}
        rows = conn.execute(
            "SELECT account, substr(date,1,7) AS m, SUM(amount) AS amt FROM transactions"
            " WHERE year_id = ? AND account BETWEEN 7000 AND 7699 GROUP BY account, m",
            (fy["id"],),
        ).fetchall()

        buckets = {
            key: {"key": key, "label": label, "monthly": [0.0] * len(months), "total": 0.0}
            for key, label, _, _ in PAYROLL_BUCKETS
        }
        for r in rows:
            if r["m"] not in midx:
                continue
            for key, _, lo, hi in PAYROLL_BUCKETS:
                if lo <= r["account"] <= hi:
                    buckets[key]["monthly"][midx[r["m"]]] += r["amt"]
                    buckets[key]["total"] += r["amt"]
                    break

        total = sum(b["total"] for b in buckets.values())
        active = [
            i for i in range(len(months))
            if buckets["gross"]["monthly"][i] > 1
        ]
        avg_month = {
            key: round(sum(b["monthly"][i] for i in active) / len(active), 2) if active else 0.0
            for key, b in buckets.items()
        }
        avg_month["total"] = round(sum(avg_month.values()), 2)
        gross = buckets["gross"]["total"]
        for b in buckets.values():
            b["total"] = round(b["total"], 2)
            b["monthly"] = [round(v, 2) for v in b["monthly"]]
        return {
            "year": int(fy["from_date"][:4]),
            "months": months,
            "buckets": [buckets[k] for k, _, _, _ in PAYROLL_BUCKETS],
            "total": round(total, 2),
            "avg_month": avg_month,
            "multiplier": round(total / gross, 2) if gross > 1 else None,
            "monthly_total": [
                round(sum(b["monthly"][i] for b in buckets.values()), 2)
                for i in range(len(months))
            ],
        }


# ── Year projection ────────────────────────────────────────────


def projection_baseline(year: int | None = None) -> dict:
    """Actuals + sensible defaults; the frontend does the interactive arithmetic."""
    with db.session() as conn:
        fy = _financial_year(conn, year)
        p = _pnl_data(conn, fy)
        elapsed = _elapsed(p["months"])
        revenue = next(
            (g["monthly"] for g in p["groups"] if g["key"] == "revenue"),
            [0.0] * len(p["months"]),
        )
        costs = [0.0] * len(p["months"])
        for g in p["groups"]:
            if g["key"] in COST_KEYS:
                costs = [round(a + b, 2) for a, b in zip(costs, g["monthly"])]

        def avg_recent(values: list[float]) -> float:
            done = [v for v in values[:elapsed]]
            recent = [v for v in done[-4:-1] or done if v > 0] or [v for v in done if v > 0]
            return round(sum(recent) / len(recent), 2) if recent else 0.0

        return {
            "year": p["year"],
            "months": p["months"],
            "elapsed_months": elapsed,
            "actual_revenue": revenue,
            "actual_costs": costs,
            "revenue_ytd": p["revenue_total"],
            "costs_ytd": p["costs_total"],
            "financial_net": p["financial_net"],
            "defaults": {
                "revenue_per_month": avg_recent(revenue),
                "costs_per_month": avg_recent(costs),
                "oneoff_costs": 0,
            },
            "tax_rate": 0.206,
        }


# ── Financial years & balance sheet (F2b / AI tools) ──────────


def _has_detail(conn, year_id: int) -> bool:
    row = conn.execute(
        "SELECT EXISTS(SELECT 1 FROM transactions WHERE year_id = ?) AS e", (year_id,)
    ).fetchone()
    return bool(row["e"])


def financial_years() -> list[dict]:
    """All mirrored years, flagging which ones have transaction detail
    (older years may be balances-only — a known mirror limitation)."""
    with db.session() as conn:
        rows = conn.execute(
            "SELECT id, from_date, to_date FROM financial_years ORDER BY from_date"
        ).fetchall()
        if not rows:
            raise NeedsSyncError
        return [
            {
                "year": int(r["from_date"][:4]),
                "from_date": r["from_date"],
                "to_date": r["to_date"],
                "has_transaction_detail": _has_detail(conn, r["id"]),
            }
            for r in rows
        ]


def balance_sheet(year: int | None = None, to_date: str | None = None) -> dict:
    """Balansräkning: IB + movement → UB per balance account (1xxx/2xxx).

    Liability-side amounts are sign-flipped so both sides read positive.
    For balances-only years (no transaction detail) the stored UB is used and
    `to_date` is ignored. Mid-period sheets get a computed "period result not
    yet booked" line so the sides tie.
    """
    with db.session() as conn:
        fy = _financial_year(conn, year)
        has_detail = _has_detail(conn, fy["id"])
        end = min(to_date, fy["to_date"]) if to_date else fy["to_date"]

        if has_detail:
            rows = conn.execute(
                "SELECT a.number, a.description, a.ib,"
                " COALESCE((SELECT SUM(t.amount) FROM transactions t"
                "   WHERE t.year_id = a.year_id AND t.account = a.number"
                "   AND t.date <= ?), 0) AS movement"
                " FROM accounts a WHERE a.year_id = ? AND a.number < 3000"
                " ORDER BY a.number",
                (end, fy["id"]),
            ).fetchall()
            accounts = [
                {"number": r["number"], "description": r["description"],
                 "ib": r["ib"], "ub": r["ib"] + r["movement"]}
                for r in rows
            ]
            pnl_sum = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) AS s FROM transactions"
                " WHERE year_id = ? AND account >= 3000 AND date <= ?",
                (fy["id"], end),
            ).fetchone()["s"]
            period_result = round(-pnl_sum, 2)  # profit positive
        else:
            end = fy["to_date"]
            rows = conn.execute(
                "SELECT number, description, ib, ub FROM accounts"
                " WHERE year_id = ? AND number < 3000 ORDER BY number",
                (fy["id"],),
            ).fetchall()
            accounts = [dict(r) for r in rows]
            period_result = 0.0

        def side(lo: int, hi: int, sign: int) -> dict:
            accs = [
                {
                    "number": a["number"],
                    "name": _account_name(a["number"], a["description"]),
                    "ib": round(sign * a["ib"], 2),
                    "movement": round(sign * (a["ub"] - a["ib"]), 2),
                    "ub": round(sign * a["ub"], 2),
                }
                for a in accounts
                if lo <= a["number"] <= hi and (abs(a["ib"]) > 0.005 or abs(a["ub"]) > 0.005)
            ]
            return {"accounts": accs, "total_ub": round(sum(a["ub"] for a in accs), 2)}

        assets = side(1000, 1999, 1)
        eq_liab = side(2000, 2999, -1)
        return {
            "year": int(fy["from_date"][:4]),
            "from_date": fy["from_date"],
            "to_date": end,
            "has_transaction_detail": has_detail,
            "balances_only": not has_detail,
            "assets": assets,
            "equity_and_liabilities": eq_liab,
            # mid-period: profit lives on 3xxx-8xxx until booked to 2099/8999
            "period_result_not_yet_booked": period_result,
            "equity_side_total_incl_result": round(eq_liab["total_ub"] + period_result, 2),
        }


def invoices_list() -> list[dict]:
    with db.session() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM invoices ORDER BY invoice_date DESC, document_number DESC"
        )]


# ── Fixed-asset register (Anläggningsregister) ────────────────────
# Accumulated depreciation is summed from scheduled-depreciation history events
# (event_id = 3); book value = acquisition_value − accumulated. This should
# reconcile with the 12x9 accumulated-depreciation account on the balance sheet.

def _accumulated_depreciation(conn, number: str) -> float:
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS s FROM asset_history "
        "WHERE asset_number = ? AND event_id = 3",
        (str(number),),
    ).fetchone()
    return round(row["s"], 2)


def assets_overview() -> dict:
    """The whole register: every asset with acquisition value/date, depreciation
    schedule, accumulated depreciation and book value, plus fleet totals.
    `status` reports whether the module is licensed/synced."""
    with db.session() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM assets ORDER BY acquisition_date, number"
        )]
        for a in rows:
            acc = _accumulated_depreciation(conn, a["number"])
            a["accumulated_depreciation"] = acc
            a["book_value"] = round((a["acquisition_value"] or 0) - acc, 2)
        totals = {
            "count": len(rows),
            "acquisition_value": round(sum(a["acquisition_value"] or 0 for a in rows), 2),
            "accumulated_depreciation": round(sum(a["accumulated_depreciation"] for a in rows), 2),
            "book_value": round(sum(a["book_value"] for a in rows), 2),
        }
        status = db.get_meta_json(conn, "assets_status", {"state": "not_synced"})
        return {"assets": rows, "totals": totals, "status": status}


def asset_detail(number: str) -> dict | None:
    """One asset's full record including its event history (acquisitions and
    every depreciation posting with the linked ledger voucher). Returns None
    when no asset with that number exists in the mirror."""
    with db.session() as conn:
        row = conn.execute(
            "SELECT * FROM assets WHERE number = ?", (str(number),)
        ).fetchone()
        if row is None:
            return None
        asset = dict(row)
        acc = _accumulated_depreciation(conn, number)
        asset["accumulated_depreciation"] = acc
        asset["book_value"] = round((asset["acquisition_value"] or 0) - acc, 2)
        asset["history"] = [dict(r) for r in conn.execute(
            "SELECT * FROM asset_history WHERE asset_number = ? ORDER BY date, history_id",
            (str(number),),
        )]
        return asset
