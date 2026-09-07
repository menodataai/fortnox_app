"""Step-1 AI foundation tests: read-only guard rails, calculate(), the
balance-sheet builder and financial-year detail flags.

Run: .venv/bin/python tests/test_ai_foundation.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import analytics, db, sie  # noqa: E402
from app.ai import calc, ledger_sql  # noqa: E402
from app.sync import _store_ledger  # noqa: E402
from tests.test_pipeline import SAMPLE_SIE  # noqa: E402

db.DB_PATH = Path(tempfile.mkdtemp()) / "mirror-ai-test.db"


def _fixture_mirror() -> None:
    db.DB_PATH.unlink(missing_ok=True)
    _store_ledger(1, sie.parse(SAMPLE_SIE))
    with db.session() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO financial_years (id, from_date, to_date)"
            " VALUES (1, '2026-01-01', '2026-12-31')"
        )
        # Equity IB matching the bank IB — real books balance at IB
        conn.execute(
            "INSERT OR REPLACE INTO accounts (year_id, number, description, ib, ub)"
            " VALUES (1, 2091, 'Balanserat resultat', -500000, -500000)"
        )
        # A balances-only earlier year (mirror limitation): accounts, no transactions
        conn.execute(
            "INSERT OR REPLACE INTO financial_years (id, from_date, to_date)"
            " VALUES (2, '2025-01-01', '2025-12-31')"
        )
        conn.execute(
            "INSERT OR REPLACE INTO accounts (year_id, number, description, ib, ub)"
            " VALUES (2, 1930, 'Företagskonto', 300000, 500000)"
        )
        conn.execute(
            "INSERT OR REPLACE INTO accounts (year_id, number, description, ib, ub)"
            " VALUES (2, 2091, 'Balanserat resultat', -100000, -300000)"
        )


def test_calculate() -> None:
    assert calc.calculate("2 + 3 * 4") == "14"
    assert calc.calculate("0.1 + 0.2") == "0.3"  # decimal, not float
    assert calc.calculate("round(88000 * 0.3142, 2)") == "27649.6"
    assert calc.calculate("round(70000 / 36, 2)") == "1944.44"
    assert calc.calculate("-(5 - 2)") == "-3"
    assert calc.calculate("abs(-7.5)") == "7.5"
    for bad in ("__import__('os')", "x + 1", "2 ** 200", "1; 2", "min(1,2)", "1 / 0"):
        try:
            calc.calculate(bad)
            raise AssertionError(f"should have rejected: {bad}")
        except ValueError:
            pass
    print("calculate OK")


def test_query_ledger_guards() -> None:
    conn = db.connect_readonly()
    try:
        # plain read works
        out = ledger_sql.run_query(conn, "SELECT number, ib FROM accounts WHERE year_id = 1 ORDER BY number")
        assert out["columns"] == ["number", "ib"]
        assert not out["truncated"] and len(out["rows"]) >= 4

        # params work
        out = ledger_sql.run_query(
            conn, "SELECT SUM(amount) AS s FROM transactions WHERE year_id = ? AND account = ?", [1, 7210]
        )
        assert out["rows"][0][0] == 88000.0

        # CTE works
        out = ledger_sql.run_query(
            conn, "WITH m AS (SELECT amount FROM transactions WHERE account = 3041) SELECT SUM(amount) FROM m"
        )
        assert out["rows"][0][0] == -215000.0

        # row cap: truncation flagged
        with db.session() as w:
            pass  # (writer session on the real path; fixture rows are few)
        out = ledger_sql.run_query(conn, "SELECT 1 FROM transactions t1, transactions t2, transactions t3")
        assert out["truncated"] and len(out["rows"]) == ledger_sql.MAX_ROWS

        # non-SELECT rejected up front
        for bad in (
            "INSERT INTO meta VALUES ('x','y')",
            "UPDATE accounts SET ib = 0",
            "DELETE FROM transactions",
            "PRAGMA journal_mode=DELETE",
            "ATTACH DATABASE '/tmp/evil.db' AS evil",
            "DROP TABLE accounts",
        ):
            try:
                ledger_sql.run_query(conn, bad)
                raise AssertionError(f"should have rejected: {bad}")
            except ValueError:
                pass

        # sneaky write hidden behind SELECT-ish prefix → authorizer/ro must deny
        try:
            ledger_sql.run_query(conn, "SELECT 1; DROP TABLE accounts")
            raise AssertionError("multi-statement should be rejected")
        except ValueError:
            pass

        # authorizer blocks writes even on a raw cursor (defense in depth)
        try:
            conn.execute("CREATE TEMP TABLE x (a)")
            raise AssertionError("authorizer should deny CREATE")
        except Exception:
            pass
    finally:
        conn.close()
    print("query_ledger guards OK")


def test_financial_years_flags() -> None:
    years = analytics.financial_years()
    by_year = {y["year"]: y for y in years}
    assert by_year[2026]["has_transaction_detail"] is True
    assert by_year[2025]["has_transaction_detail"] is False
    print("financial_years OK")


def test_balance_sheet() -> None:
    bs = analytics.balance_sheet(2026)
    assert bs["has_transaction_detail"] is True
    bank = next(a for a in bs["assets"]["accounts"] if a["number"] == 1930)
    assert bank["ib"] == 500000.0 and bank["ub"] == 627000.0
    ap = next(a for a in bs["equity_and_liabilities"]["accounts"] if a["number"] == 2440)
    assert ap["ub"] == 40500.0  # liability shown positive
    # the sheet must tie: assets = equity&liabilities + unbooked period result
    assert abs(bs["assets"]["total_ub"] - bs["equity_side_total_incl_result"]) < 0.01
    assert bs["period_result_not_yet_booked"] == 215000.0 - 32400.0 - 88000.0

    # mid-period sheet: only January activity included
    bs_jan = analytics.balance_sheet(2026, to_date="2026-01-31")
    bank_jan = next(a for a in bs_jan["assets"]["accounts"] if a["number"] == 1930)
    assert bank_jan["ub"] == 715000.0
    assert abs(bs_jan["assets"]["total_ub"] - bs_jan["equity_side_total_incl_result"]) < 0.01

    # balances-only year: stored UB used, flagged
    bs25 = analytics.balance_sheet(2025)
    assert bs25["balances_only"] is True
    bank25 = next(a for a in bs25["assets"]["accounts"] if a["number"] == 1930)
    assert bank25["ib"] == 300000.0 and bank25["ub"] == 500000.0
    print("balance_sheet OK")


def test_web_allowlist() -> None:
    import asyncio

    from app.ai import web

    assert web.host_allowed("https://www.skatteverket.se/foretag/x")
    assert web.host_allowed("https://www4.skatteverket.se/rattsligvagledning/y")
    assert not web.host_allowed("https://evil.example.com/skatteverket.se")
    assert not web.host_allowed("https://notskatteverket.se/")  # suffix, not subdomain
    assert web.host_allowed("https://ai.example.org/x", extra_domains={"ai.example.org"})

    # fetch_page must refuse non-allowlisted hosts before any network I/O
    try:
        asyncio.run(web.fetch_page_text("https://evil.example.com/page"))
        raise AssertionError("should have rejected non-allowlisted host")
    except ValueError:
        pass
    try:
        asyncio.run(web.fetch_page_text("file:///etc/passwd"))
        raise AssertionError("should have rejected non-http scheme")
    except ValueError:
        pass
    print("web allowlist OK")


def main() -> None:
    _fixture_mirror()
    test_calculate()
    test_query_ledger_guards()
    test_financial_years_flags()
    test_balance_sheet()
    test_web_allowlist()
    db.DB_PATH.unlink(missing_ok=True)
    print("ALL AI FOUNDATION TESTS PASSED")


if __name__ == "__main__":
    main()
