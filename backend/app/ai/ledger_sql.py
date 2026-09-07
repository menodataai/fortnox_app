"""The `query_ledger` power tool's core: guarded read-only SELECT over the
mirror. The connection is already read-only (mode=ro + query_only +
authorizer); this layer adds statement vetting, a row cap and a timeout."""

import re
import sqlite3
import time

MAX_ROWS = 200
TIMEOUT_S = 5.0

# Embedded in the tool docstring so the model knows the schema, the SIE sign
# convention and the classic voucher-number pitfall without trial and error.
SCHEMA_DOC = """\
Tables (SQLite):
  financial_years(id, from_date, to_date)                      -- one row per fiscal year
  accounts(year_id, number, description, ib, ub)               -- chart of accounts w/ opening (IB) and closing (UB) balances per year
  vouchers(year_id, series, number, date, description)         -- voucher heads (series 'A', 'B', 'L'...)
  transactions(id, year_id, series, voucher_number, account,
               date, description, amount)                      -- every ledger row
  invoices(document_number, customer_number, customer_name, invoice_date,
           due_date, final_pay_date, total, balance, currency, cancelled)
  supplier_invoices(given_number, supplier_name, invoice_date, due_date,
                    total, balance, currency, cancelled)
  assets(number, description, status, type_name, acquisition_value,
         acquisition_date, depreciation_method, depreciation_final,
         depreciated_to, ...)                                  -- fixed-asset register (Anläggningsregister)
  asset_history(asset_number, date, event_id, amount, notes, voucher_series,
                voucher_number, voucher_year, supplier_invoice) -- per-asset events
  meta(key, value)                                             -- last_sync, company json

Conventions:
- SIE sign convention: debit > 0, credit < 0. Revenue accounts (3xxx) sum
  NEGATIVE; costs (4xxx-7xxx) positive.
- Voucher numbers RESTART each financial year and the same series+number in a
  different year is an unrelated voucher — always join/filter on year_id.
- Older financial years may have accounts (IB/UB) but NO transactions rows
  (balances-only mirror coverage) — check before concluding "no activity".
- Dates are ISO strings 'YYYY-MM-DD'; use substr(date,1,7) for months.
- Payroll: L-series vouchers, per-employee rows carry 'anställd: N' in the
  transaction description.
- Assets: acquisition_value is a positive amount. Accumulated depreciation =
  SUM(asset_history.amount) WHERE event_id = 3 (scheduled depreciation);
  book value = acquisition_value − that. event_id 0 = acquisition. Each
  depreciation row links to its ledger voucher via (voucher_year -> a
  financial_years.id, voucher_series, voucher_number). supplier_invoice > 0
  points at supplier_invoices.given_number (the asset's supplier), else there
  is no supplier on record.

Example queries:
  -- monthly sum for one account in the 2026 year (year_id from financial_years)
  SELECT substr(date,1,7) m, SUM(amount) FROM transactions
   WHERE year_id = ? AND account = 5615 GROUP BY m ORDER BY m;
  -- per-employee gross salary rows from payroll vouchers
  SELECT date, description, amount FROM transactions
   WHERE year_id = ? AND series = 'L' AND account = 7210 ORDER BY date;
  -- text search across descriptions
  SELECT date, series, voucher_number, account, description, amount
   FROM transactions WHERE year_id = ? AND description LIKE '%leasing%';
"""


def run_query(conn: sqlite3.Connection, sql: str, params: list | None = None) -> dict:
    """Execute one SELECT with a row cap and a timeout.

    Returns {columns, rows, truncated}. Raises ValueError with a
    model-correctable message on anything else.
    """
    stripped = sql.strip().rstrip(";").strip()
    if not re.match(r"(?is)^(select|with)\b", stripped):
        raise ValueError("Only a single SELECT (or WITH ... SELECT) statement is allowed.")

    # Uniform row cap: wrap the query. Fetch one extra row to detect truncation.
    wrapped = f"SELECT * FROM ({stripped}) LIMIT {MAX_ROWS + 1}"

    # Same-thread timeout: a progress handler that aborts past the deadline.
    # (Never interrupt from another thread — sqlite3 connections are not
    # safe for cross-thread use and it corrupts the heap.)
    deadline = time.monotonic() + TIMEOUT_S
    conn.set_progress_handler(lambda: time.monotonic() > deadline, 50_000)
    try:
        cur = conn.execute(wrapped, params or [])
        rows = cur.fetchall()
    except sqlite3.OperationalError as e:
        if "interrupted" in str(e):
            raise ValueError(
                f"Query exceeded the {TIMEOUT_S:.0f}s time limit — narrow it down "
                "(filter on year_id/account, aggregate instead of listing)."
            ) from e
        raise ValueError(f"SQL error: {e}") from e
    except (sqlite3.DatabaseError, sqlite3.Warning) as e:
        # DatabaseError covers authorizer denials; Warning covers multi-statement input
        raise ValueError(f"SQL error: {e}") from e
    finally:
        conn.set_progress_handler(None, 0)

    columns = [d[0] for d in cur.description] if cur.description else []
    truncated = len(rows) > MAX_ROWS
    return {
        "columns": columns,
        "rows": [list(r) for r in rows[:MAX_ROWS]],
        "truncated": truncated,
    }
