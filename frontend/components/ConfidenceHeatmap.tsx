"use client";

import { useEffect, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

type HeatmapLocality = {
  locality: string;
  city: string;
  lat: number;
  lon: number;
  tier: number;
  avg_confidence: number;
  listing_density: number;
  record_count: number;
  avg_market_value: number;
};

function bandForConfidence(confidence: number) {
  if (confidence >= 0.76) return "high";
  if (confidence >= 0.66) return "medium";
  return "low";
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

export default function ConfidenceHeatmap() {
  const [localities, setLocalities] = useState<HeatmapLocality[]>([]);
  const [selected, setSelected] = useState<HeatmapLocality | null>(null);
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    let cancelled = false;

    async function loadHeatmap() {
      try {
        const response = await fetch(`${API_BASE_URL}/heatmap`);
        if (!response.ok) throw new Error(`Backend returned ${response.status}`);
        const data = (await response.json()) as HeatmapLocality[];
        if (!cancelled) {
          setLocalities(data);
          setSelected(data[0] ?? null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to load heatmap data");
        }
      }
    }

    loadHeatmap();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="result-card">
      <p className="section-label">Portfolio View</p>
      <h2>Confidence heatmap</h2>

      {error ? <div className="error-box">{error}</div> : null}

      <div className="heatmap-grid">
        {localities.map((item) => (
          <button
            className={`heatmap-cell ${bandForConfidence(item.avg_confidence)} ${selected?.locality === item.locality ? "active" : ""}`}
            key={item.locality}
            onClick={() => setSelected(item)}
            type="button"
          >
            <strong>{Math.round(item.avg_confidence * 100)}%</strong>
            <span>{item.locality}</span>
          </button>
        ))}
      </div>

      {selected ? (
        <div className="heatmap-detail">
          <div>
            <span>Selected market</span>
            <strong>{selected.locality}, {selected.city}</strong>
          </div>
          <div>
            <span>Tier</span>
            <strong>{selected.tier}</strong>
          </div>
          <div>
            <span>Listing density</span>
            <strong>{selected.listing_density}</strong>
          </div>
          <div>
            <span>Avg market value</span>
            <strong>{formatCurrency(selected.avg_market_value)}</strong>
          </div>
        </div>
      ) : (
        <p className="rationale">Loading locality confidence data...</p>
      )}
    </section>
  );
}
