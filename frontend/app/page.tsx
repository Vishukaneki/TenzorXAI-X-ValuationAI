"use client";

import { useState } from "react";
import CompsTable from "@/components/CompsTable";
import ConfidenceBreakdown from "@/components/ConfidenceBreakdown";
import ConfidenceHeatmap from "@/components/ConfidenceHeatmap";
import DistressBreakdown from "@/components/DistressBreakdown";
import ImageAnalysisPanel from "@/components/ImageAnalysisPanel";
import InputForm, { type ValuationFormData } from "@/components/InputForm";
import LTVCard from "@/components/LTVCard";
import NarrativePanel from "@/components/NarrativePanel";
import RiskFlags from "@/components/RiskFlags";
import ValuationCard from "@/components/ValuationCard";
import WhatIfSimulator from "@/components/WhatIfSimulator";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export type ValuationResponse = {
  market_value_range: [number, number];
  distress_value_range: [number, number];
  distress_discount_breakdown: Record<string, number>;
  resale_potential_index: number;
  rpi_interpretation: string;
  rpi_components: Record<string, number>;
  estimated_time_to_sell_days: [number, number];
  confidence_score: number;
  confidence_breakdown: Record<string, number>;
  comparable_transactions: Array<{
    locality: string;
    subtype: string;
    size_sqft: number;
    age_years: number;
    market_value: number;
    price_per_sqft: number;
  }>;
  key_drivers: Array<{
    driver: string;
    shap_impact: string;
    direction: "positive" | "negative";
  }>;
  risk_flags: Array<{
    flag: string;
    severity: "high" | "medium" | "low";
    ltv_impact: number;
    detail: string;
  }>;
  ltv_recommendation: {
    standard: number;
    conservative: number;
    rationale: string;
  };
};

function KeyDrivers({ result }: { result: ValuationResponse }) {
  return (
    <section className="result-card explainability-card">
      <div className="card-topline explainability-header">
        <div>
          <p className="section-label">Model Explainability</p>
          <h2>Top SHAP drivers</h2>
          <p className="field-hint">The model is leaning on these signals the most for the current valuation.</p>
        </div>
        <span className="pill pill-blue">{result.key_drivers.length} drivers</span>
      </div>

      <div className="driver-grid">
        {result.key_drivers.map((driver, index) => (
          <div className="driver-card" key={driver.driver}>
            <div className="driver-card-header">
              <span className="driver-index">0{index + 1}</span>
              <span className={driver.direction === "positive" ? "pill pill-blue" : "pill pill-red"}>
                {driver.shap_impact}
              </span>
            </div>
            <strong>{driver.driver.replaceAll("_", " ")}</strong>
            <span>{driver.direction} contribution to price per sqft</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function EmptyState() {
  return (
    <section className="result-card empty-state">
      <div className="empty-state-inner">
        <div className="radar-mark">RPI</div>
        <h2>Run a collateral file to generate the lender view.</h2>
        <p>
          The console will return market value, distress value, liquidity, confidence, comparable evidence,
          policy risk flags, and LTV recommendations in one audit-ready view.
        </p>
      </div>
    </section>
  );
}

export default function Home() {
  const [result, setResult] = useState<ValuationResponse | null>(null);
  const [lastRequest, setLastRequest] = useState<ValuationFormData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();

  async function runValuation(data: ValuationFormData | FormData) {
    setLoading(true);
    setError(undefined);

    try {
      let response: Response;
      
      // Check if data is FormData (image upload) or regular object
      if (data instanceof FormData) {
        // Use /valuate-with-image endpoint for image uploads
        response = await fetch(`${API_BASE_URL}/valuate-with-image`, {
          method: "POST",
          body: data,
        });
      } else {
        // Use regular /valuate endpoint for JSON data
        response = await fetch(`${API_BASE_URL}/valuate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });
      }

      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? `Backend returned ${response.status}`);
      }

      setLastRequest(data instanceof FormData ? null : data);
      setResult(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to run valuation");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <div className="hero-card">
          <p className="eyebrow">NBFC Collateral Intelligence</p>
          <h1>Valuation built for recovery risk, not brochure price.</h1>
          <p className="hero-copy">
            TenzorXAI converts a property file into a lending-grade decision pack: market range,
            distress haircut, resale liquidity, confidence, flags, and LTV.
          </p>
          <div className="hero-metrics">
            <div className="metric-tile">
              <strong>100k</strong>
              <span>Synthetic records</span>
            </div>
            <div className="metric-tile">
              <strong>3.25%</strong>
              <span>Validation MAPE</span>
            </div>
            <div className="metric-tile">
              <strong>25</strong>
              <span>Locality markets</span>
            </div>
          </div>
        </div>

        <aside className="status-panel hero-card">
          <div className="status-header">
            <div>
              <p className="section-label">Engine Status</p>
              <h2>Credit stack online</h2>
            </div>
            <span className="status-pill">Live API</span>
          </div>
          <div className="audit-list">
            <div className="audit-row">
              <span>Valuation model</span>
              <strong>LightGBM + SHAP</strong>
            </div>
            <div className="audit-row">
              <span>Resale metric</span>
              <strong>RPI 0-100</strong>
            </div>
            <div className="audit-row">
              <span>Decision output</span>
              <strong>Standard + conservative LTV</strong>
            </div>
          </div>
        </aside>
      </section>

      <section className="workspace">
        <InputForm onSubmit={runValuation} loading={loading} error={error} />

        <div className="results-column">
          <div className="results-grid">
            {result ? (
              <>
                <ValuationCard result={result} />
                <LTVCard result={result} />
                <NarrativePanel result={result} />
                <RiskFlags result={result} />
                {result.image_analysis && <ImageAnalysisPanel result={result} />}
                <KeyDrivers result={result} />
                <div className="two-col">
                  <DistressBreakdown result={result} />
                  <ConfidenceBreakdown result={result} />
                </div>
                <CompsTable result={result} />
                <div className="two-col">
                  <WhatIfSimulator baseRequest={lastRequest} apiBaseUrl={API_BASE_URL} />
                  <ConfidenceHeatmap />
                </div>
              </>
            ) : (
              <EmptyState />
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
