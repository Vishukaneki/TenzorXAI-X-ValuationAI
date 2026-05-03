"""
main.py
-------
FastAPI application. Orchestrates all engine modules.
Startup: loads data and model into memory once.
"""

import os
import json
import time
import pickle
import pandas as pd
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from logger import get_logger
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

logger   = get_logger(__name__)
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# ── APP STATE ─────────────────────────────────────────────────────────────────
state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== TenzorXAI backend starting up ===")

    try:
        logger.info("Loading locality metadata...")
        state["locality_meta"] = pd.read_csv(
            os.path.join(DATA_DIR, "locality_metadata.csv")
        ).set_index("locality").to_dict("index")
        logger.info("Loaded %d localities", len(state["locality_meta"]))

        logger.info("Loading synthetic dataset...")
        state["synthetic_df"] = pd.read_parquet(
            os.path.join(DATA_DIR, "synthetic_100k.parquet")
        )
        logger.info("Loaded synthetic dataset: %d rows", len(state["synthetic_df"]))

        logger.info("Loading confidence heatmap...")
        with open(os.path.join(DATA_DIR, "locality_confidence.json")) as f:
            state["heatmap_data"] = json.load(f)
        logger.info("Heatmap loaded: %d entries", len(state["heatmap_data"]))

        logger.info("Loading valuation model...")
        state["valuation_model"] = ValuationModel(os.path.join(DATA_DIR, "model.pkl"))
        logger.info("Valuation model loaded")

        logger.info("Initialising comparable engine...")
        state["comparable_engine"] = ComparableEngine(state["synthetic_df"])
        logger.info("Comparable engine ready")

        logger.info("=== Backend ready to serve requests ===")

    except Exception:
        logger.critical("Startup failed — backend will not serve requests", exc_info=True)
        raise

    yield

    logger.info("=== Backend shutting down ===")
    state.clear()


app = FastAPI(title="Collateral Valuation Engine", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REQUEST LOGGING MIDDLEWARE ─────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    logger.info("-> %s %s  client=%s", request.method, request.url.path,
                request.client.host if request.client else "unknown")
    try:
        response = await call_next(request)
        elapsed  = (time.perf_counter() - start) * 1000
        logger.info("<- %s %s  status=%d  %.1fms",
                    request.method, request.url.path, response.status_code, elapsed)
        return response
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000
        logger.error("UNHANDLED EXCEPTION  %s %s  %.1fms",
                     request.method, request.url.path, elapsed, exc_info=True)
        raise


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _get_locality(locality_name: str) -> dict:
    meta = state["locality_meta"]
    if locality_name in meta:
        logger.debug("Locality match (exact): %s", locality_name)
        return meta[locality_name]
    for key, val in meta.items():
        if key.lower() == locality_name.lower():
            logger.warning(
                "Locality matched case-insensitively: '%s' -> '%s'", locality_name, key
            )
            return val
    logger.error("Locality not found: '%s'  available=%s", locality_name, list(meta.keys()))
    raise HTTPException(
        status_code=404,
        detail=f"Locality '{locality_name}' not found. "
               f"Available: {list(meta.keys())}"
    )


def _run_pipeline(req: ValuationRequest, image_signals: dict = None) -> dict:
    pipeline_start = time.perf_counter()
    logger.info(
        "Pipeline start  locality=%s  type=%s  subtype=%s  size=%.0f  age=%d",
        req.locality, req.property_type, req.subtype, req.size_sqft, req.age_years,
    )

    # 1. Feature engineering
    logger.debug("Step 1: Feature engineering")
    t = time.perf_counter()
    locality_row   = _get_locality(req.locality)
    eng            = engineer_features(req, locality_row)
    model_features = eng["model_features"]
    meta           = eng["meta"]
    logger.debug(
        "Features done  %.1fms  completeness=%.2f  size_vs_norm=%.2f  tier=%d",
        (time.perf_counter() - t) * 1000, meta["completeness"],
        meta["size_vs_norm"], meta["tier"],
    )

    # 2. Valuation model
    logger.debug("Step 2: Valuation model prediction")
    t   = time.perf_counter()
    val = state["valuation_model"].predict(model_features, req.size_sqft)
    logger.info(
        "Predicted  ppsf=%.0f  range=[%.0f, %.0f]  %.1fms",
        val["price_per_sqft"],
        val["market_value_range"][0],
        val["market_value_range"][1],
        (time.perf_counter() - t) * 1000,
    )

    # 3. Comparable engine
    logger.debug("Step 3: Comparable transactions")
    t           = time.perf_counter()
    comp_result = state["comparable_engine"].find_comps(
        locality_row, req.property_type, req.size_sqft
    )
    logger.debug(
        "Comps  count=%d  density=%.3f  %.1fms",
        len(comp_result["comps"]), comp_result["density_score"],
        (time.perf_counter() - t) * 1000,
    )

    # 4. Liquidity / RPI
    logger.debug("Step 4: RPI")
    t   = time.perf_counter()
    liq = compute_rpi(req, meta)
    rpi = liq["resale_potential_index"]
    logger.info("RPI=%.1f  (%s)  %.1fms", rpi, liq["rpi_interpretation"],
                (time.perf_counter() - t) * 1000)

    # 5. Distress
    logger.debug("Step 5: Distress value")
    t    = time.perf_counter()
    dist = compute_distress(req, meta, val["market_value_range"], rpi)
    logger.debug(
        "Distress range=[%.0f, %.0f]  discount=%.1f%%  %.1fms",
        dist["distress_value_range"][0], dist["distress_value_range"][1],
        dist["distress_discount_breakdown"].get("total_discount", 0) * 100,
        (time.perf_counter() - t) * 1000,
    )

    # 6. TTL
    logger.debug("Step 6: TTL")
    t          = time.perf_counter()
    ttl_result = compute_ttl(req, meta, rpi)
    logger.debug(
        "TTL=[%d, %d] days  width_ratio=%.3f  %.1fms",
        ttl_result["estimated_time_to_sell_days"][0],
        ttl_result["estimated_time_to_sell_days"][1],
        ttl_result["ttl_range_width_ratio"],
        (time.perf_counter() - t) * 1000,
    )

    # 7. Risk flags
    logger.debug("Step 7: Risk flags")
    t            = time.perf_counter()
    struct_flags = detect_risk_flags(req, meta, rpi, comp_result["density_score"])
    image_flags  = (image_signals or {}).get("image_risk_flags", [])
    all_flags    = struct_flags + image_flags
    sev_order    = {"high": 0, "medium": 1, "low": 2}
    all_flags.sort(key=lambda x: sev_order[x["severity"]])
    high_count   = sum(1 for f in all_flags if f["severity"] == "high")
    logger.info("Risk flags  total=%d  high=%d  %.1fms",
                len(all_flags), high_count, (time.perf_counter() - t) * 1000)
    for f in all_flags:
        if f["severity"] == "high":
            logger.warning("HIGH risk flag: %s -- %s", f["flag"], f["detail"])

    # 8. Confidence
    logger.debug("Step 8: Confidence aggregation")
    t          = time.perf_counter()
    image_conf = (image_signals or {}).get("image_confidence")
    conf       = compute_confidence(
        meta, comp_result["density_score"],
        meta["size_vs_norm"], ttl_result["ttl_range_width_ratio"], image_conf,
    )
    logger.info("Confidence=%.3f  image_used=%s  %.1fms",
                conf["confidence_score"], image_conf is not None,
                (time.perf_counter() - t) * 1000)

    # 9. LTV
    logger.debug("Step 9: LTV recommendation")
    t   = time.perf_counter()
    ltv = compute_ltv(req, meta, rpi, all_flags, conf["confidence_score"])
    logger.info(
        "LTV  standard=%.0f%%  conservative=%.0f%%  %.1fms",
        ltv["ltv_recommendation"]["standard"] * 100,
        ltv["ltv_recommendation"]["conservative"] * 100,
        (time.perf_counter() - t) * 1000,
    )

    # 10. Assemble output
    output = {
        **val, **dist, **liq, **ttl_result, **conf, **ltv,
        "comparable_transactions": comp_result["comps"],
        "risk_flags":              all_flags,
    }
    if image_signals and "image_summary" in image_signals:
        output["image_analysis"] = image_signals["image_summary"]

    output.pop("ttl_range_width_ratio", None)
    output.pop("point_value", None)
    output.pop("price_per_sqft", None)

    logger.info("Pipeline complete  total=%.1fms", (time.perf_counter() - pipeline_start) * 1000)
    return output


# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.post("/valuate")
async def valuate(req: ValuationRequest):
    try:
        return _run_pipeline(req)
    except HTTPException:
        raise
    except Exception:
        logger.error("/valuate failed  req=%s", req.model_dump(), exc_info=True)
        raise


@app.post("/valuate-with-image")
async def valuate_with_image(
    locality:         str = Form(...),
    property_type:    str = Form(...),
    subtype:          str = Form(...),
    size_sqft:        float = Form(...),
    age_years:        float = Form(...),
    floor_num:        Optional[int]   = Form(None),
    total_floors:     Optional[int]   = Form(None),
    has_lift:         Optional[bool]  = Form(None),
    occupancy_status: Optional[str]   = Form(None),
    legal_status:     Optional[str]   = Form(None),
    rental_yield:     Optional[float] = Form(None),
    image:            Optional[UploadFile] = File(None),
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
        logger.info("Image upload  filename=%s  content_type=%s",
                    image.filename, image.content_type)
        try:
            img_bytes     = await image.read()
            logger.debug("Image read  bytes=%d", len(img_bytes))
            analysis      = await analyze_image(img_bytes, claimed_type=property_type)
            image_signals = image_to_risk_signals(analysis)
            logger.info("Image analysis done  confidence=%s",
                        image_signals.get("image_confidence"))
        except Exception:
            logger.error("Image analysis failed — continuing without image signals",
                         exc_info=True)

    try:
        return _run_pipeline(req, image_signals)
    except HTTPException:
        raise
    except Exception:
        logger.error("/valuate-with-image failed  req=%s", req.model_dump(), exc_info=True)
        raise


@app.post("/whatif")
async def whatif(body: WhatIfRequest):
    """Perturb inputs and re-run full pipeline. Returns both base and perturbed."""
    logger.info("What-if request  perturbations=%s", body.perturbations)
    try:
        base_result = _run_pipeline(body.base_request)

        perturbed_data   = body.base_request.model_dump()
        perturbed_data.update(body.perturbations)
        perturbed_req    = ValuationRequest(**perturbed_data)
        perturbed_result = _run_pipeline(perturbed_req)

        base_mid        = sum(base_result["market_value_range"]) / 2
        pert_mid        = sum(perturbed_result["market_value_range"]) / 2
        value_delta     = round(pert_mid - base_mid, 0)
        value_delta_pct = round((value_delta / base_mid) * 100, 2) if base_mid else 0

        logger.info(
            "What-if delta  value=%.0f (%.2f%%)  rpi_delta=%.1f",
            value_delta, value_delta_pct,
            perturbed_result["resale_potential_index"] - base_result["resale_potential_index"],
        )

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
    except HTTPException:
        raise
    except Exception:
        logger.error("/whatif failed", exc_info=True)
        raise


@app.get("/heatmap")
async def heatmap():
    return state["heatmap_data"]


@app.get("/")
async def root():
    return {
        "name":   "Collateral Valuation Engine",
        "status": "running",
        "docs":   "/docs",
        "health": "/health",
    }


@app.get("/localities")
async def localities():
    return list(state["locality_meta"].keys())


@app.get("/health")
async def health():
    return {
        "status":            "ok",
        "localities_loaded": len(state.get("locality_meta", {})),
        "synthetic_rows":    len(state.get("synthetic_df", [])),
    }
