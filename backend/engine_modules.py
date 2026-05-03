"""
distress_calculator.py
----------------------
Computes distress sale value with full per-variable discount decomposition.
"""

import numpy as np
from schemas import ValuationRequest


def compute_rpi(req: ValuationRequest, meta: dict) -> dict:
    """Compute Resale Potential Index from location, liquidity, and asset signals."""
    components = {}

    components["asset_type_base"] = meta.get("base_liquidity", {
        "apartment": 72,
        "villa": 55,
        "plot": 48,
        "commercial": 42,
    }.get(req.property_type, 55))

    components["location_demand"] = {1: 15, 2: 5, 3: -10}[meta["tier"]]
    components["market_activity_boost"] = (meta["market_activity"] - 0.5) * 20
    components["geo_proximity_boost"] = meta.get("rpi_proximity_adjust", 0.0)

    if req.subtype in {"2BHK", "3BHK"}:
        config_score = 5
    elif req.subtype in {"1BHK", "shop", "independent_house"}:
        config_score = 2
    else:
        config_score = -5
    components["config_standardness"] = config_score

    components["age_factor"] = -max(0, (req.age_years - 15) * 0.5)

    no_lift_apartment = req.property_type == "apartment" and not meta.get("has_lift", False)
    components["lift_penalty"] = -5 if no_lift_apartment else 0

    legal = req.legal_status or "clear"
    components["legal_clarity"] = 0 if legal == "clear" else -10

    rpi = float(np.clip(sum(components.values()), 0, 100))

    if rpi >= 80:
        interpretation = "highly_liquid"
    elif rpi >= 50:
        interpretation = "moderate_liquidity"
    else:
        interpretation = "illiquid_or_specialized"

    return {
        "resale_potential_index": round(rpi, 1),
        "rpi_interpretation": interpretation,
        "rpi_components": {k: round(float(v), 3) for k, v in components.items()},
    }


def compute_distress(req: ValuationRequest, meta: dict,
                     market_value_range: list, rpi: float) -> dict:
    breakdown = {}

    # Base discount by asset type
    breakdown["asset_type_base"] = {
        "apartment": 0.12, "villa": 0.20,
        "plot": 0.25, "commercial": 0.28,
    }.get(req.property_type, 0.18)

    # Location demand modifier (prime locations recover value faster)
    breakdown["location_demand_modifier"] = {1: -0.04, 2: 0.00, 3: +0.05}[meta["tier"]]

    # Legal clarity
    legal = req.legal_status or "clear"
    breakdown["legal_clarity_penalty"] = 0.00 if legal == "clear" else 0.07

    # Market activity (low activity = harder to sell at full price under distress)
    breakdown["market_activity_modifier"] = round((0.5 - meta["market_activity"]) * 0.06, 3)

    # Buyer pool (thin buyer pools → larger discount)
    breakdown["buyer_pool_penalty"] = 0.00 if rpi >= 65 else (0.03 if rpi >= 45 else 0.06)

    # Asset uniqueness (non-standard configs attract fewer buyers)
    nonstd = req.subtype not in {"2BHK", "3BHK", "1BHK", "shop"}
    breakdown["asset_uniqueness_penalty"] = 0.04 if nonstd else 0.00

    total_discount = float(np.clip(sum(breakdown.values()), 0.05, 0.45))
    breakdown["total_discount"] = round(total_discount, 3)

    distress_low  = round(market_value_range[0] * (1 - total_discount), 0)
    distress_high = round(market_value_range[1] * (1 - total_discount), 0)

    return {
        "distress_value_range":       [distress_low, distress_high],
        "distress_discount_breakdown": {k: round(v, 3) for k, v in breakdown.items()},
    }


# ─────────────────────────────────────────────────────────────────────────────

"""
ttl_calculator.py
-----------------
Estimates time-to-liquidate range in days.
Lower bound and upper bound use separate multiplier paths.
Range width feeds back to confidence aggregator as a penalty.
"""


def compute_ttl(req, meta: dict, rpi: float) -> dict:
    base_days = {
        "apartment": 45, "villa": 75, "plot": 90, "commercial": 120,
    }.get(req.property_type, 60)

    market_act   = meta["market_activity"]
    demand_mult  = 2.0 - market_act          # low activity → longer TTL

    proximity_ttl_mult = meta.get("ttl_proximity_mult", 1.0)
    lower = int(base_days * demand_mult * (1 - rpi / 200) * proximity_ttl_mult)
    lower = max(15, lower)

    # Upper bound adds uniqueness, legal, and stress factors
    legal          = req.legal_status or "clear"
    legal_mult     = 1.30 if legal != "clear" else 1.00
    nonstd         = req.subtype not in {"2BHK", "3BHK", "1BHK", "shop"}
    uniqueness_mult = 1.20 if nonstd else 1.00
    stress_mult    = 1.0 + (1 - market_act) * 0.5

    upper = int(lower * legal_mult * uniqueness_mult * stress_mult)
    upper = max(lower + 15, upper)

    # Range width ratio — wide ranges indicate high uncertainty
    range_width_ratio = (upper - lower) / max(lower, 1)

    return {
        "estimated_time_to_sell_days": [lower, upper],
        "ttl_range_width_ratio":       round(range_width_ratio, 3),
    }


# ─────────────────────────────────────────────────────────────────────────────

"""
confidence_aggregator.py
------------------------
Combines 6 signals into a single confidence score 0–1.
Per-signal breakdown returned for UI display.
"""


def compute_confidence(meta: dict, comp_density: float,
                       size_vs_norm: float, ttl_range_ratio: float,
                       image_confidence: float = None) -> dict:
    signals = {}

    # 1. Input completeness (0.5 base if minimal, 1.0 if fully filled)
    signals["data_completeness"] = round(meta["completeness"], 3)

    # 2. Comparable density (how many similar props in dataset)
    signals["comparable_density"] = round(comp_density, 3)

    # 3. Circle rate freshness (tier-1 cities updated more often)
    signals["circle_rate_freshness"] = {1: 0.90, 2: 0.75, 3: 0.60}[meta["tier"]]

    # 4. Input consistency (size vs locality norm — large deviations hurt confidence)
    consistency = 1.0 - min(abs(size_vs_norm - 1.0), 0.5) * 1.2
    signals["input_consistency"] = round(float(np.clip(consistency, 0, 1)), 3)

    # 5. Legal clarity
    legal = 1.00   # default — legal_status not flagged
    signals["legal_clarity"] = legal

    # 6. TTL range width penalty (wide range = uncertain market conditions)
    ttl_penalty = max(0, 1.0 - ttl_range_ratio * 0.4)
    signals["ttl_range_penalty"] = round(float(np.clip(ttl_penalty, 0.2, 1.0)), 3)

    if meta.get("proximity_score") is not None:
        prox_conf = float(np.clip(meta["proximity_score"] / 100.0, 0.3, 1.0))
        signals["geo_proximity_quality"] = round(prox_conf, 3)

    # 7. Image quality (optional — only present if image was analyzed)
    weights = {
        "data_completeness":      0.25,
        "comparable_density":     0.20,
        "circle_rate_freshness":  0.15,
        "input_consistency":      0.20,
        "legal_clarity":          0.10,
        "ttl_range_penalty":      0.10,
    }
    if "geo_proximity_quality" in signals:
        for key in ("data_completeness", "comparable_density", "input_consistency"):
            weights[key] -= 0.01
        weights["geo_proximity_quality"] = 0.03

    if image_confidence is not None:
        signals["image_quality"] = round(image_confidence, 3)
        for key in ("data_completeness", "comparable_density", "input_consistency"):
            weights[key] -= 0.01
        weights["image_quality"] = 0.03

    score = sum(signals[k] * weights[k] for k in signals)
    score = float(np.clip(score, 0.20, 0.95))

    return {
        "confidence_score":     round(score, 3),
        "confidence_breakdown": signals,
    }


# ─────────────────────────────────────────────────────────────────────────────

"""
risk_flags.py
-------------
Detects risk conditions and returns structured flags with severity + LTV impact.
"""

from typing import List


SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def detect_risk_flags(req, meta: dict, rpi: float,
                      comp_density: float) -> List[dict]:
    flags = []

    # 1. Size anomaly
    svn = meta["size_vs_norm"]
    if svn > 1.40:
        flags.append({
            "flag":       "size_significantly_above_locality_norm",
            "severity":   "high",
            "ltv_impact": -7,
            "detail":     f"Property is {round((svn-1)*100)}% larger than locality median",
        })
    elif svn > 1.20:
        flags.append({
            "flag":       "size_above_locality_norm",
            "severity":   "medium",
            "ltv_impact": -3,
            "detail":     f"Property is {round((svn-1)*100)}% larger than locality median",
        })
    elif svn < 0.60:
        flags.append({
            "flag":       "size_below_locality_norm",
            "severity":   "medium",
            "ltv_impact": -2,
            "detail":     "Unusually small for locality — limited buyer pool",
        })

    # 2. Circle rate vs market variance
    cr         = meta["circle_rate"]
    mult       = meta["market_multiplier"]
    cr_gap_pct = (mult - 1.0) * 100
    if cr_gap_pct > 120:
        flags.append({
            "flag":       "high_market_to_circle_rate_variance",
            "severity":   "medium",
            "ltv_impact": -3,
            "detail":     f"Market price is {round(cr_gap_pct)}% above circle rate — elevated speculation risk",
        })

    # 3. Low comparable density
    if comp_density < 0.30:
        flags.append({
            "flag":       "low_comparable_density",
            "severity":   "high",
            "ltv_impact": -5,
            "detail":     "Few comparable transactions found — valuation uncertainty is higher",
        })
    elif comp_density < 0.55:
        flags.append({
            "flag":       "moderate_comparable_density",
            "severity":   "low",
            "ltv_impact": -2,
            "detail":     "Limited comparables available in this segment",
        })

    # 4. Low market activity
    if meta["market_activity"] < 0.35:
        flags.append({
            "flag":       "low_market_activity",
            "severity":   "high",
            "ltv_impact": -7,
            "detail":     "Low listing density — slow resale market",
        })
    elif meta["market_activity"] < 0.55:
        flags.append({
            "flag":       "moderate_market_activity",
            "severity":   "medium",
            "ltv_impact": -3,
            "detail":     "Below-average market activity in this locality",
        })

    # 5. Non-standard configuration
    nonstd = req.subtype not in {"2BHK", "3BHK", "1BHK", "shop", "independent_house"}
    if nonstd and req.property_type in {"villa", "commercial"}:
        flags.append({
            "flag":       "non_standard_configuration",
            "severity":   "medium",
            "ltv_impact": -4,
            "detail":     "Niche property type — thinner buyer pool expected",
        })

    # 6. Old building
    if req.age_years > 30:
        flags.append({
            "flag":       "aging_structure",
            "severity":   "medium",
            "ltv_impact": -4,
            "detail":     f"Building age {req.age_years} years — potential structural concerns",
        })

    # 7. Legal status
    legal = req.legal_status or "clear"
    if legal != "clear":
        flags.append({
            "flag":       "legal_status_unclear",
            "severity":   "high",
            "ltv_impact": -10,
            "detail":     "Non-clear legal status significantly increases liquidation risk",
        })

    # 8. Geo-locality deviation (if exact coordinates were provided)
    geo_distance_km = meta.get("geo_distance_km")
    if geo_distance_km is not None:
        if meta.get("proximity_score") is not None and meta["proximity_score"] < 25:
            flags.append({
                "flag":       "very_low_location_proximity_score",
                "severity":   "high",
                "ltv_impact": -6,
                "detail":     f"Location proximity score is only {meta['proximity_score']:.1f}/100",
            })
        elif meta.get("proximity_score") is not None and meta["proximity_score"] < 40:
            flags.append({
                "flag":       "low_location_proximity_score",
                "severity":   "medium",
                "ltv_impact": -3,
                "detail":     f"Location proximity score is {meta['proximity_score']:.1f}/100",
            })

        if geo_distance_km > 10:
            flags.append({
                "flag":       "geo_far_from_locality_centroid",
                "severity":   "medium",
                "ltv_impact": -4,
                "detail":     f"Provided coordinates are {geo_distance_km:.1f} km from declared locality centroid",
            })
        elif geo_distance_km > 5:
            flags.append({
                "flag":       "geo_off_locality_core",
                "severity":   "low",
                "ltv_impact": -2,
                "detail":     f"Provided coordinates are {geo_distance_km:.1f} km from declared locality centroid",
            })

    # Sort by severity
    flags.sort(key=lambda x: SEVERITY_ORDER[x["severity"]])
    return flags


# ─────────────────────────────────────────────────────────────────────────────

"""
ltv_recommender.py
------------------
Produces conservative and standard LTV recommendations with rationale.
LTV is the single most important output for an NBFC lender.
"""


def compute_ltv(req, meta: dict, rpi: float,
                risk_flags: List[dict], confidence: float) -> dict:
    tier = meta["tier"]

    # Base LTV by property type (RBI/NBFC norms as anchor)
    base_ltv = {
        "apartment": 0.75,
        "villa":     0.70,
        "plot":      0.65,
        "commercial": 0.60,
    }.get(req.property_type, 0.65)

    # Tier adjustment
    tier_adj = {1: +0.02, 2: 0.00, 3: -0.05}[tier]

    # RPI adjustment (highly liquid assets can support higher LTV)
    rpi_adj = (rpi - 50) * 0.001   # ±0.05 for RPI 0–100

    # Risk flag haircuts
    total_flag_haircut = sum(abs(f["ltv_impact"]) * 0.01 for f in risk_flags)

    # Confidence penalty
    conf_penalty = (0.75 - confidence) * 0.05 if confidence < 0.75 else 0.00

    standard    = float(np.clip(base_ltv + tier_adj + rpi_adj - conf_penalty, 0.40, 0.80))
    conservative = float(np.clip(standard - total_flag_haircut - 0.05, 0.35, 0.75))

    # Build rationale string
    rationale_parts = []
    rationale_parts.append(
        f"Tier-{tier} location with {rpi:.0f}/100 resale potential "
        f"supports {standard:.0%} standard LTV."
    )
    if risk_flags:
        high_flags = [f for f in risk_flags if f["severity"] == "high"]
        if high_flags:
            rationale_parts.append(
                f"{len(high_flags)} high-severity risk flag(s) "
                f"trigger a {total_flag_haircut:.0%} haircut on conservative limit."
            )
    if confidence < 0.65:
        rationale_parts.append(
            "Low confidence score warrants additional manual verification before disbursement."
        )

    return {
        "ltv_recommendation": {
            "standard":     round(standard, 2),
            "conservative": round(conservative, 2),
            "rationale":    " ".join(rationale_parts),
        }
    }


# keep numpy available across all functions in this file
import numpy as np
