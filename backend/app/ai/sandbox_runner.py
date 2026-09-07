"""Runs INSIDE the sandbox subprocess — never imported by the backend.

Launched by sandbox.run() as:

    python -I -E sandbox_runner.py <mirror_db_path>

The user's script arrives on stdin. Before a single line of it executes this
wrapper: (1) disables networking, (2) opens the mirror read-only and injects
`db`, `q`, `qd`, and (3) aliases `decimal.Decimal` as `D`. Then it exec()s the
script in a fresh globals dict. A user exception is printed as a normal
traceback (referencing "<sandbox>") and the process exits non-zero — the
parent returns that to the model so it can fix its script.
"""

import sys


def _disable_network() -> None:
    """Best-effort but effective: user code runs only after this, and `-I`
    prevents preloading a connected socket before we patch it. We block the
    connection primitives rather than replacing the `socket` class itself —
    `ssl` subclasses `socket.socket`, so swapping the class out breaks a plain
    `import ssl`; blocking connect()/getaddrinfo() stops the I/O while leaving
    imports and the class hierarchy intact."""
    import socket

    def _blocked(*_a, **_k):
        raise RuntimeError("network disabled in sandbox")

    socket.getaddrinfo = _blocked  # type: ignore[assignment]
    socket.create_connection = _blocked  # type: ignore[assignment]
    socket.socket.connect = _blocked  # type: ignore[assignment]
    socket.socket.connect_ex = _blocked  # type: ignore[assignment]


def main() -> int:
    if len(sys.argv) < 2:
        print("sandbox_runner: missing mirror db path", file=sys.stderr)
        return 2

    db_path = sys.argv[1]
    script = sys.stdin.read()

    import sqlite3
    from decimal import Decimal

    _disable_network()

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    def q(sql, params=()):
        """Read-only SELECT → list of tuples."""
        return conn.execute(sql, params).fetchall()

    def qd(sql, params=()):
        """Read-only SELECT → list of dicts (keyed by column name)."""
        cur = conn.execute(sql, params)
        cols = [d[0] for d in cur.description] if cur.description else []
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    g = {
        "__name__": "__sandbox__",
        "__builtins__": __builtins__,
        "db": conn,
        "q": q,
        "qd": qd,
        "D": Decimal,
    }

    try:
        exec(compile(script, "<sandbox>", "exec"), g)
    except SystemExit:
        raise
    except BaseException:  # noqa: BLE001 — hand the model the full traceback
        import traceback

        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
