"""Agent-flow tests without tokens: Pydantic AI TestModel drives the full
loop — tool dispatch, SSE event emission, history persistence — through the
real FastAPI endpoint. Zero API cost.

Run: .venv/bin/python tests/test_agent_flow.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db, sie  # noqa: E402

# Fixture mirror BEFORE importing app.main (the system prompt reads the DB)
db.DB_PATH = Path(tempfile.mkdtemp()) / "mirror-agent-test.db"

from app.sync import _store_ledger  # noqa: E402
from tests.test_pipeline import SAMPLE_SIE  # noqa: E402

_store_ledger(1, sie.parse(SAMPLE_SIE))
with db.session() as conn:
    conn.execute(
        "INSERT OR REPLACE INTO financial_years (id, from_date, to_date)"
        " VALUES (1, '2026-01-01', '2026-12-31')"
    )

from fastapi.testclient import TestClient  # noqa: E402
from pydantic_ai.models.test import TestModel  # noqa: E402

from app.ai import router as ai_router  # noqa: E402
from app.ai import tools, verify  # noqa: E402
from app.ai.verify import Finding, VerificationReport  # noqa: E402
from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402

# Only offline tools — TestModel calls every allowed tool with dummy args,
# and web_search/fetch_page would hit the network.
_DEFAULT_TEST_MODEL = lambda: TestModel(  # noqa: E731
    call_tools=["get_financial_years", "get_profit_and_loss"]
)
ai_router.build_model = _DEFAULT_TEST_MODEL
settings.openrouter_api_key = settings.openrouter_api_key or "test-key"

client = TestClient(app)


def _post_chat(payload: dict) -> list[dict]:
    events = []
    with client.stream("POST", "/api/chat", json=payload) as resp:
        assert resp.status_code == 200, resp.status_code
        assert resp.headers["content-type"].startswith("text/event-stream")
        for line in resp.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


def test_chat_flow() -> None:
    events = _post_chat({"message": "How are we doing this year?"})
    kinds = [e["type"] for e in events]

    assert kinds[0] == "session"
    session_id = events[0]["session_id"]
    assert "error" not in kinds, [e for e in events if e["type"] == "error"]

    starts = [e for e in events if e["type"] == "tool_start"]
    results = [e for e in events if e["type"] == "tool_result"]
    assert {s["name"] for s in starts} == {"get_financial_years", "get_profit_and_loss"}
    assert len(results) == len(starts) and all(r["ok"] for r in results)
    assert any(e["type"] == "text" for e in events)
    done = [e for e in events if e["type"] == "done"]
    assert len(done) == 1 and done[0]["usage"]["requests"] >= 1

    # persisted?
    with db.session() as conn:
        n = conn.execute(
            "SELECT COUNT(*) AS n FROM chat_messages WHERE session_id = ?", (session_id,)
        ).fetchone()["n"]
    assert n == 1

    # follow-up turn reuses the session and history
    events2 = _post_chat({"message": "And costs?", "session_id": session_id})
    assert events2[0]["session_id"] == session_id
    assert any(e["type"] == "done" for e in events2)
    with db.session() as conn:
        n = conn.execute(
            "SELECT COUNT(*) AS n FROM chat_messages WHERE session_id = ?", (session_id,)
        ).fetchone()["n"]
    assert n == 2
    print("chat flow OK")


def test_session_endpoints() -> None:
    sessions = client.get("/api/chat/sessions").json()["sessions"]
    assert len(sessions) >= 1 and sessions[0]["runs"] >= 1

    sid = sessions[0]["id"]
    detail = client.get(f"/api/chat/sessions/{sid}").json()
    roles = [m["role"] for m in detail["messages"]]
    assert "user" in roles and "assistant" in roles and "tool_call" in roles
    # volatile <context> block must be stripped from display
    user_msgs = [m for m in detail["messages"] if m["role"] == "user"]
    assert all(not m["text"].startswith("<context>") for m in user_msgs)

    assert client.delete(f"/api/chat/sessions/{sid}").json()["ok"]
    assert client.get(f"/api/chat/sessions/{sid}").status_code == 404
    print("session endpoints OK")


def test_unknown_session_404() -> None:
    resp = client.post("/api/chat", json={"message": "hi", "session_id": "nope"})
    assert resp.status_code == 404
    print("unknown session OK")


def test_run_python_in_stream() -> None:
    """run_python (F9 change 1) is wired into the agent loop and the SSE stream
    survives a script that errors (TestModel calls it with a dummy arg)."""
    ai_router.build_model = lambda: TestModel(call_tools=["run_python"])
    try:
        events = _post_chat({"message": "compute something"})
    finally:
        ai_router.build_model = _DEFAULT_TEST_MODEL
    kinds = [e["type"] for e in events]
    assert "error" not in kinds, [e for e in events if e["type"] == "error"]
    starts = [e for e in events if e["type"] == "tool_start"]
    assert any(s["name"] == "run_python" for s in starts)
    results = [e for e in events if e["type"] == "tool_result"]
    assert results and all(r["ok"] for r in results)  # tool never raises, even on script error
    assert any(e["type"] == "done" for e in events)
    print("run_python in stream OK")


def test_verify_draft_plumbing() -> None:
    """verify_draft (F9 change 2) invokes the verifier and surfaces its
    findings in the tool result; the SSE stream still completes."""
    original = verify.verifier

    class _StubVerifier:
        async def run(self, *_a, **_k):
            class _R:
                output = VerificationReport(
                    findings=[Finding(
                        claim="March one-off total",
                        verdict="wrong",
                        detail="54,900 kr, not 62,000 — the recurring ads line is not a one-off",
                    )],
                    ok=False,
                )
            return _R()

    verify.verifier = _StubVerifier()
    ai_router.build_model = lambda: TestModel(call_tools=["verify_draft"])
    try:
        events = _post_chat({"message": "why were costs higher in March?"})
    finally:
        verify.verifier = original
        ai_router.build_model = _DEFAULT_TEST_MODEL

    kinds = [e["type"] for e in events]
    assert "error" not in kinds, [e for e in events if e["type"] == "error"]
    starts = [e for e in events if e["type"] == "tool_start"]
    assert any(s["name"] == "verify_draft" for s in starts)
    vr = next(e for e in events if e["type"] == "tool_result")
    assert "wrong" in vr["summary"] and "findings" in vr["summary"]
    assert any(e["type"] == "done" for e in events)
    print("verify_draft plumbing OK")


def test_verify_draft_degrades_gracefully() -> None:
    """A verifier that exhausts its budget must NOT abort the user's answer:
    verify_draft returns an 'incomplete' signal and the stream still finishes.
    (Regression for the request_limit=6 abort.)"""
    from pydantic_ai import UsageLimitExceeded

    original = verify.verifier

    class _BrokeVerifier:
        async def run(self, *_a, **_k):
            raise UsageLimitExceeded("The next request would exceed the request_limit of 6")

    verify.verifier = _BrokeVerifier()
    ai_router.build_model = lambda: TestModel(call_tools=["verify_draft"])
    try:
        events = _post_chat({"message": "compute the tax effect"})
    finally:
        verify.verifier = original
        ai_router.build_model = _DEFAULT_TEST_MODEL

    kinds = [e["type"] for e in events]
    assert "error" not in kinds, [e for e in events if e["type"] == "error"]  # NOT aborted
    vr = next(e for e in events if e["type"] == "tool_result")
    assert vr["ok"] and "incomplete" in vr["summary"].lower(), vr
    assert any(e["type"] == "done" for e in events)
    print("verify_draft degrades gracefully OK")


def test_trigger_sync() -> None:
    """trigger_sync (F9 change 4) runs a sync when idle and, when one is
    already in flight, waits it out instead of double-starting."""
    import asyncio

    from app import sync

    orig_run, orig_sleep = sync.run, asyncio.sleep
    orig_state = dict(sync.state)
    called = {"run": 0}

    async def fake_run():
        called["run"] += 1
        sync.state.update(status="done", error=None, counts={"invoices": 3},
                          last_sync="2026-07-31T00:00:00")

    try:
        # (a) idle → triggers a sync
        sync.run = fake_run
        sync.state.update(status="idle", error=None, counts={}, last_sync=None)
        out = asyncio.run(tools.trigger_sync())
        assert out["status"] == "done" and out["counts"] == {"invoices": 3}
        assert called["run"] == 1, out

        # (b) already running → wait it out, never start a second
        called["run"] = 0
        sync.state.update(status="running")

        async def fake_sleep(_):  # first poll flips it to done
            sync.state.update(status="done")

        asyncio.sleep = fake_sleep
        out = asyncio.run(tools.trigger_sync())
        assert out["status"] == "done" and called["run"] == 0, out
    finally:
        sync.run, asyncio.sleep = orig_run, orig_sleep
        sync.state.clear()
        sync.state.update(orig_state)
    print("trigger_sync OK")


def main() -> None:
    test_chat_flow()
    test_session_endpoints()
    test_unknown_session_404()
    test_run_python_in_stream()
    test_verify_draft_plumbing()
    test_verify_draft_degrades_gracefully()
    test_trigger_sync()
    db.DB_PATH.unlink(missing_ok=True)
    print("ALL AGENT FLOW TESTS PASSED")


if __name__ == "__main__":
    main()
