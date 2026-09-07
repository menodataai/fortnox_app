import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { VoucherModal } from "./VoucherModal";
import { clearFocus, getFocus, subscribeFocus, type Focus } from "../focus";

/* ── types ─────────────────────────────────────────────────── */

type ToolItem = {
  kind: "tool";
  id: string;
  name: string;
  args: string;
  done: boolean;
  ok?: boolean;
  summary?: string;
};
type Item =
  | { kind: "user"; text: string }
  | { kind: "assistant"; text: string }
  | ToolItem
  | { kind: "error"; text: string };

type SseEvent =
  | { type: "session"; session_id: string }
  | { type: "text"; delta: string }
  | { type: "thinking" }
  | { type: "tool_start"; id: string; name: string; args: string }
  | { type: "tool_result"; id: string; ok: boolean; summary: string }
  | { type: "done"; usage: { input_tokens: number; output_tokens: number; requests: number } }
  | { type: "error"; message: string };

/* ── per-page suggested questions ──────────────────────────── */

function suggestionsFor(path: string): string[] {
  if (path.startsWith("/accounts/")) {
    const n = path.split("/")[2];
    return [
      `What's behind account ${n} this year?`,
      `Are there recurring charges on account ${n}?`,
      `Explain what account ${n} is used for`,
    ];
  }
  const map: Record<string, string[]> = {
    "/": [
      "How are we doing this year?",
      "What needs my attention right now?",
      "Why did profit change last month?",
    ],
    "/pnl": [
      "Which costs grew the most this year?",
      "Explain 'Other external costs' — what's in it?",
    ],
    "/costs": [
      "Which of my costs are one-offs this year?",
      "Which subscriptions are we paying for?",
    ],
    "/clients": [
      "How dependent are we on our biggest client?",
      "Which invoices are still unpaid?",
    ],
    "/payroll": [
      "Explain my total payroll cost step by step",
      "Is the arbetsgivaravgift on the last payslip correct?",
    ],
    "/projection": [
      "Project our year-end profit after tax",
      "How much corporate tax should we expect?",
    ],
  };
  return map[path] ?? map["/"];
}

/** Default question when the user hits Send with a context chip but no text. */
function defaultQuestionFor(focus: Focus | null): string {
  if (!focus) return "";
  switch (focus.kind) {
    case "voucher":
      return "Explain this voucher — what is it, and what does it mean for the business?";
    case "payroll_month":
      return "Break down this month's payroll cost — what makes it up and why?";
    case "cost_item":
      return `What's behind "${focus.name}"? Break it down and flag anything worth a look.`;
    case "selection":
      return "Explain this — what does it mean and how is it calculated?";
    default:
      return "Explain what I'm looking at.";
  }
}

/* ── citation + markdown-lite rendering ────────────────────── */

const CITE_RE = /\[(voucher|account|invoice|source):([^\]\s]+)\]/g;

function renderInline(
  text: string,
  keyBase: string,
  openVoucher: (s: string, n: number, y?: number) => void,
): React.ReactNode[] {
  // split citations first, then bold/code inside the plain segments
  const out: React.ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  CITE_RE.lastIndex = 0;
  while ((m = CITE_RE.exec(text))) {
    if (m.index > last) out.push(...renderStyled(text.slice(last, m.index), `${keyBase}-t${i}`));
    const [, kind, ref] = m;
    const key = `${keyBase}-c${i++}`;
    if (kind === "voucher") {
      const [sn, y] = ref.split("@");
      const [series, num] = sn.split("/");
      out.push(
        <button
          key={key}
          className="cite"
          onClick={() => openVoucher(series, parseInt(num, 10), y ? parseInt(y, 10) : undefined)}
        >
          {sn}
          {y ? `·${y}` : ""}
        </button>,
      );
    } else if (kind === "account") {
      const [num] = ref.split("@");
      out.push(
        <Link key={key} className="cite" to={`/accounts/${num}`}>
          {num}
        </Link>,
      );
    } else if (kind === "source") {
      let host = ref;
      try {
        host = new URL(ref).hostname.replace(/^www\d?\./, "");
      } catch {
        /* keep raw */
      }
      out.push(
        <a key={key} className="cite" href={ref} target="_blank" rel="noreferrer">
          {host} ↗
        </a>,
      );
    } else {
      out.push(
        <Link key={key} className="cite" to="/clients">
          invoice {ref}
        </Link>,
      );
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(...renderStyled(text.slice(last), `${keyBase}-tail`));
  return out;
}

function renderStyled(text: string, keyBase: string): React.ReactNode[] {
  // **bold** and `code`
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((seg, i) => {
    if (seg.startsWith("**") && seg.endsWith("**"))
      return <b key={`${keyBase}-${i}`}>{seg.slice(2, -2)}</b>;
    if (seg.startsWith("`") && seg.endsWith("`"))
      return <code key={`${keyBase}-${i}`}>{seg.slice(1, -1)}</code>;
    return seg;
  });
}

function AssistantText({
  text,
  openVoucher,
}: {
  text: string;
  openVoucher: (s: string, n: number, y?: number) => void;
}) {
  const blocks: React.ReactNode[] = [];
  let list: React.ReactNode[] = [];
  let table: string[][] = [];
  const flushList = (key: string) => {
    if (list.length) {
      blocks.push(<ul key={key}>{list}</ul>);
      list = [];
    }
  };
  const flushTable = (key: string) => {
    if (!table.length) return;
    const [head, ...rows] = table;
    blocks.push(
      <table key={key}>
        <thead>
          <tr>
            {head.map((c, j) => (
              <th key={j}>{renderInline(c, `${key}-h${j}`, openVoucher)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, ri) => (
            <tr key={ri}>
              {r.map((c, j) => (
                <td key={j}>{renderInline(c, `${key}-${ri}-${j}`, openVoucher)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>,
    );
    table = [];
  };
  text.split("\n").forEach((line, i) => {
    const key = `l${i}`;
    const t = line.trim();
    if (t.startsWith("|") && t.endsWith("|") && t.length > 2) {
      const cells = t.slice(1, -1).split("|").map((c) => c.trim());
      if (!cells.every((c) => /^:?-{2,}:?$/.test(c))) table.push(cells); // skip |---|---|
      return;
    }
    flushTable(`tbl-${i}`);
    if (/^[-*•] /.test(t)) {
      list.push(<li key={key}>{renderInline(t.slice(2), key, openVoucher)}</li>);
      return;
    }
    flushList(`ul-${i}`);
    if (t.startsWith("### ") || t.startsWith("## ") || t.startsWith("# ")) {
      blocks.push(<h4 key={key}>{renderInline(t.replace(/^#+ /, ""), key, openVoucher)}</h4>);
    } else if (t && t !== "---") {
      blocks.push(<p key={key}>{renderInline(t, key, openVoucher)}</p>);
    }
  });
  flushList("ul-end");
  flushTable("tbl-end");
  return <div className="chat-md">{blocks}</div>;
}

/* ── the drawer ────────────────────────────────────────────── */

const SESSION_KEY = "fi-chat-session";
const WIDTH_KEY = "fi-chat-width";
const DEFAULT_WIDTH = 440;
const MIN_WIDTH = 340;

/** Keep the drawer between MIN_WIDTH and (nearly) the viewport width, so a
 *  stored width can never leave it wider than the screen after a resize. */
function clampWidth(w: number): number {
  const max = Math.max(MIN_WIDTH, window.innerWidth - 32);
  return Math.min(Math.max(w, MIN_WIDTH), max);
}

export function ChatDrawer() {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Item[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(
    () => sessionStorage.getItem(SESSION_KEY),
  );
  const [voucher, setVoucher] = useState<{ series: string; number: number; year?: number } | null>(
    null,
  );
  const [focus, setFocusState] = useState<Focus | null>(getFocus());
  const [width, setWidth] = useState<number>(() => {
    const saved = Number(localStorage.getItem(WIDTH_KEY));
    return clampWidth(saved > 0 ? saved : DEFAULT_WIDTH);
  });
  const abortRef = useRef<AbortController | null>(null);
  const bodyRef = useRef<HTMLDivElement | null>(null);

  // keep the width valid when the window shrinks below the stored size
  useEffect(() => {
    const onResize = () => setWidth((w) => clampWidth(w));
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  // drag the left edge to resize; the handle sits at the drawer's left, so the
  // width is simply the distance from the pointer to the right edge.
  const startResize = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    const handle = e.currentTarget;
    handle.setPointerCapture(e.pointerId);
    const onMove = (ev: PointerEvent) => setWidth(clampWidth(window.innerWidth - ev.clientX));
    const onUp = (ev: PointerEvent) => {
      handle.releasePointerCapture(e.pointerId);
      handle.removeEventListener("pointermove", onMove);
      handle.removeEventListener("pointerup", onUp);
      localStorage.setItem(WIDTH_KEY, String(clampWidth(window.innerWidth - ev.clientX)));
    };
    handle.addEventListener("pointermove", onMove);
    handle.addEventListener("pointerup", onUp);
  }, []);

  const resetWidth = useCallback(() => {
    const w = clampWidth(DEFAULT_WIDTH);
    setWidth(w);
    localStorage.setItem(WIDTH_KEY, String(w));
  }, []);

  // open from anywhere (sidebar nav item)
  useEffect(() => {
    const onOpen = () => setOpen(true);
    window.addEventListener("fi:open-chat", onOpen);
    return () => window.removeEventListener("fi:open-chat", onOpen);
  }, []);

  // mirror the shared UI-focus store into local state (for the FAB label + chip)
  useEffect(() => subscribeFocus(setFocusState), []);

  // focus is a pointer to something on the current page; drop it when the page
  // changes so we never attach stale context from a screen the user has left.
  useEffect(() => {
    clearFocus();
  }, [location.pathname]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && !voucher && setOpen(false);
    if (open) window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, voucher]);

  // restore transcript for a persisted session
  useEffect(() => {
    if (!sessionId) return;
    fetch(`/api/chat/sessions/${sessionId}`)
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then((d: { messages: { role: string; text?: string; tool?: string; id?: string; args?: string }[] }) => {
        const restored: Item[] = [];
        for (const m of d.messages) {
          if (m.role === "user") restored.push({ kind: "user", text: m.text ?? "" });
          else if (m.role === "assistant") restored.push({ kind: "assistant", text: m.text ?? "" });
          else if (m.role === "tool_call")
            restored.push({
              kind: "tool",
              id: m.id ?? "",
              name: m.tool ?? "",
              args: m.args ?? "",
              done: true,
              ok: true,
            });
        }
        setItems(restored);
      })
      .catch(() => {
        sessionStorage.removeItem(SESSION_KEY);
        setSessionId(null);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight });
  }, [items, streaming]);

  const send = useCallback(
    async (text: string) => {
      if (streaming) return;
      // With a context chip attached, an empty send means "explain this" — fall
      // back to a sensible default question for whatever is in focus.
      const focused = getFocus();
      const message = text.trim() || defaultQuestionFor(focused);
      if (!message) return;
      setInput("");
      setItems((prev) => [...prev, { kind: "user", text: message }]);
      setStreaming(true);

      const pageContext: Record<string, unknown> = { page: location.pathname };
      const acctMatch = location.pathname.match(/^\/accounts\/(\d+)/);
      if (acctMatch) pageContext.account = parseInt(acctMatch[1], 10);
      if (focused) pageContext.focus = focused;
      // Focus is per-question: consume it here so the chip clears and a stale
      // pointer never rides the next turn. Follow-ups rely on chat history;
      // re-point (hover/open) to attach something new.
      clearFocus();

      const ctrl = new AbortController();
      abortRef.current = ctrl;
      try {
        const resp = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message,
            session_id: sessionId,
            page_context: pageContext,
          }),
          signal: ctrl.signal,
        });
        if (!resp.ok || !resp.body) {
          const body = (await resp.json().catch(() => ({}))) as { detail?: string };
          throw new Error(body.detail ?? `HTTP ${resp.status}`);
        }
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          const chunks = buf.split("\n\n");
          buf = chunks.pop() ?? "";
          for (const chunk of chunks) {
            const line = chunk.split("\n").find((l) => l.startsWith("data: "));
            if (!line) continue;
            const ev = JSON.parse(line.slice(6)) as SseEvent;
            handleEvent(ev);
          }
        }
      } catch (e) {
        if ((e as Error).name !== "AbortError")
          setItems((prev) => [...prev, { kind: "error", text: (e as Error).message }]);
      } finally {
        setStreaming(false);
        abortRef.current = null;
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [sessionId, streaming, location.pathname],
  );

  const handleEvent = (ev: SseEvent) => {
    switch (ev.type) {
      case "session":
        setSessionId(ev.session_id);
        sessionStorage.setItem(SESSION_KEY, ev.session_id);
        break;
      case "text":
        setItems((prev) => {
          const lastItem = prev[prev.length - 1];
          if (lastItem?.kind === "assistant")
            return [...prev.slice(0, -1), { kind: "assistant", text: lastItem.text + ev.delta }];
          return [...prev, { kind: "assistant", text: ev.delta }];
        });
        break;
      case "tool_start":
        setItems((prev) => [
          ...prev,
          { kind: "tool", id: ev.id, name: ev.name, args: ev.args, done: false },
        ]);
        break;
      case "tool_result":
        setItems((prev) =>
          prev.map((it) =>
            it.kind === "tool" && it.id === ev.id
              ? { ...it, done: true, ok: ev.ok, summary: ev.summary }
              : it,
          ),
        );
        break;
      case "error":
        setItems((prev) => [...prev, { kind: "error", text: ev.message }]);
        break;
      default:
        break;
    }
  };

  const newChat = () => {
    abortRef.current?.abort();
    sessionStorage.removeItem(SESSION_KEY);
    setSessionId(null);
    setItems([]);
  };

  const openVoucher = (series: string, number: number, year?: number) =>
    setVoucher({ series, number, year });

  const acct = location.pathname.match(/^\/accounts\/(\d+)/)?.[1];

  return (
    <>
      {!open && (
        <button
          className="chat-fab"
          onClick={() => setOpen(true)}
          aria-label={focus ? `Ask the AI assistant about ${focus.label}` : "Ask the AI assistant"}
        >
          ✦ {focus ? "Ask about this" : "Ask"}
        </button>
      )}
      {open && (
        <aside className="chat-drawer" aria-label="AI assistant" style={{ width }}>
          <div
            className="chat-resizer"
            onPointerDown={startResize}
            onDoubleClick={resetWidth}
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize assistant panel (double-click to reset)"
            title="Drag to resize · double-click to reset"
          />
          <div className="chat-head">
            <div>
              <b>✦ Assistant</b>
              <small>read-only · every number traceable</small>
            </div>
            <div className="chat-head-actions">
              <button className="link-button" onClick={newChat} disabled={streaming && !sessionId}>
                New chat
              </button>
              <button className="modal-close" onClick={() => setOpen(false)} aria-label="Close">
                ✕
              </button>
            </div>
          </div>

          <div className="chat-body" ref={bodyRef}>
            {items.length === 0 && (
              <div className="chat-suggest">
                <p>
                  Ask about your real numbers{acct ? ` — like account ${acct}` : ""}. Answers cite
                  the vouchers and accounts they came from.
                </p>
                {suggestionsFor(location.pathname).map((q) => (
                  <button key={q} onClick={() => send(q)}>
                    {q}
                  </button>
                ))}
              </div>
            )}
            {items.map((it, i) => {
              if (it.kind === "user")
                return (
                  <div key={i} className="chat-msg user">
                    {it.text}
                  </div>
                );
              if (it.kind === "assistant")
                return (
                  <div key={i} className="chat-msg assistant">
                    <AssistantText text={it.text} openVoucher={openVoucher} />
                  </div>
                );
              if (it.kind === "error")
                return (
                  <div key={i} className="chat-msg error">
                    {it.text}
                  </div>
                );
              return (
                <details key={i} className={`chat-tool${it.done ? "" : " running"}`}>
                  <summary>
                    <span className="tool-dot" data-ok={it.ok !== false} />
                    {it.name}
                    {!it.done && "…"}
                  </summary>
                  <div className="tool-detail">
                    <div className="tool-args">{it.args}</div>
                    {it.summary && <div className="tool-summary">{it.summary}</div>}
                  </div>
                </details>
              );
            })}
            {streaming && <div className="chat-pulse">working…</div>}
          </div>

          {focus && (
            <div className="chat-context" title="The assistant will use this as context">
              <span className="ctx-label">✦ About: {focus.label}</span>
              <button
                className="ctx-clear"
                onClick={() => clearFocus()}
                aria-label="Remove context"
                title="Remove context"
              >
                ✕
              </button>
            </div>
          )}
          <div className="chat-input">
            <textarea
              value={input}
              placeholder={focus ? "Ask about this — or just hit Send…" : "Ask about your numbers…"}
              rows={2}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send(input);
                }
              }}
            />
            {streaming ? (
              <button className="button" onClick={() => abortRef.current?.abort()}>
                Stop
              </button>
            ) : (
              <button
                className="button"
                onClick={() => send(input)}
                disabled={!input.trim() && !focus}
              >
                Send
              </button>
            )}
          </div>
          <div className="chat-foot">
            Estimates, not tax advice — confirm important conclusions with your accountant.
          </div>
        </aside>
      )}
      {voucher && (
        <VoucherModal
          series={voucher.series}
          number={voucher.number}
          year={voucher.year}
          onClose={() => setVoucher(null)}
        />
      )}
    </>
  );
}
