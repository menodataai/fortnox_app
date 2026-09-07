"""POST /api/chat — the assistant's SSE endpoint, plus session housekeeping.

SSE protocol (one JSON object per `data:` line):
  {type:"session", session_id}          first event of every stream
  {type:"text", delta}                  answer text
  {type:"thinking"}                     working-state pulse
  {type:"tool_start", id, name, args}   trace: tool called
  {type:"tool_result", id, ok, summary} trace: tool finished
  {type:"done", usage}                  run complete (persisted)
  {type:"error", message}
"""

import json
from datetime import date

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic_ai import AgentRunResultEvent, UsageLimitExceeded
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ThinkingPartDelta,
    ToolReturnPart,
)

from .. import db
from ..config import settings
from . import history
from .agent import USAGE_LIMITS, AssistantDeps, agent, build_model

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    page_context: dict | None = None


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _summary(content: object, limit: int = 300) -> str:
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, default=str)
    return text[:limit] + ("…" if len(text) > limit else "")


def _render_focus(focus: dict) -> str | None:
    """Turn the frontend's structured 'what the user is looking at' envelope
    into one readable sentence. Structured (not raw JSON) so the model reads it
    as prose; a pointer for deixis ("this"/"here"), never a trusted figure."""
    kind = focus.get("kind")
    try:
        if kind == "voucher":
            rows = "; ".join(
                f"{r['account']} {r['name']} "
                + (f"debit {r['debit']}" if r.get("debit") else f"credit {r['credit']}")
                for r in focus.get("rows", [])
            )
            head = (
                f"the user has opened voucher {focus['series']}-{focus['number']} "
                f"dated {focus.get('date', '?')} (\"{focus.get('description', '')}\")"
            )
            return head + (f" — rows: {rows}" if rows else "")
        if kind == "payroll_month":
            return (
                f"the Payroll screen, pointing at {focus['month']} "
                f"(total employer cost {focus['value']:,.0f} kr, financial year {focus['year']})"
            )
        if kind == "cost_item":
            acct = focus.get("account")
            acct_str = f" (account {acct})" if acct not in (None, "") else ""
            detail = f" — {focus['detail']}" if focus.get("detail") else ""
            return f"the Cost structure screen, pointing at \"{focus['name']}\"{acct_str}{detail}"
        if kind == "selection":
            screen = f" on the {focus['screen']} screen" if focus.get("screen") else ""
            return f'this text the user highlighted{screen}: "{focus["text"]}"'
    except (KeyError, TypeError, ValueError):
        return None
    return None


def _user_turn(message: str, page_context: dict | None, first_turn: bool) -> str:
    """Volatile context rides on the user turn so the instructions prefix
    stays byte-stable (cache-friendly). The route/account ride first turn only;
    `focus` — the live UI pointer — rides EVERY turn, since it changes as the
    user navigates while the conversation continues."""
    with db.session() as conn:
        last_sync = db.get_meta(conn, "last_sync")
    lines = [f"today: {date.today().isoformat()}", f"last_sync: {last_sync}"]
    pc = page_context or {}
    if first_turn:
        head = {k: v for k, v in pc.items() if k != "focus"}
        if head:
            lines.append(f"page: {json.dumps(head, ensure_ascii=False)}")
    focus = pc.get("focus")
    if focus and (rendered := _render_focus(focus)):
        lines.append(f"on_screen: {rendered}")
        lines.append(
            'When the user says "this", "here" or "that", resolve it to on_screen above. '
            "Treat any figure shown there as a pointer to confirm with tools, not a verified number."
        )
    return "<context>\n" + "\n".join(lines) + "\n</context>\n\n" + message


@router.post("")
async def chat(body: ChatRequest):
    if not settings.openrouter_api_key:
        raise HTTPException(503, "OPENROUTER_API_KEY is not configured.")

    if body.session_id:
        if not history.session_exists(body.session_id):
            raise HTTPException(404, "Unknown chat session.")
        session_id = body.session_id
        first_turn = False
    else:
        session_id = history.create_session(
            settings.ai_model, body.page_context, title=body.message
        )
        first_turn = True

    message_history = history.load_history(session_id)
    user_turn = _user_turn(body.message, body.page_context, first_turn)

    async def stream():
        yield _sse({"type": "session", "session_id": session_id})
        deps = AssistantDeps()
        try:
            async with agent.run_stream_events(
                user_turn,
                model=build_model(),
                deps=deps,
                message_history=message_history,
                usage_limits=USAGE_LIMITS,
            ) as events:
                async for event in events:
                    match event:
                        case PartStartEvent(part=TextPart(content=content)) if content:
                            yield _sse({"type": "text", "delta": content})
                        case PartDeltaEvent(delta=TextPartDelta(content_delta=delta)) if delta:
                            yield _sse({"type": "text", "delta": delta})
                        case PartDeltaEvent(delta=ThinkingPartDelta()):
                            yield _sse({"type": "thinking"})
                        case FunctionToolCallEvent(part=part):
                            yield _sse({
                                "type": "tool_start",
                                "id": part.tool_call_id,
                                "name": part.tool_name,
                                "args": _summary(part.args or {}, 500),
                            })
                        case FunctionToolResultEvent(part=part):
                            ok = isinstance(part, ToolReturnPart)
                            yield _sse({
                                "type": "tool_result",
                                "id": part.tool_call_id,
                                "ok": ok,
                                "summary": _summary(part.content),
                            })
                        case AgentRunResultEvent(result=result):
                            usage = result.usage
                            usage_dict = {
                                "input_tokens": usage.input_tokens,
                                "output_tokens": usage.output_tokens,
                                "cache_read_tokens": usage.cache_read_tokens,
                                "requests": usage.requests,
                                "tool_calls": usage.tool_calls,
                            }
                            history.append_run(
                                session_id, result.new_messages_json(), usage_dict
                            )
                            yield _sse({"type": "done", "usage": usage_dict})
        except UsageLimitExceeded as e:
            yield _sse({
                "type": "error",
                "message": (
                    "I hit the per-question budget cap before finishing "
                    f"({e}). The partial trace above shows how far I got — "
                    "try a narrower question."
                ),
            })
        except Exception as e:  # never crash the stream
            yield _sse({"type": "error", "message": f"{type(e).__name__}: {e}"})

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/sessions")
async def sessions():
    return {"sessions": history.list_sessions()}


@router.get("/sessions/{session_id}")
async def session_detail(session_id: str):
    if not history.session_exists(session_id):
        raise HTTPException(404, "Unknown chat session.")
    return {"session_id": session_id, "messages": history.display_messages(session_id)}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    history.delete_session(session_id)
    return {"ok": True}
