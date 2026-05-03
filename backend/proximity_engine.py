"""
proximity_engine.py
-------------------
Computes location proximity signals from latitude/longitude.

Modes:
1) Heuristic fallback (default, no external API)
2) Optional live POI lookup via Overpass API (ENABLE_POI_LOOKUP=true)
"""

import os
import time
import math
from typing import Optional, Dict, Tuple

import httpx
import numpy as np

from logger import get_logger

logger = get_logger(__name__)

DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_MIRRORS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

_CACHE: Dict[Tuple[float, float], Tuple[float, dict]] = {}


def compute_proximity_signals(
    latitude: Optional[float],
    longitude: Optional[float],
    locality_row: dict,
    use_live_lookup: bool = True,
) -> dict:
    """
    Returns normalized proximity signals and a 0-100 proximity score.
    Safe fallback behavior when external lookup is disabled/unavailable.
    """
    if latitude is None or longitude is None:
        return {"available": False}

    loc_lat = float(locality_row["lat"])
    loc_lon = float(locality_row["lon"])
    listing_density = float(locality_row.get("listing_density", 50.0))

    distance_to_locality_km = _haversine_km(latitude, longitude, loc_lat, loc_lon)
    geo_alignment = float(np.clip(1.0 - (distance_to_locality_km / 15.0), 0.0, 1.0))

    settings = _runtime_settings()
    poi_payload = None
    poi_endpoint = None
    fallback_reason = None
    if use_live_lookup and settings["enable_poi_lookup"]:
        poi_payload, poi_endpoint, fallback_reason = _fetch_poi_payload(
            latitude, longitude, settings
        )

    if poi_payload:
        signals = _signals_from_poi_payload(
            latitude, longitude, poi_payload, listing_density, distance_to_locality_km
        )
        signals["source"] = "overpass_api"
    else:
        signals = _signals_from_fallback(listing_density, geo_alignment, distance_to_locality_km)
        signals["source"] = "heuristic"
        if not fallback_reason and not use_live_lookup:
            fallback_reason = "Skipped live POI lookup (fast mode)"
        elif not fallback_reason and settings["enable_poi_lookup"]:
            fallback_reason = "No POI data returned"
        elif not fallback_reason:
            fallback_reason = "ENABLE_POI_LOOKUP=false"

    score = _proximity_score(signals)
    market_activity_mult = float(np.clip(0.92 + (score / 100.0) * 0.18, 0.85, 1.12))
    market_multiplier_mult = float(np.clip(0.94 + (score / 100.0) * 0.16, 0.88, 1.10))
    infra_score_mult = float(np.clip(0.90 + (score / 100.0) * 0.20, 0.86, 1.14))
    rpi_adjust = round((score - 50.0) / 10.0, 2)  # roughly -5 to +5
    ttl_mult = float(np.clip(1.10 - (score / 100.0) * 0.20, 0.90, 1.10))

    return {
        "available": True,
        "source": signals["source"],
        "overpass_endpoint": poi_endpoint,
        "fallback_reason": None if signals["source"] == "overpass_api" else fallback_reason,
        "proximity_score": score,
        "school_distance_km": signals["school_distance_km"],
        "metro_distance_km": signals["metro_distance_km"],
        "market_distance_km": signals["market_distance_km"],
        "busy_score": signals["busy_score"],
        "distance_to_locality_km": round(distance_to_locality_km, 3),
        "market_activity_mult": market_activity_mult,
        "market_multiplier_mult": market_multiplier_mult,
        "infra_score_mult": infra_score_mult,
        "rpi_adjust": rpi_adjust,
        "ttl_mult": ttl_mult,
        "score_components": {
            "school_access": signals["school_access_score"],
            "metro_access": signals["metro_access_score"],
            "market_access": signals["market_access_score"],
            "busyness": signals["busy_score"],
        },
    }


def _signals_from_fallback(
    listing_density: float,
    geo_alignment: float,
    distance_to_locality_km: float,
) -> dict:
    # Heuristic estimates when live POI lookup is disabled or unavailable.
    school_distance_km = round(max(0.3, 2.6 - 1.6 * geo_alignment), 2)
    metro_distance_km = round(max(0.5, 3.2 - 2.0 * geo_alignment), 2)
    market_distance_km = round(max(0.2, 2.2 - 1.5 * geo_alignment), 2)
    busy_score = float(
        np.clip(0.55 * (listing_density / 100.0) + 0.45 * geo_alignment, 0.0, 1.0)
    )

    return {
        "school_distance_km": school_distance_km,
        "metro_distance_km": metro_distance_km,
        "market_distance_km": market_distance_km,
        "school_access_score": _distance_score(school_distance_km),
        "metro_access_score": _distance_score(metro_distance_km),
        "market_access_score": _distance_score(market_distance_km),
        "busy_score": busy_score,
        "locality_alignment": geo_alignment,
        "distance_to_locality_km": distance_to_locality_km,
    }


def _signals_from_poi_payload(
    latitude: float,
    longitude: float,
    payload: dict,
    listing_density: float,
    distance_to_locality_km: float,
) -> dict:
    school_distances = []
    metro_distances = []
    market_distances = []
    roads_1km = 0
    poi_count_1km = 0

    for element in payload.get("elements", []):
        tags = element.get("tags", {})
        lat, lon = _element_lat_lon(element)
        if lat is None or lon is None:
            continue

        distance_km = _haversine_km(latitude, longitude, lat, lon)
        if distance_km <= 1.0:
            poi_count_1km += 1

        if tags.get("amenity") == "school":
            school_distances.append(distance_km)
        elif tags.get("railway") in {"station", "subway_entrance"} or tags.get("station") in {
            "subway",
            "metro",
            "light_rail",
        }:
            metro_distances.append(distance_km)
        elif tags.get("amenity") == "marketplace" or tags.get("shop") == "mall":
            market_distances.append(distance_km)

        if element.get("type") == "way" and tags.get("highway") in {
            "primary",
            "secondary",
            "tertiary",
            "residential",
        }:
            roads_1km += 1

    school_distance_km = round(min(school_distances), 2) if school_distances else None
    metro_distance_km = round(min(metro_distances), 2) if metro_distances else None
    market_distance_km = round(min(market_distances), 2) if market_distances else None

    busy_score = float(
        np.clip(
            0.45 * (listing_density / 100.0)
            + 0.30 * min(poi_count_1km / 12.0, 1.0)
            + 0.25 * min(roads_1km / 80.0, 1.0),
            0.0,
            1.0,
        )
    )

    return {
        "school_distance_km": school_distance_km,
        "metro_distance_km": metro_distance_km,
        "market_distance_km": market_distance_km,
        "school_access_score": _distance_score(school_distance_km),
        "metro_access_score": _distance_score(metro_distance_km),
        "market_access_score": _distance_score(market_distance_km),
        "busy_score": busy_score,
        "distance_to_locality_km": distance_to_locality_km,
    }


def _fetch_poi_payload(latitude: float, longitude: float, settings: dict) -> Tuple[Optional[dict], Optional[str], Optional[str]]:
    key = (round(latitude, 4), round(longitude, 4))
    now = time.time()
    cached = _CACHE.get(key)
    if cached and now - cached[0] < settings["cache_ttl_sec"]:
        return cached[1], "cache", None

    query = f"""
[out:json][timeout:20];
(
  nwr(around:{settings["poi_radius_m"]},{latitude},{longitude})["amenity"="school"];
  nwr(around:{settings["poi_radius_m"]},{latitude},{longitude})["railway"="station"];
  nwr(around:{settings["poi_radius_m"]},{latitude},{longitude})["railway"="subway_entrance"];
  nwr(around:{settings["poi_radius_m"]},{latitude},{longitude})["station"~"subway|metro|light_rail"];
  nwr(around:{settings["poi_radius_m"]},{latitude},{longitude})["amenity"="marketplace"];
  nwr(around:{settings["poi_radius_m"]},{latitude},{longitude})["shop"="mall"];
  way(around:1000,{latitude},{longitude})["highway"~"primary|secondary|tertiary|residential"];
);
out center;
"""
    headers = {
        "User-Agent": "TenzorXAI/1.0 (proximity-engine)",
        "Accept": "application/json",
    }

    endpoints = [settings["overpass_url"]] + OVERPASS_MIRRORS
    unique_endpoints = []
    for ep in endpoints:
        if ep and ep not in unique_endpoints:
            unique_endpoints.append(ep)

    last_error = None
    with httpx.Client(timeout=settings["poi_timeout_sec"], headers=headers) as client:
        for endpoint in unique_endpoints:
            try:
                response = client.post(endpoint, content=query, headers={"Content-Type": "text/plain"})
                if response.status_code == 406:
                    response = client.post(endpoint, data={"data": query})
                response.raise_for_status()
                data = response.json()
                _CACHE[key] = (now, data)
                return data, endpoint, None
            except Exception as exc:
                last_error = f"{endpoint}: {exc}"
                logger.warning("POI lookup failed on %s (%s)", endpoint, exc)

    logger.warning("POI lookup failed; using heuristic fallback (%s)", last_error)
    return None, None, last_error


def _runtime_settings() -> dict:
    return {
        "enable_poi_lookup": os.getenv("ENABLE_POI_LOOKUP", "false").lower() == "true",
        "overpass_url": os.getenv("OVERPASS_URL", DEFAULT_OVERPASS_URL),
        "poi_radius_m": int(os.getenv("POI_SEARCH_RADIUS_M", "3000")),
        "poi_timeout_sec": float(os.getenv("POI_TIMEOUT_SEC", "4.0")),
        "cache_ttl_sec": int(os.getenv("POI_CACHE_TTL_SEC", "900")),
    }


def _proximity_score(signals: dict) -> float:
    score = 100.0 * (
        0.30 * signals["school_access_score"]
        + 0.30 * signals["metro_access_score"]
        + 0.25 * signals["market_access_score"]
        + 0.15 * signals["busy_score"]
    )
    return round(float(np.clip(score, 0.0, 100.0)), 1)


def _distance_score(distance_km: Optional[float]) -> float:
    if distance_km is None:
        return 0.45
    if distance_km <= 0.5:
        return 1.0
    if distance_km <= 1.0:
        return 0.85
    if distance_km <= 2.0:
        return 0.65
    if distance_km <= 3.0:
        return 0.45
    return 0.25


def _element_lat_lon(element: dict) -> Tuple[Optional[float], Optional[float]]:
    if "lat" in element and "lon" in element:
        return element["lat"], element["lon"]
    center = element.get("center")
    if center and "lat" in center and "lon" in center:
        return center["lat"], center["lon"]
    return None, None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
