import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { setFocus } from "../focus";

/* Select any text in the app → a floating "✦ Ask about this" appears near it →
 * clicking captures the highlighted text as assistant focus and opens the chat.
 * The general escape hatch for anything without its own ✦ affordance: KPI tiles,
 * notes, chart labels, prose. Selections inside the chat drawer are ignored. */

const SCREEN_NAMES: Record<string, string> = {
  "/": "Overview",
  "/pnl": "Profit & loss",
  "/costs": "Cost structure",
  "/clients": "Clients & invoices",
  "/payroll": "Payroll",
  "/projection": "Year projection",
};

function screenName(path: string): string {
  if (path.startsWith("/accounts/")) return `Account ${path.split("/")[2]}`;
  return SCREEN_NAMES[path] ?? "";
}

function inChrome(node: Node | null): boolean {
  const el = node instanceof Element ? node : node?.parentElement;
  return !!el?.closest(".chat-drawer, .sel-ask, .chat-fab");
}

export function SelectionAsk() {
  const location = useLocation();
  const [pop, setPop] = useState<{ x: number; y: number; text: string } | null>(null);

  useEffect(() => {
    const onMouseUp = () => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed) return;
      const text = sel.toString().trim();
      if (text.length < 2) return;
      if (inChrome(sel.anchorNode) || inChrome(sel.focusNode)) return;
      const rect = sel.getRangeAt(0).getBoundingClientRect();
      if (!rect.width && !rect.height) return;
      setPop({ x: rect.left + rect.width / 2, y: rect.top, text });
    };
    const onMouseDown = (e: MouseEvent) => {
      if (e.target instanceof Element && e.target.closest(".sel-ask")) return;
      setPop(null);
    };
    const onScroll = () => setPop(null);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setPop(null);

    document.addEventListener("mouseup", onMouseUp);
    document.addEventListener("mousedown", onMouseDown);
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mouseup", onMouseUp);
      document.removeEventListener("mousedown", onMouseDown);
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("keydown", onKey);
    };
  }, []);

  // drop the popover when the page changes
  useEffect(() => setPop(null), [location.pathname]);

  if (!pop) return null;

  const ask = () => {
    const { text } = pop;
    const label = text.length > 44 ? `${text.slice(0, 44).trim()}…` : text;
    setFocus({ kind: "selection", label, text, screen: screenName(location.pathname) });
    window.dispatchEvent(new CustomEvent("fi:open-chat"));
    window.getSelection()?.removeAllRanges();
    setPop(null);
  };

  return (
    <button
      className="sel-ask"
      style={{ left: pop.x, top: pop.y }}
      // preventDefault on mousedown keeps the text selection alive through the click
      onMouseDown={(e) => e.preventDefault()}
      onClick={ask}
    >
      ✦ Ask about this
    </button>
  );
}
