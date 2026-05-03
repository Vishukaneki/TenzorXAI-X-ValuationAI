"""
image_analyzer.py
-----------------
Sends property image to Cloudflare Workers AI (LLaVA) or uses mock analysis.
Returns structured condition assessment that feeds into
confidence_aggregator and risk_flags.

Environment Variables:
- CF_ACCOUNT_ID: Cloudflare account ID (required for real analysis)
- CF_API_TOKEN: Cloudflare API token (required for real analysis)
- MOCK_IMAGE_ANALYSIS: Set to "true" to use mock analysis instead of Cloudflare
"""

import os
import httpx
import json
import re
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID", "")
CF_API_TOKEN  = os.getenv("CF_API_TOKEN", "")
LLAVA_MODEL   = "@cf/llava-hf/llava-1.5-7b-hf"

# Fallback to a mock implementation if Cloudflare credentials are not set
MOCK_IMAGE_ANALYSIS = os.getenv("MOCK_IMAGE_ANALYSIS", "false").lower() == "true"

SYSTEM_PROMPT = """You are a property condition assessor for an Indian NBFC lender.
Analyze the property image and return ONLY a JSON object with no extra text.
Be conservative and objective. If unsure about any field, use null."""

USER_PROMPT = """Analyze this property image and return exactly this JSON:
{
  "construction_quality": "good" | "average" | "poor",
  "visible_condition": "well_maintained" | "average" | "deteriorating",
  "estimated_floors": <integer or null>,
  "visible_issues": [<list of strings, max 4, e.g. "water_stains", "paint_peeling", "cracks">],
  "property_type_matches_claimed": true | false | null,
  "surrounding_area_quality": "good" | "average" | "poor",
  "confidence_in_analysis": <float 0.0 to 1.0>
}
Return only the JSON. No explanation."""


async def analyze_image(image_bytes: bytes,
                        claimed_type: str = "apartment") -> Optional[dict]:
    """
    Sends image to LLaVA via CF Workers AI.
    Returns structured dict or None if analysis fails.
    """
    # Check if we should use mock analysis
    if MOCK_IMAGE_ANALYSIS:
        return _mock_image_analysis(claimed_type)
    
    # Skip silently if not configured
    if not CF_ACCOUNT_ID or not CF_API_TOKEN:
        print("[image_analyzer] Cloudflare credentials not configured. Skipping image analysis.")
        return None

    image_array = list(image_bytes)

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{CF_ACCOUNT_ID}/ai/run/{LLAVA_MODEL}"
    )

    payload = {
        "prompt": f"{SYSTEM_PROMPT}\n\n{USER_PROMPT.replace('apartment', claimed_type)}",
        "image": image_array
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {CF_API_TOKEN}"},
                json=payload,
            )
            resp.raise_for_status()
            
            # Print the full response for debugging
            response_data = resp.json()
            print(f"[image_analyzer] Full response: {response_data}")
            
            raw_text = _extract_raw_text(response_data)
            if not raw_text:
                print(f"[image_analyzer] Unexpected response structure: {response_data}")
                return None

            parsed = _parse_llava_response(raw_text, claimed_type=claimed_type)
            if parsed:
                return parsed

            # Fallback: if model returned narrative text instead of strict JSON,
            # derive conservative signals from keywords.
            fallback = _extract_signals_from_text(raw_text, claimed_type=claimed_type)
            if fallback:
                print(f"[image_analyzer] Using text-derived fallback: {fallback}")
                return fallback

            print(f"[image_analyzer] Could not parse model output: {raw_text}")
            return None
                
    except httpx.HTTPStatusError as e:
        print(f"[image_analyzer] HTTP error {e.response.status_code}: {e.response.text}")
        return None
    except Exception as e:
        print(f"[image_analyzer] LLaVA call failed: {e}")
        return None


def _mock_image_analysis(claimed_type: str) -> dict:
    """
    Mock implementation for testing without Cloudflare.
    Returns a sample analysis result.
    """
    print("[image_analyzer] Using mock image analysis")
    return {
        "construction_quality": "average",
        "visible_condition": "well_maintained",
        "estimated_floors": 5,
        "visible_issues": [],
        "property_type_matches_claimed": True,
        "surrounding_area_quality": "good",
        "confidence_in_analysis": 0.8,
    }


def _extract_raw_text(response_data: dict) -> Optional[str]:
    result = response_data.get("result")

    if isinstance(result, str) and result.strip():
        return result.strip()

    if isinstance(result, list):
        chunks = []
        for item in result:
            if isinstance(item, str) and item.strip():
                chunks.append(item.strip())
            elif isinstance(item, dict):
                for key in ("response", "description", "output_text", "text"):
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        chunks.append(value.strip())
        joined = "\n".join(chunks).strip()
        if joined:
            return joined

    if isinstance(result, dict):
        for key in ("response", "description", "output_text", "text"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, list):
                joined = "\n".join(v for v in value if isinstance(v, str)).strip()
                if joined:
                    return joined

    for key in ("response", "description", "output_text", "text"):
        value = response_data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _normalize_analysis(data: dict, claimed_type: str) -> dict:
    def pick(*keys, default=None):
        for key in keys:
            if key in data and data.get(key) is not None:
                return data.get(key)
        return default

    def norm_quality(value, default="average"):
        text = str(value or "").strip().lower()
        if text in {"good", "excellent", "high", "well_built"}:
            return "good"
        if text in {"poor", "bad", "low", "weak", "substandard"}:
            return "poor"
        return default

    def norm_condition(value, default="average"):
        text = str(value or "").strip().lower()
        if text in {"well_maintained", "well maintained", "maintained", "good"}:
            return "well_maintained"
        if text in {"deteriorating", "deteriorated", "poor", "damaged"}:
            return "deteriorating"
        return default

    def norm_bool(value):
        if isinstance(value, bool):
            return value
        text = str(value or "").strip().lower()
        if text in {"true", "yes", "match", "matches", "matching"}:
            return True
        if text in {"false", "no", "mismatch", "does_not_match", "not_matching"}:
            return False
        return None

    def norm_issues(value):
        if isinstance(value, str):
            raw_items = [part.strip() for part in re.split(r"[,;|/]", value) if part.strip()]
        elif isinstance(value, list):
            raw_items = [str(item).strip() for item in value if str(item).strip()]
        else:
            raw_items = []

        normalized = []
        for item in raw_items:
            key = item.lower().replace(" ", "_").replace("-", "_")
            if key in {"crack", "cracks", "wall_cracks"}:
                normalized.append("cracks")
            elif key in {"structural_damage", "structure_damage", "structural_cracks"}:
                normalized.append("structural_damage")
            elif key in {"water_stain", "water_stains"}:
                normalized.append("water_stains")
            elif key in {"paint_peeling", "peeling_paint", "paint_damage"}:
                normalized.append("paint_peeling")
            elif key in {"dampness", "seepage", "leakage"}:
                normalized.append("dampness")
            else:
                normalized.append(key)

        deduped = []
        seen = set()
        for issue in normalized:
            if issue not in seen:
                deduped.append(issue)
                seen.add(issue)
        return deduped[:4]

    def norm_confidence(value, default=0.5):
        try:
            conf = float(value)
            if conf > 1:
                conf = conf / 100.0 if conf <= 100 else 1.0
            return max(0.0, min(conf, 1.0))
        except (TypeError, ValueError):
            return default

    floors = pick("estimated_floors", "floors", "num_floors")
    if floors is not None:
        try:
            floors = int(floors)
        except (TypeError, ValueError):
            floors = None

    return {
        "construction_quality":          norm_quality(
            pick("construction_quality", "construction", "build_quality"), "average"
        ),
        "visible_condition":             norm_condition(
            pick("visible_condition", "condition", "property_condition"), "average"
        ),
        "estimated_floors":              floors,
        "visible_issues":                norm_issues(
            pick("visible_issues", "issues", "issues_detected", default=[])
        ),
        "property_type_matches_claimed": norm_bool(
            pick("property_type_matches_claimed", "type_matches_claim", "property_type_match")
        ),
        "surrounding_area_quality":      norm_quality(
            pick("surrounding_area_quality", "area_quality", "locality_quality"), "average"
        ),
        "confidence_in_analysis":        norm_confidence(
            pick("confidence_in_analysis", "confidence", "analysis_confidence"), 0.5
        ),
    }


def _parse_llava_response(text: str, claimed_type: str = "apartment") -> Optional[dict]:
    def _sanitize_json_text(value: str) -> str:
        # Some model responses include Markdown-escaped underscores (\_) inside JSON keys.
        # That sequence is not a valid JSON escape, so normalize it before parsing.
        return value.replace("\\_", "_")

    try:
        # Handle different text formats
        clean = text.strip()
        
        # Strip any markdown fences
        clean = re.sub(r"```json|```", "", clean).strip()
        clean = _sanitize_json_text(clean)
        
        # Try to parse as JSON
        if clean.startswith('{') and clean.endswith('}'):
            data = json.loads(clean)
        else:
            # Sometimes the response is just plain text - try to extract JSON from it
            # Look for JSON-like patterns in the text
            json_match = re.search(r'\{.*\}', clean, re.DOTALL)
            if json_match:
                data = json.loads(_sanitize_json_text(json_match.group()))
            else:
                print(f"[image_analyzer] Could not find JSON in response: {clean}")
                return None

        result = _normalize_analysis(data, claimed_type=claimed_type)
        
        print(f"[image_analyzer] Parsed result: {result}")
        return result
        
    except json.JSONDecodeError as e:
        print(f"[image_analyzer] JSON decode error: {e}")
        print(f"[image_analyzer] Raw text was: {text}")
        return None
    except Exception as e:
        print(f"[image_analyzer] Parse error: {e}")
        return None


def _extract_signals_from_text(text: str, claimed_type: str = "apartment") -> Optional[dict]:
    lower = text.lower()

    construction_quality = "average"
    if any(token in lower for token in ("poor construction", "substandard", "weak structure", "bad quality")):
        construction_quality = "poor"
    elif any(token in lower for token in ("good construction", "well built", "high quality", "excellent")):
        construction_quality = "good"

    visible_condition = "average"
    if any(token in lower for token in ("deteriorating", "deteriorated", "damaged", "poor condition")):
        visible_condition = "deteriorating"
    elif any(token in lower for token in ("well maintained", "well-maintained", "good condition")):
        visible_condition = "well_maintained"

    visible_issues = []
    keyword_to_issue = {
        "crack": "cracks",
        "structural": "structural_damage",
        "water stain": "water_stains",
        "seepage": "dampness",
        "damp": "dampness",
        "paint peeling": "paint_peeling",
    }
    for keyword, issue in keyword_to_issue.items():
        if keyword in lower and issue not in visible_issues:
            visible_issues.append(issue)

    prop_type_matches = None
    if any(token in lower for token in ("type mismatch", "does not match", "not matching")):
        prop_type_matches = False
    elif any(token in lower for token in ("matches the claimed type", "type matches", "consistent with")):
        prop_type_matches = True

    confidence = 0.5
    conf_match = re.search(r"confidence[^0-9]*([0-9]+(?:\.[0-9]+)?)", lower)
    if conf_match:
        raw = float(conf_match.group(1))
        confidence = raw / 100.0 if raw > 1 else raw
        confidence = max(0.0, min(confidence, 1.0))

    floors = None
    floor_match = re.search(r"\b([0-9]{1,2})\s*(?:floors?|storeys?|stories?)\b", lower)
    if floor_match:
        floors = int(floor_match.group(1))

    if not any([
        visible_issues,
        construction_quality != "average",
        visible_condition != "average",
        prop_type_matches is not None,
    ]):
        return None

    return _normalize_analysis({
        "construction_quality": construction_quality,
        "visible_condition": visible_condition,
        "estimated_floors": floors,
        "visible_issues": visible_issues,
        "property_type_matches_claimed": prop_type_matches,
        "surrounding_area_quality": "average",
        "confidence_in_analysis": confidence,
    }, claimed_type=claimed_type)


def image_to_risk_signals(analysis: dict) -> dict:
    """
    Converts LLaVA output into signals ready for risk_flags and confidence_aggregator.
    """
    if analysis is None:
        return {
            "image_confidence": None,
            "image_confidence_effective": None,
            "image_risk_flags": [],
            "image_market_penalty_pct": 0.0,
            "image_rpi_penalty": 0.0,
        }

    flags = []
    market_penalty_pct = 0.0
    rpi_penalty = 0.0

    if analysis["visible_condition"] == "deteriorating":
        flags.append({
            "flag":       "image_deteriorating_condition",
            "severity":   "medium",
            "ltv_impact": -6,
            "detail":     "Visual inspection indicates deteriorating property condition",
        })
        market_penalty_pct += 0.08
        rpi_penalty += 6.0

    if analysis["construction_quality"] == "poor":
        flags.append({
            "flag":       "image_poor_construction_quality",
            "severity":   "high",
            "ltv_impact": -8,
            "detail":     "Image analysis indicates poor construction quality",
        })
        market_penalty_pct += 0.10
        rpi_penalty += 7.0

    if analysis.get("property_type_matches_claimed") is False:
        flags.append({
            "flag":       "image_property_type_mismatch",
            "severity":   "high",
            "ltv_impact": -10,
            "detail":     "Property type in image does not match declared type",
        })
        market_penalty_pct += 0.08
        rpi_penalty += 8.0

    if analysis.get("surrounding_area_quality") == "poor":
        flags.append({
            "flag":       "image_poor_surrounding_area_quality",
            "severity":   "medium",
            "ltv_impact": -4,
            "detail":     "Surrounding area quality appears poor in visual inspection",
        })
        market_penalty_pct += 0.04
        rpi_penalty += 3.0

    for issue in analysis.get("visible_issues", []):
        if issue in {"cracks", "structural_damage"}:
            flags.append({
                "flag":       f"image_visible_{issue}",
                "severity":   "high",
                "ltv_impact": -6 if issue == "cracks" else -8,
                "detail":     f"Visible {issue.replace('_', ' ')} detected in image",
            })
            market_penalty_pct += 0.06 if issue == "cracks" else 0.08
            rpi_penalty += 4.0 if issue == "cracks" else 5.0
        elif issue in {"water_stains", "dampness"}:
            flags.append({
                "flag":       f"image_visible_{issue}",
                "severity":   "medium",
                "ltv_impact": -3 if issue == "water_stains" else -4,
                "detail":     f"Visible {issue.replace('_', ' ')} detected in image",
            })
            market_penalty_pct += 0.03 if issue == "water_stains" else 0.04
            rpi_penalty += 2.0 if issue == "water_stains" else 3.0
        elif issue == "paint_peeling":
            flags.append({
                "flag":       "image_visible_paint_peeling",
                "severity":   "low",
                "ltv_impact": -2,
                "detail":     "Visible paint peeling detected in image",
            })
            market_penalty_pct += 0.015
            rpi_penalty += 1.0

    market_penalty_pct = round(min(market_penalty_pct, 0.28), 3)
    rpi_penalty = round(min(rpi_penalty, 18.0), 1)

    raw_image_conf = analysis["confidence_in_analysis"]
    image_conf_effective = max(0.05, raw_image_conf * (1.0 - market_penalty_pct * 1.3))
    image_conf_effective = round(min(image_conf_effective, 1.0), 3)

    return {
        "image_confidence":  raw_image_conf,
        "image_confidence_effective": image_conf_effective,
        "image_risk_flags":  flags,
        "image_market_penalty_pct": market_penalty_pct,
        "image_rpi_penalty": rpi_penalty,
        "image_summary":     analysis,
    }
