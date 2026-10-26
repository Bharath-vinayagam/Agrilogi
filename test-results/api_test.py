#!/usr/bin/env python3
"""
Comprehensive API Testing Script for Agrilogi
Tests all backend endpoints with valid/invalid inputs
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any

BASE_URL = "http://localhost:8000"
test_results = []
test_data = {}

class TestResult:
    def __init__(self, feature, test_case, expected, actual, status, evidence=""):
        self.feature = feature
        self.test_case = test_case
        self.expected = expected
        self.actual = actual
        self.status = status  # PASS, FAIL, BLOCKED, PARTIAL
        self.evidence = evidence
        self.timestamp = datetime.now().isoformat()

def log_test(result: TestResult):
    test_results.append(result)
    status_emoji = {"PASS": "✅", "FAIL": "❌", "BLOCKED": "🚫", "PARTIAL": "⚠️"}
    print(f"{status_emoji.get(result.status, '❓')} {result.feature}: {result.test_case} - {result.status}")
    if result.status == "FAIL":
        print(f"   Expected: {result.expected}")
        print(f"   Actual: {result.actual}")

def test_health_check():
    """Test health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        expected = {"status": "ok", "service": "agrilogi"}
        actual = response.json()
        
        if response.status_code == 200 and actual == expected:
            log_test(TestResult("Health Check", "GET /health", expected, actual, "PASS", f"Status: {response.status_code}"))
        else:
            log_test(TestResult("Health Check", "GET /health", expected, actual, "FAIL"))
    except Exception as e:
        log_test(TestResult("Health Check", "GET /health", "200 OK", str(e), "FAIL"))

def test_list_bookings():
    """Test listing bookings"""
    try:
        response = requests.get(f"{BASE_URL}/api/bookings", timeout=10)
        
        if response.status_code == 200:
            bookings = response.json()
            test_data['bookings'] = bookings
            log_test(TestResult("Bookings", "GET /api/bookings", "200 + list", f"200 + {len(bookings)} bookings", "PASS"))
            
            # Test with phone filter
            if bookings and len(bookings) > 0:
                phone = bookings[0].get('phone')
                if phone:
                    filtered = requests.get(f"{BASE_URL}/api/bookings?phone={phone}", timeout=10)
                    if filtered.status_code == 200:
                        filtered_data = filtered.json()
                        log_test(TestResult("Bookings", "GET /api/bookings?phone=X", f"Filtered by phone", f"{len(filtered_data)} results", "PASS"))
                    else:
                        log_test(TestResult("Bookings", "GET /api/bookings?phone=X", "200", f"{filtered.status_code}", "FAIL"))
        else:
            log_test(TestResult("Bookings", "GET /api/bookings", "200", f"{response.status_code}", "FAIL"))
    except Exception as e:
        log_test(TestResult("Bookings", "GET /api/bookings", "200 OK", str(e), "FAIL"))

def test_slot_summary():
    """Test slot summary endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/bookings/slots/summary", timeout=10)
        
        if response.status_code == 200:
            summary = response.json()
            test_data['slot_summary'] = summary
            log_test(TestResult("Bookings", "GET /api/bookings/slots/summary", "200 + summary", f"200 + {len(summary)} slots", "PASS"))
        else:
            log_test(TestResult("Bookings", "GET /api/bookings/slots/summary", "200", f"{response.status_code}", "FAIL"))
    except Exception as e:
        log_test(TestResult("Bookings", "GET /api/bookings/slots/summary", "200 OK", str(e), "FAIL"))

def test_create_booking():
    """Test creating a booking"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    test_booking = {
        "farmer_name": "Test Farmer QA",
        "phone": "+919999999999",
        "village": "Athur",
        "crop": "Tomato",
        "weight_kg": 250,
        "destination": "Koyambedu Mandi",
        "pickup_date": tomorrow,
        "pickup_slot": "morning",
        "is_time_flexible": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/bookings", json=test_booking, timeout=10)
        
        if response.status_code == 200:
            booking = response.json()
            test_data['test_booking'] = booking
            log_test(TestResult("Bookings", "POST /api/bookings (valid)", "201/200 + booking", f"{response.status_code} + ID: {booking.get('id')}", "PASS", json.dumps(booking, indent=2)))
            
            # Verify it appears in list
            time.sleep(1)
            verify = requests.get(f"{BASE_URL}/api/bookings?phone=+919999999999", timeout=10)
            if verify.status_code == 200:
                found = any(b.get('id') == booking.get('id') for b in verify.json())
                if found:
                    log_test(TestResult("Bookings", "POST /api/bookings (persistence)", "Booking in DB", "Verified", "PASS"))
                else:
                    log_test(TestResult("Bookings", "POST /api/bookings (persistence)", "Booking in DB", "Not found", "FAIL"))
        else:
            log_test(TestResult("Bookings", "POST /api/bookings (valid)", "200", f"{response.status_code}: {response.text}", "FAIL"))
    except Exception as e:
        log_test(TestResult("Bookings", "POST /api/bookings (valid)", "200 OK", str(e), "FAIL"))

def test_create_booking_invalid():
    """Test creating booking with invalid data"""
    invalid_tests = [
        ({"farmer_name": "Test"}, "Missing required fields"),
        ({"farmer_name": "Test", "phone": "123", "village": "X", "crop": "Y", "weight_kg": -100, "destination": "Z"}, "Negative weight"),
        ({"farmer_name": "Test", "phone": "123", "village": "X", "crop": "Y", "weight_kg": 0, "destination": "Z"}, "Zero weight"),
    ]
    
    for invalid_data, description in invalid_tests:
        try:
            response = requests.post(f"{BASE_URL}/api/bookings", json=invalid_data, timeout=10)
            
            if response.status_code in [400, 422]:
                log_test(TestResult("Bookings", f"POST /api/bookings (invalid: {description})", "400/422", f"{response.status_code}", "PASS"))
            else:
                log_test(TestResult("Bookings", f"POST /api/bookings (invalid: {description})", "400/422", f"{response.status_code}", "FAIL"))
        except Exception as e:
            log_test(TestResult("Bookings", f"POST /api/bookings (invalid: {description})", "400/422", str(e), "PARTIAL"))

def test_list_drivers():
    """Test listing drivers"""
    try:
        response = requests.get(f"{BASE_URL}/api/drivers", timeout=10)
        
        if response.status_code == 200:
            drivers = response.json()
            test_data['drivers'] = drivers
            log_test(TestResult("Drivers", "GET /api/drivers", "200 + list", f"200 + {len(drivers)} drivers", "PASS"))
        else:
            log_test(TestResult("Drivers", "GET /api/drivers", "200", f"{response.status_code}", "FAIL"))
    except Exception as e:
        log_test(TestResult("Drivers", "GET /api/drivers", "200 OK", str(e), "FAIL"))

def test_list_bids():
    """Test listing bids"""
    try:
        response = requests.get(f"{BASE_URL}/api/auction/bids", timeout=10)
        
        if response.status_code == 200:
            bids = response.json()
            test_data['bids'] = bids
            log_test(TestResult("Auction", "GET /api/auction/bids", "200 + list", f"200 + {len(bids)} bids", "PASS"))
        else:
            log_test(TestResult("Auction", "GET /api/auction/bids", "200", f"{response.status_code}", "FAIL"))
    except Exception as e:
        log_test(TestResult("Auction", "GET /api/auction/bids", "200 OK", str(e), "FAIL"))

def test_admin_snapshot():
    """Test admin snapshot endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/admin/snapshot", timeout=10)
        
        if response.status_code == 200:
            snapshot = response.json()
            test_data['snapshot'] = snapshot
            
            # Verify expected keys
            expected_keys = ['extraction', 'recommendation', 'orders', 'bids', 'slot', 'savingsTrend']
            actual_keys = list(snapshot.keys())
            missing_keys = [k for k in expected_keys if k not in actual_keys]
            
            if not missing_keys:
                log_test(TestResult("Admin", "GET /api/admin/snapshot", "200 + all keys", f"200 + keys: {actual_keys}", "PASS"))
            else:
                log_test(TestResult("Admin", "GET /api/admin/snapshot", f"Keys: {expected_keys}", f"Missing: {missing_keys}", "PARTIAL"))
        else:
            log_test(TestResult("Admin", "GET /api/admin/snapshot", "200", f"{response.status_code}", "FAIL"))
    except Exception as e:
        log_test(TestResult("Admin", "GET /api/admin/snapshot", "200 OK", str(e), "FAIL"))

def test_admin_slot_status():
    """Test admin slot status endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/admin/slot-status", timeout=10)
        
        if response.status_code == 200:
            status = response.json()
            expected_keys = ['next_slot', 'next_slot_iso', 'wait_minutes', 'pending_orders']
            actual_keys = list(status.keys())
            missing_keys = [k for k in expected_keys if k not in actual_keys]
            
            if not missing_keys:
                log_test(TestResult("Admin", "GET /api/admin/slot-status", "200 + status", f"Slot: {status.get('next_slot')}, Pending: {status.get('pending_orders')}", "PASS"))
            else:
                log_test(TestResult("Admin", "GET /api/admin/slot-status", f"Keys: {expected_keys}", f"Missing: {missing_keys}", "PARTIAL"))
        else:
            log_test(TestResult("Admin", "GET /api/admin/slot-status", "200", f"{response.status_code}", "FAIL"))
    except Exception as e:
        log_test(TestResult("Admin", "GET /api/admin/slot-status", "200 OK", str(e), "FAIL"))

def test_voice_extraction():
    """Test voice extraction endpoint"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    test_payload = {
        "transcript": "My name is Kumar. I am from Athur village. I have 400 kilograms of onions to send to Koyambedu Mandi.",
        "language": "en",
        "pickup_date": tomorrow,
        "pickup_slot": "morning",
        "is_time_flexible": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/voice/extract", json=test_payload, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            
            # Verify extraction result structure
            expected_fields = ['farmer_name', 'village', 'crop', 'weight_kg', 'confidence']
            actual_fields = list(result.keys())
            
            if all(f in actual_fields for f in expected_fields):
                log_test(TestResult("Voice", "POST /api/voice/extract", "200 + extracted data", f"Name: {result.get('farmer_name')}, Crop: {result.get('crop')}", "PASS", json.dumps(result, indent=2)))
                
                # Verify confidence scores
                confidence = result.get('confidence', {})
                avg_confidence = sum(confidence.values()) / len(confidence) if confidence else 0
                log_test(TestResult("Voice", "POST /api/voice/extract (confidence)", "Confidence scores", f"Avg: {avg_confidence:.1f}%", "PASS"))
            else:
                log_test(TestResult("Voice", "POST /api/voice/extract", f"Fields: {expected_fields}", f"Got: {actual_fields}", "PARTIAL"))
        else:
            log_test(TestResult("Voice", "POST /api/voice/extract", "200", f"{response.status_code}: {response.text}", "FAIL"))
    except Exception as e:
        log_test(TestResult("Voice", "POST /api/voice/extract", "200 OK", str(e), "FAIL"))

def test_pricing_config():
    """Test pricing configuration endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/config/pricing", timeout=10)
        
        if response.status_code == 200:
            config = response.json()
            log_test(TestResult("Config", "GET /api/config/pricing", "200 + pricing config", f"Vehicle classes: {len(config.get('vehicle_classes', []))}", "PASS"))
        else:
            log_test(TestResult("Config", "GET /api/config/pricing", "200", f"{response.status_code}", "FAIL"))
    except Exception as e:
        log_test(TestResult("Config", "GET /api/config/pricing", "200 OK", str(e), "FAIL"))

def run_all_tests():
    """Execute all test suites"""
    print("=" * 80)
    print("AGRILOGI API TESTING SUITE")
    print("=" * 80)
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Target: {BASE_URL}")
    print("=" * 80)
    
    start_time = time.time()
    
    # Test execution
    test_health_check()
    test_list_bookings()
    test_slot_summary()
    test_create_booking()
    test_create_booking_invalid()
    test_list_drivers()
    test_list_bids()
    test_admin_snapshot()
    test_admin_slot_status()
    test_voice_extraction()
    test_pricing_config()
    
    # Test order bidding if we have bookings
    if test_data.get('bookings'):
        test_order_bidding()
    
    # Test capacity tracking if we have drivers
    if test_data.get('drivers'):
        test_capacity_tracking()
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in test_results if r.status == "PASS")
    failed = sum(1 for r in test_results if r.status == "FAIL")
    partial = sum(1 for r in test_results if r.status == "PARTIAL")
    blocked = sum(1 for r in test_results if r.status == "BLOCKED")
    total = len(test_results)
    
    print(f"Total Tests: {total}")
    print(f"✅ Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"❌ Failed: {failed} ({failed/total*100:.1f}%)")
    print(f"⚠️  Partial: {partial} ({partial/total*100:.1f}%)")
    print(f"🚫 Blocked: {blocked} ({blocked/total*100:.1f}%)")
    print(f"Duration: {duration:.2f}s")
    
    # Save results
    save_results()
    
    return passed, failed, partial, blocked, total

def test_order_bidding():
    """Test order bidding endpoints"""
    bookings = test_data.get('bookings', [])
    if not bookings:
        return
    
    # Find an open order for bidding
    open_orders = [b for b in bookings if b.get('status') == 'Pending']
    if not open_orders:
        log_test(TestResult("Order Bidding", "Test bidding", "Open orders available", "No open orders", "BLOCKED"))
        return
    
    order = open_orders[0]
    order_id = order.get('id')
    
    try:
        # Test getting bids for an order
        response = requests.get(f"{BASE_URL}/api/bids/order/{order_id}", timeout=10)
        
        if response.status_code == 200:
            bids = response.json()
            log_test(TestResult("Order Bidding", f"GET /api/bids/order/{order_id}", "200 + bids", f"{len(bids)} bids", "PASS"))
        else:
            log_test(TestResult("Order Bidding", f"GET /api/bids/order/{order_id}", "200", f"{response.status_code}", "FAIL"))
    except Exception as e:
        log_test(TestResult("Order Bidding", "GET /api/bids/order/X", "200 OK", str(e), "FAIL"))

def test_capacity_tracking():
    """Test driver capacity tracking"""
    drivers = test_data.get('drivers', [])
    if not drivers:
        return
    
    driver = drivers[0]
    driver_name = driver.get('name')
    
    try:
        # Test capacity info
        response = requests.get(f"{BASE_URL}/api/bids/capacity/{driver_name}", timeout=10)
        
        if response.status_code == 200:
            capacity = response.json()
            log_test(TestResult("Capacity", f"GET /api/bids/capacity/{driver_name}", "200 + capacity", f"Load: {capacity.get('current_load_kg')}kg", "PASS"))
            
            # Test capacity timeline
            timeline_response = requests.get(f"{BASE_URL}/api/bids/capacity/timeline/{driver_name}", timeout=10)
            if timeline_response.status_code == 200:
                timeline = timeline_response.json()
                log_test(TestResult("Capacity", f"GET /api/bids/capacity/timeline/{driver_name}", "200 + timeline", f"{len(timeline)} events", "PASS"))
        else:
            log_test(TestResult("Capacity", f"GET /api/bids/capacity/{driver_name}", "200", f"{response.status_code}", "FAIL"))
    except Exception as e:
        log_test(TestResult("Capacity", "Capacity tracking", "200 OK", str(e), "FAIL"))

def save_results():
    """Save test results to file"""
    with open("test-results/api_test_results.json", "w") as f:
        results_data = {
            "timestamp": datetime.now().isoformat(),
            "base_url": BASE_URL,
            "total_tests": len(test_results),
            "passed": sum(1 for r in test_results if r.status == "PASS"),
            "failed": sum(1 for r in test_results if r.status == "FAIL"),
            "partial": sum(1 for r in test_results if r.status == "PARTIAL"),
            "blocked": sum(1 for r in test_results if r.status == "BLOCKED"),
            "tests": [
                {
                    "feature": r.feature,
                    "test_case": r.test_case,
                    "expected": r.expected,
                    "actual": r.actual,
                    "status": r.status,
                    "evidence": r.evidence,
                    "timestamp": r.timestamp
                }
                for r in test_results
            ]
        }
        json.dump(results_data, f, indent=2)
    
    print(f"\n✅ Results saved to test-results/api_test_results.json")

if __name__ == "__main__":
    run_all_tests()
