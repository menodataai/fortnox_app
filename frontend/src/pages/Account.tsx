import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, kr, krPlain, monthLabel } from "../api";
import type { AccountDetail } from "../types";
import { VoucherModal } from "../components/VoucherModal";

export function Account() {
  const { number } = useParams();
  const [data, setData] = useState<AccountDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [voucher, setVoucher] = useState<{ series: string; number: number } | null>(null);

  useEffect(() => {
    setData(null);
    api
      .account(Number(number))
      .then(setData)
      .catch((e) => setError(String(e.message ?? e)));
  }, [number]);

  const filtered = useMemo(() => {
    if (!data) return [];
    const q = search.trim().toLowerCase();
    if (!q) return data.transactions;
    return data.transactions.filter((t) =>
      `${t.description} ${t.series}-${t.voucher_number}`.toLowerCase().includes(q),
    );
  }, [data, search]);

  if (error) return <div className="error-banner">{error}</div>;
  if (!data) return <p className="empty">Loading…</p>;

  const maxMonthly = Math.max(1, ...data.monthly.map(Math.abs));

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Account explorer</h1>
          <div className="sub">Every transaction behind every number</div>
        </div>
        <div className="spacer" />
        <span className="period">
          Financial year <b>{data.year}</b>
        </span>
      </div>

      <div className="crumbs">
        <Link to="/pnl">Profit &amp; loss</Link> / {data.group} /{" "}
        <b>
          {data.number} {data.name}
        </b>
      </div>

      <div className="card">
        <div className="acct-head">
          <span className="no">Account {data.number}</span>
          <h2>{data.name}</h2>
        </div>
        {data.explain && (
          <div className="explain">
            <b>What this account is:</b> {data.explain}
          </div>
        )}
        <div className="acct-stats">
          {data.is_balance_account ? (
            <>
              <div className="s">
                <div className="l">Opening balance</div>
                <div className="v">{kr(data.ib)}</div>
              </div>
              <div className="s">
                <div className="l">Current balance</div>
                <div className="v">{kr(data.ub ?? 0)}</div>
              </div>
            </>
          ) : (
            <>
              <div className="s">
                <div className="l">Period total</div>
                <div className="v">{kr(data.period_total)}</div>
              </div>
              <div className="s">
                <div className="l">Monthly average (active months)</div>
                <div className="v">{kr(data.monthly_average)}</div>
              </div>
            </>
          )}
          <div className="s">
            <div className="l">Transactions</div>
            <div className="v">{data.transaction_count}</div>
          </div>
        </div>
        <div className="mini-chart" aria-label="Monthly activity">
          {data.monthly.map((v, i) => (
            <div
              key={i}
              className="mini-bar"
              title={`${monthLabel(data.months[i])} · ${kr(v)}`}
              style={{ height: `${(Math.abs(v) / maxMonthly) * 100}%`, minHeight: 2 }}
            />
          ))}
        </div>
        <div className="mini-x">
          {data.months.map((m) => (
            <span key={m}>{monthLabel(m)}</span>
          ))}
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div className="search-row">
          <input
            className="search-input"
            placeholder="Search descriptions — e.g. “AWS”"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search transactions"
          />
        </div>
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Voucher</th>
                <th style={{ minWidth: 220 }}>Description</th>
                <th className="num">Amount</th>
                <th className="num">{data.is_balance_account ? "Balance" : "Running total"}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((t, i) => (
                <tr
                  key={i}
                  className="clickable"
                  onClick={() => setVoucher({ series: t.series, number: t.voucher_number })}
                >
                  <td>{t.date}</td>
                  <td className="voucher-link">
                    {t.series}-{t.voucher_number}
                  </td>
                  <td style={{ whiteSpace: "normal" }}>{t.description || "—"}</td>
                  <td className="num">{krPlain(t.amount)}</td>
                  <td className="num">{krPlain(t.running)}</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={5} className="empty">
                    No transactions{search ? " matching your search" : " this year"}.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="showing">
          Showing {filtered.length} of {data.transaction_count} transactions · amounts in kr ·
          click a row to open the full voucher
        </div>
      </div>

      {voucher && (
        <VoucherModal
          series={voucher.series}
          number={voucher.number}
          onClose={() => setVoucher(null)}
        />
      )}
    </>
  );
}
