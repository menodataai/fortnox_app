/* Shared "UI focus" store — the fine-grained thing the user is currently
 * pointing at (an open voucher, a hovered payroll bar). Views push a snapshot
 * here; the chat drawer reads it at send-time and shows it as a removable chip
 * so the assistant knows what "this" / "here" refers to.
 *
 * Deliberately a tiny module-level store (not React context / Redux): the
 * drawer only needs the current snapshot when sending, plus a subscription to
 * keep the chip in sync. Page-level context (route, account number) is NOT
 * kept here — the drawer already derives that from the URL. Only true in-page
 * pointers live here, so nothing sets focus on mount and route changes can
 * safely clear it without racing a page's own effects.
 */
import type { VoucherRow } from "./types";

export type Focus =
  | {
      kind: "voucher";
      /** short label for the context chip, e.g. "Voucher G-6" */
      label: string;
      series: string;
      number: number;
      date: string;
      description: string;
      rows: VoucherRow[];
    }
  | {
      kind: "payroll_month";
      label: string;
      year: number;
      /** display month, e.g. "Mar" */
      month: string;
      value: number;
    }
  | {
      kind: "cost_item";
      label: string;
      /** the line item's name, e.g. "Leasing av personbilar" */
      name: string;
      account: number | string | null;
      /** free-text detail for the model, e.g. "57,007 kr this period · 4.7% of costs" */
      detail?: string;
    }
  | {
      kind: "selection";
      label: string;
      /** the exact text the user highlighted on the page */
      text: string;
      /** the screen it was selected on, e.g. "Overview" */
      screen?: string;
    };

let current: Focus | null = null;
const listeners = new Set<(f: Focus | null) => void>();

export function setFocus(f: Focus | null): void {
  current = f;
  listeners.forEach((l) => l(current));
}

export function getFocus(): Focus | null {
  return current;
}

export function clearFocus(): void {
  setFocus(null);
}

export function subscribeFocus(fn: (f: Focus | null) => void): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}
