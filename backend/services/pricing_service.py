"""
services/pricing_service.py

Calculates individual transport costs based on real distance to mandi,
vehicle class rates, and dynamic weight factors.

Formula for Solo Transport:
"What would this farmer pay hiring a truck alone?"
    Solo cost = Driver's full trip cost (fuel + wage) × distance + base fee
    This represents hiring the entire vehicle for the trip.

Formula for Shared Transport:
"What does each farmer pay when pooled together?"
    Total pool cost = Solo cost for the route
    Each farmer's share = (Total pool cost / number of farmers) + proportional allocation
"""

import math
from typing import Optional

from services.mandi_config import get_mandi_coords
from services.rate_config import (
    get_vehicle_class_for_weight,
    MIN_RATE_PER_KG,
    FALLBACK_RATE_PER_KG,
)


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculates great-circle distance between two points in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def calculate_individual_cost(
    weight_kg: int,
    farmer_lat: Optional[float],
    farmer_lng: Optional[float],
    destination: str,
) -> int:
    """
    Returns the individual transport cost for a farmer hiring an appropriate truck alone.
    This is the SOLO cost - hiring the entire vehicle yourself.
    
    Solo Cost = Base Fee + (Distance × (Fuel + Driver Wage per km))
    """
    if weight_kg <= 0:
        return 0

    if farmer_lat is not None and farmer_lng is not None and destination:
        mandi = get_mandi_coords(destination)
        if mandi:
            mandi_lat, mandi_lng = mandi
            distance_km = _haversine_km(farmer_lat, farmer_lng, mandi_lat, mandi_lng)
            v_class = get_vehicle_class_for_weight(weight_kg)
            
            # Solo transport = hiring the full vehicle
            # Driver needs to cover: fuel + their wage
            base_fee = v_class["base_fee"]
            fuel_per_km = v_class["fuel_cost_per_km"]
            driver_per_km = v_class["driver_cost_per_km"]
            
            # Total cost for hiring the truck solo
            cost = base_fee + (distance_km * (fuel_per_km + driver_per_km))
            
            # Enforce minimum rate floor (₹3/kg)
            floor_cost = weight_kg * MIN_RATE_PER_KG
            final_cost = max(round(cost), floor_cost)
            
            print(f"\n🚚 INDIVIDUAL COST CALCULATION:")
            print(f"   Weight: {weight_kg}kg")
            print(f"   Vehicle class: {v_class['name']}")
            print(f"   Distance: {round(distance_km, 2)}km")
            print(f"   Base fee: ₹{base_fee}")
            print(f"   Fuel rate: ₹{fuel_per_km}/km")
            print(f"   Driver wage rate: ₹{driver_per_km}/km")
            print(f"   Calculated: {base_fee} + ({round(distance_km, 2)} × {fuel_per_km + driver_per_km}) = ₹{round(cost)}")
            print(f"   Floor (₹3/kg): ₹{floor_cost}")
            print(f"   Final individual cost: ₹{final_cost}")
            
            return final_cost

    # Fallback when coordinates are missing or mandi is unmapped
    fallback = round(weight_kg * FALLBACK_RATE_PER_KG)
    print(f"\n⚠️  FALLBACK: No GPS/mandi, using ₹9/kg × {weight_kg}kg = ₹{fallback}")
    return fallback
