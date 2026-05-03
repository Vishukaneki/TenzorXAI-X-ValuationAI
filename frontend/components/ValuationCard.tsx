import type { ValuationResponse } from "@/app/page";

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

export default function ValuationCard({ result }: { result: ValuationResponse }) {
  const [low, high] = result.market_value_range;
  const [distressLow, distressHigh] = result.distress_value_range;

  return (
    <section className="result-card">
      <div className="card-topline">
        <div>
          <p className="section-label">Market Valuation</p>
          <h2>Credit committee range</h2>
          <div className="value-range">
            <strong>{formatCurrency(low)}</strong>
            <span>to</span>
            <strong>{formatCurrency(high)}</strong>
          </div>
        </div>
        <span className="pill pill-blue">{result.rpi_interpretation.replaceAll("_", " ")}</span>
      </div>

      <div className="card-band">
        <div className="mini-stat">
          <span>Distress range</span>
          <strong>{formatCurrency(distressLow)} - {formatCurrency(distressHigh)}</strong>
        </div>
        <div className="mini-stat">
          <span>Resale potential</span>
          <strong>{result.resale_potential_index}/100</strong>
        </div>
        <div className="mini-stat">
          <span>Confidence</span>
          <strong>{Math.round(result.confidence_score * 100)}%</strong>
        </div>
      </div>
    </section>
  );
}
