import type { ValuationResponse } from "@/app/page";

export default function LTVCard({ result }: { result: ValuationResponse }) {
  const { standard, conservative, rationale } = result.ltv_recommendation;

  return (
    <section className="result-card">
      <p className="section-label">Lending Decision</p>
      <h2>LTV recommendation</h2>
      <div className="ltv-split">
        <div className="ltv-box">
          <span>Standard limit</span>
          <strong>{Math.round(standard * 100)}%</strong>
        </div>
        <div className="ltv-box conservative">
          <span>Conservative limit</span>
          <strong>{Math.round(conservative * 100)}%</strong>
        </div>
      </div>
      <p className="rationale">{rationale}</p>
    </section>
  );
}
