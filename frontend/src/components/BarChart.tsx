import { useState } from "react";
import { kr, monthLabel } from "../api";

export interface Series {
  name: string;
  className: string; // rev | cost | proj
  values: number[];
  /** Optional per-month class override (e.g. "proj" for future months). */
  classNames?: (string | undefined)[];
  /** Optional per-month name override for the tooltip. */
  names?: (string | undefined)[];
}

function niceStep(target: number): number {
  const pow = Math.pow(10, Math.floor(Math.log10(Math.max(target, 1))));
  for (const m of [1, 2, 5, 10]) {
    if (m * pow >= target) return m * pow;
  }
  return 10 * pow;
}

const short = (n: number) =>
  n >= 1_000_000 ? `${n / 1_000_000}M` : n >= 1000 ? `${n / 1000}k` : `${n}`;

export function BarChart({
  months,
  series,
  onFocus,
}: {
  months: string[];
  series: Series[];
  /** Fired when a bar is hovered — lets a page capture it as assistant focus. */
  onFocus?: (month: string, seriesName: string, value: number) => void;
}) {
  const [tip, setTip] = useState<{ x: number; y: number; text: string } | null>(null);
  const maxVal = Math.max(1, ...series.flatMap((s) => s.values));
  const step = niceStep(maxVal / 2.2);
  const scaleMax = step * 2.5;

  return (
    <div className="chart-wrap">
      <div className="chart">
        {[0, step, step * 2].map((v) => (
          <div key={v} className="gridline" style={{ bottom: `${(v / scaleMax) * 100}%` }}>
            <span>{short(v)}</span>
          </div>
        ))}
        {months.map((m, i) => (
          <div key={m} className="month-group">
            {series.map((s) => (
              <div
                key={s.name}
                className={`bar ${s.classNames?.[i] ?? s.className}`}
                style={{ height: `${((s.values[i] ?? 0) / scaleMax) * 100}%` }}
                onMouseEnter={(e) => {
                  setTip({
                    x: e.clientX,
                    y: e.clientY,
                    text: `${monthLabel(m)} · ${s.names?.[i] ?? s.name} ${kr(s.values[i] ?? 0)}`,
                  });
                  onFocus?.(m, s.names?.[i] ?? s.name, s.values[i] ?? 0);
                }}
                onMouseMove={(e) => setTip((t) => t && { ...t, x: e.clientX, y: e.clientY })}
                onMouseLeave={() => setTip(null)}
              />
            ))}
          </div>
        ))}
      </div>
      <div className="x-labels">
        {months.map((m) => (
          <span key={m}>{monthLabel(m)}</span>
        ))}
      </div>
      {tip && (
        <div className="tooltip" style={{ left: tip.x + 12, top: tip.y - 34 }}>
          {tip.text}
        </div>
      )}
    </div>
  );
}
