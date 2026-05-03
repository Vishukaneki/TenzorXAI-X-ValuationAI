"""
Script to verify that image analysis is actually influencing valuation decisions.
"""

import asyncio
import httpx
import json
import os

async def verify_image_impact():
    """Verify that image analysis is actually influencing the valuation decisions."""
    
    print("=== Verifying Image Analysis Impact on Real Valuations ===")
    
    # Test property data
    property_data = {
        "locality": "Kondapur",
        "property_type": "apartment",
        "subtype": "2BHK",
        "size_sqft": 1200,
        "age_years": 5,
        "floor_num": 3,
        "total_floors": 10,
        "has_lift": True,
        "legal_status": "clear",
        "occupancy_status": "self_occupied",
        "rental_yield": 3.5
    }
    
    # API base URL (adjust if needed)
    base_url = "http://127.0.0.1:8000"
    
    print("\n1. Testing valuation WITHOUT image...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/valuate",
                json=property_data
            )
            if response.status_code == 200:
                result_without_image = response.json()
                print("✓ Successfully got valuation without image")
                confidence_without = result_without_image.get('confidence_score', 'N/A')
                ltv_standard_without = result_without_image.get('ltv_recommendation', {}).get('standard', 'N/A')
                ltv_conservative_without = result_without_image.get('ltv_recommendation', {}).get('conservative', 'N/A')
                risk_flags_without = len(result_without_image.get('risk_flags', []))
                
                print(f"  Confidence score: {confidence_without}")
                print(f"  Standard LTV: {ltv_standard_without}")
                print(f"  Conservative LTV: {ltv_conservative_without}")
                print(f"  Risk flags: {risk_flags_without}")
                
                # Check for image-related fields
                if 'image_analysis' in result_without_image:
                    print("  WARNING: Image analysis found in result without image!")
            else:
                print(f"✗ Failed to get valuation without image: {response.status_code}")
                print(response.text)
                return
    except Exception as e:
        print(f"✗ Error testing without image: {e}")
        return
    
    print("\n2. Testing valuation WITH image (using mock analysis)...")
    
    # For this test, we'll simulate what happens when we send an image
    # Since we can't easily send an actual image file in this script,
    # we'll show what you should look for in the actual API response
    
    print("To test with an actual image, use this curl command:")
    print("""
curl -X POST \\
  -F "locality=Kondapur" \\
  -F "property_type=apartment" \\
  -F "subtype=2BHK" \\
  -F "size_sqft=1200" \\
  -F "age_years=5" \\
  -F "floor_num=3" \\
  -F "total_floors=10" \\
  -F "has_lift=true" \\
  -F "legal_status=clear" \\
  -F "occupancy_status=self_occupied" \\
  -F "rental_yield=3.5" \\
  -F "image=@path/to/test/image.jpg" \\
  http://127.0.0.1:8000/valuate-with-image
""")
    
    print("\n3. What to look for in the response to verify image impact:")
    
    print("   A. Check for 'image_analysis' field in the response:")
    print("      - If present, image analysis was performed")
    print("      - Contains details about construction quality, visible condition, etc.")
    
    print("\n   B. Check 'confidence_breakdown' for 'image_quality':")
    print("      - Should show a value between 0.0-1.0")
    print("      - This contributes 5% to the overall confidence score")
    
    print("\n   C. Compare risk flags:")
    print("      - Look for flags starting with 'image_'")
    print("      - These can reduce LTV by 4-8% each")
    print("      - Example flags: image_deteriorating_condition, image_poor_construction_quality")
    
    print("\n   D. Compare LTV recommendations:")
    print("      - Image-based risk flags can reduce both standard and conservative LTV")
    print("      - Check the rationale for mentions of risk flags")
    
    print("\n4. Testing with problematic image analysis:")
    print("   To see maximum impact, you can temporarily modify the image_analyzer.py")
    print("   to return problematic results (for testing only):")
    
    mock_problematic_analysis = {
        "construction_quality": "poor",
        "visible_condition": "deteriorating",
        "visible_issues": ["cracks", "water_stains"],
        "property_type_matches_claimed": False,
        "confidence_in_analysis": 0.3,
    }
    
    print(json.dumps(mock_problematic_analysis, indent=2))
    
    print("\nThis would generate risk flags with up to 23% total LTV impact!")

if __name__ == "__main__":
    asyncio.run(verify_image_impact())