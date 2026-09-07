import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, kr, krPlain } from "../api";
import type { CostStructure as CostData } from "../types";
import { VoucherModal } from "../components/VoucherModal";
import { AskAbout } from "../components/AskAbout";

export function CostStructure() {
  const [data, setData] = useState<CostData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [voucher, setVoucher] = useState<{ series: string; number: number } | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.costs().then(setData).catch((e) => setError(String(e.message ?? e)));
  }, []);

  if (error) return <div className="error-banner">{error}</div>;
  if (!data) return <p className="empty">Loading…</p>;

  const maxTotal = Math.max(1, ...data.categories.map((c) => c.total));
  const personnelShare = data.categories.find((c) => c.label.startsWith("Personnel"))?.share ?? 0;

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Cost structure</h1>
          <div className="sub">Where the money goes, and what runs every month</div>
        </div>
        <div className="spacer" />
        <span className="period">
          Financial year <b>{data.year}</b>
        </span>
      </div>

      <div className="tiles">
        <div className="card tile">
          <div className="label">Total costs, year to date</div>
          <div className="value">
            {krPlain(data.total_costs)} <small>kr</small>
          </div>
          <div className="note">
            {Math.round(personnelShare * 100)}% personnel · {Math.round((1 - personnelShare) * 100)}%
            everything else
          </div>
        </div>
        <div className="card tile">
          <div className="label">Monthly burn rate</div>
          <div className="value">
            {krPlain(data.burn_per_month)} <small>kr</small>
          </div>
          <div className="note">recurring costs that run even when you don't bill</div>
        </div>
        <div className="card tile">
          <div className="label">One-off costs detected</div>
          <div className="value">
            {krPlain(data.oneoff_total)} <small>kr</small>
          </div>
          <div className="note">unusual transactions vs. each account's normal level</div>
        </div>
        {data.runway_months != null && (
          <div className="card tile">
            <div className="label">Cash runway</div>
            <div className="value">
              {data.runway_months} <small>months</small>
            </div>
            <div className="note">cash in bank ÷ monthly burn, if billing stopped today</div>
          </div>
        )}
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <h2>Where the money goes</h2>
        <div className="card-sub">
          Jan – {data.months[data.elapsed_months - 1]?.slice(0, 7)} · click a category to see its
          transactions
        </div>
        <div className="hbar-list">
          {data.categories.map((c, i) => (
            <div
              key={i}
              className={`hbar${c.account ? " clickable" : ""}`}
              onClick={() => c.account && navigate(`/accounts/${c.account}`)}
              role={c.account ? "link" : undefined}
            >
              <div className="hl">{c.label}</div>
              <div className="track">
                <div className="fill" style={{ width: `${(c.total / maxTotal) * 100}%` }} />
                <span className="hv">
                  {krPlain(c.total)} <small>· {(c.share * 100).toFixed(1)}%</small>
                </span>
                <AskAbout
                  focus={{
                    kind: "cost_item",
                    label: c.label,
                    name: c.label,
                    account: c.account,
                    detail: `${krPlain(c.total)} kr this period · ${(c.share * 100).toFixed(1)}% of costs (FY ${data.year})`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
        <div className="hint">
          Bars are proportional to spend. Your cost base is largely fixed — it runs whether or
          not you bill, which is why low-billing months show a loss.
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <h2>Recurring costs — detected automatically</h2>
        <div className="card-sub">Anything appearing at a similar amount every month or quarter</div>
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>What</th>
                <th>Account</th>
                <th>Frequency</th>
                <th className="num">Per month</th>
                <th className="num">Per year</th>
                <th>Trend</th>
                <th aria-label="Ask the assistant" />
              </tr>
            </thead>
            <tbody>
              {data.recurring.map((r, i) => (
                <tr
                  key={i}
                  className={typeof r.account === "number" ? "clickable" : ""}
                  onClick={() => typeof r.account === "number" && navigate(`/accounts/${r.account}`)}
                >
                  <td style={{ whiteSpace: "normal" }}>{r.label}</td>
                  <td>{r.account}</td>
                  <td>{r.frequency}</td>
                  <td className="num">{krPlain(r.per_month)}</td>
                  <td className="num">{krPlain(r.per_month * 12)}</td>
                  <td>
                    {Math.abs(r.trend) < 0.08 ? (
                      <span className="badge good">→ stable</span>
                    ) : r.trend > 0 ? (
                      <span className="badge warning">▲ +{Math.round(r.trend * 100)}%</span>
                    ) : (
                      <span className="badge good">▼ {Math.round(r.trend * 100)}%</span>
                    )}
                  </td>
                  <td className="row-action">
                    <AskAbout
                      focus={{
                        kind: "cost_item",
                        label: r.label,
                        name: r.label,
                        account: r.account,
                        detail: `recurring · ${r.frequency} · ${krPlain(r.per_month)} kr/month (≈ ${krPlain(r.per_month * 12)} kr/year)`,
                      }}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="showing">
          Total recurring ≈ {kr(data.burn_per_month)}/month · {kr(data.burn_per_month * 12)}/year at
          current levels
        </div>
      </div>

      {data.oneoffs.length > 0 && (
        <div className="card" style={{ marginTop: 14 }}>
          <h2>One-off costs</h2>
          <div className="card-sub">
            Transactions well above their account's normal level — excluded from the burn rate
          </div>
          <div className="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Voucher</th>
                  <th style={{ minWidth: 220 }}>Description</th>
                  <th>Account</th>
                  <th className="num">Amount</th>
                </tr>
              </thead>
              <tbody>
                {data.oneoffs.map((o, i) => (
                  <tr
                    key={i}
                    className="clickable"
                    onClick={() => setVoucher({ series: o.series, number: o.voucher_number })}
                  >
                    <td>{o.date}</td>
                    <td className="voucher-link">
                      {o.series}-{o.voucher_number}
                    </td>
                    <td style={{ whiteSpace: "normal" }}>{o.description || "—"}</td>
                    <td>{o.account}</td>
                    <td className="num">{krPlain(o.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

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
