"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import { C, axisProps } from "@/lib/tokens";

interface Row {
  vintage: number;
  kept: number;
  defaults: number;
  default_pct: number;
}

const ELEVATED = new Set([2006, 2007, 2008, 2019]);

export function VintagePanel({ data }: { data: Row[] }) {
  const rows = data.filter((d) => d.kept >= 10000);
  return (
    <section className="panel">
      <h2 className="panel-title">Default rate by vintage</h2>
      <div className="panel-sub">24-month default rate, by origination year</div>
      <div style={{ width: "100%", height: 260, marginTop: 12 }}>
        <ResponsiveContainer>
          <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 20, left: 8 }}>
            <XAxis
              dataKey="vintage"
              {...axisProps}
              interval={2}
              label={{ value: "origination year", position: "insideBottom", offset: -8, fill: C.muted, fontSize: 11 }}
            />
            <YAxis
              {...axisProps}
              width={40}
              tickFormatter={(v) => `${v}%`}
            />
            <Bar dataKey="default_pct" isAnimationActive={false}>
              {rows.map((r) => (
                <Cell key={r.vintage} fill={ELEVATED.has(r.vintage) ? C.red : C.accent} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="caption">
        Red = elevated vintages. 2006–08 is the housing crisis; 2019 is inflated by COVID-era
        forbearance (reported as delinquent). The crisis spike validates the label.
      </div>
    </section>
  );
}
