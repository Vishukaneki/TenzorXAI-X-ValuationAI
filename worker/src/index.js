/**
 * Cloudflare Worker - Narrative Generator
 * POST /narrate  { valuation: <JSON object> }
 * Returns: { narrative: "<string>", source: "workers_ai" | "openrouter" | "fallback" }
 */

const SYSTEM_PROMPT = `You are a senior credit analyst at an Indian NBFC writing
collateral assessment summaries for the credit committee.
Write in professional financial English. Be specific with numbers.
Never mention "AI", "model", or "algorithm".
Write exactly 5 concise bullet points.
Each bullet must start with "- ".
Cover market value, distress value, liquidity/time-to-sell, risk flags, and LTV recommendation.
No headers. No paragraph format.`;

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return corsResponse(new Response(null, { status: 204 }));
    }

    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/health") {
      return corsResponse(Response.json({ status: "ok", service: "narrative-worker" }));
    }

    if (request.method !== "POST") {
      return corsResponse(new Response("Method not allowed", { status: 405 }));
    }

    if (url.pathname !== "/" && url.pathname !== "/narrate") {
      return corsResponse(new Response("Not found", { status: 404 }));
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return corsResponse(new Response("Invalid JSON", { status: 400 }));
    }

    const valuation = body.valuation;
    if (!valuation) {
      return corsResponse(new Response("Missing valuation field", { status: 400 }));
    }

    const userPrompt = buildPrompt(valuation);

    try {
      const narrative = await callWorkersAI(env, userPrompt);
      return corsResponse(Response.json({ narrative, source: "workers_ai" }));
    } catch (error) {
      console.error("Workers AI failed:", error.message);
    }

    try {
      const narrative = await callOpenRouter(env, userPrompt);
      return corsResponse(Response.json({ narrative, source: "openrouter" }));
    } catch (error) {
      console.error("OpenRouter failed:", error.message);
      return corsResponse(
        Response.json({ narrative: buildFallbackNarrative(valuation), source: "fallback" })
      );
    }
  },
};

function buildPrompt(v) {
  const mvLow = fmt(v.market_value_range?.[0]);
  const mvHigh = fmt(v.market_value_range?.[1]);
  const dvLow = fmt(v.distress_value_range?.[0]);
  const dvHigh = fmt(v.distress_value_range?.[1]);
  const rpi = v.resale_potential_index ?? "N/A";
  const ttlL = v.estimated_time_to_sell_days?.[0] ?? "N/A";
  const ttlH = v.estimated_time_to_sell_days?.[1] ?? "N/A";
  const conf = v.confidence_score ? `${(v.confidence_score * 100).toFixed(0)}%` : "N/A";
  const stdLTV = v.ltv_recommendation?.standard
    ? `${(v.ltv_recommendation.standard * 100).toFixed(0)}%`
    : "N/A";
  const conLTV = v.ltv_recommendation?.conservative
    ? `${(v.ltv_recommendation.conservative * 100).toFixed(0)}%`
    : "N/A";

  const highFlags = (v.risk_flags ?? [])
    .filter((flag) => flag.severity === "high")
    .map((flag) => flag.flag.replaceAll("_", " "))
    .join(", ") || "none";

  const topDriver = v.key_drivers?.[0]?.driver?.replaceAll("_", " ") ?? "location";

  return `Write a credit committee collateral assessment summary for this property:

Market Value: INR ${mvLow} - INR ${mvHigh}
Distress Sale Value: INR ${dvLow} - INR ${dvHigh}
Resale Potential Index: ${rpi}/100
Estimated Time to Sell: ${ttlL}-${ttlH} days
Confidence Score: ${conf}
Recommended LTV: ${conLTV} conservative to ${stdLTV} standard
High Severity Risk Flags: ${highFlags}
Primary Value Driver: ${topDriver}

Write the 5 bullet point summary now:`;
}

async function callWorkersAI(env, userPrompt) {
  const response = await env.AI.run("@cf/meta/llama-3.1-8b-instruct", {
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      { role: "user", content: userPrompt },
    ],
    max_tokens: 320,
    temperature: 0.25,
  });

  const text = response?.response?.trim();
  if (!text) throw new Error("Empty Workers AI response");
  return normalizeBullets(text);
}

async function callOpenRouter(env, userPrompt) {
  const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.OPENROUTER_API_KEY}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://collateral-engine.arbitrz.com",
    },
    body: JSON.stringify({
      model: "meta-llama/llama-3.3-70b-instruct:free",
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: userPrompt },
      ],
      max_tokens: 320,
      temperature: 0.25,
    }),
  });

  const data = await res.json();
  const text = data?.choices?.[0]?.message?.content?.trim();
  if (!text) throw new Error("Empty OpenRouter response");
  return normalizeBullets(text);
}

function buildFallbackNarrative(v) {
  const mvMid = avg(v.market_value_range);
  const distressMid = avg(v.distress_value_range);
  const rpi = v.resale_potential_index ?? 50;
  const ttlL = v.estimated_time_to_sell_days?.[0] ?? "N/A";
  const ttlH = v.estimated_time_to_sell_days?.[1] ?? "N/A";
  const conf = v.confidence_score ?? 0.6;
  const liq = rpi >= 70 ? "favorable" : rpi >= 50 ? "moderate" : "limited";
  const flags = (v.risk_flags ?? []).filter((flag) => flag.severity === "high").length;
  const ltv = v.ltv_recommendation;

  return [
    `- Market value is assessed around INR ${fmt(mvMid)} based on the submitted collateral profile.`,
    `- Distress sale value is estimated around INR ${fmt(distressMid)}, reflecting forced-sale recovery assumptions.`,
    `- Resale potential index is ${rpi}/100 with ${liq} liquidity and an expected sale window of ${ttlL}-${ttlH} days.`,
    `- Risk review shows ${flags} high-severity flag(s), with confidence at ${(conf * 100).toFixed(0)}%.`,
    `- Recommended LTV is ${(ltv?.conservative * 100).toFixed(0)}% conservative to ${(ltv?.standard * 100).toFixed(0)}% standard, subject to legal and documentation checks.`,
  ].join("\n");
}

function normalizeBullets(text) {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => line.replace(/^[-*]\s*/, "- ").replace(/^\d+[.)]\s*/, "- "))
    .slice(0, 5)
    .join("\n");
}

function fmt(n) {
  if (n == null) return "N/A";
  if (n >= 10_000_000) return `${(n / 10_000_000).toFixed(2)} Cr`;
  if (n >= 100_000) return `${(n / 100_000).toFixed(2)} L`;
  return n.toLocaleString("en-IN");
}

function avg(arr) {
  if (!arr || arr.length < 2) return arr?.[0] ?? 0;
  return (arr[0] + arr[1]) / 2;
}

function corsResponse(res) {
  const headers = new Headers(res.headers);
  headers.set("Access-Control-Allow-Origin", "*");
  headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  headers.set("Access-Control-Allow-Headers", "Content-Type");
  return new Response(res.body, { status: res.status, headers });
}
