"use client";

import { useEffect, useState } from "react";
import type { ValuationResponse } from "@/app/page";
import type { ValuationFormData } from "@/components/InputForm";

type WhatIfResult = {
  base: ValuationResponse;
  perturbed: ValuationResponse;
  perturbations: Partial<ValuationFormData>;
  value_delta: number;
  value_delta_pct: number;
  rpi_delta: number;
  confidence_delta: number;
};

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDelta(value: number, suffix = "") {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value}${suffix}`;
}

function formatCurrencyDelta(value: number) {
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatCurrency(value)}`;
}

export default function WhatIfSimulator({
  baseRequest,
  apiBaseUrl,
}: {
  baseRequest: ValuationFormData | null;
  apiBaseUrl: string;
}) {
  const [ageYears, setAgeYears] = useState(3);
  const [floorNum, setFloorNum] = useState(10);
  const [sizeSqft, setSizeSqft] = useState(1250);
  const [legalStatus, setLegalStatus] = useState("clear");
  const [result, setResult] = useState<WhatIfResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    if (!baseRequest) return;
    setAgeYears(Math.round(baseRequest.age_years));
    setFloorNum(baseRequest.floor_num ?? 5);
    setSizeSqft(Math.round(baseRequest.size_sqft));
    setLegalStatus(baseRequest.legal_status ?? "clear");
    setResult(null);
    setError(undefined);
  }, [baseRequest]);

  async function runScenario() {
    if (!baseRequest) return;

    setLoading(true);
    setError(undefined);

    try {
      const response = await fetch(`${apiBaseUrl}/whatif`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          base_request: baseRequest,
          perturbations: {
            age_years: ageYears,
            floor_num: floorNum,
            size_sqft: sizeSqft,
            legal_status: legalStatus,
          },
        }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? `Backend returned ${response.status}`);
      }

      setResult(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to run what-if scenario");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="result-card">
      <p className="section-label">Scenario Lab</p>
      <h2>What-if simulator</h2>

      <div className="scenario-grid">
        <label>
          <span>Age: {ageYears} yrs</span>
          <input type="range" min="0" max="35" value={ageYears} onChange={(event) => setAgeYears(Number(event.target.value))} />
        </label>
        <label>
          <span>Floor: {floorNum}</span>
          <input type="range" min="0" max="30" value={floorNum} onChange={(event) => setFloorNum(Number(event.target.value))} />
        </label>
        <label>
          <span>Size: {sizeSqft} sqft</span>
          <input type="range" min="400" max="3000" step="50" value={sizeSqft} onChange={(event) => setSizeSqft(Number(event.target.value))} />
        </label>
        <label>
          <span>Legal status</span>
          <select value={legalStatus} onChange={(event) => setLegalStatus(event.target.value)}>
            <option value="clear">Clear</option>
            <option value="pending">Pending</option>
            <option value="disputed">Disputed</option>
          </select>
        </label>
      </div>

      <button className="secondary-button" type="button" onClick={runScenario} disabled={loading || !baseRequest}>
        {loading ? "Running scenario..." : "Run what-if"}
      </button>

      {!baseRequest ? (
        <p className="rationale">Run one valuation first to use this simulator.</p>
      ) : null}

      {error ? <div className="error-box">{error}</div> : null}

      {result ? (
        <div className="scenario-output">
          <div className="mini-stat">
            <span>Value delta</span>
            <strong>{formatCurrencyDelta(result.value_delta)}</strong>
          </div>
          <div className="mini-stat">
            <span>Value change</span>
            <strong>{formatDelta(result.value_delta_pct, "%")}</strong>
          </div>
          <div className="mini-stat">
            <span>RPI delta</span>
            <strong>{formatDelta(result.rpi_delta)}</strong>
          </div>
          <div className="mini-stat">
            <span>Confidence delta</span>
            <strong>{formatDelta(Math.round(result.confidence_delta * 100), " pts")}</strong>
          </div>
        </div>
      ) : (
        <p className="rationale">Stress the collateral file and compare value, liquidity, and confidence deltas.</p>
      )}
    </section>
  );
}
