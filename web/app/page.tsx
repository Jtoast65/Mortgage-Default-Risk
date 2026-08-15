import { CutoffPanel } from "@/components/CutoffPanel";
import { MetricsStrip } from "@/components/MetricsStrip";
import { ReliabilityCurve } from "@/components/ReliabilityCurve";
import { VintagePanel } from "@/components/VintagePanel";
import { ScoreForm } from "@/components/ScoreForm";
import { ModelCard } from "@/components/ModelCard";

import cutoff from "@/public/data/cutoff_curve_A.json";
import metrics from "@/public/data/metrics.json";
import vintage from "@/public/data/vintage_default_rate.json";
import reliability from "@/public/data/reliability_curve_A.json";

export default function Home() {
  const logistic = (metrics as any).A.models.logistic.test;

  return (
    <main className="page">
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 20 }}>Mortgage Default Risk</h1>
        <p className="panel-sub" style={{ maxWidth: 640, marginTop: 6 }}>
          Calibrated probability of default on US mortgages, priced into dollars. Trained on
          Freddie Mac loans with a strict vintage split — the probabilities are usable for
          loan pricing, not just ranking.
        </p>
      </header>

      <MetricsStrip
        auc={logistic.auc}
        ks={logistic.ks}
        brier={logistic.brier}
        reductionPer1b={(cutoff as any).headline.reduction_per_1b}
        reductionPct={(cutoff as any).headline.reduction_pct}
      />

      <div style={{ height: 16 }} />
      <CutoffPanel data={cutoff as any} />

      <div style={{ height: 16 }} />
      <div className="grid-2">
        <ReliabilityCurve data={reliability as any} />
        <VintagePanel data={vintage as any} />
      </div>

      <div style={{ height: 16 }} />
      <ScoreForm />

      <div style={{ height: 16 }} />
      <ModelCard />

      <footer className="caption" style={{ marginTop: 32, textAlign: "center" }}>
        <a href="https://github.com/Jtoast65/Mortgage-Default-Risk">source</a>
        {" · "}
        <a href="https://mortgage-default-risk-api.onrender.com/docs">API docs</a>
        {" · "}Freddie Mac Single-Family Loan-Level Dataset · data not redistributed
      </footer>
    </main>
  );
}
