"""Conversation persistence: Pydantic AI's own serialized ModelMessage lists,
one row per agent run, in mirror.db. Replay is lossless and framework-native."""

import json
import uuid
from datetime import datetime, timezone

from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from .. import db

RECENT_RUNS_VERBATIM = 10
STUB = "[tool output elided — older turn]"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_session(model: str, page_context: dict | None, title: str) -> str:
    session_id = uuid.uuid4().hex[:12]
    with db.session() as conn:
        conn.execute(
            "INSERT INTO chat_sessions (id, title, created_at, model, page_context)"
            " VALUES (?, ?, ?, ?, ?)",
            (session_id, title[:80], _now(), model, json.dumps(page_context or {})),
        )
    return session_id


def session_exists(session_id: str) -> bool:
    with db.session() as conn:
        return conn.execute(
            "SELECT 1 FROM chat_sessions WHERE id = ?", (session_id,)
        ).fetchone() is not None


def append_run(session_id: str, messages_json: bytes | str, usage: dict | None) -> None:
    if isinstance(messages_json, bytes):
        messages_json = messages_json.decode()
    with db.session() as conn:
        seq = conn.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 AS n FROM chat_messages WHERE session_id = ?",
            (session_id,),
        ).fetchone()["n"]
        conn.execute(
            "INSERT INTO chat_messages (session_id, seq, messages_json, usage_json, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (session_id, seq, messages_json, json.dumps(usage or {}), _now()),
        )


def load_history(session_id: str) -> list[ModelMessage]:
    """Full history, windowed: the last N runs verbatim; older runs keep their
    text but tool-return payloads are replaced with one-line stubs."""
    with db.session() as conn:
        rows = conn.execute(
            "SELECT messages_json FROM chat_messages WHERE session_id = ? ORDER BY seq",
            (session_id,),
        ).fetchall()

    messages: list[ModelMessage] = []
    cutoff = len(rows) - RECENT_RUNS_VERBATIM
    for i, row in enumerate(rows):
        run_msgs = ModelMessagesTypeAdapter.validate_json(row["messages_json"])
        if i < cutoff:
            for msg in run_msgs:
                for part in msg.parts:
                    if isinstance(part, ToolReturnPart):
                        part.content = STUB
        messages.extend(run_msgs)
    return messages


def list_sessions() -> list[dict]:
    with db.session() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT s.id, s.title, s.created_at, s.model,"
            " (SELECT COUNT(*) FROM chat_messages m WHERE m.session_id = s.id) AS runs"
            " FROM chat_sessions s ORDER BY s.created_at DESC"
        )]


def delete_session(session_id: str) -> None:
    with db.session() as conn:
        conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))


def display_messages(session_id: str) -> list[dict]:
    """Flatten stored runs into UI-friendly items: user / assistant text and
    the tool trace, in order."""
    items: list[dict] = []
    for msg in load_history(session_id):
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, UserPromptPart) and isinstance(part.content, str):
                    text = part.content
                    if text.startswith("<context>"):
                        text = text.split("</context>", 1)[-1].lstrip()
                    items.append({"role": "user", "text": text})
                elif isinstance(part, ToolReturnPart):
                    items.append({
                        "role": "tool_result",
                        "tool": part.tool_name,
                        "id": part.tool_call_id,
                        "ok": True,
                    })
        elif isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, TextPart) and part.content.strip():
                    items.append({"role": "assistant", "text": part.content})
                elif isinstance(part, ToolCallPart):
                    items.append({
                        "role": "tool_call",
                        "tool": part.tool_name,
                        "id": part.tool_call_id,
                        "args": part.args if isinstance(part.args, str) else json.dumps(part.args or {}),
                    })
    return items
