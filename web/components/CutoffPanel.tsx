"use client";

import { useMemo, useState } from "react";
import {
  Line,
  LineChart,
  ReferenceDot,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import { C, axisProps } from "@/lib/tokens";
import { num, pct, usd } from "@/lib/format";

interface Point {
  cutoff: number;
  approval_rate: number;
  expected_loss_per_1b: number;
  realized_loss_per_1b: number;
  defaults_approved: number;
  good_rejected: number;
}
interface CutoffData {
  lgd: number;
  base_default_rate: number;
  headline: { cutoff: number };
  curve: Point[];
  scorecard_curve: Point[];
}

function Stat({ label, value, red }: { label: string; value: string; red?: boolean }) {
  return (
    <div>
      <div className="metric-label">{label}</div>
      <div className={`metric-value mono${red ? " metric-red" : ""}`}>{value}</div>
    </div>
  );
}

export function CutoffPanel({ data }: { data: CutoffData }) {
  const n = data.curve.length;
  const defaultIdx = Math.max(
    0,
    data.curve.findIndex((p) => p.cutoff >= data.headline.cutoff)
  );
  const [idx, setIdx] = useState(defaultIdx);
  const p = data.curve[idx];

  // Merge model + scorecard curves on approval rate for the tradeoff chart.
  const chart = useMemo(
    () =>
      data.curve.map((c, i) => ({
        approval: c.approval_rate * 100,
        model: c.realized_loss_per_1b / 1e6,
        scorecard: (data.scorecard_curve[i]?.realized_loss_per_1b ?? 0) / 1e6,
      })),
    [data]
  );

  return (
    <section className="panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div>
          <h2 className="panel-title">Approval cutoff</h2>
          <div className="panel-sub">
            Approve loans below the PD cutoff. Test book: 2020–21 originations.
          </div>
        </div>
        <div className="mono" style={{ fontSize: 20, color: C.accent }}>
          {pct(p.cutoff, 1)} PD
        </div>
      </div>

      <input
        type="range"
        min={0}
        max={n - 1}
        value={idx}
        onChange={(e) => setIdx(Number(e.target.value))}
        aria-label="PD cutoff"
        style={{ margin: "20px 0 24px" }}
      />

      <div className="stat-row">
        <Stat label="Approval rate" value={pct(p.approval_rate, 1)} />
        <Stat label="Exp. loss / $1B" value={usd(p.expected_loss_per_1b)} red />
        <Stat label="Defaults approved" value={num(p.defaults_approved)} red />
        <Stat label="Good loans rejected" value={num(p.good_rejected)} />
      </div>

      <div style={{ width: "100%", height: 220 }}>
        <ResponsiveContainer>
          <LineChart data={chart} margin={{ top: 8, right: 12, bottom: 20, left: 8 }}>
            <XAxis
              dataKey="approval"
              type="number"
              domain={[0, 100]}
              ticks={[0, 20, 40, 60, 80, 100]}
              {...axisProps}
              label={{
                value: "approval rate (%)",
                position: "insideBottom",
                offset: -8,
                fill: C.muted,
                fontSize: 11,
              }}
            />
            <YAxis
              {...axisProps}
              width={44}
              label={{
                value: "loss $M/$1B",
                angle: -90,
                position: "insideLeft",
                fill: C.muted,
                fontSize: 11,
              }}
            />
            <Line
              type="monotone"
              dataKey="scorecard"
              stroke={C.muted}
              dot={false}
              strokeWidth={1.4}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="model"
              stroke={C.accent}
              dot={false}
              strokeWidth={1.8}
              isAnimationActive={false}
            />
            <ReferenceDot
              x={p.approval_rate * 100}
              y={p.realized_loss_per_1b / 1e6}
              r={4}
              fill={C.red}
              stroke="none"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="caption">
        Blue = calibrated model, grey = FICO×LTV scorecard. The model sits below the scorecard
        at every approval rate; red dot marks the current cutoff.
      </div>
    </section>
  );
}
