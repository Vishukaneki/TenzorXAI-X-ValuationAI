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
import base64
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

    b64 = base64.b64encode(image_bytes).decode("utf-8")
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
            
            # Handle different response structures
            if "result" in response_data and "response" in response_data["result"]:
                raw_text = response_data["result"]["response"]
                return _parse_llava_response(raw_text)
            elif "response" in response_data:
                raw_text = response_data["response"]
                return _parse_llava_response(raw_text)
            else:
                print(f"[image_analyzer] Unexpected response structure: {response_data}")
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


def _parse_llava_response(text: str) -> Optional[dict]:
    import json, re
    try:
        # Handle different text formats
        clean = text.strip()
        
        # Strip any markdown fences
        clean = re.sub(r"```json|```", "", clean).strip()
        
        # Try to parse as JSON
        if clean.startswith('{') and clean.endswith('}'):
            data = json.loads(clean)
        else:
            # Sometimes the response is just plain text - try to extract JSON from it
            # Look for JSON-like patterns in the text
            json_match = re.search(r'\{.*\}', clean, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                print(f"[image_analyzer] Could not find JSON in response: {clean}")
                return None

        # Normalize and validate keys with default values
        result = {
            "construction_quality":          data.get("construction_quality", "average"),
            "visible_condition":             data.get("visible_condition", "average"),
            "estimated_floors":              data.get("estimated_floors"),
            "visible_issues":                data.get("visible_issues", []),
            "property_type_matches_claimed": data.get("property_type_matches_claimed"),
            "surrounding_area_quality":      data.get("surrounding_area_quality", "average"),
            "confidence_in_analysis":        float(data.get("confidence_in_analysis", 0.5)),
        }
        
        print(f"[image_analyzer] Parsed result: {result}")
        return result
        
    except json.JSONDecodeError as e:
        print(f"[image_analyzer] JSON decode error: {e}")
        print(f"[image_analyzer] Raw text was: {text}")
        return None
    except Exception as e:
        print(f"[image_analyzer] Parse error: {e}")
        return None


def image_to_risk_signals(analysis: dict) -> dict:
    """
    Converts LLaVA output into signals ready for risk_flags and confidence_aggregator.
    """
    if analysis is None:
        return {"image_confidence": None, "image_risk_flags": []}

    flags = []

    if analysis["visible_condition"] == "deteriorating":
        flags.append({
            "flag":       "image_deteriorating_condition",
            "severity":   "medium",
            "ltv_impact": -4,
            "detail":     "Visual inspection indicates deteriorating property condition",
        })

    if analysis["construction_quality"] == "poor":
        flags.append({
            "flag":       "image_poor_construction_quality",
            "severity":   "high",
            "ltv_impact": -6,
            "detail":     "Image analysis indicates poor construction quality",
        })

    if analysis.get("property_type_matches_claimed") is False:
        flags.append({
            "flag":       "image_property_type_mismatch",
            "severity":   "high",
            "ltv_impact": -8,
            "detail":     "Property type in image does not match declared type",
        })

    for issue in analysis.get("visible_issues", []):
        if issue in {"cracks", "structural_damage"}:
            flags.append({
                "flag":       f"image_visible_{issue}",
                "severity":   "high",
                "ltv_impact": -5,
                "detail":     f"Visible {issue.replace('_', ' ')} detected in image",
            })

    return {
        "image_confidence":  analysis["confidence_in_analysis"],
        "image_risk_flags":  flags,
        "image_summary":     analysis,
    }
