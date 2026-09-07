import { useEffect, useMemo, useState } from "react";
import { api, krPlain } from "../api";
import type { ProjectionBaseline } from "../types";
import { BarChart } from "../components/BarChart";

function NumberInput({
  value,
  onChange,
  step = 1000,
}: {
  value: number;
  onChange: (v: number) => void;
  step?: number;
}) {
  return (
    <input
      type="number"
      value={Math.round(value)}
      step={step}
      min={0}
      onChange={(e) => onChange(Number(e.target.value) || 0)}
    />
  );
}

export function Projection() {
  const [data, setData] = useState<ProjectionBaseline | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revPerMonth, setRevPerMonth] = useState<number | null>(null);
  const [costPerMonth, setCostPerMonth] = useState<number | null>(null);
  const [oneoff, setOneoff] = useState(0);

  useEffect(() => {
    api
      .projection()
      .then((d) => {
        setData(d);
        setRevPerMonth(d.defaults.revenue_per_month);
        setCostPerMonth(d.defaults.costs_per_month);
      })
      .catch((e) => setError(String(e.message ?? e)));
  }, []);

  const calc = useMemo(() => {
    if (!data || revPerMonth == null || costPerMonth == null) return null;
    const remaining = data.months.length - data.elapsed_months;
    const revenue = data.revenue_ytd + remaining * revPerMonth;
    const costs = data.costs_ytd + remaining * costPerMonth + oneoff;
    const profit = revenue - costs + data.financial_net;
    const tax = profit > 0 ? profit * data.tax_rate : 0;
    return { remaining, revenue, costs, profit, tax, after: profit - tax };
  }, [data, revPerMonth, costPerMonth, oneoff]);

  if (error) return <div className="error-banner">{error}</div>;
  if (!data || !calc || revPerMonth == null || costPerMonth == null)
    return <p className="empty">Loading…</p>;

  const chartValues = data.months.map((_, i) =>
    i < data.elapsed_months ? data.actual_revenue[i] : revPerMonth,
  );
  const chartClasses = data.months.map((_, i) =>
    i < data.elapsed_months ? undefined : "proj",
  );
  const chartNames = data.months.map((_, i) =>
    i < data.elapsed_months ? "Actual" : "Projected",
  );

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Year projection</h1>
          <div className="sub">Where {data.year} lands if the assumptions hold</div>
        </div>
        <div className="spacer" />
        <span className="period">
          Full year <b>{data.year}</b>
        </span>
      </div>

      <div className="proj-grid">
        <div className="card">
          <h2>Assumptions</h2>
          <div className="card-sub">
            Defaults from your recent months — adjust and the projection updates
          </div>
          <div className="assump">
            <div className="row">
              <span className="k">
                Revenue / month
                <small>for the {calc.remaining} remaining months, excl. VAT</small>
              </span>
              <NumberInput value={revPerMonth} onChange={setRevPerMonth} step={5000} />
            </div>
            <div className="row">
              <span className="k">
                Costs / month
                <small>salaries + recurring costs, from your ledger</small>
              </span>
              <NumberInput value={costPerMonth} onChange={setCostPerMonth} step={5000} />
            </div>
            <div className="row">
              <span className="k">
                Planned one-off costs
                <small>equipment, conferences, anything extra</small>
              </span>
              <NumberInput value={oneoff} onChange={setOneoff} step={5000} />
            </div>
          </div>
          <div className="est-note" style={{ margin: "0 18px 16px" }}>
            ⚠ Estimate, not tax advice — confirm year-end figures with your accountant.
          </div>
        </div>

        <div className="card">
          <div className="proj-tiles">
            <div className="tile">
              <div className="label">Projected revenue</div>
              <div className="value">
                {krPlain(calc.revenue)} <small>kr</small>
              </div>
            </div>
            <div className="tile">
              <div className="label">Projected costs</div>
              <div className="value">
                {krPlain(calc.costs)} <small>kr</small>
              </div>
            </div>
            <div className="tile">
              <div className="label">Profit before tax</div>
              <div className="value">
                {krPlain(calc.profit)} <small>kr</small>
              </div>
            </div>
            <div className="tile">
              <div className="label">Corporate tax (20.6%)</div>
              <div className="value">
                −{krPlain(calc.tax)} <small>kr</small>
              </div>
            </div>
            <div className="tile">
              <div className="label">Profit after tax</div>
              <div className="value">
                {krPlain(calc.after)} <small>kr</small>
              </div>
            </div>
          </div>
          <h2>Monthly revenue — actual and projected</h2>
          <div className="legend">
            <span className="key">
              <span className="swatch sw-rev" />Actual
            </span>
            <span className="key">
              <span className="swatch sw-proj" />Projected
            </span>
          </div>
          <BarChart
            months={data.months}
            series={[
              {
                name: "Revenue",
                className: "rev",
                values: chartValues,
                classNames: chartClasses,
                names: chartNames,
              },
            ]}
          />
        </div>
      </div>
    </>
  );
}
