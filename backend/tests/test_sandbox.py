"""Sandbox tests for run_python (F9 change 1) — offline, zero tokens.

Exercises the security envelope: read-only DB, no network, no leaked secrets,
CPU/wall limits, output caps. The timeout case patches the module limits down
so the kill path is exercised in ~2s instead of 15.

Run: .venv/bin/python tests/test_sandbox.py
"""

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db, sie  # noqa: E402
from app.sync import _store_ledger  # noqa: E402
from tests.test_pipeline import SAMPLE_SIE  # noqa: E402

db.DB_PATH = Path(tempfile.mkdtemp()) / "mirror-sandbox-test.db"


def _fixture_mirror() -> None:
    db.DB_PATH.unlink(missing_ok=True)
    _store_ledger(1, sie.parse(SAMPLE_SIE))


from app.ai import sandbox  # noqa: E402  (after DB_PATH is set; sandbox reads it at call time)


def test_happy_path() -> None:
    r = sandbox.run("print({'answer': int(D('40') * 2 + D('2'))})")
    assert r["exit_code"] == 0, r
    assert "{'answer': 82}" in r["stdout"]
    print("happy path OK")


def test_readonly_db() -> None:
    # q() reads the fixture
    r = sandbox.run("print('rows', q('SELECT COUNT(*) FROM transactions')[0][0])")
    assert r["exit_code"] == 0 and "rows " in r["stdout"], r

    # qd() returns dicts
    r = sandbox.run("print(qd('SELECT number FROM accounts ORDER BY number LIMIT 1'))")
    assert r["exit_code"] == 0 and "number" in r["stdout"], r

    # writes fail at the driver (mode=ro)
    r = sandbox.run("db.execute(\"INSERT INTO meta VALUES ('x','y')\")")
    assert r["exit_code"] != 0
    assert "readonly" in r["stderr"].lower() or "read-only" in r["stderr"].lower(), r["stderr"]
    print("read-only db OK")


def test_network_blocked() -> None:
    r = sandbox.run("import urllib.request; urllib.request.urlopen('http://example.com', timeout=3)")
    assert r["exit_code"] != 0
    assert "network disabled in sandbox" in r["stderr"], r["stderr"]
    # ssl must still import (we don't break the socket class)
    r2 = sandbox.run("import ssl; print('ssl ok', bool(ssl.SSLSocket))")
    assert r2["exit_code"] == 0 and "ssl ok" in r2["stdout"], r2
    print("network blocked OK")


def test_timeout_killed() -> None:
    orig = sandbox.WALL_TIMEOUT_S
    sandbox.WALL_TIMEOUT_S = 2
    try:
        t0 = time.monotonic()
        r = sandbox.run("import time\nwhile True:\n    time.sleep(1)")
        elapsed = time.monotonic() - t0
    finally:
        sandbox.WALL_TIMEOUT_S = orig
    assert r["exit_code"] == -1, r
    assert "wall-clock" in r["stderr"], r["stderr"]
    assert elapsed < 10, elapsed
    print(f"timeout killed OK ({elapsed:.1f}s)")


def test_output_cap() -> None:
    r = sandbox.run("print('x' * 1_000_000)")
    assert r["exit_code"] == 0
    assert len(r["stdout"]) <= sandbox.MAX_OUTPUT_CHARS + 20
    assert r["stdout"].rstrip().endswith("[truncated]"), r["stdout"][-40:]
    print("output cap OK")


def test_no_secret_leak() -> None:
    r = sandbox.run("import os; print('|'.join(f'{k}={v}' for k, v in os.environ.items()))")
    assert r["exit_code"] == 0
    blob = r["stdout"]
    for secret in ("OPENROUTER_API_KEY", "FORTNOX_CLIENT_SECRET", "TAVILY_API_KEY", "FORTNOX_CLIENT_ID"):
        assert secret not in blob, f"leaked {secret}: {blob}"
    print("no secret leak OK")


def main() -> None:
    _fixture_mirror()
    test_happy_path()
    test_readonly_db()
    test_network_blocked()
    test_timeout_killed()
    test_output_cap()
    test_no_secret_leak()
    db.DB_PATH.unlink(missing_ok=True)
    print("ALL SANDBOX TESTS PASSED")


if __name__ == "__main__":
    main()
