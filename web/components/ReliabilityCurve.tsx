"use client";

import {
  Line,
  LineChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import { C, axisProps } from "@/lib/tokens";

interface Rel {
  brier_raw: number;
  brier_calibrated: number;
  raw: { mean_predicted: number; observed: number }[];
  calibrated: { mean_predicted: number; observed: number }[];
}

export function ReliabilityCurve({ data }: { data: Rel }) {
  const hi = Math.max(
    ...data.raw.map((d) => Math.max(d.mean_predicted, d.observed)),
    ...data.calibrated.map((d) => Math.max(d.mean_predicted, d.observed))
  );
  const diag = [
    { x: 0, y: 0 },
    { x: hi, y: hi },
  ];
  const raw = data.raw.map((d) => ({ x: d.mean_predicted, y: d.observed }));
  const cal = data.calibrated.map((d) => ({ x: d.mean_predicted, y: d.observed }));
  const improvement = Math.round(
    (100 * (data.brier_raw - data.brier_calibrated)) / data.brier_raw
  );

  return (
    <section className="panel">
      <h2 className="panel-title">Reliability curve</h2>
      <div className="panel-sub">XGBoost, test set — raw vs isotonic-calibrated</div>
      <div style={{ width: "100%", height: 260, marginTop: 12 }}>
        <ResponsiveContainer>
          <LineChart margin={{ top: 8, right: 12, bottom: 20, left: 8 }}>
            <XAxis
              type="number"
              dataKey="x"
              domain={[0, hi]}
              {...axisProps}
              tickFormatter={(v) => v.toFixed(2)}
              label={{ value: "predicted PD", position: "insideBottom", offset: -8, fill: C.muted, fontSize: 11 }}
            />
            <YAxis
              type="number"
              dataKey="y"
              domain={[0, hi]}
              width={44}
              {...axisProps}
              tickFormatter={(v) => v.toFixed(2)}
              label={{ value: "observed", angle: -90, position: "insideLeft", fill: C.muted, fontSize: 11 }}
            />
            <Line data={diag} dataKey="y" stroke={C.muted} strokeDasharray="4 4" dot={false} strokeWidth={1} isAnimationActive={false} />
            <Line data={raw} dataKey="y" stroke={C.red} dot={{ r: 3, fill: C.red }} strokeWidth={1.5} isAnimationActive={false} name="raw" />
            <Line data={cal} dataKey="y" stroke={C.accent} dot={{ r: 3, fill: C.accent }} strokeWidth={1.5} isAnimationActive={false} name="calibrated" />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="caption">
        Raw scores (red) sit far below the diagonal — badly over-confident. Isotonic (blue)
        pulls them onto it: Brier {data.brier_raw.toFixed(3)} → {data.brier_calibrated.toFixed(4)} ({improvement}% better).
      </div>
    </section>
  );
}
