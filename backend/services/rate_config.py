"""
services/rate_config.py

Single source of truth for vehicle class rates and minimum pricing floors.
"""

from typing import Dict, Any

VEHICLE_CLASSES: Dict[str, Dict[str, Any]] = {
    "mini": {
        "name": "mini",
        "capacity_kg": 500,
        "cost_per_km": 12,        # Farmer-side rate (what farmers pay per km share)
        "base_fee": 150,
        "fuel_cost_per_km": 8,    # Driver's actual diesel cost per km (mini truck / Tata Ace)
        "driver_cost_per_km": 2,  # Driver's own labour/earnings per km
    },
    "standard": {
        "name": "standard",
        "capacity_kg": 1100,
        "cost_per_km": 20,        # Farmer-side rate
        "base_fee": 250,
        "fuel_cost_per_km": 12,   # Driver's actual diesel cost per km (standard truck)
        "driver_cost_per_km": 3,  # Driver's own labour/earnings per km
    },
    "heavy": {
        "name": "heavy",
        "capacity_kg": 2500,
        "cost_per_km": 28,        # Farmer-side rate
        "base_fee": 400,
        "fuel_cost_per_km": 18,   # Driver's actual diesel cost per km (heavy truck)
        "driver_cost_per_km": 4,  # Driver's own labour/earnings per km
    },
}

# Absolute pricing floor: at least ₹3 per kg for individual solo transport
MIN_RATE_PER_KG: int = 3

# Shared cooperative pooling floor: ₹1.5 per kg (enables 25%-50% pooling savings)
SHARED_MIN_RATE_PER_KG: float = 1.5

# Fallback rate when GPS or mandi is unknown (3x floor)
FALLBACK_RATE_PER_KG: int = 9


def get_vehicle_class_for_weight(weight_kg: int) -> Dict[str, Any]:
    """
    Select the smallest vehicle class where capacity_kg >= weight_kg.
    If weight exceeds heavy class (2500kg), returns heavy class.
    """
    for v_class in ["mini", "standard", "heavy"]:
        cfg = VEHICLE_CLASSES[v_class]
        if weight_kg <= cfg["capacity_kg"]:
            return cfg
    return VEHICLE_CLASSES["heavy"]


def calculate_driver_trip_cost(distance_km: float, weight_kg: int) -> Dict[str, Any]:
    """
    Calculate a driver's actual trip cost breakdown for a given distance and load.
    All costs are distance-based — no flat daily wage.
    Returns fuel, driver earnings, total cost, and a suggested minimum bid.
    """
    v_class = get_vehicle_class_for_weight(weight_kg)
    fuel = round(distance_km * v_class["fuel_cost_per_km"])
    driver_earnings = round(distance_km * v_class["driver_cost_per_km"])
    total_cost = fuel + driver_earnings
    # Suggested bid: cost + 20% margin for profit
    suggested_min = round(total_cost * 1.2)
    suggested_max = round(total_cost * 1.5)
    return {
        "vehicle_class": v_class["name"],
        "distance_km": round(distance_km),
        "fuel_cost": fuel,
        "driver_earnings": driver_earnings,
        "total_driver_cost": total_cost,
        "suggested_bid_min": suggested_min,
        "suggested_bid_max": suggested_max,
    }
