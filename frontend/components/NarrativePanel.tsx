"use client";

import { useEffect, useState } from "react";
import type { ValuationResponse } from "@/app/page";

const WORKER_URL = process.env.NEXT_PUBLIC_WORKER_URL ?? "http://127.0.0.1:8787";

type NarrativeState = {
  narrative: string;
  source: "workers_ai" | "openrouter" | "fallback";
};

export default function NarrativePanel({ result }: { result: ValuationResponse }) {
  const [memo, setMemo] = useState<NarrativeState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    let cancelled = false;

    async function generateNarrative() {
      setLoading(true);
      setError(undefined);
      setMemo(null);

      try {
        const response = await fetch(`${WORKER_URL}/narrate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ valuation: result }),
        });

        if (!response.ok) {
          throw new Error(`Narrative worker returned ${response.status}`);
        }

        const payload = (await response.json()) as NarrativeState;
        if (!cancelled) setMemo(payload);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to generate narrative memo");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    generateNarrative();

    return () => {
      cancelled = true;
    };
  }, [result]);

  return (
    <section className="result-card narrative-card">
      <div className="card-topline">
        <div className="memo-brand">
          <div className={`memo-bot ${loading ? "is-thinking" : "is-ready"}`} aria-hidden="true">
            <span className="memo-bot-antenna" />
            <span className="memo-bot-head">
              <span className="memo-bot-eye left" />
              <span className="memo-bot-eye right" />
              <span className="memo-bot-mouth" />
            </span>
            <span className="memo-bot-ring" />
          </div>
          <div>
            <p className="section-label">Committee Note</p>
            <h2>{loading ? "Generating response" : "Narrative memo"}</h2>
            <p className="field-hint">This is the AI response, surfaced as the committee-facing explanation for the valuation.</p>
            {loading ? <p className="memo-status">Thinking, reading the collateral signals, and drafting the committee note...</p> : null}
          </div>
        </div>
        {loading ? <span className="pill pill-yellow">Processing</span> : memo ? <span className="pill pill-blue">{memo.source.replaceAll("_", " ")}</span> : null}
      </div>

      {loading ? (
        <div className="memo-callout">
          <div className="thinking-line">
            <span className="thinking-dot" />
            <span className="thinking-dot" />
            <span className="thinking-dot" />
          </div>
          <p className="rationale">Drafting lender memo from valuation signals...</p>
        </div>
      ) : null}

      {error ? (
        <div className="error-box">
          {error}. Start the Worker locally with <strong>npm run dev</strong> inside the worker folder.
        </div>
      ) : null}

      {memo ? (
        <div className="memo-callout">
          <p className="memo-label">Highlighted response</p>
          <p className="memo-text">{memo.narrative}</p>
        </div>
      ) : null}
    </section>
  );
}
