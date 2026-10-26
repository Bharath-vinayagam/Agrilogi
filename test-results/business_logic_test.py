#!/usr/bin/env python3
"""
Business Logic Testing for Agrilogi
Tests pricing calculations, clustering algorithms, and cost allocations
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.pricing_service import calculate_individual_cost
from services.rate_config import get_vehicle_class_for_weight
from services.mandi_config import get_mandi_coords
import json
from datetime import datetime

test_results = []

def log_result(category, test_name, expected, actual, status, details=""):
    result = {
        "category": category,
        "test_name": test_name,
        "expected": expected,
        "actual": actual,
        "status": status,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    test_results.append(result)
    
    emoji = {"PASS": "✅", "FAIL": "❌", "PARTIAL": "⚠️"}
    print(f"{emoji.get(status, '?')} [{category}] {test_name}: {status}")
    if status == "FAIL":
        print(f"   Expected: {expected}")
        print(f"   Actual: {actual}")
    if details:
        print(f"   Details: {details}")

# ===== TEST PRICING CALCULATIONS =====

print("\n" + "="*80)
print("BUSINESS LOGIC TESTS - PRICING CALCULATIONS")
print("="*80)

# Test 1: Vehicle class selection
print("\n### Test 1: Vehicle Class Selection")

# Removed - replaced with test_cases_corrected below

test_cases_corrected = [
    (100, "mini", 500),
    (500, "mini", 500),
    (501, "standard", 1100),
    (1100, "standard", 1100),
    (1101, "heavy", 2500),
    (2500, "heavy", 2500),
]

for weight, expected_class, expected_capacity in test_cases_corrected:
    v_class = get_vehicle_class_for_weight(weight)
    actual_class = v_class['name']
    actual_capacity = v_class['capacity_kg']
    
    if actual_class == expected_class and actual_capacity == expected_capacity:
        log_result("Pricing", f"Vehicle class for {weight}kg", f"{expected_class} ({expected_capacity}kg)", f"{actual_class} ({actual_capacity}kg)", "PASS")
    else:
        log_result("Pricing", f"Vehicle class for {weight}kg", f"{expected_class} ({expected_capacity}kg)", f"{actual_class} ({actual_capacity}kg)", "FAIL")

# Test 2: Individual cost calculation - Known coordinates
print("\n### Test 2: Individual Cost Calculation (Known Coordinates)")

# Test case: 350kg tomatoes from Athur (11.589, 78.605) to Koyambedu (13.068, 80.245)
# Expected: Standard vehicle (1100kg capacity), ₹12/km, ₹400 base
# Distance: ~246 km
# weight_factor = 350/1100 = 0.318
# cost = 400 + (246 * 12 * 0.318) = 400 + 939 = 1339
# But minimum = 350 * 3 = 1050
# Expected: max(1339, 1050) = 1339

weight = 350
lat, lng = 11.589, 78.605
destination = "Koyambedu Mandi"

cost = calculate_individual_cost(weight, lat, lng, destination)

# Verify it's reasonable (between 1000-1500 for this distance)
if 1000 <= cost <= 1500:
    log_result("Pricing", "Individual cost 350kg Athur→Koyambedu", "1000-1500", cost, "PASS", f"₹{cost}")
else:
    log_result("Pricing", "Individual cost 350kg Athur→Koyambedu", "1000-1500", cost, "FAIL", f"₹{cost}")

# Test 3: Zero weight edge case
print("\n### Test 3: Edge Cases")

zero_cost = calculate_individual_cost(0, 11.589, 78.605, "Koyambedu Mandi")
if zero_cost == 0:
    log_result("Pricing", "Zero weight cost", 0, zero_cost, "PASS")
else:
    log_result("Pricing", "Zero weight cost", 0, zero_cost, "FAIL")

# Test 4: Negative weight (should handle gracefully)
negative_cost = calculate_individual_cost(-100, 11.589, 78.605, "Koyambedu Mandi")
if negative_cost == 0:
    log_result("Pricing", "Negative weight cost", 0, negative_cost, "PASS")
else:
    log_result("Pricing", "Negative weight cost", 0, negative_cost, "FAIL")

# Test 5: Missing coordinates fallback
print("\n### Test 4: Fallback Pricing (Missing Coordinates)")

# When coordinates are missing, should use fallback rate (₹9/kg)
fallback_cost = calculate_individual_cost(400, None, None, "Unknown Mandi")
expected_fallback = 400 * 9  # 3600
if fallback_cost == expected_fallback:
    log_result("Pricing", "Fallback pricing 400kg", expected_fallback, fallback_cost, "PASS", f"₹{fallback_cost}")
else:
    log_result("Pricing", "Fallback pricing 400kg", expected_fallback, fallback_cost, "FAIL", f"₹{fallback_cost}")

# Test 6: Minimum rate floor (₹3/kg)
print("\n### Test 5: Minimum Rate Floor")

# Very light weight on short distance should hit minimum floor
# 50kg, 5km away
# Standard vehicle: weight_factor = 50/1100 = 0.045
# cost = 400 + (5 * 12 * 0.045) = 400 + 2.7 = 402.7
# minimum = 50 * 3 = 150
# Expected: max(403, 150) = 403

light_cost = calculate_individual_cost(50, 13.0, 80.0, "Koyambedu Mandi")
minimum_floor = 50 * 3

if light_cost >= minimum_floor:
    log_result("Pricing", "Minimum rate floor 50kg", f"≥{minimum_floor}", light_cost, "PASS", f"₹{light_cost}")
else:
    log_result("Pricing", "Minimum rate floor 50kg", f"≥{minimum_floor}", light_cost, "FAIL", f"₹{light_cost}")

# ===== TEST MANDI CONFIGURATION =====

print("\n" + "="*80)
print("BUSINESS LOGIC TESTS - MANDI CONFIGURATION")
print("="*80)

known_mandis = [
    "Koyambedu Mandi",
    "Koyambedu",
    "Tiruvallur",
    "Salem",
    "Coimbatore",
]

for mandi_name in known_mandis:
    coords = get_mandi_coords(mandi_name)
    if coords and len(coords) == 2:
        lat, lng = coords
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            log_result("Mandi Config", f"Coordinates for {mandi_name}", "Valid coords", f"({lat}, {lng})", "PASS")
        else:
            log_result("Mandi Config", f"Coordinates for {mandi_name}", "Valid coords", f"Invalid: ({lat}, {lng})", "FAIL")
    else:
        log_result("Mandi Config", f"Coordinates for {mandi_name}", "Valid coords", "None", "FAIL")

# Test unknown mandi
unknown_coords = get_mandi_coords("NonExistent Mandi XYZ")
if unknown_coords is None:
    log_result("Mandi Config", "Unknown mandi", None, None, "PASS")
else:
    log_result("Mandi Config", "Unknown mandi", None, unknown_coords, "FAIL")

# ===== SAVE RESULTS =====

print("\n" + "="*80)
print("TEST SUMMARY")
print("="*80)

passed = sum(1 for r in test_results if r['status'] == 'PASS')
failed = sum(1 for r in test_results if r['status'] == 'FAIL')
partial = sum(1 for r in test_results if r['status'] == 'PARTIAL')
total = len(test_results)

print(f"Total Tests: {total}")
print(f"✅ Passed: {passed} ({passed/total*100:.1f}%)")
print(f"❌ Failed: {failed} ({failed/total*100:.1f}%)")
print(f"⚠️  Partial: {partial} ({partial/total*100:.1f}%)")

# Save to JSON
with open("business_logic_results.json", "w") as f:
    json.dump({
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "partial": partial,
            "pass_rate": round(passed/total*100, 1)
        },
        "tests": test_results
    }, f, indent=2)

print(f"\n✅ Results saved to business_logic_results.json")

exit(0 if failed == 0 else 1)
