import type { ValuationResponse } from "@/app/page";

export default function RiskFlags({ result }: { result: ValuationResponse }) {
  return (
    <section className="result-card">
      <div className="card-topline">
        <div>
          <p className="section-label">Risk Controls</p>
          <h2>Policy flags</h2>
        </div>
        <span className={`pill ${result.risk_flags.length ? "pill-yellow" : "pill-blue"}`}>
          {result.risk_flags.length} active
        </span>
      </div>
      <div className="flag-list">
        {result.risk_flags.length ? (
          result.risk_flags.map((flag) => (
            <div className={`flag-row ${flag.severity}`} key={flag.flag}>
              <strong>{flag.flag.replaceAll("_", " ")}</strong>
              <span>{flag.detail}</span>
              <span>Severity: {flag.severity} | LTV impact: {flag.ltv_impact}%</span>
            </div>
          ))
        ) : (
          <div className="flag-row low">
            <strong>No major risk flags</strong>
            <span>The submitted collateral profile did not trigger structural policy warnings.</span>
          </div>
        )}
      </div>
    </section>
  );
}
