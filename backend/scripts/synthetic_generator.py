"""
synthetic_generator.py
----------------------
Generates 100k physics-based synthetic Indian property records.
Every number is anchored to real circle rates and domain rules.
Run once: python scripts/synthetic_generator.py
Outputs:  backend/data/synthetic_100k.parquet
          backend/data/locality_metadata.csv
          backend/data/locality_confidence.json
"""

import numpy as np
import pandas as pd
import json
import os
from dataclasses import dataclass, field
from typing import List, Tuple

np.random.seed(42)

# ── OUTPUT PATHS ─────────────────────────────────────────────────────────────
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUT_DIR, exist_ok=True)

# ── LOCALITY MASTER ───────────────────────────────────────────────────────────
# circle_rate = ₹/sqft (government floor)
# tier        = 1 (prime) / 2 (mid) / 3 (outer)
# multiplier  = market / circle rate ratio (how hot the market is)
# norm_size   = typical apartment size in sqft for this locality
# listing_density = synthetic listing count proxy (higher = more liquid)
# lat/lon     = approximate centroid for heatmap

LOCALITIES = [
    # ── DELHI NCR ──────────────────────────────────────────────────────────
    {"locality": "South Delhi",        "city": "Delhi",     "tier": 1, "circle_rate": 8500,  "multiplier_mu": 2.2, "multiplier_sigma": 0.15, "norm_size": 1400, "listing_density": 85,  "lat": 28.549,  "lon": 77.206},
    {"locality": "Dwarka",             "city": "Delhi",     "tier": 2, "circle_rate": 5500,  "multiplier_mu": 1.6, "multiplier_sigma": 0.12, "norm_size": 1100, "listing_density": 70,  "lat": 28.592,  "lon": 77.046},
    {"locality": "Rohini",             "city": "Delhi",     "tier": 2, "circle_rate": 4800,  "multiplier_mu": 1.5, "multiplier_sigma": 0.10, "norm_size": 1050, "listing_density": 65,  "lat": 28.732,  "lon": 77.064},
    {"locality": "Noida Sector 18",    "city": "Delhi",     "tier": 2, "circle_rate": 5200,  "multiplier_mu": 1.7, "multiplier_sigma": 0.13, "norm_size": 1150, "listing_density": 72,  "lat": 28.570,  "lon": 77.321},
    {"locality": "Greater Noida West", "city": "Delhi",     "tier": 3, "circle_rate": 3200,  "multiplier_mu": 1.2, "multiplier_sigma": 0.10, "norm_size": 950,  "listing_density": 45,  "lat": 28.609,  "lon": 77.427},
    {"locality": "Gurgaon Golf Course","city": "Delhi",     "tier": 1, "circle_rate": 9000,  "multiplier_mu": 2.4, "multiplier_sigma": 0.18, "norm_size": 1600, "listing_density": 88,  "lat": 28.459,  "lon": 77.102},
    {"locality": "Faridabad Old",      "city": "Delhi",     "tier": 3, "circle_rate": 3000,  "multiplier_mu": 1.1, "multiplier_sigma": 0.08, "norm_size": 900,  "listing_density": 38,  "lat": 28.408,  "lon": 77.317},

    # ── MUMBAI MMR ──────────────────────────────────────────────────────────
    {"locality": "Bandra West",        "city": "Mumbai",    "tier": 1, "circle_rate": 18000, "multiplier_mu": 2.5, "multiplier_sigma": 0.20, "norm_size": 950,  "listing_density": 90,  "lat": 19.059,  "lon": 72.826},
    {"locality": "Andheri West",       "city": "Mumbai",    "tier": 2, "circle_rate": 11000, "multiplier_mu": 1.8, "multiplier_sigma": 0.14, "norm_size": 800,  "listing_density": 78,  "lat": 19.136,  "lon": 72.826},
    {"locality": "Thane West",         "city": "Mumbai",    "tier": 2, "circle_rate": 8500,  "multiplier_mu": 1.6, "multiplier_sigma": 0.12, "norm_size": 900,  "listing_density": 68,  "lat": 19.218,  "lon": 72.978},
    {"locality": "Navi Mumbai Vashi",  "city": "Mumbai",    "tier": 2, "circle_rate": 7800,  "multiplier_mu": 1.5, "multiplier_sigma": 0.11, "norm_size": 950,  "listing_density": 65,  "lat": 19.075,  "lon": 73.009},
    {"locality": "Mira Road",          "city": "Mumbai",    "tier": 3, "circle_rate": 5500,  "multiplier_mu": 1.3, "multiplier_sigma": 0.09, "norm_size": 700,  "listing_density": 48,  "lat": 19.401,  "lon": 72.869},
    {"locality": "Powai",              "city": "Mumbai",    "tier": 1, "circle_rate": 14000, "multiplier_mu": 2.1, "multiplier_sigma": 0.16, "norm_size": 1000, "listing_density": 82,  "lat": 19.118,  "lon": 72.906},

    # ── BANGALORE ───────────────────────────────────────────────────────────
    {"locality": "Koramangala",        "city": "Bangalore", "tier": 1, "circle_rate": 7500,  "multiplier_mu": 2.3, "multiplier_sigma": 0.17, "norm_size": 1200, "listing_density": 87,  "lat": 12.935,  "lon": 77.624},
    {"locality": "Whitefield",         "city": "Bangalore", "tier": 2, "circle_rate": 5800,  "multiplier_mu": 1.7, "multiplier_sigma": 0.13, "norm_size": 1300, "listing_density": 74,  "lat": 12.969,  "lon": 77.750},
    {"locality": "HSR Layout",         "city": "Bangalore", "tier": 1, "circle_rate": 7000,  "multiplier_mu": 2.1, "multiplier_sigma": 0.15, "norm_size": 1150, "listing_density": 83,  "lat": 12.912,  "lon": 77.640},
    {"locality": "Electronic City",    "city": "Bangalore", "tier": 2, "circle_rate": 4500,  "multiplier_mu": 1.5, "multiplier_sigma": 0.11, "norm_size": 1100, "listing_density": 62,  "lat": 12.839,  "lon": 77.677},
    {"locality": "Sarjapur Road",      "city": "Bangalore", "tier": 2, "circle_rate": 5200,  "multiplier_mu": 1.6, "multiplier_sigma": 0.12, "norm_size": 1200, "listing_density": 66,  "lat": 12.908,  "lon": 77.686},
    {"locality": "Yelahanka",          "city": "Bangalore", "tier": 3, "circle_rate": 3500,  "multiplier_mu": 1.2, "multiplier_sigma": 0.09, "norm_size": 1000, "listing_density": 42,  "lat": 13.101,  "lon": 77.596},

    # ── HYDERABAD ───────────────────────────────────────────────────────────
    {"locality": "Jubilee Hills",      "city": "Hyderabad", "tier": 1, "circle_rate": 8000,  "multiplier_mu": 2.2, "multiplier_sigma": 0.16, "norm_size": 1500, "listing_density": 84,  "lat": 17.432,  "lon": 78.407},
    {"locality": "Kondapur",           "city": "Hyderabad", "tier": 2, "circle_rate": 5500,  "multiplier_mu": 1.7, "multiplier_sigma": 0.13, "norm_size": 1200, "listing_density": 73,  "lat": 17.460,  "lon": 78.352},
    {"locality": "Gachibowli",         "city": "Hyderabad", "tier": 2, "circle_rate": 6000,  "multiplier_mu": 1.8, "multiplier_sigma": 0.14, "norm_size": 1250, "listing_density": 76,  "lat": 17.440,  "lon": 78.348},
    {"locality": "Kukatpally",         "city": "Hyderabad", "tier": 2, "circle_rate": 4800,  "multiplier_mu": 1.5, "multiplier_sigma": 0.11, "norm_size": 1100, "listing_density": 64,  "lat": 17.494,  "lon": 78.395},
    {"locality": "LB Nagar",           "city": "Hyderabad", "tier": 3, "circle_rate": 3200,  "multiplier_mu": 1.2, "multiplier_sigma": 0.09, "norm_size": 950,  "listing_density": 40,  "lat": 17.348,  "lon": 78.552},
    {"locality": "Miyapur",            "city": "Hyderabad", "tier": 3, "circle_rate": 3800,  "multiplier_mu": 1.3, "multiplier_sigma": 0.10, "norm_size": 1000, "listing_density": 47,  "lat": 17.496,  "lon": 78.352},
]

# ── PROPERTY TYPES ────────────────────────────────────────────────────────────
PROPERTY_TYPES = {
    "apartment": {
        "subtypes": ["1BHK", "2BHK", "3BHK", "4BHK"],
        "subtype_weights": [0.15, 0.45, 0.30, 0.10],
        "subtype_size_ranges": {           # (min, max) sqft carpet
            "1BHK": (400,  650),
            "2BHK": (750,  1200),
            "3BHK": (1100, 1800),
            "4BHK": (1600, 2800),
        },
        "subtype_premium": {               # relative to 2BHK baseline
            "1BHK": 0.95,
            "2BHK": 1.00,
            "3BHK": 1.04,
            "4BHK": 1.06,
        },
        "base_liquidity": 72,
        "weight": 0.60,
    },
    "villa": {
        "subtypes": ["independent_house", "row_house", "villa"],
        "subtype_weights": [0.40, 0.35, 0.25],
        "subtype_size_ranges": {
            "independent_house": (1200, 3000),
            "row_house":         (1000, 2200),
            "villa":             (2000, 5000),
        },
        "subtype_premium": {
            "independent_house": 1.05,
            "row_house":         1.02,
            "villa":             1.15,
        },
        "base_liquidity": 55,
        "weight": 0.20,
    },
    "plot": {
        "subtypes": ["residential_plot", "corner_plot"],
        "subtype_weights": [0.70, 0.30],
        "subtype_size_ranges": {
            "residential_plot": (200, 1000),   # sqyd
            "corner_plot":      (200, 800),
        },
        "subtype_premium": {
            "residential_plot": 1.00,
            "corner_plot":      1.10,
        },
        "base_liquidity": 48,
        "weight": 0.12,
    },
    "commercial": {
        "subtypes": ["shop", "office"],
        "subtype_weights": [0.55, 0.45],
        "subtype_size_ranges": {
            "shop":   (200, 800),
            "office": (400, 2000),
        },
        "subtype_premium": {
            "shop":   1.00,
            "office": 1.08,
        },
        "base_liquidity": 42,
        "weight": 0.08,
    },
}

FLOOR_ADJUSTMENTS = {
    "ground":  -0.08,
    "low":     -0.02,   # 1–3
    "mid":      0.00,   # 4–8
    "high":    +0.04,   # 9–15
    "top":     +0.05,   # top floor
}

# ── PHYSICS ENGINE ────────────────────────────────────────────────────────────

def age_depreciation(age: float) -> float:
    """1% per year, floored at 0.60 for very old properties."""
    return max(0.60, 1.0 - 0.01 * age)


def floor_adjustment(floor: int, total_floors: int) -> Tuple[str, float]:
    if floor == 0:
        return "ground", FLOOR_ADJUSTMENTS["ground"]
    elif floor <= 3:
        return "low", FLOOR_ADJUSTMENTS["low"]
    elif floor == total_floors:
        return "top", FLOOR_ADJUSTMENTS["top"]
    elif floor <= 8:
        return "mid", FLOOR_ADJUSTMENTS["mid"]
    else:
        return "high", FLOOR_ADJUSTMENTS["high"]


def infrastructure_score(locality: dict) -> float:
    """
    Tier-based proxy for metro distance, highway access, hospitals, schools.
    Returns 0–1.  Real system would use lat/lon + POI distance.
    """
    base = {1: 0.85, 2: 0.60, 3: 0.35}[locality["tier"]]
    noise = np.random.normal(0, 0.05)
    return float(np.clip(base + noise, 0.10, 1.0))


def market_activity_score(locality: dict) -> float:
    """Normalise listing_density to 0–1."""
    return float(np.clip(locality["listing_density"] / 100.0, 0.1, 1.0))


def generate_record(locality: dict, prop_type: str, prop_config: dict) -> dict:
    """Generate one synthetic property record with all physics applied."""

    # ── SUBTYPE ──────────────────────────────────────────────────────────────
    subtype = np.random.choice(
        prop_config["subtypes"],
        p=prop_config["subtype_weights"]
    )
    size_range = prop_config["subtype_size_ranges"][subtype]
    size_sqft  = float(np.random.uniform(*size_range))

    # ── AGE ──────────────────────────────────────────────────────────────────
    age = float(np.random.choice(
        np.arange(0, 41),
        p=_age_distribution()
    ))
    age_category = "new" if age < 5 else ("mid_age" if age <= 15 else "old")

    # ── FLOOR ────────────────────────────────────────────────────────────────
    total_floors = int(np.random.choice([4, 7, 12, 20, 30],
                                        p=[0.25, 0.30, 0.25, 0.15, 0.05]))
    floor_num    = int(np.random.randint(0, total_floors + 1))
    floor_label, floor_adj = floor_adjustment(floor_num, total_floors)
    has_lift = total_floors >= 4

    # ── BASE PRICE PHYSICS ───────────────────────────────────────────────────
    market_multiplier = float(np.random.normal(
        locality["multiplier_mu"], locality["multiplier_sigma"]
    ))
    market_multiplier = max(1.0, market_multiplier)

    infra_score       = infrastructure_score(locality)
    market_act        = market_activity_score(locality)
    subtype_premium   = prop_config["subtype_premium"][subtype]
    depr              = age_depreciation(age)

    price_per_sqft = (
        locality["circle_rate"]
        * market_multiplier
        * subtype_premium
        * depr
        * (1 + floor_adj)
        * (1 + 0.05 * infra_score)          # infrastructure premium
        * np.random.normal(1.0, 0.04)        # residual noise
    )
    price_per_sqft = max(locality["circle_rate"] * 0.95, price_per_sqft)

    market_value = price_per_sqft * size_sqft

    # ── LIQUIDITY & DISTRESS ─────────────────────────────────────────────────
    rpi = _compute_rpi(locality, prop_type, subtype, market_act, age)
    liquidity_discount = _compute_liquidity_discount(
        prop_type, locality, rpi, market_act
    )
    distress_value = market_value * (1 - liquidity_discount)

    # ── SIZE ANOMALY ─────────────────────────────────────────────────────────
    size_vs_norm = size_sqft / locality["norm_size"]

    # ── CONFIDENCE ───────────────────────────────────────────────────────────
    confidence = _compute_confidence(locality, size_vs_norm, market_act)

    # ── TTL ──────────────────────────────────────────────────────────────────
    ttl_low, ttl_high = _compute_ttl(rpi, prop_type, market_act)

    return {
        # identifiers
        "locality":            locality["locality"],
        "city":                locality["city"],
        "tier":                locality["tier"],
        "lat":                 locality["lat"] + np.random.normal(0, 0.005),
        "lon":                 locality["lon"] + np.random.normal(0, 0.005),

        # property
        "property_type":       prop_type,
        "subtype":             subtype,
        "size_sqft":           round(size_sqft, 1),
        "age_years":           age,
        "age_category":        age_category,
        "floor_num":           floor_num,
        "total_floors":        total_floors,
        "floor_label":         floor_label,
        "has_lift":            has_lift,

        # derived features (used by LightGBM)
        "circle_rate":         locality["circle_rate"],
        "market_multiplier":   round(market_multiplier, 3),
        "infra_score":         round(infra_score, 3),
        "market_activity":     round(market_act, 3),
        "subtype_premium":     subtype_premium,
        "age_depreciation":    round(depr, 3),
        "floor_adjustment":    round(floor_adj, 3),
        "size_vs_norm":        round(size_vs_norm, 3),

        # targets
        "price_per_sqft":      round(price_per_sqft, 2),
        "market_value":        round(market_value, 0),
        "distress_value":      round(distress_value, 0),
        "liquidity_discount":  round(liquidity_discount, 3),
        "resale_potential_index": round(rpi, 1),
        "ttl_low_days":        ttl_low,
        "ttl_high_days":       ttl_high,
        "confidence":          round(confidence, 3),
        "listing_density":     locality["listing_density"],
    }


def _age_distribution() -> np.ndarray:
    """Realistic age distribution — more mid-age stock than new or very old."""
    ages = np.arange(0, 41)
    weights = np.where(ages < 5,  3.0,
              np.where(ages <= 15, 5.0,
              np.where(ages <= 25, 3.0, 1.5)))
    return weights / weights.sum()


def _compute_rpi(locality, prop_type, subtype, market_act, age) -> float:
    base       = PROPERTY_TYPES[prop_type]["base_liquidity"]
    tier_boost = {1: 15, 2: 5, 3: -10}[locality["tier"]]
    act_boost  = (market_act - 0.5) * 20      # ±10 around neutral
    age_penalty = max(0, (age - 15) * 0.5)    # penalty for old buildings
    # 2BHK is the most liquid apartment config
    config_boost = 5 if subtype == "2BHK" else (2 if subtype == "3BHK" else -3)
    rpi = base + tier_boost + act_boost + config_boost - age_penalty
    return float(np.clip(rpi + np.random.normal(0, 3), 0, 100))


def _compute_liquidity_discount(prop_type, locality, rpi, market_act) -> float:
    base_discount = {
        "apartment":  0.12,
        "villa":      0.20,
        "plot":       0.25,
        "commercial": 0.28,
    }[prop_type]
    location_mod  = -0.04 if locality["tier"] == 1 else (0 if locality["tier"] == 2 else 0.05)
    activity_mod  = (0.5 - market_act) * 0.06   # low activity = higher discount
    rpi_mod       = (50 - rpi) * 0.001           # high RPI reduces discount
    total = base_discount + location_mod + activity_mod + rpi_mod
    return float(np.clip(total + np.random.normal(0, 0.01), 0.05, 0.45))


def _compute_confidence(locality, size_vs_norm, market_act) -> float:
    comp_density  = np.clip(locality["listing_density"] / 100.0, 0.1, 1.0)
    consistency   = 1.0 - min(abs(size_vs_norm - 1.0), 0.5)
    freshness     = {1: 0.90, 2: 0.75, 3: 0.60}[locality["tier"]]
    confidence    = 0.35 * comp_density + 0.30 * consistency + 0.20 * freshness + 0.15 * market_act
    return float(np.clip(confidence + np.random.normal(0, 0.02), 0.20, 0.95))


def _compute_ttl(rpi, prop_type, market_act) -> Tuple[int, int]:
    base = {
        "apartment":  45,
        "villa":      75,
        "plot":       90,
        "commercial": 120,
    }[prop_type]
    demand_mult   = 2.0 - market_act           # low activity = longer TTL
    lower = int(base * demand_mult * (1 - rpi / 200))
    upper = int(lower * (1.5 + (1 - market_act) * 0.8))
    lower = max(15, lower)
    upper = max(lower + 15, upper)
    return lower, upper


# ── MAIN GENERATOR ────────────────────────────────────────────────────────────

def generate_dataset(n: int = 100_000) -> pd.DataFrame:
    print(f"Generating {n:,} synthetic property records...")
    records = []

    locality_weights = np.array([1.0] * len(LOCALITIES))
    locality_weights /= locality_weights.sum()

    prop_types  = list(PROPERTY_TYPES.keys())
    prop_weights = np.array([PROPERTY_TYPES[p]["weight"] for p in prop_types])
    prop_weights /= prop_weights.sum()

    for i in range(n):
        loc       = LOCALITIES[np.random.choice(len(LOCALITIES), p=locality_weights)]
        prop_type = np.random.choice(prop_types, p=prop_weights)
        record    = generate_record(loc, prop_type, PROPERTY_TYPES[prop_type])
        records.append(record)

        if (i + 1) % 10_000 == 0:
            print(f"  {i + 1:,} / {n:,} records generated")

    df = pd.DataFrame(records)
    print(f"Dataset shape: {df.shape}")
    return df


def save_locality_metadata():
    """Save locality metadata for heatmap and circle rate lookups."""
    df = pd.DataFrame(LOCALITIES)
    df.to_csv(os.path.join(OUT_DIR, "locality_metadata.csv"), index=False)
    print(f"Saved locality_metadata.csv ({len(df)} localities)")


def save_circle_rates():
    """Save circle rates keyed by locality for fast lookup."""
    rows = [{"locality": l["locality"], "city": l["city"],
             "circle_rate": l["circle_rate"], "tier": l["tier"]} for l in LOCALITIES]
    pd.DataFrame(rows).to_csv(os.path.join(OUT_DIR, "circle_rates.csv"), index=False)
    print("Saved circle_rates.csv")


def save_confidence_heatmap(df: pd.DataFrame):
    """
    Precompute per-locality confidence stats for the Leaflet heatmap.
    Output: list of {locality, city, lat, lon, avg_confidence, listing_density, tier}
    """
    heatmap = []
    for loc in LOCALITIES:
        subset = df[df["locality"] == loc["locality"]]
        heatmap.append({
            "locality":        loc["locality"],
            "city":            loc["city"],
            "lat":             loc["lat"],
            "lon":             loc["lon"],
            "tier":            loc["tier"],
            "avg_confidence":  round(float(subset["confidence"].mean()), 3),
            "listing_density": loc["listing_density"],
            "record_count":    len(subset),
            "avg_market_value": round(float(subset["market_value"].mean()), 0),
        })

    with open(os.path.join(OUT_DIR, "locality_confidence.json"), "w") as f:
        json.dump(heatmap, f, indent=2)
    print(f"Saved locality_confidence.json ({len(heatmap)} localities)")


if __name__ == "__main__":
    save_locality_metadata()
    save_circle_rates()

    df = generate_dataset(100_000)

    out_path = os.path.join(OUT_DIR, "synthetic_100k.parquet")
    df.to_parquet(out_path, index=False)
    print(f"\nSaved synthetic_100k.parquet → {out_path}")

    save_confidence_heatmap(df)

    # Quick sanity check
    print("\n── Sanity Check ─────────────────────────────────────────")
    print(df[["city", "property_type", "market_value", "resale_potential_index",
              "confidence", "ttl_low_days"]].groupby(["city", "property_type"]).mean().round(1))
    print("\nDone. Run train_model.py next.")
