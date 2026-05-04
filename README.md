<div align="center">

```
 ██████╗ ██████╗ ██╗     ██╗      █████╗ ████████╗███████╗██████╗  █████╗ ██╗
██╔════╝██╔═══██╗██║     ██║     ██╔══██╗╚══██╔══╝██╔════╝██╔══██╗██╔══██╗██║
██║     ██║   ██║██║     ██║     ███████║   ██║   █████╗  ██████╔╝███████║██║
██║     ██║   ██║██║     ██║     ██╔══██║   ██║   ██╔══╝  ██╔══██╗██╔══██║██║
╚██████╗╚██████╔╝███████╗███████╗██║  ██║   ██║   ███████╗██║  ██║██║  ██║███████╗
 ╚═════╝ ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
```

# AI-Powered Collateral Valuation & Resale Liquidity Engine

**A collateral intelligence layer for Indian NBFCs and secured lenders.**
Not a property price predictor. A full-stack lending decision support system.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)
![LightGBM](https://img.shields.io/badge/LightGBM-4.3-2980B9?style=flat-square)
![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=nextdotjs&logoColor=white)
![Cloudflare](https://img.shields.io/badge/Cloudflare_Workers-AI-F38020?style=flat-square&logo=cloudflare&logoColor=white)
![Status](https://img.shields.io/badge/Status-Full_Stack_Complete-22c55e?style=flat-square)

</div>

---

## The Problem We're Solving

Property-backed lending in India relies on:
- Manual site inspections by valuers
- Broker inputs with inherent conflicts of interest
- Circle rates that lag actual market by 2–5 years
- Subjective local judgement with no audit trail

The result: **valuation variance of 20–40%** on the same asset, conservative lending decisions, slow credit turnaround, and no systematic framework for exit risk.

For an NBFC, **resale certainty matters as much as current value.** A ₹2Cr apartment in a tier-3 locality with zero market activity is riskier collateral than a ₹1.5Cr apartment in Koramangala — even though it's nominally worth more.

This engine answers both questions a lender actually needs answered:

> **1. What is this property worth today?**
> **2. If we have to liquidate it, how fast and at what haircut?**

---

## What This Is Not

| ❌ What we didn't build | ✅ What we built instead |
|---|---|
| A regression model predicting price | A structured valuation + liquidity framework |
| A single point estimate | Range-based outputs with calibrated uncertainty |
| A black box | Every output traceable to an input or business rule |
| A chatbot | A credit committee decision support tool |
| Scraped data dependent | Physics-based synthetic data anchored to real circle rates |

## Image Analysis Feature

The system includes an optional image analysis component that uses Cloudflare Workers AI to analyze property images:

- **Visual Condition Assessment**: Detects construction quality, visible issues, and property condition
- **Risk Flag Integration**: Image analysis results are converted to risk flags that affect LTV recommendations
- **Confidence Scoring**: AI confidence levels contribute to overall valuation confidence
- **Fallback Mechanism**: Works with or without Cloudflare credentials using mock analysis for testing

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                                 │
│                                                                               │
│   Next.js 14 (App Router) · Tailwind CSS · shadcn/ui · Recharts · Leaflet   │
│                                                                               │
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Input Form  │  │  Valuation Card  │  │  What-If     │  │  Confidence  │  │
│  │              │  │                  │  │  Simulator   │  │  Heatmap     │  │
│  │  Mandatory:  │  │  Market Range    │  │              │  │              │  │
│  │  · locality  │  │  Distress Range  │  │  Sliders:    │  │  Leaflet.js  │  │
│  │  · type      │  │  RPI 0–100       │  │  · Age       │  │  per-locality│  │
│  │  · subtype   │  │  TTL Range       │  │  · Floor     │  │  confidence  │  │
│  │  · size      │  │  Confidence      │  │  · Size      │  │  color-coded │  │
│  │  · age       │  │  Risk Flags      │  │              │  │  click for   │  │
│  │              │  │  LTV Rec         │  │  Delta bar   │  │  stats popup │  │
│  │  Optional:   │  │  Comps Table     │  │  chart       │  │              │  │
│  │  · floor     │  │  SHAP Drivers    │  │  (recharts)  │  │              │  │
│  │  · legal     │  │  Narrative       │  │              │  │              │  │
│  │  · occupancy │  │  Image Analysis  │  │              │  │              │  │
│  │  · GPS coords│  │  Proximity Stats │  │              │  │              │  │
│  │  · image     │  │                  │  │              │  │              │  │
│  └──────────────┘  └─────────────────┘  └──────────────┘  └──────────────┘  │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
              ┌────────────────┴─────────────────┐
              │ POST /valuate                     │ POST /narrate
              │ POST /valuate-with-image          │
              │ POST /whatif                      │
              │ GET  /heatmap                     │
              ▼                                   ▼
┌─────────────────────────────┐   ┌──────────────────────────────────────────┐
│       FastAPI Backend        │   │          Cloudflare Worker                │
│       Python 3.11            │   │                                           │
│       Uvicorn                │   │  Primary:  Workers AI                     │
│                              │   │            llama-3.1-8b-instruct          │
│  All 10 engine modules       │   │                                           │
│  load at startup.            │   │  Fallback: OpenRouter                     │
│  Data held in memory.        │   │            llama-3.3-70b-instruct:free    │
│  No database required.       │   │                                           │
│                              │   │  Fallback²: Deterministic template        │
└──────────────┬───────────────┘   │            (never fails at demo)         │
               │                   └─────────────────────┬────────────────────┘
               ▼                                         │
┌───────────────────────────────────────────────────────┼─────────────────────┐
│                    IMAGE ANALYSIS                     │                     │
│                                                       ▼                     │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │              Cloudflare Workers AI (LLaVA)                             │  │
│  │                                                                       │  │
│  │  Analyzes property images for:                                        │  │
│  │  - Construction quality                                               │  │
│  │  - Visible condition                                                  │  │
│  │  - Property type verification                                         │  │
│  │  - Visible issues (cracks, water stains, etc.)                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ENGINE LAYER                                    │
│                                                                               │
│  ① feature_engineer.py   → circle rate + tier + age + floor + completeness  │
│  ② valuation_model.py    → LightGBM predict + ±8% band + SHAP drivers       │
│  ③ comparable_engine.py  → top-5 comps by city + type + size ±25%           │
│  ④ liquidity_scorer.py   → RPI 0–100 from 7 weighted components             │
│  ⑤ distress_calculator.py→ dynamic discount decomposed across 6 variables   │
│  ⑥ ttl_calculator.py     → lower/upper bound with separate multiplier paths  │
│  ⑦ confidence_aggregator.py → 6–7 signals weighted → 0–1 score             │
│  ⑧ risk_flags.py         → structured flags: {name, severity, ltv_impact}  │
│  ⑨ ltv_recommender.py   → conservative + standard LTV with rationale        │
│  ⑩ image_analyzer.py    → LLaVA vision → condition + risk signals           │
│                                                                               │
└──────────────┬──────────────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               DATA LAYER                                     │
│                                                                               │
│  synthetic_100k.parquet     100k records · 4 cities · 25 localities          │
│  locality_metadata.csv      tier · circle rate · norm_size · lat/lon         │
│  circle_rates.csv           per-locality statutory floor values               │
│  locality_confidence.json   precomputed heatmap data                         │
│  model.pkl                  trained LightGBM · 3.25% MAPE                   │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## How the Application Works - Step by Step

This section explains the complete workflow of the application from user interaction to final output.

### Step 1: User Input and Request Initiation

1. **Frontend Interaction**: User accesses the web interface at `http://localhost:3000`
2. **Data Entry**: User fills out the property valuation form with:
   - **Required Fields**: locality, property type, subtype, size (sqft), age (years)
   - **Optional Fields**: floor number, total floors, lift availability, legal status, occupancy status, rental yield
   - **Geolocation (Optional)**: latitude and longitude coordinates for proximity scoring
   - **Image Upload (Optional)**: property photo for visual condition assessment

3. **Request Routing**:
   - Standard submission → `POST /valuate` endpoint
   - With image → `POST /valuate-with-image` endpoint
   - Scenario analysis → `POST /whatif` endpoint

### Step 2: Backend Processing Pipeline

#### 2.1 Locality Context Resolution
- System looks up locality in `locality_metadata.csv` to get:
  - `tier` (1=prime, 2=mid, 3=outer)
  - `circle_rate` (statutory floor value)
  - `norm_size` (typical property size)
  - `listing_density` (market activity indicator)
  - Geographic coordinates (centroid)

#### 2.2 Feature Engineering
The system calculates 13 predictive features:
- **Age Depreciation**: `max(0.60, 1.0 - 0.01 × age)`
- **Floor Adjustment**: Ground (-8%), Top (+5%), Mid (0%)
- **Subtype Premium**: Based on property configuration
- **Market Activity Proxy**: From listing density data
- **Size vs Norm**: Anomaly detection feature
- **Completeness Score**: Percentage of optional fields provided
- **Infrastructure Score**: Based on locality tier

#### 2.3 Proximity Scoring (When Coordinates Provided)
If latitude/longitude are provided:
1. **Live POI Lookup**: Queries Overpass API for nearby amenities when `ENABLE_POI_LOOKUP=true`
2. **POI Categories Searched**:
   - Schools (educational accessibility)
   - Metro stations (public transport)
   - Markets (commercial access)
   - Busy areas (urban activity)
3. **Fallback Mechanism**: Uses heuristic calculation if live lookup fails
4. **Result**: Proximity score (0-100) with component breakdown:
   - School distance
   - Metro distance
   - Market distance
   - Busy area score

### 3) Core Valuation Engine

#### 3.1 Machine Learning Prediction
- **Model**: LightGBM trained on 100k synthetic records
- **Input**: 13 engineered features
- **Output**: Price per sqft prediction
- **Range Calculation**: ±8% uncertainty band around point estimate
- **Explainability**: Top 5 SHAP drivers showing feature impact

#### 3.2 Comparable Transaction Analysis
- Searches synthetic dataset for similar properties:
  - Same city + property type + tier
  - Size within ±25% of subject property
- Returns top 5 comparable transactions
- Calculates density score (0-1) for confidence weighting

#### 3.3 Risk and Liquidity Assessment
Multiple engine modules process the valuation data:

**Resale Potential Index (RPI)**: 0-100 score combining:
- Asset type base value
- Location demand factors
- Market activity boost
- Configuration standardness
- Age factor
- Lift availability
- Legal clarity

**Distress Value Calculation**: 6-component discount breakdown:
- Asset type base discount
- Location demand modifier
- Legal clarity penalty
- Market activity modifier
- Buyer pool penalty
- Asset uniqueness penalty

**Time to Liquidate (TTL)**: Lower/upper bound estimation:
- Lower bound: Base days × demand multiplier × (1 - RPI/200)
- Upper bound: Lower × legal multiplier × uniqueness multiplier × stress multiplier

**Confidence Scoring**: Weighted aggregation (0-1 score):
- Data completeness (25%)
- Comparable density (20%)
- Circle rate freshness (15%)
- Input consistency (20%)
- Legal clarity (10%)
- TTL range penalty (10%)
- Image quality (5%, when provided)

**Risk Flag Generation**: Structured alerts with severity and LTV impact:
- Size anomalies
- Circle rate variance
- Comparable density issues
- Market activity concerns
- Configuration problems
- Building age flags
- Legal status issues
- Image-based visual issues (when provided)

**LTV Recommendation**: Conservative and standard loan-to-value ratios:
- Standard LTV = Base + tier adjustment + RPI adjustment - confidence penalty
- Conservative LTV = Standard - Σ(risk flag haircuts) - 0.05
- Natural language rationale explaining the recommendation

### 4) Image Intelligence Processing (When Image Provided)

If property image was uploaded:

1. **Cloudflare AI Analysis**: Image sent to LLaVA-1.5-7B model via Cloudflare Workers AI
2. **Structured Response Parsing**: AI output converted to standardized assessment:
   - Construction quality (good/average/poor)
   - Visible condition (well_maintained/average/deteriorating)
   - Visible issues (cracks, stains, structural damage)
   - Property type verification
   - Surrounding area quality
   - AI confidence level (0.0-1.0)
3. **Risk Integration**: Image findings converted to:
   - Additional risk flags with severity ratings
   - Confidence score contribution (5% weight)
   - Market/RPI penalties for severe visual issues

### 5) What-If Scenario Analysis

When user requests scenario analysis via `/whatif` endpoint:

1. **Base Valuation**: Complete pipeline run on current property data
2. **Perturbation Application**: User-specified changes (age, floor, size, etc.)
3. **Fast Mode Processing**: Skips live POI calls for speed, uses heuristic proximity
4. **Delta Calculation**: Compares base vs perturbed results:
   - Value change (absolute and percentage)
   - RPI change
   - Confidence score change
5. **Side-by-side Comparison**: Both results displayed with visual deltas

### 6) Narrative Generation

Independent process that generates natural language explanation:

1. **Cloudflare Worker Invocation**: Sends valuation data to CF Worker
2. **Primary LLM**: llama-3.1-8b-instruct for detailed narrative
3. **Fallback Chain**: 
   - OpenRouter llama-3-8b-instruct:free if primary unavailable
   - Deterministic template as hard fallback (never fails)
4. **Output**: Credit committee paragraph explaining valuation rationale

### 7) Final Response Assembly and Frontend Rendering

Backend combines all processed information into structured JSON response:

**Core Valuation Data**:
- Market value range (with ±8% uncertainty band)
- Distress value range with 6-component breakdown
- Resale Potential Index (0-100) with interpretation
- Time-to-liquidate estimate (days, lower/upper bounds)
- Confidence score (0-1) with per-signal breakdown
- Comparable transactions with price/sqft highlights
- Key drivers from SHAP analysis
- Structured risk flags with severity and LTV impact
- LTV recommendations (standard and conservative) with rationale

**Optional Components**:
- Image analysis results and impact assessment
- Location proximity score and component breakdown
- What-if scenario deltas

**Frontend Visualization**:
- Interactive dashboard with all components
- Valuation card with ranges and RPI gauge
- Distress waterfall chart showing discount components
- Confidence breakdown with horizontal bar charts
- Risk flags panel color-coded by severity
- Comparable transactions table with sorting
- LTV card with rationale explanation
- What-if simulator with delta visualization
- Confidence heatmap for locality comparison
- Image analysis panel (when applicable)
- Narrative panel with fade-in explanation

---

## Engine Modules — Deep Dive

### ① Feature Engineer
Transforms raw API input into the 13-feature vector fed to LightGBM. Every derivation is documented and traceable.

| Feature | Source | Logic |
|---|---|---|
| `circle_rate` | locality lookup | statutory floor, ₹/sqft |
| `tier` | locality metadata | 1 = prime, 2 = mid, 3 = outer |
| `market_multiplier` | locality metadata | µ of historical market/circle ratio |
| `age_depreciation` | age input | `max(0.60, 1.0 - 0.01 × age)` |
| `floor_adjustment` | floor + total floors | ground: −8%, top: +5%, mid: 0% |
| `subtype_premium` | subtype lookup | 2BHK = 1.0 baseline |
| `size_vs_norm` | size ÷ locality norm | anomaly signal |
| `infra_score` | tier proxy | tier-1: 0.85, tier-2: 0.60, tier-3: 0.35 |
| `market_activity` | listing_density ÷ 100 | 0–1 |
| `completeness` | optional fields filled | 0.5 (minimal) → 1.0 (full) |

### ② Valuation Model
LightGBM trained on 100k synthetic records. Outputs price/sqft × size = point estimate, then applies ±8% uncertainty band for the range. SHAP TreeExplainer extracts the top-5 feature contributions as percentage impacts — these become `key_drivers` in the response.

**Validation MAPE: 3.25%** — strong for a physics-based synthetic dataset.

### ③ Comparable Engine
Queries the synthetic dataset for the 5 nearest comparable transactions matching: same city + same property_type + same tier + size within ±25%. Falls back to same city + type if the tier is sparse. Returns a `density_score` (0–1) that feeds into the confidence aggregator.

### ④ Liquidity Scorer — Resale Potential Index
Seven components summed and clipped to 0–100:

```
RPI = asset_type_base          # apartment: 72, villa: 55, plot: 48, commercial: 42
    + location_demand           # tier-1: +15, tier-2: +5, tier-3: −10
    + market_activity_boost     # (activity − 0.5) × 20 → ±10
    + config_standardness       # 2BHK/3BHK: +5, villa: −5
    + age_factor                # −0.5 per year beyond age 15
    + lift_penalty              # apartment without lift: −5
    + legal_clarity             # non-clear title: −10
```

Interpretation: 80–100 = highly liquid · 50–79 = moderate · <50 = illiquid/specialized

### ⑤ Distress Calculator
Six-variable decomposition — every component visible in the API response:

```
total_discount = asset_type_base           # 12–28% by type
               + location_demand_modifier  # tier-1: −4%, tier-3: +5%
               + legal_clarity_penalty     # +7% if not clear
               + market_activity_modifier  # low activity → higher discount
               + buyer_pool_penalty        # thin buyer pool → +3–6%
               + asset_uniqueness_penalty  # non-standard config → +4%

distress_range = market_range × (1 − total_discount)
```

### ⑥ Time To Liquidate
Lower and upper bounds computed via separate multiplier paths — range width itself becomes a confidence penalty signal:

```
lower = base_days[type] × demand_multiplier × (1 − RPI/200)
upper = lower × legal_multiplier × uniqueness_multiplier × stress_multiplier
```

### ⑦ Confidence Aggregator
Weighted signal fusion returning both a score and a per-signal breakdown for UI display:

| Signal | Weight | Description |
|---|---|---|
| `data_completeness` | 25% | % of optional fields provided |
| `comparable_density` | 20% | how many comps matched |
| `circle_rate_freshness` | 15% | tier-1 data is more current |
| `input_consistency` | 20% | size vs locality norm deviation |
| `legal_clarity` | 10% | title status |
| `ttl_range_penalty` | 10% | wide TTL range = uncertain market |
| `image_quality` | 5% | only when image is provided |

### ⑧ Risk Flag Engine
Structured flags with severity and quantified LTV impact — not just a list of strings:

```json
{
  "flag": "size_significantly_above_locality_norm",
  "severity": "high",
  "ltv_impact": -7,
  "detail": "Property is 52% larger than locality median"
}
```

Seven flag categories: size anomaly · circle rate variance · comp density · market activity · configuration · building age · legal status. Image analysis adds up to 4 additional visual flags.

### ⑨ LTV Recommender
Produces the output NBFCs actually use for disbursement decisions:

```
standard     = base_ltv[type] + tier_adj + rpi_adj − conf_penalty
conservative = standard − Σ(risk_flag_haircuts) − 0.05
```

Plus a natural language rationale string built from the actual flag data — not a template.

### ⑩ Image Analyzer
Sends property photos to Cloudflare Workers AI (LLaVA-1.5-7B) with a structured prompt. Returns a typed assessment object that feeds directly into risk flags and confidence:

- `construction_quality` → liquidity modifier
- `visible_condition` → risk flag if deteriorating
- `visible_issues` → individual flags for cracks, stains, structural damage
- `property_type_matches_claimed` → high-severity flag if mismatch
- `confidence_in_analysis` → added to confidence aggregator (5% weight)

---

## API Reference

### `POST /valuate`
Full valuation pipeline. Returns complete JSON response.

```json
// Request
{
  "locality": "Kondapur",
  "property_type": "apartment",
  "subtype": "2BHK",
  "size_sqft": 1150,
  "age_years": 8,
  "floor_num": 5,
  "total_floors": 12,
  "has_lift": true,
  "legal_status": "clear"
}

// Response
{
  "market_value_range": [9500000, 11500000],
  "distress_value_range": [7980000, 9660000],
  "distress_discount_breakdown": {
    "asset_type_base": 0.12,
    "location_demand_modifier": 0.00,
    "legal_clarity_penalty": 0.00,
    "market_activity_modifier": 0.02,
    "buyer_pool_penalty": 0.00,
    "asset_uniqueness_penalty": 0.00,
    "total_discount": 0.14
  },
  "resale_potential_index": 74.2,
  "rpi_interpretation": "moderate_liquidity",
  "rpi_components": { ... },
  "estimated_time_to_sell_days": [42, 75],
  "confidence_score": 0.71,
  "confidence_breakdown": { ... },
  "comparable_transactions": [ ... ],
  "key_drivers": [
    { "driver": "circle_rate", "shap_impact": "+12.4%", "direction": "positive" },
    { "driver": "market_activity", "shap_impact": "+4.1%", "direction": "positive" }
  ],
  "risk_flags": [
    { "flag": "size_above_locality_norm", "severity": "medium", "ltv_impact": -3, "detail": "..." }
  ],
  "ltv_recommendation": {
    "standard": 0.68,
    "conservative": 0.60,
    "rationale": "Tier-2 location with 74/100 resale potential supports 68% standard LTV. ..."
  }
}
```

### `POST /valuate-with-image`
Multipart form data. Same as above plus image upload → LLaVA analysis injected into risk flags and confidence.

### `POST /whatif`
Perturbation analysis. Reruns the full pipeline with modified inputs and returns both results plus computed deltas.

```json
// Request
{
  "base_request": { ...same as /valuate... },
  "perturbations": { "age_years": 3, "floor_num": 10 }
}

// Response
{
  "base": { ...full valuation... },
  "perturbed": { ...full valuation... },
  "value_delta": 850000,
  "value_delta_pct": 8.1,
  "rpi_delta": 3.2,
  "confidence_delta": 0.04
}
```

### `GET /heatmap`
Returns precomputed per-locality confidence data for Leaflet.js choropleth map.

### `GET /localities`
Returns list of all supported locality names.

---

## Data Architecture

### Synthetic Data Generation — Why It's Defensible

We don't use scraped data. Scraping is legally grey, brittle at demo time, and produces noisy labels. Instead, we generate physics-based synthetic data anchored to government-published circle rates.

**The generation formula:**

```
price_per_sqft = circle_rate[locality]
               × market_multiplier        # sampled from N(µ_tier, σ_tier)
               × subtype_premium          # 2BHK = 1.0, villa = 1.05–1.15
               × age_depreciation         # max(0.60, 1 − 0.01 × age)
               × (1 + floor_adjustment)   # −8% to +5%
               × (1 + 0.05 × infra_score) # infrastructure premium
               × N(1.0, 0.04)             # residual market noise
```

When a judge asks "how did you generate this?" — this is the answer. It's how manual valuers actually think.

### Coverage

| City | Localities | Circle Rate Range |
|---|---|---|
| Delhi NCR | 7 | ₹3,000 – ₹9,000/sqft |
| Mumbai MMR | 6 | ₹5,500 – ₹18,000/sqft |
| Bangalore | 6 | ₹3,500 – ₹7,500/sqft |
| Hyderabad | 6 | ₹3,200 – ₹8,000/sqft |

**Total: 25 localities · 100,000 synthetic records · 31 columns**

### Model Performance

```
Algorithm:        LightGBM (gradient boosted trees)
Target:           price_per_sqft
Train / Val:      85,000 / 15,000 records
Validation MAPE:  3.25%
Top features:     circle_rate, market_activity, listing_density,
                  age_depreciation, market_multiplier
```

---

## Tech Stack

### Backend
| Tool | Version | Purpose |
|---|---|---|
| Python | 3.11 | Runtime |
| FastAPI | 0.111 | REST API framework |
| Uvicorn | 0.29 | ASGI server |
| LightGBM | 4.3 | Valuation model |
| SHAP | 0.45 | Model explainability / key drivers |
| Pandas | 2.2 | Data processing |
| PyArrow | 16.0 | Parquet I/O |
| httpx | 0.27 | Async HTTP (LLaVA calls) |
| Pydantic | 2.7 | Request/response validation |
| scikit-learn | 1.4 | Train/val split + metrics |

### AI / Inference
| Tool | Purpose |
|---|---|
| Cloudflare Workers AI — `llama-3.1-8b-instruct` | Narrative generation (primary) |
| Cloudflare Workers AI — `llava-1.5-7b-hf` | Property image analysis |
| OpenRouter — `meta-llama/llama-3.3-70b-instruct:free` | Narrative fallback |
| Deterministic template | Hard fallback (never fails at demo) |

### Frontend
| Tool | Purpose |
|---|---|
| Next.js 14 | App Router, SSR |
| Tailwind CSS | Styling |
| shadcn/ui | Component library |
| Recharts | What-if delta bar chart |
| Leaflet.js | Confidence heatmap |

### Infrastructure
| Tool | Purpose |
|---|---|
| Cloudflare Workers | Narrative generation edge function |
| Railway / Render | FastAPI backend hosting (free tier) |
| Vercel | Next.js frontend hosting |

---

## Project Structure

```
TenzorXAI/
├── LICENSE
├── README.md
├── backend/
│   ├── main.py
│   ├── schemas.py
│   ├── feature_engineer.py
│   ├── proximity_engine.py
│   ├── valuation_model.py
│   ├── comparable_engine.py
│   ├── engine_modules.py
│   ├── image_analyzer.py
│   ├── logger.py
│   ├── requirements.txt
│   ├── scripts/
│   │   ├── synthetic_generator.py
│   │   └── train_model.py
│   └── data/
│       ├── synthetic_100k.parquet
│       ├── locality_metadata.csv
│       ├── circle_rates.csv
│       ├── locality_confidence.json
│       └── model.pkl
├── frontend/
│   ├── package.json
│   ├── next.config.mjs
│   ├── tsconfig.json
│   ├── app/
│   │   ├── page.tsx
│   │   ├── layout.tsx
│   │   ├── globals.css
│   │   └── results/page.tsx
│   └── components/
│       ├── InputForm.tsx
│       ├── ValuationCard.tsx
│       ├── DistressBreakdown.tsx
│       ├── ConfidenceBreakdown.tsx
│       ├── CompsTable.tsx
│       ├── RiskFlags.tsx
│       ├── LTVCard.tsx
│       ├── WhatIfSimulator.tsx
│       ├── ConfidenceHeatmap.tsx
│       ├── NarrativePanel.tsx
│       └── ImageAnalysisPanel.tsx
├── worker/
│   ├── package.json
│   ├── wrangler.toml
│   └── src/
│       └── index.js
├── docs/
│   ├── colab_training.md
│   └── image_analysis_setup.md
└── notebooks/
    └── train_backend_on_colab.ipynb
```

---

## What's Built vs What's Planned

### ✅ Complete

- [x] Physics-based synthetic data generator — 100k records, 25 localities, 4 cities
- [x] LightGBM valuation model — 3.25% MAPE on validation set
- [x] Full feature engineering pipeline — 13 features, all traceable
- [x] Comparable transaction engine — size + type + tier matching
- [x] Resale Potential Index — 7-component decomposition
- [x] Distress value calculator — 6-variable discount breakdown
- [x] Time-to-liquidate estimator — separate lower/upper bound paths
- [x] Confidence aggregator — 6–7 weighted signals with per-signal breakdown
- [x] Risk flag engine — severity + LTV impact per flag
- [x] LTV recommender — conservative + standard + natural language rationale
- [x] Image analyzer — LLaVA via CF Workers AI → risk signals
- [x] FastAPI backend — `/valuate`, `/valuate-with-image`, `/whatif`, `/heatmap`, `/localities`, `/health`
- [x] Cloudflare Worker — narrative generation with 3-tier fallback chain
- [x] Precomputed heatmap data — per-locality confidence stats
- [x] **Frontend — Input Form** — mandatory + optional fields, image upload
- [x] **Frontend — Valuation Card** — range display, RPI gauge, confidence meter
- [x] **Frontend — Distress Breakdown** — waterfall chart of discount components
- [x] **Frontend — Confidence Breakdown** — per-signal horizontal bar chart
- [x] **Frontend — Comparables Table** — sortable, price/sqft highlighted
- [x] **Frontend — Risk Flags Panel** — color coded by severity (red/amber/green)
- [x] **Frontend — LTV Card** — conservative vs standard with rationale
- [x] **Frontend — What-If Simulator** — sliders → delta bar chart (Recharts)
- [x] **Frontend — Confidence Heatmap** — Leaflet choropleth, click for locality stats
- [x] **Frontend — Narrative Panel** — LLM paragraph, fade-in after valuation card

---

## Running Locally

For low-spec laptops, train the backend data/model in Google Colab instead of locally:
[Colab backend training guide](docs/colab_training.md) and [ready-to-run notebook](notebooks/train_backend_on_colab.ipynb).

### Backend

```bash
cd /e/TenzorXAI
source .venv/Scripts/activate

# Install dependencies
python -m pip install -r backend/requirements.txt

# Generate synthetic data (run once)
python backend/scripts/synthetic_generator.py

# Train model (run once, ~2 minutes)
python backend/scripts/train_model.py

# Start API
python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
```

```bash
# Quick smoke test
curl -X POST http://localhost:8000/valuate \
  -H "Content-Type: application/json" \
  -d '{
    "locality": "Kondapur",
    "property_type": "apartment",
    "subtype": "2BHK",
    "size_sqft": 1150,
    "age_years": 8
  }'
```

### Cloudflare Worker

```bash
cd worker

# Install local Worker dependencies
npm install

# Run locally for frontend narrative memos
npm run dev
```

The local Worker runs at:

```text
http://127.0.0.1:8787
```

For deployment:

```bash
cd worker

# Set OpenRouter API key as secret
npx wrangler secret put OPENROUTER_API_KEY

# Deploy
npm run deploy

# Test
curl -X POST https://collateral-narrative-worker.<your-subdomain>.workers.dev/narrate \
  -H "Content-Type: application/json" \
  -d '{ "valuation": { ...response from /valuate... } }'
```

### Environment Variables

```bash
# backend/.env
CF_ACCOUNT_ID=your_cloudflare_account_id
CF_API_TOKEN=your_cloudflare_api_token
# Optional live POI lookup for proximity score (schools/metro/market)
ENABLE_POI_LOOKUP=false
OVERPASS_URL=https://overpass-api.de/api/interpreter
POI_SEARCH_RADIUS_M=3000
POI_TIMEOUT_SEC=4.0
POI_CACHE_TTL_SEC=900

# worker — set via wrangler secret, not .env
OPENROUTER_API_KEY=your_openrouter_key
```

## Run on Your System (End-to-End)

Use this when you want the backend + frontend + worker running together on your machine.

### 1) Prerequisites

- Python 3.11+
- Node.js 18+
- npm

### 2) Start Backend API (FastAPI)

```powershell
cd E:\TenzorXAI

# Create and activate venv (first time only)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install backend dependencies
python -m pip install -r backend\requirements.txt

# Generate data and train model (first time only)
python backend\scripts\synthetic_generator.py
python backend\scripts\train_model.py

# Run API
python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
```

### 3) Start Frontend (Next.js)

Open a new terminal:

```powershell
cd E:\TenzorXAI\frontend
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:3000
```

### 4) Start Worker (Cloudflare Wrangler)

Open another new terminal:

```powershell
cd E:\TenzorXAI\worker
npm install
npm run dev
```

Worker URL:

```text
http://127.0.0.1:8787
```

### 5) Optional quick API test

```powershell
curl -X POST http://localhost:8000/valuate -H "Content-Type: application/json" -d "{\"locality\":\"Kondapur\",\"property_type\":\"apartment\",\"subtype\":\"2BHK\",\"size_sqft\":1150,\"age_years\":8}"
```

---

## Output Schema

```json
{
  "market_value_range":           [number, number],
  "distress_value_range":         [number, number],
  "distress_discount_breakdown":  {
    "asset_type_base":            number,
    "location_demand_modifier":   number,
    "legal_clarity_penalty":      number,
    "market_activity_modifier":   number,
    "buyer_pool_penalty":         number,
    "asset_uniqueness_penalty":   number,
    "total_discount":             number
  },
  "resale_potential_index":       number,
  "rpi_interpretation":           "highly_liquid" | "moderate_liquidity" | "illiquid_or_specialized",
  "rpi_components":               { ...7 components... },
  "estimated_time_to_sell_days":  [number, number],
  "confidence_score":             number,
  "confidence_breakdown":         { ...6-7 signals... },
  "comparable_transactions":      [{ locality, subtype, size_sqft, age_years, market_value, price_per_sqft }],
  "key_drivers":                  [{ driver, shap_impact, direction }],
  "risk_flags":                   [{ flag, severity, ltv_impact, detail }],
  "ltv_recommendation":           { standard, conservative, rationale },
  "image_analysis":               { ...optional, only when image provided... },
  "narrative":                    "string — credit committee paragraph from CF Worker"
}
```

---

## Design Decisions & Tradeoffs

**Why LightGBM over a neural network?**
SHAP support is first-class, training takes seconds not hours, and 3.25% MAPE on structured tabular data is genuinely hard to beat with a neural net. The explainability requirement from the PS rules out black boxes anyway.

**Why physics-based synthetic data over scraping?**
Scraping MagicBricks/99acres is legally grey, brittle at demo time, and produces noisy unlabeled data. Our synthetic generator is deterministic, reproducible, and can be explained to judges in two sentences. The ±4% Gaussian noise on top of the physics formula produces realistic variance without overfitting to any single market condition.

**Why Cloudflare Workers for the narrative, not the FastAPI backend?**
The narrative call is independent of the valuation pipeline. Putting it in a CF Worker means the frontend gets valuation data immediately and the narrative fades in ~2 seconds later. Better UX, and CF Workers are globally distributed with near-zero cold start.

**Why no database?**
For a hackathon, loading 100k Parquet records into memory at startup is faster, simpler, and removes an entire failure surface. The comparable engine runs a pandas filter query in ~5ms. No Redis, no Postgres, no migration files.

**Why ranges instead of point estimates?**
Because real estate valuation has genuine uncertainty and any system that pretends otherwise is lying to the lender. The PS explicitly requires ranges. Our ±8% band on the valuation model is conservative by design — it's better to be calibrated than precise.

---

## Supported Localities

| City | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| Delhi NCR | South Delhi, Gurgaon Golf Course | Dwarka, Rohini, Noida Sector 18 | Greater Noida West, Faridabad Old |
| Mumbai MMR | Bandra West, Powai | Andheri West, Thane West, Navi Mumbai Vashi | Mira Road |
| Bangalore | Koramangala, HSR Layout | Whitefield, Electronic City, Sarjapur Road | Yelahanka |
| Hyderabad | Jubilee Hills | Kondapur, Gachibowli, Kukatpally | LB Nagar, Miyapur |

---

<div align="center">

**Built for the collateral intelligence layer that Indian lending actually needs.**

*Every number traceable. Every output explainable. Every flag actionable.*

</div>
