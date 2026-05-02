"""
Script to analyze the impact of image analysis on valuation results.
"""

import asyncio
import os
from image_analyzer import analyze_image, image_to_risk_signals

async def test_image_analysis_impact():
    """Test and display the specific impact of image analysis."""
    
    print("=== Image Analysis Impact Test ===")
    
    # Check if we're using mock analysis
    mock_enabled = os.getenv("MOCK_IMAGE_ANALYSIS", "false").lower() == "true"
    if mock_enabled:
        print("Using mock image analysis")
    else:
        print("Using Cloudflare Workers AI for image analysis")
        
    # Check Cloudflare credentials
    cf_account_id = os.getenv("CF_ACCOUNT_ID", "")
    cf_api_token = os.getenv("CF_API_TOKEN", "")
    
    print("\nAnalyzing image...")
    
    # Always use mock analysis to demonstrate the impact
    print("Demonstrating with mock analysis results:")
    analysis = {
        "construction_quality": "average",
        "visible_condition": "well_maintained",
        "estimated_floors": 5,
        "visible_issues": [],  # Try changing this to ["cracks"] to see impact
        "property_type_matches_claimed": True,
        "surrounding_area_quality": "good",
        "confidence_in_analysis": 0.8,
    }
    
    print(f"\nImage Analysis Results:")
    print(f"  Construction Quality: {analysis.get('construction_quality')}")
    print(f"  Visible Condition: {analysis.get('visible_condition')}")
    print(f"  Visible Issues: {analysis.get('visible_issues')}")
    print(f"  Confidence in Analysis: {analysis.get('confidence_in_analysis')}")
    
    # Convert to risk signals
    risk_signals = image_to_risk_signals(analysis)
    
    print(f"\nRisk Signals Generated:")
    print(f"  Image Confidence: {risk_signals.get('image_confidence')}")
    print(f"  Number of Risk Flags: {len(risk_signals.get('image_risk_flags', []))}")
    
    # Display each risk flag
    for i, flag in enumerate(risk_signals.get('image_risk_flags', [])):
        print(f"    Flag {i+1}: {flag.get('flag')} ({flag.get('severity')}) - {flag.get('ltv_impact')}% LTV impact")
    
    print(f"\nImpact on Decision Making:")
    print(f"  1. Confidence Score: Image quality contributes 5% to overall confidence")
    print(f"  2. Risk Flags: Image-based flags can reduce LTV by up to 8% each")
    print(f"  3. LTV Recommendation: Both standard and conservative LTVs are affected")
    
    # Show what happens with problematic image analysis
    print(f"\nExample of High Impact Scenario:")
    problematic_analysis = {
        "construction_quality": "poor",
        "visible_condition": "deteriorating",
        "visible_issues": ["cracks", "water_stains"],
        "property_type_matches_claimed": False,
        "confidence_in_analysis": 0.3,
    }
    
    problematic_signals = image_to_risk_signals(problematic_analysis)
    print(f"  With problematic image analysis:")
    for flag in problematic_signals.get('image_risk_flags', []):
        print(f"    - {flag.get('flag')}: {flag.get('ltv_impact')}% LTV impact")
    
    total_ltv_impact = sum(abs(flag['ltv_impact']) for flag in problematic_signals.get('image_risk_flags', []))
    print(f"  Total potential LTV impact from image flags: {total_ltv_impact}%")

if __name__ == "__main__":
    asyncio.run(test_image_analysis_impact())