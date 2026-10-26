"""
Test script to create Kumar TPK order and debug why it's not storing in DB
"""
import requests
import json

# Backend API endpoint
API_URL = "http://localhost:8000/api/bookings"

# Kumar TPK order payload
kumar_order = {
    "farmer_name": "Kumar TPK",
    "phone": "+919876543202",
    "village": "Murugan Temple Road, Thiruparankundram, Madurai District, Tamil Nadu - 625005",
    "crop": "Onion",
    "weight_kg": 400,
    "destination": "Koyambedu Mandi",
    "pickup_date": "2026-10-17",
    "pickup_time": "06:00",
    "flexible_timing": True
}

print("=" * 80)
print("🧪 TEST: Creating Kumar TPK Order")
print("=" * 80)
print(f"\n📋 Order Details:")
print(json.dumps(kumar_order, indent=2))

print(f"\n📡 Sending POST request to: {API_URL}")
print("-" * 80)

try:
    response = requests.post(
        API_URL,
        json=kumar_order,
        headers={"Content-Type": "application/json"},
        timeout=60
    )
    
    print(f"\n📊 Response Status: {response.status_code}")
    print(f"📊 Response Headers: {dict(response.headers)}")
    print("-" * 80)
    
    if response.status_code == 200 or response.status_code == 201:
        print("✅ SUCCESS! Order created successfully!")
        response_data = response.json()
        print(f"\n📦 Response Data:")
        print(json.dumps(response_data, indent=2))
        
        # Verify critical fields
        order_id = response_data.get('id')
        individual_cost = response_data.get('individual_cost')
        
        print(f"\n✅ Order ID: {order_id}")
        print(f"✅ Individual Cost: ₹{individual_cost}")
        print(f"\n🎯 NEXT: Check Supabase orders table for order ID: {order_id}")
        
    else:
        print(f"❌ FAILED! Status code: {response.status_code}")
        print(f"\n❌ Error Response:")
        try:
            error_data = response.json()
            print(json.dumps(error_data, indent=2))
        except:
            print(response.text)
            
except requests.exceptions.ConnectionError:
    print("❌ CONNECTION ERROR!")
    print("   Backend server is not running.")
    print("   Start it with: cd backend && python main.py")
    
except requests.exceptions.Timeout:
    print("❌ TIMEOUT ERROR!")
    print("   Request took longer than 60 seconds.")
    print("   This might indicate geocoding or database issues.")
    
except Exception as e:
    print(f"❌ UNEXPECTED ERROR: {type(e).__name__}")
    print(f"   {str(e)}")

print("\n" + "=" * 80)
print("📝 CHECK BACKEND CONSOLE for detailed logs with emoji indicators")
print("=" * 80)
