"use client";

import { useState } from "react";
import { scoreLoan, type LoanInput, type ScoreResult } from "@/lib/api";
import { C } from "@/lib/tokens";
import { pct, usd } from "@/lib/format";

const DEFAULTS: LoanInput = {
  credit_score: 720, original_ltv: 80, original_cltv: 80, original_dti: 35,
  original_upb: 250000, original_interest_rate: 4.0, loan_term: 360,
  loan_purpose: "P", occupancy_status: "P", property_type: "SF",
  number_of_units: 1, number_of_borrowers: 2, first_time_homebuyer_flag: "N",
  mi_percent: 0, channel: "R", ppm_flag: "N", amortization_type: "FRM",
  property_state: "CA", msa: "31080",
};

const NUM_FIELDS: [keyof LoanInput, string][] = [
  ["credit_score", "Credit score"],
  ["original_ltv", "LTV"],
  ["original_cltv", "CLTV"],
  ["original_dti", "DTI"],
  ["original_upb", "Loan amount ($)"],
  ["original_interest_rate", "Rate (%)"],
  ["mi_percent", "MI (%)"],
];
const SELECTS: [keyof LoanInput, string, string[]][] = [
  ["loan_purpose", "Purpose", ["P", "C", "N"]],
  ["occupancy_status", "Occupancy", ["P", "I", "S"]],
  ["property_type", "Property", ["SF", "CO", "PU", "MH"]],
  ["first_time_homebuyer_flag", "First-time buyer", ["N", "Y"]],
];

const BAND_COLOR: Record<string, string> = {
  low: C.accent, moderate: C.accent, elevated: C.red, high: C.red,
};

export function ScoreForm() {
  const [loan, setLoan] = useState<LoanInput>(DEFAULTS);
  const [result, setResult] = useState<ScoreResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setLoading(true);
    setError(null);
    try {
      setResult(await scoreLoan(loan));
    } catch {
      setError("The model service didn't respond. It may be waking from sleep — try again in a moment.");
    } finally {
      setLoading(false);
    }
  }

  const set = (k: keyof LoanInput, v: string, numeric: boolean) =>
    setLoan({ ...loan, [k]: v === "" ? null : numeric ? Number(v) : v });

  return (
    <section className="panel">
      <h2 className="panel-title">Score a loan</h2>
      <div className="panel-sub">Live calibrated PD from the deployed model (POST /score).</div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 12, margin: "16px 0" }}>
        {NUM_FIELDS.map(([k, label]) => (
          <label key={k} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span className="metric-label">{label}</span>
            <input
              className="mono"
              type="number"
              value={loan[k] ?? ""}
              onChange={(e) => set(k, e.target.value, true)}
              style={inputStyle}
            />
          </label>
        ))}
        {SELECTS.map(([k, label, opts]) => (
          <label key={k} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span className="metric-label">{label}</span>
            <select value={(loan[k] as string) ?? ""} onChange={(e) => set(k, e.target.value, false)} style={inputStyle}>
              {opts.map((o) => (
                <option key={o} value={o}>{o}</option>
              ))}
            </select>
          </label>
        ))}
      </div>

      <button onClick={submit} disabled={loading} style={buttonStyle}>
        {loading ? "Scoring…" : "Score loan"}
      </button>

      {error && <div className="caption" style={{ color: C.red, marginTop: 12 }}>{error}</div>}

      {result && !error && (
        <div style={{ display: "flex", gap: 32, marginTop: 20, alignItems: "baseline", flexWrap: "wrap" }}>
          <div>
            <div className="metric-label">Calibrated PD</div>
            <div className="metric-value mono" style={{ color: BAND_COLOR[result.risk_band] }}>
              {pct(result.calibrated_pd, 2)}
            </div>
            <div className="panel-sub" style={{ textTransform: "uppercase" }}>{result.risk_band} risk</div>
          </div>
          <div>
            <div className="metric-label">Expected loss</div>
            <div className="metric-value mono metric-red">{usd(result.expected_loss, false)}</div>
            <div className="panel-sub">PD × LGD {result.lgd} × loan amount</div>
          </div>
        </div>
      )}
    </section>
  );
}

const inputStyle: React.CSSProperties = {
  background: "#1E252F",
  border: "1px solid #252C38",
  borderRadius: 4,
  color: "#E6EAF0",
  padding: "7px 9px",
  fontSize: 14,
};
const buttonStyle: React.CSSProperties = {
  background: "#4F8EF7",
  color: "#0B0E14",
  border: "none",
  borderRadius: 4,
  padding: "9px 18px",
  fontSize: 14,
  fontWeight: 600,
  cursor: "pointer",
};
