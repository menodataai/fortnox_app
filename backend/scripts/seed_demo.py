"""Seed the demo mirror with a fictional Swedish AB — no Fortnox account needed.

Generates two coherent fiscal years (2025 + 2026 YTD) of double-entry
bookkeeping for **Nordvind Konsult AB**, a fictional two-person AI-consulting
aktiebolag in Umeå: customer invoices with VAT, supplier invoices, payroll with
withheld tax and arbetsgivaravgifter, quarterly VAT settlements, depreciation
with a matching fixed-asset register, year-end closing and a spring dividend.

Every voucher balances to zero, opening balances tie, and the bank account
never goes negative — asserted at build time, so the dashboard, P&L, balance
sheet and AI chat all reconcile.

Run from backend/:  python -m scripts.seed_demo
Then start the app with DEMO_MODE=1 — data lands in backend/data-demo/,
your real mirror is never touched.
"""

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

os.environ["DEMO_MODE"] = "1"  # before app imports: pins DATA_DIR to data-demo/

from app import db  # noqa: E402
from app.config import DATA_DIR  # noqa: E402

TODAY = date(2026, 8, 5) if "--frozen" in sys.argv else date.today()

COMPANY = {
    "CompanyName": "Nordvind Konsult AB",
    "OrganizationNumber": "559012-3456",  # fictional
    "Address": "Storgatan 24",
    "ZipCode": "903 26",
    "City": "Umeå",
    "CountryCode": "SE",
    "Email": "hej@nordvindkonsult.example",
}

VAT = 0.25
AGA = 0.3142          # arbetsgivaravgifter
SLP = 0.2426          # särskild löneskatt on pension premiums
TAX = 0.206           # bolagsskatt

ACCOUNTS = {
    1220: "Inventarier och verktyg",
    1229: "Ackumulerade avskrivningar inventarier",
    1510: "Kundfordringar",
    1930: "Företagskonto",
    2081: "Aktiekapital",
    2091: "Balanserad vinst eller förlust",
    2098: "Vinst eller förlust från föregående år",
    2099: "Årets resultat",
    2440: "Leverantörsskulder",
    2510: "Skatteskulder",
    2610: "Utgående moms 25%",
    2641: "Ingående moms",
    2650: "Redovisningskonto för moms",
    2710: "Personalskatt",
    2731: "Avräkning lagstadgade sociala avgifter",
    2898: "Outtagen vinstutdelning",
    2941: "Beräknad upplupen särskild löneskatt",
    3041: "Försäljning tjänster 25% moms",
    5010: "Lokalhyra",
    5410: "Förbrukningsinventarier",
    5810: "Resekostnader",
    5910: "Annonsering och marknadsföring",
    6070: "Representation",
    6212: "Mobiltelefon och internet",
    6310: "Företagsförsäkringar",
    6530: "Redovisningstjänster",
    6540: "IT-tjänster och programvara",
    6570: "Bankkostnader",
    7210: "Löner till tjänstemän",
    7220: "Löner till företagsledare",
    7412: "Premier för tjänstepension",
    7510: "Lagstadgade arbetsgivaravgifter",
    7533: "Särskild löneskatt på pensionskostnader",
    7830: "Avskrivningar på inventarier",
    8910: "Skatt på årets resultat",
    8999: "Årets resultat",
}


@dataclass
class Voucher:
    series: str
    d: date
    text: str
    rows: list[tuple[int, float, str]]  # (account, amount, row text)
    number: int = 0

    def __post_init__(self):
        total = sum(a for _, a, _ in self.rows)
        assert abs(total) < 0.005, f"unbalanced voucher {self.text}: {total}"


@dataclass
class Book:
    """Chronological journal across both years; split by year at store time."""
    vouchers: list[Voucher] = field(default_factory=list)
    invoices: list[dict] = field(default_factory=list)
    supplier_invoices: list[dict] = field(default_factory=list)
    _inv_no: int = 1000
    _sup_no: int = 5000

    def add(self, series, d, text, rows):
        rows = [(acct, round(amt, 2), rt) for acct, amt, rt in rows if abs(amt) > 0.004]
        self.vouchers.append(Voucher(series, d, text, rows))

    # ── Customer invoicing ────────────────────────────────────────
    def invoice(self, d: date, customer: str, net: float, what: str,
                paid: date | None, due_days: int = 30):
        if paid and paid > TODAY:
            paid = None
        self._inv_no += 1
        no = str(self._inv_no)
        gross = round(net * (1 + VAT), 2)
        due = d.fromordinal(d.toordinal() + due_days)
        self.add("A", d, f"Kundfaktura {no} {customer}", [
            (1510, gross, f"Faktura {no}"),
            (3041, -net, what),
            (2610, -round(net * VAT, 2), "Utgående moms 25%"),
        ])
        if paid:
            self.add("A", paid, f"Inbetalning kundfaktura {no} {customer}", [
                (1930, gross, ""), (1510, -gross, f"Faktura {no}"),
            ])
        self.invoices.append({
            "document_number": no, "customer_name": customer,
            "invoice_date": d.isoformat(), "due_date": due.isoformat(),
            "final_pay_date": paid.isoformat() if paid else None,
            "total": gross, "balance": 0.0 if paid else gross,
        })

    # ── Supplier invoices ─────────────────────────────────────────
    def supplier(self, d: date, name: str, net: float, acct: int, what: str,
                 paid: date | None, vat: bool = True, due_days: int = 30,
                 register: bool = True):
        if paid and paid > TODAY:
            paid = None
        self._sup_no += 1
        vat_amt = round(net * VAT, 2) if vat else 0.0
        gross = round(net + vat_amt, 2)
        due = d.fromordinal(d.toordinal() + due_days)
        rows = [(acct, net, what)]
        if vat_amt:
            rows.append((2641, vat_amt, "Ingående moms"))
        rows.append((2440, -gross, name))
        self.add("A", d, f"Leverantörsfaktura {name} — {what}", rows)
        if paid:
            self.add("A", paid, f"Betalning {name}", [
                (2440, gross, name), (1930, -gross, ""),
            ])
        if register:
            self.supplier_invoices.append({
                "given_number": str(self._sup_no), "supplier_name": name,
                "invoice_date": d.isoformat(), "due_date": due.isoformat(),
                "total": gross, "balance": 0.0 if paid else gross,
            })

    # ── Payroll ───────────────────────────────────────────────────
    def payroll(self, d: date, month_name: str,
                director: tuple[float, float], employee: tuple[float, float] | None):
        """director/employee = (gross, withheld tax). Books salary + AGA;
        the tax/AGA payment to Skatteverket is a separate call (12th next month)."""
        rows, gross_total, tax_total = [], 0.0, 0.0
        g, t = director
        rows.append((7220, g, f"Lön {month_name}, anställd: 1"))
        gross_total, tax_total = gross_total + g, tax_total + t
        if employee:
            g2, t2 = employee
            rows.append((7210, g2, f"Lön {month_name}, anställd: 2"))
            gross_total, tax_total = gross_total + g2, tax_total + t2
        aga = round(gross_total * AGA, 2)
        rows += [
            (2710, -tax_total, "Avdragen preliminärskatt"),
            (1930, -(gross_total - tax_total), "Nettolön"),
            (7510, aga, "Arbetsgivaravgifter"),
            (2731, -aga, "Arbetsgivaravgifter"),
        ]
        self.add("L", d, f"Lön {month_name}", rows)
        return tax_total, aga

    def pay_payroll_taxes(self, d: date, month_name: str, tax: float, aga: float):
        self.add("A", d, f"Skatteverket: källskatt och arbetsgivaravgifter {month_name}", [
            (2710, tax, ""), (2731, aga, ""), (1930, -(tax + aga), ""),
        ])

    def pension(self, d: date, premium: float, paid: date):
        self.supplier(d, "SPP Tjänstepension", premium, 7412,
                      "Tjänstepensionspremier", paid, vat=False, register=False)
        slp = round(premium * SLP, 2)
        self.add("A", d, "Upplupen särskild löneskatt på pension", [
            (7533, slp, ""), (2941, -slp, ""),
        ])

    # ── VAT settlement ────────────────────────────────────────────
    def settle_vat(self, upto: date, settle_date: date, label: str):
        """Zero out 2610/2641 balances accrued up to `upto`, pay net same day."""
        out_vat = -sum(a for v in self.vouchers if v.d <= upto
                       for acct, a, _ in v.rows if acct == 2610)
        in_vat = sum(a for v in self.vouchers if v.d <= upto
                     for acct, a, _ in v.rows if acct == 2641)
        net = round(out_vat - in_vat, 2)
        self.add("A", settle_date, f"Momsredovisning {label}", [
            (2610, round(out_vat, 2), ""), (2641, -round(in_vat, 2), ""),
            (2650, -net, ""),
        ])
        self.add("A", settle_date, f"Betalning moms {label}", [
            (2650, net, ""), (1930, -net, ""),
        ])


def month_name_sv(m: int) -> str:
    return ["januari", "februari", "mars", "april", "maj", "juni", "juli",
            "augusti", "september", "oktober", "november", "december"][m - 1]


def build() -> tuple[Book, dict[int, float]]:
    b = Book()

    # ── Opening balances 2025-01-01 (company founded 2023) ────────
    ib = {
        1930: 520_000.00,
        1510: 81_250.00,   # December-2024 invoice, paid in January
        2081: -25_000.00,
        2440: -8_200.00,   # December accounting + phone, paid in January
        2710: -15_100.00,  # December payroll tax + AGA, paid in January
        2731: -15_081.60,
        2941: -3_600.00,   # accrued särskild löneskatt 2024
        2510: -31_000.00,  # 2024 corporate tax, paid in March
    }
    ib[2091] = -round(sum(ib.values()), 2)  # retained earnings balance the sheet

    # ── January 2025: clear the opening items ─────────────────────
    b.add("A", date(2025, 1, 10), "Betalning leverantörsskulder från december", [
        (2440, 8_200, ""), (1930, -8_200, "")])
    b.add("A", date(2025, 1, 12), "Skatteverket: källskatt och arbetsgivaravgifter december", [
        (2710, 15_100, ""), (2731, 15_081.60, ""), (1930, -30_181.60, "")])
    b.add("A", date(2025, 1, 20), "Inbetalning kundfaktura 998 Fjällström Energi AB", [
        (1930, 81_250, ""), (1510, -81_250, "")])
    b.add("A", date(2025, 3, 12), "Betalning slutlig skatt 2024", [
        (2510, 31_000, ""), (1930, -31_000, "")])

    # ── Fixed assets: laptops + desk bought Feb 2025 ──────────────
    b.supplier(date(2025, 2, 4), "NordIT Solutions AB", 68_000, 1220,
               "2 st MacBook Pro + kontorsmöbler", date(2025, 3, 1))
    # straight-line: laptops 56k/36m + desk 12k/60m = 1,755.56 kr/month from March
    DEP = 1_755.56

    # ── Recurring engine, Jan 2025 → today ────────────────────────
    prev_payroll: tuple[str, float, float] | None = ("december", 0, 0)  # cleared above
    months = [(y, m) for y in (2025, 2026) for m in range(1, 13)
              if date(y, m, 1) <= TODAY]

    for y, m in months:
        mn = month_name_sv(m)
        first, mid, late = date(y, m, 3), date(y, m, 15), date(y, m, 25)
        eom = date(y + (m == 12), m % 12 + 1, 1).fromordinal(
            date(y + (m == 12), m % 12 + 1, 1).toordinal() - 1)

        # — Revenue —
        retainer = 120_000 if y == 2025 else 135_000
        b.invoice(eom, "Fjällström Energi AB", retainer,
                  f"Konsultarvode {mn}, AI-plattform",
                  paid=_plus(eom, 32) if _plus(eom, 32) <= TODAY else None)
        if y == 2025 and 2 <= m <= 6:
            b.invoice(eom, "Baltika Retail AB", 55_000,
                      f"Dataplattform sprint {mn}", paid=_plus(eom, 45))
        if (y == 2025 and m >= 9) or (y == 2026 and 3 <= m <= 7):
            paid = _plus(eom, 25)
            b.invoice(eom, "Nordic Health Partners AB", 65_000 if y == 2025 else 70_000,
                      f"ML-prognosmodell {mn}", paid=paid if paid <= TODAY else None)
        if (y, m) in ((2025, 4), (2025, 10), (2026, 3)):
            b.invoice(mid, "Kranholm Logistik AB", 18_000,
                      "AI-workshop ledningsgrupp", paid=_plus(mid, 30))
        if (y, m) == (2026, 6):  # the overdue one on the dashboard
            b.invoice(date(2026, 6, 10), "Kranholm Logistik AB", 18_000,
                      "AI-workshop uppföljning", paid=None)

        # — Operating costs —
        b.supplier(first, "Cityfastigheter Umeå AB", 14_500, 5010,
                   f"Hyra {mn}", _plus(first, 25))
        b.supplier(first, "Siffra Redovisning AB", 3_900, 6530,
                   f"Redovisning {mn}", _plus(first, 25))
        b.supplier(first, "Molnfaktura AB", 4_200 if y == 2025 else 6_800, 6540,
                   f"Programvara och API-tjänster {mn}",
                   _plus(first, 44), due_days=45)
        b.supplier(first, "TeleNorr AB", 1_100, 6212,
                   f"Mobil och bredband {mn}", _plus(first, 25))
        b.add("A", eom, "Bankavgifter", [(6570, 120, ""), (1930, -120, "")])
        b.add("A", mid, "LinkedIn-annonsering", [
            (5910, 900, ""), (2641, 225, "Ingående moms"), (1930, -1_125, "")])
        b.add("A", mid, "Kontorsmaterial", [
            (5410, 480, ""), (2641, 120, "Ingående moms"), (1930, -600, "")])
        if m == 1:
            b.supplier(mid, "Trygg Företagsförsäkring AB", 9_600, 6310,
                       f"Företagsförsäkring {y}", _plus(mid, 25), vat=False)
        if (y, m) in ((2025, 3), (2025, 5), (2025, 9), (2025, 11), (2026, 5)):
            b.supplier(mid, "SJ / Scandic", 7_500, 5810,
                       "Resa kunduppdrag Stockholm", _plus(mid, 20))
        if (y, m) == (2026, 3):  # the March cost spike the demo chat can explain
            b.supplier(date(2026, 3, 9), "SJ / Scandic", 12_400, 5810,
                       "Resa + hotell, AI-konferens Stockholm", date(2026, 3, 29))
            b.supplier(date(2026, 3, 11), "Nordic AI Summit AB", 18_000, 5910,
                       "Monter och sponsring, Nordic AI Summit", date(2026, 3, 31))
            b.supplier(date(2026, 3, 17), "NordIT Solutions AB", 24_500, 5410,
                       "MacBook Air, ny konsultdator", date(2026, 4, 6))
        if (y, m) in ((2025, 6), (2025, 12), (2026, 6)):
            b.add("A", mid, "Representation kundmiddag", [
                (6070, 1_400, ""), (1930, -1_400, "")])
        if (y, m) in ((2025, 6),):
            b.supplier(mid, "NordIT Solutions AB", 4_800, 5410,
                       "Skärm och tillbehör", _plus(mid, 25))

        # — Depreciation (from March 2025) —
        if (y, m) >= (2025, 3):
            b.add("A", eom, "Avskrivning inventarier", [
                (7830, DEP, ""), (1229, -DEP, "")])

        # — Payroll: employee #2 starts March 2025 —
        director = (48_000, 14_400) if y == 2025 else (52_000, 15_900)
        employee = None
        if (y, m) >= (2025, 3):
            employee = (38_000, 10_100) if y == 2025 else (42_000, 11_400)
        if prev_payroll and prev_payroll[1]:
            pm, pt, pa = prev_payroll
            b.pay_payroll_taxes(date(y, m, 12), pm, pt, pa)
        tax, aga = b.payroll(late, mn, director, employee)
        prev_payroll = (mn, tax, aga)
        b.pension(late, 3_120 + (2_280 if employee else 0), _plus(late, 20))

        # — Quarterly VAT (small AB): settle ~6 weeks after quarter end —
        for q_end, s_date, label in (
            (date(y, 3, 31), date(y, 5, 12), f"Q1 {y}"),
            (date(y, 6, 30), date(y, 8, 4), f"Q2 {y}"),
            (date(y, 9, 30), date(y, 11, 12), f"Q3 {y}"),
        ):
            if (y, m) == (s_date.year, s_date.month) and mid.month == s_date.month \
                    and s_date <= TODAY and first <= s_date:
                b.settle_vat(q_end, s_date, label)
        if m == 2:  # Q4 previous year
            q_end, s_date = date(y - 1, 12, 31), date(y, 2, 12)
            if y == 2026 and s_date <= TODAY:
                b.settle_vat(q_end, s_date, f"Q4 {y-1}")

    # ── Year-end 2025: corporate tax + close the result ───────────
    pnl_2025 = sum(a for v in b.vouchers if v.d.year == 2025
                   for acct, a, _ in v.rows if 3000 <= acct <= 8899)
    profit_before_tax = -pnl_2025
    tax_2025 = round(round(profit_before_tax * TAX / 100) * 100, 2)
    b.add("A", date(2025, 12, 31), "Beräknad skatt på årets resultat", [
        (8910, tax_2025, ""), (2510, -tax_2025, "")])
    result_2025 = round(profit_before_tax - tax_2025, 2)
    b.add("A", date(2025, 12, 31), "Årets resultat", [
        (8999, result_2025, ""), (2099, -result_2025, "")])

    # ── 2026: pay 2025 tax, årsstämma moves result, dividend ──────
    b.add("A", date(2026, 3, 12), "Betalning slutlig skatt 2025", [
        (2510, tax_2025, ""), (1930, -tax_2025, "")])
    b.add("A", date(2026, 4, 21), "Resultatdisposition enligt årsstämma", [
        (2099, result_2025, ""), (2091, -(result_2025 - 120_000), ""),
        (2898, -120_000, "Beslutad utdelning")])
    b.add("A", date(2026, 5, 5), "Utbetalning utdelning", [
        (2898, 120_000, ""), (1930, -120_000, "")])

    # Books end at today: drop anything the loop dated into the future
    # (current-month invoicing, payroll on the 25th, month-end fees...).
    b.vouchers = [v for v in b.vouchers if v.d <= TODAY]
    b.invoices = [i for i in b.invoices if i["invoice_date"] <= TODAY.isoformat()]
    b.supplier_invoices = [s for s in b.supplier_invoices
                           if s["invoice_date"] <= TODAY.isoformat()]

    return b, ib


def _plus(d: date, days: int) -> date:
    return date.fromordinal(d.toordinal() + days)


def store(b: Book, ib_2025: dict[int, float]) -> None:
    years = {2025: 1, 2026: 2}
    b.vouchers.sort(key=lambda v: (v.d, v.series))
    counters: dict[tuple[int, str], int] = {}
    for v in b.vouchers:
        yid = years[v.d.year]
        counters[(yid, v.series)] = counters.get((yid, v.series), 0) + 1
        v.number = counters[(yid, v.series)]

    # per-year account balances: ib 2026 = ub 2025
    def year_sum(year: int) -> dict[int, float]:
        out: dict[int, float] = {}
        for v in b.vouchers:
            if v.d.year != year:
                continue
            for acct, a, _ in v.rows:
                out[acct] = round(out.get(acct, 0) + a, 2)
        return out

    sums = {y: year_sum(y) for y in years}
    ib = {2025: ib_2025, 2026: {}}
    for acct in set(ib_2025) | set(sums[2025]):
        if acct < 3000:
            ib[2026][acct] = round(ib_2025.get(acct, 0) + sums[2025].get(acct, 0), 2)
    for y in years:
        tie = sum(v for a, v in ib[y].items())
        assert abs(tie) < 0.02, f"IB {y} does not tie: {tie}"

    # bank never negative
    bal = ib_2025[1930]
    for v in b.vouchers:
        for acct, a, _ in v.rows:
            if acct == 1930:
                bal += a
                assert bal > 0, f"bank negative on {v.d}: {bal:.2f} ({v.text})"

    if DATA_DIR.name != "data-demo":
        raise SystemExit(f"refusing to write outside data-demo: {DATA_DIR}")
    db.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if db.DB_PATH.exists():
        db.DB_PATH.unlink()

    with db.session() as conn:
        for y, yid in years.items():
            conn.execute("INSERT INTO financial_years (id, from_date, to_date) VALUES (?,?,?)",
                         (yid, f"{y}-01-01", f"{y}-12-31"))
            accts = set(ib[y]) | set(sums[y])
            for acct in sorted(accts):
                conn.execute(
                    "INSERT INTO accounts (year_id, number, description, ib, ub) VALUES (?,?,?,?,?)",
                    (yid, acct, ACCOUNTS.get(acct, ""),
                     ib[y].get(acct, 0.0) if acct < 3000 else 0.0,
                     round(ib[y].get(acct, 0.0) + sums[y].get(acct, 0.0), 2)
                     if acct < 3000 else sums[y].get(acct, 0.0)))
        for v in b.vouchers:
            yid = years[v.d.year]
            conn.execute(
                "INSERT INTO vouchers (year_id, series, number, date, description) VALUES (?,?,?,?,?)",
                (yid, v.series, v.number, v.d.isoformat(), v.text))
            for acct, a, rt in v.rows:
                conn.execute(
                    "INSERT INTO transactions (year_id, series, voucher_number, account,"
                    " date, description, amount) VALUES (?,?,?,?,?,?,?)",
                    (yid, v.series, v.number, acct, v.d.isoformat(), rt or v.text, a))
        for inv in b.invoices:
            conn.execute(
                "INSERT INTO invoices (document_number, customer_number, customer_name,"
                " invoice_date, due_date, final_pay_date, total, balance, currency, cancelled)"
                " VALUES (?,?,?,?,?,?,?,?, 'SEK', 0)",
                (inv["document_number"], inv["document_number"][-2:], inv["customer_name"],
                 inv["invoice_date"], inv["due_date"], inv["final_pay_date"],
                 inv["total"], inv["balance"]))
        for s in b.supplier_invoices:
            conn.execute(
                "INSERT INTO supplier_invoices (given_number, supplier_name, invoice_date,"
                " due_date, total, balance, currency, cancelled) VALUES (?,?,?,?,?,?, 'SEK', 0)",
                (s["given_number"], s["supplier_name"], s["invoice_date"],
                 s["due_date"], s["total"], s["balance"]))

        _store_assets(conn)
        db.set_meta(conn, "company", json.dumps(COMPANY))
        db.set_meta(conn, "assets_status", json.dumps({"state": "ok", "count": 3}))
        db.set_meta(conn, "last_sync",
                    datetime.now(timezone.utc).isoformat(timespec="seconds"))


def _store_assets(conn) -> None:
    conn.execute("INSERT INTO asset_types (id, number, description, type) VALUES (1,'1220','Inventarier och datorer',0)")
    assets = [
        ("INV-1", 'MacBook Pro 16" (konsult 1)', 28_000, 36, 777.78),
        ("INV-2", 'MacBook Pro 14" (konsult 2)', 28_000, 36, 777.78),
        ("INV-3", "Höj- och sänkbara skrivbord + möbler", 12_000, 60, 200.00),
    ]
    def _eom(d: date) -> date:
        nxt = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        return date.fromordinal(nxt.toordinal() - 1)

    # only fully elapsed months carry a depreciation event (mirrors the ledger)
    dep_months = [date(y, m, 1) for y in (2025, 2026) for m in range(1, 13)
                  if date(2025, 3, 1) <= date(y, m, 1) and _eom(date(y, m, 1)) <= TODAY]
    for i, (no, desc, value, months, monthly) in enumerate(assets, start=1):
        final = date(2025 + (2 + months) // 12 - (1 if months == 60 else 0), 2, 28)
        conn.execute(
            "INSERT INTO assets (number, id, description, status, type_id, type_name,"
            " acquisition_value, acquisition_date, acquisition_start, depreciation_method,"
            " depreciation_final, depreciated_to) VALUES (?,?,?,?,1,'Inventarier och datorer',?,?,?,0,?,?)",
            (no, i, desc, "ACTIVE", value, "2025-02-04", "2025-03-01",
             final.isoformat(), _eom(dep_months[-1]).isoformat()))
        conn.execute(
            "INSERT INTO asset_history (asset_number, history_id, date, event_id, amount,"
            " user_name) VALUES (?,?,?,0,?,'demo')",
            (no, i * 1000, "2025-02-04", value))
        for j, dm in enumerate(dep_months):
            eom = date(dm.year + (dm.month == 12), dm.month % 12 + 1, 1)
            eom = date.fromordinal(eom.toordinal() - 1)
            conn.execute(
                "INSERT INTO asset_history (asset_number, history_id, date, event_id,"
                " amount, user_name, voucher_series, voucher_year) VALUES (?,?,?,3,?,'demo','A',?)",
                (no, i * 1000 + j + 1, eom.isoformat(), monthly,
                 1 if dm.year == 2025 else 2))


if __name__ == "__main__":
    book, ib = build()
    store(book, ib)
    n_txn = sum(len(v.rows) for v in book.vouchers)
    print(f"Seeded {DATA_DIR / 'mirror.db'}")
    print(f"  {len(book.vouchers)} vouchers, {n_txn} transaction rows,"
          f" {len(book.invoices)} invoices, {len(book.supplier_invoices)} supplier invoices")
