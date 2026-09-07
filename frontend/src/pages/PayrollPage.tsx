import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, krPlain, monthLabel } from "../api";
import { setFocus } from "../focus";
import type { Payroll } from "../types";
import { BarChart } from "../components/BarChart";

const STEP_HELP: Record<string, string> = {
  gross: "what your payslips show, before income tax is withheld",
  social: "arbetsgivaravgifter & payroll taxes — paid on top, never shown on a payslip",
  pension: "the company's premiums to your pension plans",
  other: "education, wellness allowance, other staff costs",
};

export function PayrollPage() {
  const [data, setData] = useState<Payroll | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.payroll().then(setData).catch((e) => setError(String(e.message ?? e)));
  }, []);

  if (error) return <div className="error-banner">{error}</div>;
  if (!data) return <p className="empty">Loading…</p>;

  const grossAvg = data.avg_month.gross || 1;
  const steps = data.buckets.filter((b) => Math.abs(data.avg_month[b.key]) > 1);

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Payroll</h1>
          <div className="sub">What your team really costs the company — and why</div>
        </div>
        <div className="spacer" />
        <span className="period">
          Financial year <b>{data.year}</b>
        </span>
      </div>

      <div className="tiles">
        <div className="card tile">
          <div className="label">Payroll cost, year to date</div>
          <div className="value">
            {krPlain(data.total)} <small>kr</small>
          </div>
        </div>
        <div className="card tile">
          <div className="label">Average per month</div>
          <div className="value">
            {krPlain(data.avg_month.total)} <small>kr</small>
          </div>
          <div className="note">for {krPlain(grossAvg)} kr of gross salary</div>
        </div>
        {data.multiplier && (
          <div className="card tile">
            <div className="label">Cost multiplier</div>
            <div className="value">{data.multiplier}×</div>
            <div className="note">every 1 kr of salary costs the company {data.multiplier} kr</div>
          </div>
        )}
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <h2>From payslip to company cost — average month</h2>
        <div className="card-sub">
          Payslips are prepared by your accountant · figures read from salary accounts 70xx–76xx
        </div>
        <div className="pay-steps">
          {steps.map((b, i) => (
            <div className="pay-step" key={b.key}>
              <span className="op">{i === 0 ? "" : "+"}</span>
              <span className="pk">
                {b.label}
                <small>{STEP_HELP[b.key]}</small>
              </span>
              <div
                className="pbar"
                style={{
                  width: `${Math.min(100, (Math.abs(data.avg_month[b.key]) / grossAvg) * 100)}%`,
                }}
              />
              <span className="pv">{krPlain(data.avg_month[b.key])}</span>
            </div>
          ))}
          <div className="pay-step total-row">
            <span className="op">=</span>
            <span className="pk">Total employer cost per month (average)</span>
            <span />
            <span className="pv">{krPlain(data.avg_month.total)}</span>
          </div>
        </div>
        <div className="hint">
          The income tax deducted on payslips isn't a company cost — the company withholds it
          from gross salary and forwards it to Skatteverket on the employees' behalf.{" "}
          <a
            style={{ cursor: "pointer" }}
            onClick={() => navigate("/accounts/7510")}
          >
            See the employer-contribution transactions →
          </a>
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <h2>Payroll cost by month</h2>
        <div className="legend">
          <span className="key">
            <span className="swatch sw-rev" />Total employer cost
          </span>
        </div>
        <BarChart
          months={data.months}
          series={[{ name: "Payroll", className: "rev", values: data.monthly_total }]}
          onFocus={(month, _name, value) =>
            setFocus({
              kind: "payroll_month",
              label: `${monthLabel(month)} payroll · ${krPlain(value)} kr`,
              year: data.year,
              month: monthLabel(month),
              value,
            })
          }
        />
        <div className="hint" style={{ paddingTop: 0 }}>
          Spikes usually mean vacation pay, retroactive salary or an extra payroll run — click
          into the 70xx accounts from the P&amp;L to see the underlying vouchers.
        </div>
      </div>
    </>
  );
}
