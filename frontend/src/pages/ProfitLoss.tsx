import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, krPlain } from "../api";
import type { Pnl } from "../types";

const NEGATIVE_GROUPS = new Set(["direct", "external", "personnel", "depreciation", "other_op", "tax"]);

function quarterSums(monthly: number[]): number[] {
  const q = [0, 0, 0, 0];
  monthly.forEach((v, i) => {
    q[Math.min(3, Math.floor(i / 3))] += v;
  });
  return q;
}

function Amount({ value, negative }: { value: number; negative?: boolean }) {
  if (Math.abs(value) < 0.005) return <>0</>;
  const shown = negative ? -value : value;
  return <>{shown > 0 && negative === false ? "+" : ""}{krPlain(shown)}</>;
}

export function ProfitLoss() {
  const [data, setData] = useState<Pnl | null>(null);
  const [open, setOpen] = useState<Set<string>>(new Set(["external"]));
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.pnl().then(setData).catch((e) => setError(String(e.message ?? e)));
  }, []);

  if (error) return <div className="error-banner">{error}</div>;
  if (!data) return <p className="empty">Loading…</p>;

  const toggle = (key: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  const profitQ = quarterSums(data.profit_monthly);

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Profit &amp; loss</h1>
          <div className="sub">Your resultaträkning, in plain language — every line opens</div>
        </div>
        <div className="spacer" />
        <span className="period">
          Financial year <b>{data.year}</b>
        </span>
      </div>

      <div className="card">
        <div className="tbl-wrap">
          <table className="pnl">
            <thead>
              <tr>
                <th style={{ minWidth: 280 }}>Line</th>
                <th className="num">Q1</th>
                <th className="num">Q2</th>
                <th className="num">Q3</th>
                <th className="num">Q4</th>
                <th className="num">Year to date</th>
              </tr>
            </thead>
            <tbody>
              {data.groups.map((g) => {
                const neg = NEGATIVE_GROUPS.has(g.key);
                const q = quarterSums(g.monthly);
                const isOpen = open.has(g.key);
                return [
                  <tr key={g.key} className="grp" onClick={() => toggle(g.key)}>
                    <td>
                      <span className={`chev${isOpen ? " open" : ""}`}>▸</span>
                      {g.name}
                    </td>
                    {q.map((v, i) => (
                      <td key={i} className="num">
                        <Amount value={v} negative={neg} />
                      </td>
                    ))}
                    <td className="num">
                      <Amount value={g.total} negative={neg} />
                    </td>
                  </tr>,
                  ...(isOpen
                    ? g.accounts.map((a) => {
                        const aq = quarterSums(a.monthly);
                        return (
                          <tr
                            key={`${g.key}-${a.number}`}
                            className="sub clickable"
                            onClick={() => navigate(`/accounts/${a.number}`)}
                          >
                            <td>
                              <span className="acct-no">{a.number}</span>
                              {a.name}
                            </td>
                            {aq.map((v, i) => (
                              <td key={i} className="num">
                                <Amount value={v} negative={neg} />
                              </td>
                            ))}
                            <td className="num">
                              <span className="voucher-link">transactions →</span>
                            </td>
                          </tr>
                        );
                      })
                    : []),
                ];
              })}
              <tr className="total">
                <td>Profit before tax</td>
                {profitQ.map((v, i) => (
                  <td key={i} className="num">
                    {krPlain(v)}
                  </td>
                ))}
                <td className="num">{krPlain(data.profit_before_tax)}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="hint">
          Corporate tax (20.6%) is booked at year-end, not monthly. Click any group to
          open its accounts; click an account to see every transaction behind the number.
        </div>
      </div>
    </>
  );
}
