"""
Test script to verify image analysis impact on valuation decisions.
"""

import asyncio
import httpx
import json

async def test_valuation_with_and_without_image():
    """Test the difference between valuation with and without image analysis."""
    
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
    
    print("Testing valuation impact of image analysis...")
    
    # Test 1: Valuation without image
    print("\n1. Testing without image...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/valuate",
                json=property_data
            )
            if response.status_code == 200:
                result_without_image = response.json()
                print("✓ Successfully got valuation without image")
                print(f"  Confidence score: {result_without_image.get('confidence_score', 'N/A')}")
                print(f"  Standard LTV: {result_without_image.get('ltv_recommendation', {}).get('standard', 'N/A')}")
                print(f"  Conservative LTV: {result_without_image.get('ltv_recommendation', {}).get('conservative', 'N/A')}")
                print(f"  Risk flags: {len(result_without_image.get('risk_flags', []))}")
            else:
                print(f"✗ Failed to get valuation without image: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"✗ Error testing without image: {e}")
    
    # Test 2: Valuation with image (you'll need to provide a real image file)
    print("\n2. Testing with image...")
    print("   Note: You need to provide an actual image file for this test")
    print("   The image should be a property photo in JPEG format")
    
    # Example of how to test with an image file:
    print("""
To test with an image file, use a tool like curl:
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
  -F "image=@path/to/your/image.jpg" \\
  http://127.0.0.1:8000/valuate-with-image
""")

if __name__ == "__main__":
    asyncio.run(test_valuation_with_and_without_image())