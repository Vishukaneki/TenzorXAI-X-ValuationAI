import type { ValuationResponse } from "@/app/page";

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

export default function CompsTable({ result }: { result: ValuationResponse }) {
  return (
    <section className="result-card comps-card">
      <div className="card-topline comps-header">
        <div>
          <p className="section-label">Comparable Evidence</p>
          <h2>Nearest synthetic comps</h2>
          <p className="field-hint">These comparables are shown in a more readable card layout for quicker scanning.</p>
        </div>
        <span className="pill pill-yellow">{result.comparable_transactions.length} comps</span>
      </div>

      <div className="comps-list">
        {result.comparable_transactions.map((comp, index) => (
          <article className="comp-row comp-card" key={`${comp.locality}-${index}`}>
            <div className="comp-card-main">
              <div className="comp-card-top">
                <strong>{comp.locality}</strong>
                <span className="comp-index">#{index + 1}</span>
              </div>
              <p className="comp-meta">
                {comp.subtype.replaceAll("_", " ")} · {comp.size_sqft} sqft · age {comp.age_years} yrs
              </p>
            </div>

            <div className="comp-card-value">
              <span>Estimated market value</span>
              <strong>{formatCurrency(comp.market_value)}</strong>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
