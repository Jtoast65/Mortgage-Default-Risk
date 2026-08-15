export function ModelCard() {
  const rows: [string, React.ReactNode][] = [
    ["Data", "Freddie Mac Single-Family Loan-Level sample (~1.4M loans, 1999–2026). Licence prohibits redistribution — data not committed."],
    ["Label", "Default = 180+ days delinquent, or foreclosure / REO / short-sale, within a fixed 24-month window from origination."],
    ["Split", "By origination vintage, never random. Experiment A: train 2010–17, calibrate 2018–19, test 2020–21."],
    ["Features", "Origination-only (what a lender knows at underwriting). A build-time assertion fails if any performance-file field leaks in."],
    ["Model", "Logistic regression, deployed; isotonic calibration fit on validation only. Scorecard and XGBoost reported alongside."],
    ["LGD", "Empirical 0.456 — dollar-weighted realized loss over 15,130 disposed defaulted loans, not an assumption."],
    ["Limitations", "Prepayment is treated as a competing risk (censored), not modelled jointly. Constant LGD. 2019 PDs are inflated by COVID-era forbearance."],
  ];
  return (
    <section className="panel">
      <h2 className="panel-title">Model card</h2>
      <div className="panel-sub">What this is, how it was built, and what it assumes.</div>
      <table style={{ marginTop: 12 }}>
        <tbody>
          {rows.map(([k, v]) => (
            <tr key={k}>
              <th style={{ width: 130, verticalAlign: "top", whiteSpace: "nowrap" }}>{k}</th>
              <td style={{ color: "var(--text)" }}>{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
