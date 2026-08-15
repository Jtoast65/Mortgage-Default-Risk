export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "https://mortgage-default-risk-api.onrender.com";

export interface LoanInput {
  credit_score: number | null;
  original_ltv: number | null;
  original_cltv: number | null;
  original_dti: number | null;
  original_upb: number | null;
  original_interest_rate: number | null;
  loan_term: number | null;
  loan_purpose: string | null;
  occupancy_status: string | null;
  property_type: string | null;
  number_of_units: number | null;
  number_of_borrowers: number | null;
  first_time_homebuyer_flag: string | null;
  mi_percent: number | null;
  channel: string | null;
  ppm_flag: string | null;
  amortization_type: string | null;
  property_state: string | null;
  msa: string | null;
}

export interface ScoreResult {
  calibrated_pd: number;
  risk_band: string;
  lgd: number;
  expected_loss: number;
}

export async function scoreLoan(loan: LoanInput): Promise<ScoreResult> {
  const res = await fetch(`${API_BASE}/score`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(loan),
  });
  if (!res.ok) throw new Error(`Scoring failed (${res.status})`);
  return res.json();
}
