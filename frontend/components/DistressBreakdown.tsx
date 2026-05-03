import type { ValuationResponse } from "@/app/page";

const labels: Record<string, string> = {
  asset_type_base: "Asset type base",
  location_demand_modifier: "Location demand",
  legal_clarity_penalty: "Legal clarity",
  market_activity_modifier: "Market activity",
  buyer_pool_penalty: "Buyer pool",
  asset_uniqueness_penalty: "Asset uniqueness",
  total_discount: "Total discount",
};

export default function DistressBreakdown({ result }: { result: ValuationResponse }) {
  const entries = Object.entries(result.distress_discount_breakdown);

  return (
    <section className="result-card">
      <p className="section-label">Distress Sale</p>
      <h2>Haircut decomposition</h2>
      <div className="breakdown-list">
        {entries.map(([key, value]) => (
          <div className="bar-row" key={key}>
            <span>{labels[key] ?? key}</span>
            <div className="bar-track">
              <div
                className="bar-fill"
                style={{ width: `${Math.min(Math.abs(value) * 220, 100)}%` }}
              />
            </div>
            <strong>{value >= 0 ? "+" : ""}{Math.round(value * 100)}%</strong>
          </div>
        ))}
      </div>
    </section>
  );
}
