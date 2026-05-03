"use client";

import { ValuationResponse } from "@/app/page";

export default function ImageAnalysisPanel({ result }: { result: ValuationResponse }) {
  const imageAnalysis = result.image_analysis;

  if (!imageAnalysis) {
    return null;
  }

  // friend/main: richer helpers and image_impact display
  const formatLabel = (value?: string | null) => (value ? value.replaceAll("_", " ") : "Not detected");
  const issues = imageAnalysis.visible_issues ?? [];
  const impact = result.image_impact;
  const imageQuality = result.confidence_breakdown?.image_quality;

  const imageStatus =
    (impact?.market_value_penalty_pct ?? 0) >= 0.08 || (impact?.image_risk_flags_added ?? 0) > 0
      ? "Image indicates elevated risk"
      : "Image indicates neutral/stable condition";

  return (
    <section className="result-card image-analysis-card">
      <div className="card-topline">
        <div>
          <p className="section-label">Image Analysis</p>
          <h2>Visual Property Assessment</h2>
          <p className="field-hint">AI-powered analysis of property condition from uploaded image</p>
        </div>
        <span className="pill pill-blue">
          {imageAnalysis.confidence_in_analysis
            ? `${Math.round(imageAnalysis.confidence_in_analysis * 100)}% confidence`
            : "Analysis complete"}
        </span>
      </div>

      <div className="image-status-banner">{imageStatus}</div>

      <div className="image-grid">
        <div className="image-section">
          <h3>Condition Assessment</h3>
          <div className="image-kv-list">
            <div className="image-kv-row">
              <span>Construction quality</span>
              <strong>{formatLabel(imageAnalysis.construction_quality)}</strong>
            </div>
            <div className="image-kv-row">
              <span>Visible condition</span>
              <strong>{formatLabel(imageAnalysis.visible_condition)}</strong>
            </div>
            <div className="image-kv-row">
              <span>Surrounding area</span>
              <strong>{formatLabel(imageAnalysis.surrounding_area_quality)}</strong>
            </div>
            <div className="image-kv-row">
              <span>Property type match</span>
              <strong>
                {imageAnalysis.property_type_matches_claimed === true
                  ? "Matches"
                  : imageAnalysis.property_type_matches_claimed === false
                    ? "Mismatch"
                    : "Unknown"}
              </strong>
            </div>
            <div className="image-kv-row">
              <span>Estimated floors</span>
              <strong>{imageAnalysis.estimated_floors ?? "N/A"}</strong>
            </div>
          </div>
        </div>

        <div className="image-section">
          <h3>Detected Issues</h3>
          {issues.length > 0 ? (
            <ul className="image-issues-list">
              {issues.map((issue: string, index: number) => (
                <li key={index}>
                  <span className="issue-dot">!</span>
                  <span>{formatLabel(issue)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="field-hint">No significant issues detected</p>
          )}
        </div>
      </div>

      <div className="image-impact-grid">
        <div className="mini-stat">
          <span>Image risk flags</span>
          <strong>{impact?.image_risk_flags_added ?? 0}</strong>
        </div>
        <div className="mini-stat">
          <span>Market value impact</span>
          <strong>-{Math.round((impact?.market_value_penalty_pct ?? 0) * 100)}%</strong>
        </div>
        <div className="mini-stat">
          <span>Liquidity penalty</span>
          <strong>-{impact?.rpi_penalty_points ?? 0} RPI</strong>
        </div>
      </div>

      {imageQuality !== undefined ? (
        <p className="image-note">
          Confidence uses image signal at {Math.round(imageQuality * 100)}%.
          {impact?.image_confidence_effective !== undefined
            ? ` Effective confidence: ${Math.round(impact.image_confidence_effective * 100)}%.`
            : ""}
        </p>
      ) : null}
    </section>
  );
}
