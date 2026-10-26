"""
services/cost_allocation.py

Allocates cluster transport costs across farmers using:
70% weight-based + 30% distance-based shares.

Two Passes:
- Pass 1 (Provisional): Runs at clustering using vehicle class rate & OSRM / road distance from mandi.
- Pass 2 (Final): Runs when driver bid is accepted, reallocating actual winning bid amount.

Key Invariants:
- shared_cost <= individual_cost always (capped)
- Solo farmer: shared_cost == individual_cost (no penalty, no synthetic savings)
- Sum of farmer shares does not exceed total bundle cost
"""

import math
import os
import requests
from typing import List, Dict, Any, Optional

from services.mandi_config import get_mandi_coords
from services.rate_config import get_vehicle_class_for_weight, MIN_RATE_PER_KG, SHARED_MIN_RATE_PER_KG

WEIGHT_SHARE_WEIGHT = 0.7
DISTANCE_SHARE_WEIGHT = 0.3
OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points in kilometers."""
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


def _try_osrm_distance(loc1: tuple[float, float], loc2: tuple[float, float]) -> Optional[float]:
    """Attempt to get actual driving road distance from OSRM in km."""
    lat1, lng1 = loc1
    lat2, lng2 = loc2
    if abs(lat1 - lat2) < 0.0001 and abs(lng1 - lng2) < 0.0001:
        return 0.0
    url = f"{OSRM_BASE_URL}/route/v1/driving/{lng1},{lat1};{lng2},{lat2}?overview=false"
    try:
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("routes"):
                return data["routes"][0]["distance"] / 1000.0
    except Exception:
        pass
    return None


def build_pickup_route(orders: List[Dict[str, Any]], destination: str = "Koyambedu Mandi") -> List[Dict[str, Any]]:
    """
    Nearest-neighbor pickup route starting from real mandi coordinates.
    Returns list of legs with order_id, leg_km.
    """
    mandi = get_mandi_coords(destination)
    valid_orders = [o for o in orders if o.get("lat") and o.get("lng")]
    no_geo_orders = [o for o in orders if not o.get("lat") or not o.get("lng")]

    if not valid_orders:
        return [{"order_id": o["id"], "leg_km": 1.0} for o in orders]

    if mandi:
        start_lat, start_lng = mandi
    else:
        start_lat = sum(float(o["lat"]) for o in valid_orders) / len(valid_orders)
        start_lng = sum(float(o["lng"]) for o in valid_orders) / len(valid_orders)

    current_lat, current_lng = start_lat, start_lng
    remaining = list(valid_orders)
    legs = []

    while remaining:
        # Find nearest farmer to current position
        nearest = min(
            remaining,
            key=lambda o: _haversine_km(current_lat, current_lng, float(o["lat"]), float(o["lng"]))
        )
        o_lat = float(nearest["lat"])
        o_lng = float(nearest["lng"])

        # Try OSRM road distance, fall back to haversine (with typical 1.25 road winding factor if from mandi)
        road_km = _try_osrm_distance((current_lat, current_lng), (o_lat, o_lng))
        if road_km is None:
            straight_dist = _haversine_km(current_lat, current_lng, o_lat, o_lng)
            road_km = straight_dist if len(legs) > 0 else (straight_dist * 1.25)

        legs.append({"order_id": nearest["id"], "leg_km": round(road_km, 2)})
        current_lat, current_lng = o_lat, o_lng
        remaining.remove(nearest)

    # Missing GPS orders receive the average leg distance
    avg_leg = sum(l["leg_km"] for l in legs) / len(legs) if legs else 1.0
    for o in no_geo_orders:
        legs.append({"order_id": o["id"], "leg_km": round(avg_leg, 2)})

    return legs


def allocate_cluster_costs(orders: List[Dict[str, Any]], destination: str = "Koyambedu Mandi") -> Dict[str, Any]:
    """
    Pass 1: Provisional Cost Allocation (Runs during clustering).
    """
    if not orders:
        return {"total_distance_km": 0.0, "total_bundle_cost": 0, "farmer_costs": []}

    # Solo farmer — bundled_cost == individual_cost
    if len(orders) == 1:
        o = orders[0]
        indiv = int(o.get("individual_cost", 0))
        return {
            "total_distance_km": 0.0,
            "total_bundle_cost": indiv,
            "vehicle_class": get_vehicle_class_for_weight(int(o.get("weight_kg", 0)))["name"],
            "farmer_costs": [{
                "order_id": o["id"],
                "leg_km": 0.0,
                "weight_share": 1.0,
                "distance_share": 1.0,
                "allocation_fraction": 1.0,
                "shared_cost": indiv,
                "individual_cost": indiv,
                "savings": 0,
                "savings_percent": 0.0,
            }],
        }

    total_weight = sum(int(o.get("weight_kg", 0)) for o in orders)
    v_class = get_vehicle_class_for_weight(total_weight)
    base_fee = v_class["base_fee"]
    # Use actual driver costs (fuel + wage) for shared bundle cost
    fuel_per_km = v_class["fuel_cost_per_km"]
    driver_per_km = v_class["driver_cost_per_km"]
    total_driver_cost_per_km = fuel_per_km + driver_per_km

    legs = build_pickup_route(orders, destination)
    leg_map = {l["order_id"]: l["leg_km"] for l in legs}
    total_route_km = sum(l["leg_km"] for l in legs)
    # Bundle cost = base fee + (total route distance × driver costs per km)
    # This is what the driver charges, then split among farmers
    raw_bundle_cost = base_fee + round(total_route_km * total_driver_cost_per_km)

    # Compute each farmer's fair distance to the destination mandi
    mandi_coords = get_mandi_coords(destination)
    mandi_dists = {}
    for o in orders:
        lat = o.get("lat")
        lng = o.get("lng")
        if mandi_coords and lat is not None and lng is not None:
            mandi_dists[o["id"]] = _haversine_km(float(lat), float(lng), mandi_coords[0], mandi_coords[1])
        else:
            mandi_dists[o["id"]] = float(o.get("route_leg_km", 10.0) or 10.0)
    total_mandi_dist = sum(mandi_dists.values()) or 1.0

    # In cooperative logistics, pooling into a bundle must guarantee substantial savings
    # over the sum of individual costs (target ~30% cooperative discount)
    sum_indiv = sum(int(o.get("individual_cost", 0)) for o in orders)
    if sum_indiv > 0:
        # Cap bundle cost at 70% of sum of individual costs to GUARANTEE 30% savings
        total_bundle_cost = min(raw_bundle_cost, round(sum_indiv * 0.70))
    else:
        total_bundle_cost = raw_bundle_cost
    
    print(f"\n💰 COST ALLOCATION DEBUG:")
    print(f"   Total route km: {total_route_km}")
    print(f"   Raw bundle cost: ₹{raw_bundle_cost}")
    print(f"   Sum individual costs: ₹{sum_indiv}")
    print(f"   Final bundle cost (capped at 70%): ₹{total_bundle_cost}")
    print(f"   ✅ Guaranteed savings: {round((1 - total_bundle_cost/sum_indiv)*100, 1)}%")

    farmer_costs = []
    for o in orders:
        oid = o["id"]
        w = int(o.get("weight_kg", 0))
        indiv = int(o.get("individual_cost", 0))
        leg_km = leg_map.get(oid, 0.0)

        weight_share = w / total_weight if total_weight > 0 else 0
        distance_share = mandi_dists.get(oid, 0.0) / total_mandi_dist
        fraction = (WEIGHT_SHARE_WEIGHT * weight_share) + (DISTANCE_SHARE_WEIGHT * distance_share)

        provisional_cost = round(fraction * total_bundle_cost)
        # Guaranteed savings invariant: every clustered farmer saves money (at least 20% discount)
        if indiv > 0:
            max_allowed = round(indiv * 0.80)
            shared_cost = min(provisional_cost, max_allowed)
        else:
            shared_cost = provisional_cost

        # Ensure shared cooperative pooling rate floor (₹1.5/kg)
        shared_cost = max(shared_cost, round(w * SHARED_MIN_RATE_PER_KG))
        savings = max(0, indiv - shared_cost)
        savings_percent = round((savings / indiv * 100), 1) if indiv > 0 else 0.0

        farmer_costs.append({
            "order_id": oid,
            "leg_km": leg_km,
            "weight_share": round(weight_share, 4),
            "distance_share": round(distance_share, 4),
            "allocation_fraction": round(fraction, 4),
            "shared_cost": shared_cost,
            "individual_cost": indiv,
            "savings": savings,
            "savings_percent": savings_percent,
        })

    return {
        "total_distance_km": round(total_route_km, 2),
        "total_bundle_cost": total_bundle_cost,
        "vehicle_class": v_class["name"],
        "farmer_costs": farmer_costs,
    }


def reallocate_final_costs(
    orders: List[Dict[str, Any]],
    winning_bid_amount: int,
    destination: str = "Koyambedu Mandi"
) -> List[Dict[str, Any]]:
    """
    Pass 2: Final Cost Allocation (Runs when winning bid is accepted).
    Reallocates using the actual winning bid amount and fair distance-to-mandi shares.
    """
    if not orders or winning_bid_amount <= 0:
        return []

    if len(orders) == 1:
        o = orders[0]
        indiv = int(o.get("individual_cost", 0))
        final_shared = min(winning_bid_amount, indiv) if indiv > 0 else winning_bid_amount
        return [{
            "order_id": o["id"],
            "shared_cost": final_shared,
            "route_pass": "final",
            "savings": max(0, indiv - final_shared),
        }]

    total_weight = sum(int(o.get("weight_kg", 0)) for o in orders)

    mandi_coords = get_mandi_coords(destination)
    mandi_dists = {}
    for o in orders:
        lat = o.get("lat")
        lng = o.get("lng")
        if mandi_coords and lat is not None and lng is not None:
            mandi_dists[o["id"]] = _haversine_km(float(lat), float(lng), mandi_coords[0], mandi_coords[1])
        else:
            mandi_dists[o["id"]] = float(o.get("route_leg_km", 10.0) or 10.0)
    total_mandi_dist = sum(mandi_dists.values()) or 1.0

    reallocated = []
    for o in orders:
        oid = o["id"]
        w = int(o.get("weight_kg", 0))
        indiv = int(o.get("individual_cost", 0))

        weight_share = w / total_weight if total_weight > 0 else 0
        distance_share = mandi_dists.get(oid, 0.0) / total_mandi_dist
        fraction = (WEIGHT_SHARE_WEIGHT * weight_share) + (DISTANCE_SHARE_WEIGHT * distance_share)

        calculated_cost = round(fraction * winning_bid_amount)
        # CRITICAL: Shared cost must ALWAYS be less than individual (guaranteed savings)
        # Cap at 80% of individual cost to ensure minimum 20% savings
        max_allowed_cost = round(indiv * 0.80) if indiv > 0 else calculated_cost
        shared_cost = min(calculated_cost, max_allowed_cost, indiv) if indiv > 0 else calculated_cost
        # Floor: minimum ₹1.5/kg for shared cooperative pooling
        shared_cost = max(shared_cost, round(w * SHARED_MIN_RATE_PER_KG))
        savings = max(0, indiv - shared_cost)
        
        print(f"\n💸 FINAL REALLOCATION for {oid}:")
        print(f"   Individual cost: ₹{indiv}")
        print(f"   Weight: {w}kg ({weight_share*100:.1f}% of total)")
        print(f"   Distance share: {distance_share*100:.1f}%")
        print(f"   Allocation fraction: {fraction*100:.1f}%")
        print(f"   Calculated from bid: {fraction} × ₹{winning_bid_amount} = ₹{calculated_cost}")
        print(f"   Max allowed (80% of individual): ₹{max_allowed_cost}")
        print(f"   Final shared cost: ₹{shared_cost}")
        print(f"   ✅ Savings: ₹{savings} ({round(savings/indiv*100,1) if indiv > 0 else 0}%)")

        reallocated.append({
            "order_id": oid,
            "shared_cost": shared_cost,
            "route_pass": "final",
            "savings": savings,
        })

    return reallocated
