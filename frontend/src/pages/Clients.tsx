import { useEffect, useState } from "react";
import { api, krPlain } from "../api";
import type { ClientsOverview } from "../types";

const STATUS: Record<string, { label: string; cls: string; icon: string }> = {
  paid: { label: "Paid", cls: "good", icon: "✓" },
  open: { label: "Awaiting payment", cls: "info", icon: "◔" },
  overdue: { label: "Overdue", cls: "critical", icon: "⚠" },
};

export function Clients() {
  const [data, setData] = useState<ClientsOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.clients().then(setData).catch((e) => setError(String(e.message ?? e)));
  }, []);

  if (error) return <div className="error-banner">{error}</div>;
  if (!data) return <p className="empty">Loading…</p>;

  const top = data.clients[0];

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Clients &amp; invoices</h1>
          <div className="sub">Who pays you, how much, and how fast</div>
        </div>
        <div className="spacer" />
        <span className="period">
          Financial year <b>{data.year}</b>
        </span>
      </div>

      {top && top.share_fy >= 0.6 && (
        <div className="risk">
          <span aria-hidden="true">⚠</span>
          <span>
            <b>
              {Math.round(top.share_fy * 100)}% of {data.year} revenue comes from {top.name}.
            </b>{" "}
            Client concentration is the company's biggest business risk — if the engagement
            ends, your fixed costs continue. See the runway figure on the Cost structure page.
          </span>
        </div>
      )}

      <div className="tiles">
        <div className="card tile">
          <div className="label">Invoiced, year to date</div>
          <div className="value">
            {krPlain(data.invoiced_total)} <small>kr</small>
          </div>
          <div className="note">{data.invoice_count} invoices · amounts incl. VAT</div>
        </div>
        <div className="card tile">
          <div className="label">Outstanding</div>
          <div className="value">
            {krPlain(data.outstanding_total)} <small>kr</small>
          </div>
          <div className="note">
            {data.outstanding_count} invoice{data.outstanding_count === 1 ? "" : "s"} unpaid
          </div>
        </div>
        <div className="card tile">
          <div className="label">Average time to payment</div>
          <div className="value">
            {data.avg_days_to_pay ?? "—"} <small>days</small>
          </div>
          <div className="note">across all paid invoices</div>
        </div>
        <div className="card tile">
          <div className="label">Active clients</div>
          <div className="value">{data.active_clients}</div>
          <div className="note">{data.clients.length} in total in Fortnox</div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <h2>Clients</h2>
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Client</th>
                <th>Status</th>
                <th className="num">Invoiced {data.year}</th>
                <th>Share of revenue</th>
                <th className="num">Avg days to pay</th>
                <th>Last invoice</th>
              </tr>
            </thead>
            <tbody>
              {data.clients.map((c) => (
                <tr key={c.name} className={c.active ? "" : "muted-row"}>
                  <td>{c.active ? <b>{c.name}</b> : c.name}</td>
                  <td>
                    {c.active ? (
                      <span className="badge good">✓ Active</span>
                    ) : (
                      <span className="badge info">◌ Inactive</span>
                    )}
                  </td>
                  <td className="num">{krPlain(c.invoiced_fy)}</td>
                  <td>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                      <span className="share-track">
                        <span
                          className="share-fill"
                          style={{ width: `${Math.round(c.share_fy * 100)}%` }}
                        />
                      </span>
                      {c.share_fy > 0 ? `${Math.round(c.share_fy * 100)}%` : "—"}
                    </span>
                  </td>
                  <td className="num">{c.avg_days_to_pay ?? "—"}</td>
                  <td>
                    {c.last_invoice_date
                      ? `#${c.last_invoice_number} · ${c.last_invoice_date}`
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <h2>Invoices {data.year}</h2>
        <div className="card-sub">Via Fortnox Faktura · amounts incl. VAT</div>
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Invoice</th>
                <th>Client</th>
                <th>Sent</th>
                <th>Due</th>
                <th>Paid</th>
                <th className="num">Amount</th>
                <th className="num">Balance</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.invoices.map((i) => {
                const s = STATUS[i.status];
                return (
                  <tr key={i.document_number}>
                    <td>#{i.document_number}</td>
                    <td>{i.customer_name}</td>
                    <td>{i.invoice_date ?? "—"}</td>
                    <td>{i.due_date ?? "—"}</td>
                    <td>{i.final_pay_date ?? "—"}</td>
                    <td className="num">{krPlain(i.total)}</td>
                    <td className="num">{i.balance > 0 ? krPlain(i.balance) : ""}</td>
                    <td>
                      <span className={`badge ${s.cls}`}>
                        <span aria-hidden="true">{s.icon}</span> {s.label}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="showing">
          Ledger revenue on the Overview excludes VAT — invoice totals here include it, so the
          sums differ by design.
        </div>
      </div>
    </>
  );
}
