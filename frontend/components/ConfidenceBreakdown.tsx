import type { ValuationResponse } from "@/app/page";

export default function ConfidenceBreakdown({ result }: { result: ValuationResponse }) {
  return (
    <section className="result-card">
      <p className="section-label">Confidence</p>
      <h2>Signal quality</h2>
      <div className="breakdown-list">
        {Object.entries(result.confidence_breakdown).map(([key, value]) => (
          <div className="bar-row" key={key}>
            <span>{key.replaceAll("_", " ")}</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${Math.round(value * 100)}%` }} />
            </div>
            <strong>{Math.round(value * 100)}%</strong>
          </div>
        ))}
      </div>
    </section>
  );
}
