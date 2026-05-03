"""
feature_engineer.py
-------------------
Transforms raw API input into the feature vector fed to LightGBM.
Every derivation is explicit and documented — full traceability.
"""

import pandas as pd
import numpy as np
from typing import Optional
from schemas import ValuationRequest
from logger import get_logger

logger = get_logger(__name__)

# ── STATIC LOOKUPS ────────────────────────────────────────────────────────────
# Loaded once at startup by main.py and passed in.
# Kept separate from this module to allow easy mocking in tests.

SUBTYPE_PREMIUMS = {
    # Apartments
    "1BHK": 0.95, "2BHK": 1.00, "3BHK": 1.04, "4BHK": 1.06,
    # Villas
    "independent_house": 1.05, "row_house": 1.02, "villa": 1.15,
    # Plots
    "residential_plot": 1.00, "corner_plot": 1.10,
    # Commercial
    "shop": 1.00, "office": 1.08,
}

PROPERTY_TYPE_BASE_LIQUIDITY = {
    "apartment": 72, "villa": 55, "plot": 48, "commercial": 42,
}


def engineer_features(req: ValuationRequest, locality_row: dict) -> dict:
    """
    Returns a flat dict with:
      - model_features: dict fed to LightGBM (matches FEATURES in train_model.py)
      - meta:           dict of derived signals used by downstream scorers
    """

    # ── AGE DEPRECIATION ─────────────────────────────────────────────────────
    age           = req.age_years
    age_depr      = max(0.60, 1.0 - 0.01 * age)
    age_category  = "new" if age < 5 else ("mid_age" if age <= 15 else "old")

    # ── FLOOR ADJUSTMENT ─────────────────────────────────────────────────────
    floor_adj, floor_label = _floor_adjustment(req.floor_num, req.total_floors)

    # ── SUBTYPE PREMIUM ───────────────────────────────────────────────────────
    subtype_premium = SUBTYPE_PREMIUMS.get(req.subtype, 1.00)
    if req.subtype not in SUBTYPE_PREMIUMS:
        logger.warning(
            "Unknown subtype '%s' — defaulting premium to 1.00", req.subtype
        )

    # ── INFRASTRUCTURE SCORE (tier proxy) ────────────────────────────────────
    tier        = int(locality_row["tier"])
    infra_score = {1: 0.85, 2: 0.60, 3: 0.35}[tier]

    # ── MARKET ACTIVITY ───────────────────────────────────────────────────────
    listing_density  = float(locality_row["listing_density"])
    market_activity  = float(np.clip(listing_density / 100.0, 0.1, 1.0))

    # ── SIZE VS LOCALITY NORM ─────────────────────────────────────────────────
    norm_size    = float(locality_row["norm_size"])
    size_vs_norm = req.size_sqft / norm_size

    # ── MARKET MULTIPLIER (tier-based point estimate) ─────────────────────────
    market_multiplier = float(locality_row["multiplier_mu"])

    # ── HAS LIFT ──────────────────────────────────────────────────────────────
    has_lift = req.has_lift if req.has_lift is not None else (
        req.total_floors is not None and req.total_floors >= 4
    )

    # ── INPUT COMPLETENESS ────────────────────────────────────────────────────
    optional_fields = [req.floor_num, req.total_floors, req.has_lift,
                       req.occupancy_status, req.legal_status, req.rental_yield]
    filled          = sum(1 for f in optional_fields if f is not None)
    completeness    = 0.5 + 0.5 * (filled / len(optional_fields))  # 0.5–1.0

    model_features = {
        "circle_rate":       float(locality_row["circle_rate"]),
        "tier":              tier,
        "market_multiplier": market_multiplier,
        "infra_score":       infra_score,
        "market_activity":   market_activity,
        "subtype_premium":   subtype_premium,
        "age_depreciation":  age_depr,
        "floor_adjustment":  floor_adj,
        "size_sqft":         req.size_sqft,
        "size_vs_norm":      size_vs_norm,
        "age_years":         float(age),
        "has_lift":          int(has_lift),
        "listing_density":   listing_density,
    }

    meta = {
        "age_category":       age_category,
        "age_depreciation":   age_depr,
        "floor_label":        floor_label,
        "floor_adjustment":   floor_adj,
        "subtype_premium":    subtype_premium,
        "infra_score":        infra_score,
        "market_activity":    market_activity,
        "market_multiplier":  market_multiplier,
        "size_vs_norm":       size_vs_norm,
        "completeness":       completeness,
        "tier":               tier,
        "circle_rate":        float(locality_row["circle_rate"]),
        "listing_density":    listing_density,
        "norm_size":          norm_size,
        "base_liquidity":     PROPERTY_TYPE_BASE_LIQUIDITY.get(req.property_type, 55),
        "has_lift":           has_lift,
    }

    if completeness < 0.65:
        logger.warning(
            "Low input completeness=%.2f for locality=%s — confidence may be reduced",
            completeness, req.locality,
        )

    logger.debug(
        "engineer_features done  completeness=%.2f  tier=%d  market_activity=%.2f  "
        "size_vs_norm=%.2f  floor=%s  subtype_premium=%.2f",
        completeness, tier, market_activity, size_vs_norm, floor_label, subtype_premium,
    )

    return {"model_features": model_features, "meta": meta}


def _floor_adjustment(floor_num: Optional[int], total_floors: Optional[int]):
    if floor_num is None:
        return 0.00, "unknown"
    if floor_num == 0:
        return -0.08, "ground"
    if total_floors is not None and floor_num == total_floors:
        return +0.05, "top"
    if floor_num <= 3:
        return -0.02, "low"
    if floor_num <= 8:
        return  0.00, "mid"
    return +0.04, "high"
