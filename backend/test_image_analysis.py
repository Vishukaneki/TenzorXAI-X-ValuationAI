"""
Test script for image analysis functionality.
"""

import asyncio
import os
from image_analyzer import analyze_image, image_to_risk_signals

async def test_image_analysis():
    """Test the image analysis functionality."""
    print("Testing image analysis...")
    
    # Check if we're using mock analysis
    mock_enabled = os.getenv("MOCK_IMAGE_ANALYSIS", "false").lower() == "true"
    if mock_enabled:
        print("Using mock image analysis (no Cloudflare credentials required)")
    else:
        print("Using Cloudflare Workers AI for image analysis")
        # Check if credentials are set
        cf_account_id = os.getenv("CF_ACCOUNT_ID", "")
        cf_api_token = os.getenv("CF_API_TOKEN", "")
        if not cf_account_id or not cf_api_token:
            print("WARNING: Cloudflare credentials not set. Image analysis will be skipped.")
            return
    
    # Create dummy image bytes (in a real scenario, this would be actual image data)
    dummy_image_bytes = b"dummy_image_data"
    
    # Test the analysis
    analysis = await analyze_image(dummy_image_bytes, "apartment")
    
    if analysis is None:
        print("Image analysis returned None (skipped or failed)")
        return
    
    print("Image analysis result:")
    print(f"  Construction quality: {analysis.get('construction_quality')}")
    print(f"  Visible condition: {analysis.get('visible_condition')}")
    print(f"  Confidence: {analysis.get('confidence_in_analysis')}")
    
    # Test conversion to risk signals
    risk_signals = image_to_risk_signals(analysis)
    print("\nRisk signals:")
    print(f"  Image confidence: {risk_signals.get('image_confidence')}")
    print(f"  Risk flags: {len(risk_signals.get('image_risk_flags', []))}")

if __name__ == "__main__":
    asyncio.run(test_image_analysis())