"""SQLite mirror of the Fortnox data. Single-user local app: one file,
short-lived connections, WAL for reader/writer overlap during sync."""

import json
import sqlite3
from contextlib import contextmanager

from .config import DATA_DIR

DB_PATH = DATA_DIR / "mirror.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
  key   TEXT PRIMARY KEY,
  value TEXT
);
CREATE TABLE IF NOT EXISTS financial_years (
  id        INTEGER PRIMARY KEY,
  from_date TEXT NOT NULL,
  to_date   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS accounts (
  year_id     INTEGER NOT NULL,
  number      INTEGER NOT NULL,
  description TEXT DEFAULT '',
  ib          REAL DEFAULT 0,
  ub          REAL DEFAULT 0,
  PRIMARY KEY (year_id, number)
);
CREATE TABLE IF NOT EXISTS vouchers (
  year_id     INTEGER NOT NULL,
  series      TEXT NOT NULL,
  number      INTEGER NOT NULL,
  date        TEXT NOT NULL,
  description TEXT DEFAULT '',
  PRIMARY KEY (year_id, series, number)
);
CREATE TABLE IF NOT EXISTS transactions (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  year_id        INTEGER NOT NULL,
  series         TEXT NOT NULL,
  voucher_number INTEGER NOT NULL,
  account        INTEGER NOT NULL,
  date           TEXT NOT NULL,
  description    TEXT DEFAULT '',
  amount         REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_txn_account ON transactions (year_id, account, date);
CREATE INDEX IF NOT EXISTS idx_txn_voucher ON transactions (year_id, series, voucher_number);
CREATE TABLE IF NOT EXISTS invoices (
  document_number TEXT PRIMARY KEY,
  customer_number TEXT,
  customer_name   TEXT,
  invoice_date    TEXT,
  due_date        TEXT,
  final_pay_date  TEXT,
  total           REAL DEFAULT 0,
  balance         REAL DEFAULT 0,
  currency        TEXT DEFAULT 'SEK',
  cancelled       INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS supplier_invoices (
  given_number  TEXT PRIMARY KEY,
  supplier_name TEXT,
  invoice_date  TEXT,
  due_date      TEXT,
  total         REAL DEFAULT 0,
  balance       REAL DEFAULT 0,
  currency      TEXT DEFAULT 'SEK',
  cancelled     INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS asset_types (
  id          INTEGER PRIMARY KEY,
  number      TEXT,          -- BAS account for the type, e.g. '1220'
  description TEXT DEFAULT '',
  type        INTEGER,       -- 0 tangible / 1 partial / 2 non-depreciable (Fortnox code)
  notes       TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS assets (
  number                       TEXT PRIMARY KEY,   -- Fortnox asset Number
  id                           INTEGER,
  description                  TEXT DEFAULT '',
  status                       TEXT DEFAULT '',
  type_id                      INTEGER,            -- -> asset_types.id
  type_name                    TEXT DEFAULT '',
  acquisition_value            REAL DEFAULT 0,
  acquisition_date             TEXT,               -- purchase date
  acquisition_start            TEXT,               -- depreciation start
  depreciation_method          INTEGER,            -- 0 = straight-line (Rak)
  depreciation_final           TEXT,               -- schedule end date
  depreciated_to               TEXT,               -- depreciated through this date
  depreciate_to_residual_value REAL DEFAULT 0,
  manual_ob                    REAL DEFAULT 0,
  notes                        TEXT DEFAULT '',
  reference                    TEXT DEFAULT '',
  brand                        TEXT DEFAULT '',
  cost_center                  TEXT DEFAULT '',
  project                      TEXT DEFAULT '',
  asset_group                  TEXT DEFAULT '',
  placement                    TEXT DEFAULT '',
  room                         TEXT DEFAULT '',
  department                   TEXT DEFAULT '',
  insured_with                 TEXT DEFAULT '',
  insured_number               TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS asset_history (
  asset_number    TEXT NOT NULL,        -- -> assets.number
  history_id      INTEGER,
  date            TEXT,
  event_id        INTEGER,              -- 0 acquisition, 3 scheduled depreciation (other codes: write up/down, sell, scrap)
  amount          REAL DEFAULT 0,
  user_name       TEXT DEFAULT '',
  notes           TEXT DEFAULT '',
  voucher_series  TEXT,                 -- ledger link (join transactions on year+series+number)
  voucher_number  INTEGER,
  voucher_year    INTEGER,
  supplier_invoice INTEGER DEFAULT 0    -- >0 => asset booked from this supplier invoice (supplier source)
);
CREATE INDEX IF NOT EXISTS idx_asset_hist ON asset_history (asset_number, date);
CREATE TABLE IF NOT EXISTS chat_sessions (
  id           TEXT PRIMARY KEY,
  title        TEXT DEFAULT '',
  created_at   TEXT NOT NULL,
  model        TEXT DEFAULT '',
  page_context TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS chat_messages (
  session_id    TEXT NOT NULL,
  seq           INTEGER NOT NULL,
  messages_json TEXT NOT NULL,
  usage_json    TEXT DEFAULT '',
  created_at    TEXT NOT NULL,
  PRIMARY KEY (session_id, seq)
);
"""


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    return conn


@contextmanager
def session():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def connect_readonly() -> sqlite3.Connection:
    """Connection for the AI tool layer: mode=ro + query_only + an authorizer
    that denies everything except reading. Triple-belt read-only."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=1")  # before the authorizer: it's a PRAGMA
    allowed = {
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_FUNCTION,
        sqlite3.SQLITE_RECURSIVE,
    }
    conn.set_authorizer(
        lambda action, *_: sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY
    )
    return conn


def get_meta(conn: sqlite3.Connection, key: str, default=None):
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def get_meta_json(conn: sqlite3.Connection, key: str, default=None):
    raw = get_meta(conn, key)
    return json.loads(raw) if raw else default


def has_ledger_data() -> bool:
    with session() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM transactions").fetchone()
        return row["n"] > 0
