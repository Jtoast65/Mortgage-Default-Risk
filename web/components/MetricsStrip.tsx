import { pct, usd } from "@/lib/format";

function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div style={{ flex: 1, minWidth: 120 }}>
      <div className="metric-label">{label}</div>
      <div className="metric-value mono">{value}</div>
      {sub && <div className="panel-sub">{sub}</div>}
    </div>
  );
}

export function MetricsStrip({
  auc,
  ks,
  brier,
  reductionPer1b,
  reductionPct,
}: {
  auc: number;
  ks: number;
  brier: number;
  reductionPer1b: number;
  reductionPct: number;
}) {
  return (
    <section className="panel">
      <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
        <Metric label="AUC" value={auc.toFixed(3)} sub="rank discrimination" />
        <Metric label="KS" value={ks.toFixed(3)} sub="max separation" />
        <Metric label="Brier" value={brier.toFixed(4)} sub="calibrated" />
        <Metric
          label="Loss cut vs scorecard"
          value={usd(reductionPer1b)}
          sub={`per $1B · ${pct(reductionPct / 100, 0)} at 4% cutoff`}
        />
      </div>
    </section>
  );
}
