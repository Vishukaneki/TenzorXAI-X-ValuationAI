"""
main.py
-------
FastAPI application. Orchestrates all engine modules.
Startup: loads data and model into memory once.
"""

import os
import json
import pickle
import pandas as pd
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from schemas import ValuationRequest, WhatIfRequest
from feature_engineer import engineer_features
from valuation_model import ValuationModel
from comparable_engine import ComparableEngine
from image_analyzer import analyze_image, image_to_risk_signals

# Engine module functions (all in engine_modules.py)
from engine_modules import (
    compute_rpi,
    compute_distress,
    compute_ttl,
    compute_confidence,
    detect_risk_flags,
    compute_ltv,
)

DATA_DIR  = os.path.join(os.path.dirname(__file__), "data")

# ── APP STATE ─────────────────────────────────────────────────────────────────
state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading data and model...")

    state["locality_meta"] = pd.read_csv(
        os.path.join(DATA_DIR, "locality_metadata.csv")
    ).set_index("locality").to_dict("index")

    state["synthetic_df"] = pd.read_parquet(
        os.path.join(DATA_DIR, "synthetic_100k.parquet")
    )

    with open(os.path.join(DATA_DIR, "locality_confidence.json")) as f:
        state["heatmap_data"] = json.load(f)

    state["valuation_model"]  = ValuationModel(os.path.join(DATA_DIR, "model.pkl"))
    state["comparable_engine"] = ComparableEngine(state["synthetic_df"])

    print("Ready.")
    yield
    state.clear()


app = FastAPI(title="Collateral Valuation Engine", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _get_locality(locality_name: str) -> dict:
    meta = state["locality_meta"]
    # Exact match first
    if locality_name in meta:
        return meta[locality_name]
    # Case-insensitive fallback
    for key, val in meta.items():
        if key.lower() == locality_name.lower():
            return val
    raise HTTPException(
        status_code=404,
        detail=f"Locality '{locality_name}' not found. "
               f"Available: {list(meta.keys())}"
    )


def _run_pipeline(req: ValuationRequest,
                  image_signals: dict = None) -> dict:
    locality_row = _get_locality(req.locality)

    # 1. Feature engineering
    eng = engineer_features(req, locality_row)
    model_features = eng["model_features"]
    meta           = eng["meta"]

    # 2. Valuation model
    val = state["valuation_model"].predict(model_features, req.size_sqft)

    # 3. Comparable engine
    comp_result = state["comparable_engine"].find_comps(
        locality_row, req.property_type, req.size_sqft
    )

    # 4. Liquidity scoring
    liq = compute_rpi(req, meta)
    rpi = liq["resale_potential_index"]

    # 5. Distress calculation
    dist = compute_distress(req, meta, val["market_value_range"], rpi)

    # 6. Time to liquidate
    ttl_result = compute_ttl(req, meta, rpi)

    # 7. Risk flags (structural + image)
    struct_flags = detect_risk_flags(req, meta, rpi, comp_result["density_score"])
    image_flags  = (image_signals or {}).get("image_risk_flags", [])
    all_flags    = struct_flags + image_flags
    # Re-sort combined flags by severity
    sev_order = {"high": 0, "medium": 1, "low": 2}
    all_flags.sort(key=lambda x: sev_order[x["severity"]])

    # 8. Confidence aggregation
    image_conf = (image_signals or {}).get("image_confidence")
    conf = compute_confidence(
        meta,
        comp_result["density_score"],
        meta["size_vs_norm"],
        ttl_result["ttl_range_width_ratio"],
        image_conf,
    )

    # 9. LTV recommendation
    ltv = compute_ltv(req, meta, rpi, all_flags, conf["confidence_score"])

    # 10. Assemble output
    output = {
        **val,
        **dist,
        **liq,
        **ttl_result,
        **conf,
        **ltv,
        "comparable_transactions": comp_result["comps"],
        "risk_flags":              all_flags,
    }

    if image_signals and "image_summary" in image_signals:
        output["image_analysis"] = image_signals["image_summary"]

    # Remove internal-only fields
    output.pop("ttl_range_width_ratio", None)
    output.pop("point_value", None)
    output.pop("price_per_sqft", None)

    return output


# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.post("/valuate")
async def valuate(req: ValuationRequest):
    return _run_pipeline(req)


@app.post("/valuate-with-image")
async def valuate_with_image(
    locality:        str = Form(...),
    property_type:   str = Form(...),
    subtype:         str = Form(...),
    size_sqft:       float = Form(...),
    age_years:       float = Form(...),
    floor_num:       Optional[int]   = Form(None),
    total_floors:    Optional[int]   = Form(None),
    has_lift:        Optional[bool]  = Form(None),
    occupancy_status: Optional[str] = Form(None),
    legal_status:    Optional[str]  = Form(None),
    rental_yield:    Optional[float] = Form(None),
    image:           Optional[UploadFile] = File(None),
):
    req = ValuationRequest(
        locality=locality, property_type=property_type, subtype=subtype,
        size_sqft=size_sqft, age_years=age_years, floor_num=floor_num,
        total_floors=total_floors, has_lift=has_lift,
        occupancy_status=occupancy_status, legal_status=legal_status,
        rental_yield=rental_yield,
    )

    image_signals = None
    if image:
        img_bytes = await image.read()
        analysis  = await analyze_image(img_bytes, claimed_type=property_type)
        image_signals = image_to_risk_signals(analysis)

    return _run_pipeline(req, image_signals)


@app.post("/whatif")
async def whatif(body: WhatIfRequest):
    """Perturb inputs and re-run full pipeline. Returns both base and perturbed."""
    base_result = _run_pipeline(body.base_request)

    # Apply perturbations
    perturbed_data = body.base_request.model_dump()
    perturbed_data.update(body.perturbations)
    perturbed_req  = ValuationRequest(**perturbed_data)
    perturbed_result = _run_pipeline(perturbed_req)

    # Compute deltas
    base_mid    = sum(base_result["market_value_range"]) / 2
    pert_mid    = sum(perturbed_result["market_value_range"]) / 2
    value_delta = round(pert_mid - base_mid, 0)
    value_delta_pct = round((value_delta / base_mid) * 100, 2) if base_mid else 0

    return {
        "base":             base_result,
        "perturbed":        perturbed_result,
        "perturbations":    body.perturbations,
        "value_delta":      value_delta,
        "value_delta_pct":  value_delta_pct,
        "rpi_delta":        round(
            perturbed_result["resale_potential_index"] -
            base_result["resale_potential_index"], 1
        ),
        "confidence_delta": round(
            perturbed_result["confidence_score"] -
            base_result["confidence_score"], 3
        ),
    }


@app.get("/heatmap")
async def heatmap():
    return state["heatmap_data"]

@app.get("/")
async def root():
    return {
        "name": "Collateral Valuation Engine",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/localities")
async def localities():
    return list(state["locality_meta"].keys())


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "localities_loaded": len(state.get("locality_meta", {})),
        "synthetic_rows":    len(state.get("synthetic_df", [])),
    }
