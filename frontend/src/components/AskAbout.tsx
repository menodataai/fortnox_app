import { setFocus, type Focus } from "../focus";

/** A small "✦" affordance for rows/cards whose PRIMARY click does something
 *  else (navigate to an account, open a voucher). Clicking it captures the row
 *  as assistant focus and opens the chat, without triggering the row's own
 *  click (stopPropagation). Hidden until the row is hovered/focused — see the
 *  `.ask-about` rules in styles.css. */
export function AskAbout({ focus }: { focus: Focus }) {
  return (
    <button
      type="button"
      className="ask-about"
      aria-label={`Ask the assistant about ${focus.label}`}
      title="Ask the assistant about this"
      onClick={(e) => {
        e.stopPropagation();
        setFocus(focus);
        window.dispatchEvent(new CustomEvent("fi:open-chat"));
      }}
    >
      ✦
    </button>
  );
}
