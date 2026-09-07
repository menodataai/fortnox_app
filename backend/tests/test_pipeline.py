"""End-to-end test of the data pipeline: SIE bytes → parser → mirror → analytics.

Run: .venv/bin/python -m pytest tests/ -q   (or plain: python tests/test_pipeline.py)
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import analytics, db, sie  # noqa: E402
from app.sync import _store_ledger  # noqa: E402

# Never touch the real mirror — run against a throwaway database
db.DB_PATH = Path(tempfile.mkdtemp()) / "mirror-test.db"

SAMPLE_SIE = b"""#FLAGGA 0
#PROGRAM "Fortnox" 3.44.3
#FORMAT PC8
#SIETYP 4
#FNAMN "Nordvind Konsult AB"
#RAR 0 20260101 20261231
#KONTO 1930 "F\x94retagskonto"
#KONTO 2440 "Leverant\x94rsskulder"
#KONTO 2641 "Ing\x86ende moms"
#KONTO 3041 "F\x94rs\x84ljning tj\x84nster 25%"
#KONTO 5410 "F\x94rbrukningsinventarier"
#KONTO 7210 "L\x94ner tj\x84nstem\x84n"
#IB 0 1930 500000.00
#UB 0 1930 480000.00
#RES 0 3041 -215000.00
#RES 0 5410 32400.00
#VER A 1 20260131 "Kundfaktura 1041"
{
#TRANS 1930 {} 215000.00 "" "Betalning"
#TRANS 3041 {} -215000.00
}
#VER A 58 20260314 "Elgiganten laptop"
{
#TRANS 5410 {} 32400.00 20260314 "MacBook Pro"
#TRANS 2641 {} 8100.00
#TRANS 2440 {} -40500.00
}
#VER B 3 20260225 "L\x94n januari"
{
#TRANS 7210 {} 88000.00
#TRANS 1930 {} -88000.00
}
"""


def main() -> None:
    # Parse
    parsed = sie.parse(SAMPLE_SIE)
    assert parsed.year_start == "2026-01-01" and parsed.year_end == "2026-12-31"
    assert parsed.accounts[1930] == "Företagskonto", parsed.accounts[1930]
    assert parsed.ib[1930] == 500000.00
    assert parsed.res[3041] == -215000.00
    assert len(parsed.vouchers) == 3
    laptop = parsed.vouchers[1]
    assert laptop.series == "A" and laptop.number == 58
    assert [t.amount for t in laptop.trans] == [32400.00, 8100.00, -40500.00]
    assert laptop.trans[0].text == "MacBook Pro"
    assert sum(t.amount for t in laptop.trans) == 0.0  # double entry balances

    # Store into a scratch mirror
    db.DB_PATH.unlink(missing_ok=True)
    _store_ledger(1, parsed)
    with db.session() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO financial_years (id, from_date, to_date)"
            " VALUES (1, '2026-01-01', '2026-12-31')"
        )

    # Analytics
    p = analytics.pnl(2026)
    assert p["revenue_total"] == 215000.00, p["revenue_total"]
    assert p["costs_total"] == 32400.00 + 88000.00, p["costs_total"]
    assert p["profit_before_tax"] == 215000.00 - 120400.00
    ext = next(g for g in p["groups"] if g["key"] == "external")
    assert ext["accounts"][0]["number"] == 5410
    assert ext["monthly"][2] == 32400.00  # March

    acct = analytics.account_detail(5410, 2026)
    assert acct["period_total"] == 32400.00
    assert acct["transactions"][0]["voucher_number"] == 58
    assert acct["explain"] and "Equipment" in acct["explain"]

    v = analytics.voucher_detail("A", 58, 2026)
    assert len(v["rows"]) == 3
    assert v["rows"][0]["debit"] == 32400.00 and v["rows"][2]["credit"] == 40500.00

    bank = analytics.account_detail(1930, 2026)
    assert bank["is_balance_account"] and bank["ib"] == 500000.00
    assert bank["ub"] == 500000.00 + 215000.00 - 88000.00

    summary = analytics.dashboard_summary(2026)
    assert summary["cash"] == 627000.00, summary["cash"]
    assert summary["revenue_ytd"] == 215000.00

    db.DB_PATH.unlink(missing_ok=True)
    print("ALL PIPELINE TESTS PASSED")


if __name__ == "__main__":
    main()
