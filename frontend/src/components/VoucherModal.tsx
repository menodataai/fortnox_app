import { useEffect, useState } from "react";
import { api, krPlain } from "../api";
import { setFocus } from "../focus";
import type { Voucher } from "../types";

interface Props {
  series: string;
  number: number;
  year?: number;
  onClose: () => void;
}

export function VoucherModal({ series, number, year, onClose }: Props) {
  const [voucher, setVoucher] = useState<Voucher | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .voucher(series, number, year)
      .then(setVoucher)
      .catch((e) => setError(String(e.message ?? e)));
  }, [series, number, year]);

  // While this voucher is on screen, it's what "this" refers to for the assistant.
  useEffect(() => {
    if (!voucher) return;
    setFocus({
      kind: "voucher",
      label: `Voucher ${voucher.series}-${voucher.number}`,
      series: voucher.series,
      number: voucher.number,
      date: voucher.date,
      description: voucher.description,
      rows: voucher.rows,
    });
  }, [voucher]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const hasVat = voucher?.rows.some((r) => r.account >= 2610 && r.account <= 2649);

  return (
    <div className="modal-scrim" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={`Voucher ${series}-${number}`}>
        <div className="modal-head">
          <h2>{voucher?.description || "Voucher"}</h2>
          <span className="vno">
            {series}-{number}
            {voucher?.date ? ` · ${voucher.date}` : ""}
          </span>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <div className="modal-sub">Booked in Fortnox · series {series}</div>
        {error && <div className="error-banner">{error}</div>}
        {voucher && (
          <>
            <div className="tbl-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Account</th>
                    <th style={{ minWidth: 180 }}>Name</th>
                    <th className="num">Debit</th>
                    <th className="num">Credit</th>
                  </tr>
                </thead>
                <tbody>
                  {voucher.rows.map((r, i) => (
                    <tr key={i}>
                      <td>{r.account}</td>
                      <td style={{ whiteSpace: "normal" }}>{r.name}</td>
                      <td className="num">{r.debit != null ? krPlain(r.debit) : ""}</td>
                      <td className="num">{r.credit != null ? krPlain(r.credit) : ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {hasVat && (
              <div className="explain">
                <b>Reading this voucher:</b> rows on 26xx accounts are VAT (moms) — the
                company either owes it to or reclaims it from Skatteverket. Only the
                other rows affect your profit.
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
