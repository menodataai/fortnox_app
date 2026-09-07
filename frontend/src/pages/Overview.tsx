import { useEffect, useState } from "react";
import { api, kr, krPlain } from "../api";
import type { DashboardSummary } from "../types";
import { BarChart } from "../components/BarChart";

const BADGE: Record<string, { label: string; icon: string }> = {
  critical: { label: "Overdue", icon: "⚠" },
  warning: { label: "Due soon", icon: "⚠" },
  info: { label: "Waiting", icon: "◔" },
};

export function Overview() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.summary().then(setData).catch((e) => setError(String(e.message ?? e)));
  }, []);

  if (error) return <div className="error-banner">{error}</div>;
  if (!data) return <p className="empty">Loading…</p>;

  const margin =
    data.revenue_ytd > 0 ? Math.round((data.profit_ytd / data.revenue_ytd) * 100) : 0;

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Overview</h1>
          <div className="sub">How {data.company_name || "the company"} is doing, at a glance</div>
        </div>
        <div className="spacer" />
        <span className="period">
          Financial year <b>{data.year}</b>
        </span>
      </div>

      <div className="tiles">
        <div className="card tile">
          <div className="label">Revenue, year to date</div>
          <div className="value">
            {krPlain(data.revenue_ytd)} <small>kr</small>
          </div>
        </div>
        <div className="card tile">
          <div className="label">Costs, year to date</div>
          <div className="value">
            {krPlain(data.costs_ytd)} <small>kr</small>
          </div>
        </div>
        <div className="card tile">
          <div className="label">Profit before tax</div>
          <div className="value">
            {krPlain(data.profit_ytd)} <small>kr</small>
          </div>
          <div className={`delta ${data.profit_ytd >= 0 ? "good" : "bad"}`}>
            {margin}% margin
          </div>
        </div>
        <div className="card tile">
          <div className="label">Cash in bank</div>
          <div className="value">
            {krPlain(data.cash)} <small>kr</small>
          </div>
          <div className="note">bank accounts 1900–1999</div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <h2>Revenue vs. costs by month</h2>
          <div className="card-sub">Profit is the gap between the bars · hover for exact figures</div>
          <div className="legend">
            <span className="key">
              <span className="swatch sw-rev" />Revenue
            </span>
            <span className="key">
              <span className="swatch sw-cost" />Costs
            </span>
          </div>
          <BarChart
            months={data.monthly.months}
            series={[
              { name: "Revenue", className: "rev", values: data.monthly.revenue },
              { name: "Costs", className: "cost", values: data.monthly.costs },
            ]}
          />
        </div>

        <div className="card">
          <h2>Needs your attention</h2>
          <div className="card-sub">
            {data.attention.length
              ? `${data.attention.length} item${data.attention.length > 1 ? "s" : ""}`
              : "Nothing right now"}
          </div>
          <ul className="attn">
            {data.attention.map((a, i) => {
              const b = BADGE[a.level] ?? BADGE.info;
              return (
                <li key={i}>
                  <span className={`badge ${a.level}`}>
                    <span aria-hidden="true">{b.icon}</span> {b.label}
                  </span>
                  <span>
                    <span className="t">{a.title}</span>
                    <br />
                    <span className="d">{a.detail}</span>
                  </span>
                </li>
              );
            })}
            {data.attention.length === 0 && (
              <li>
                <span className="badge good">✓ All clear</span>
                <span className="d">No overdue invoices or upcoming payments in the next 14 days.</span>
              </li>
            )}
          </ul>
        </div>
      </div>

      {data.outstanding_count > 0 && (
        <p className="hint" style={{ padding: "14px 4px 0" }}>
          Outstanding client invoices: {kr(data.outstanding_total)} across{" "}
          {data.outstanding_count} invoice{data.outstanding_count > 1 ? "s" : ""}
          {data.overdue_count > 0 && ` — of which ${kr(data.overdue_total)} overdue`}.
        </p>
      )}
    </>
  );
}
