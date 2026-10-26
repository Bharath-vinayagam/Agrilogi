"""
Route Optimization API — integrated into KrishiBundle backend.

Pipeline:
  TomTom Matrix Routing v2 (traffic=live, travelMode=truck)
  -> OR-Tools CVRP (minimise travelTimeInSeconds)
  -> OSRM Route API (GeoJSON road geometry)

Endpoints:
  POST /api/route-optimization/cluster/{cluster_id}
      Fetches all orders in a cluster from Supabase and runs the full pipeline.
      Returns optimised route + comparison + geometry.

  POST /api/route-optimization/custom
      Custom payload — for testing or external integration.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from database.db import supabase_client
from services.osrm_service import get_route_geometry, OSRMError
from services.tomtom_service import (
    get_travel_time_matrix,
    TomTomError,
    TomTomKeyMissingError,
)
from services.route_optimizer import (
    optimize_route,
    baseline_route,
    individual_trips_baseline,
    CapacityViolationError,
    RoutingError,
)

router = APIRouter(prefix="/api/route-optimization", tags=["Route Optimization"])

TRUCK_CAPACITY_KG = 1100.0  # Standard cooperative truck

from services.mandi_config import MANDI_COORDS


def _resolve_mandi(destination: str, cluster_id: str, farmers: list) -> dict:
    """Return mandi lat/lng from known list, or fall back to farmer centroid."""
    key = destination.strip().lower()
    for k, v in MANDI_COORDS.items():
        if k in key or key in k:
            return {
                "mandi_id": f"mandi-{cluster_id}",
                "name":     v["name"],
                "latitude":  v["lat"],
                "longitude": v["lng"],
            }
    # Unknown mandi — use centroid of farmers as rough proxy
    avg_lat = sum(f["latitude"]  for f in farmers) / len(farmers)
    avg_lng = sum(f["longitude"] for f in farmers) / len(farmers)
    return {
        "mandi_id": f"mandi-{cluster_id}",
        "name":     destination,
        "latitude":  avg_lat + 0.3,
        "longitude": avg_lng + 0.3,
    }


# ── Pydantic models ────────────────────────────────────────────────────────

class FarmerInput(BaseModel):
    farmer_id: str
    name: str
    latitude: float
    longitude: float
    quantity_kg: float


class MandiInput(BaseModel):
    mandi_id: str
    name: str
    latitude: float
    longitude: float


class VehicleInput(BaseModel):
    vehicle_id: str
    capacity_kg: float


class CustomOptimizeRequest(BaseModel):
    farmers: List[FarmerInput]
    mandi: MandiInput
    vehicle: VehicleInput


# ── Pipeline ────────────────────────────────────────────────────────────────

def _run_pipeline(farmers: list, mandi: dict, vehicle: dict) -> dict:
    """
    Full optimization pipeline:
    1. Capacity pre-check
    2. TomTom Matrix → n×n travel-time matrix
    3. OR-Tools CVRP → optimised sequence
    4. Baseline (original order) → comparison
    5. OSRM → GeoJSON road geometry
    """
    total_demand = sum(f["quantity_kg"] for f in farmers)
    if total_demand > vehicle["capacity_kg"]:
        raise CapacityViolationError(
            f"Total bundle quantity ({total_demand} kg) exceeds "
            f"vehicle capacity ({vehicle['capacity_kg']} kg)."
        )

    # Location list: mandi at index 0, farmers at 1..n
    locations = [{"latitude": mandi["latitude"], "longitude": mandi["longitude"]}] + [
        {"latitude": f["latitude"], "longitude": f["longitude"]} for f in farmers
    ]

    tt_matrix       = get_travel_time_matrix(locations)
    duration_matrix = tt_matrix["durations"]
    distance_matrix = tt_matrix["distances"]
    delay_matrix    = tt_matrix["traffic_delays"]

    opt_result  = optimize_route(farmers, mandi, vehicle, duration_matrix, distance_matrix)
    base_result = individual_trips_baseline(farmers, duration_matrix, distance_matrix)
    seq_result  = baseline_route(farmers, mandi, duration_matrix, distance_matrix)

    ordered_locations = [
        {"latitude": step["latitude"], "longitude": step["longitude"]}
        for step in opt_result["route"]
    ]
    geometry_result = get_route_geometry(ordered_locations)

    # Traffic delay sum along optimised route
    route_nodes = []
    for step in opt_result["route"]:
        if step["type"] == "mandi":
            route_nodes.append(0)
        else:
            idx = next(
                i + 1 for i, f in enumerate(farmers) if f["farmer_id"] == step["id"]
            )
            route_nodes.append(idx)

    total_traffic_delay_s = sum(
        delay_matrix[route_nodes[k]][route_nodes[k + 1]]
        for k in range(len(route_nodes) - 1)
    )

    opt_dist_km  = opt_result["total_distance_m"] / 1000
    opt_dur_min  = opt_result["total_duration_s"] / 60
    base_dist_km = base_result["total_distance_m"] / 1000
    base_dur_min = base_result["total_duration_s"] / 60
    seq_dist_km  = seq_result["total_distance_m"] / 1000
    seq_dur_min  = seq_result["total_duration_s"] / 60

    def pct_saving(base, opt):
        return 0.0 if base == 0 else round((base - opt) / base * 100, 2)

    return {
        "cluster_id":                 None,  # set by caller
        "total_distance_km":          round(opt_dist_km, 3),
        "total_duration_minutes":     round(opt_dur_min, 2),
        "traffic_delay_minutes":      round(total_traffic_delay_s / 60, 2),
        "total_load_kg":              total_demand,
        "vehicle_capacity_kg":        vehicle["capacity_kg"],
        "capacity_utilization_percent": round(total_demand / vehicle["capacity_kg"] * 100, 2),
        "route":                      opt_result["route"],
        "geometry":                   geometry_result["geometry"],
        "comparison": {
            "label":                      "Individual Trips vs Consolidated Optimized Route",
            "original_distance_km":       round(base_dist_km, 3),
            "optimized_distance_km":      round(opt_dist_km, 3),
            "distance_saving_percent":    pct_saving(base_dist_km, opt_dist_km),
            "original_duration_minutes":  round(base_dur_min, 2),
            "optimized_duration_minutes": round(opt_dur_min, 2),
            "time_saving_percent":        pct_saving(base_dur_min, opt_dur_min),
            "sequential_distance_km":     round(seq_dist_km, 3),
            "sequential_duration_minutes": round(seq_dur_min, 2),
            "sequence_saving_percent":    pct_saving(seq_dist_km, opt_dist_km),
        },
    }


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/cluster/{cluster_id}")
def optimize_cluster(cluster_id: str, vehicle_capacity_kg: float = TRUCK_CAPACITY_KG):
    """
    Fetch all orders for a cluster from Supabase and run route optimization.
    Orders must have lat/lng coordinates.
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Database client not configured.")

    try:
        res = supabase_client.table("orders").select("*").eq("cluster_id", cluster_id).execute()
        orders = res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    if not orders:
        raise HTTPException(status_code=404, detail=f"No orders found for cluster {cluster_id}.")

    # Filter orders with GPS coordinates
    geo_orders = [o for o in orders if o.get("lat") and o.get("lng")]
    if not geo_orders:
        raise HTTPException(status_code=422, detail="No orders in this cluster have GPS coordinates.")

    # Build farmers list
    farmers = [
        {
            "farmer_id":   o["id"],
            "name":        o["farmer_name"],
            "latitude":    float(o["lat"]),
            "longitude":   float(o["lng"]),
            "quantity_kg": float(o["weight_kg"]),
        }
        for o in geo_orders
    ]

    # Use known mandi coordinates for accurate routing
    destination = orders[0].get("destination", "Mandi")
    mandi = _resolve_mandi(destination, cluster_id, farmers)

    vehicle = {"vehicle_id": "V001", "capacity_kg": vehicle_capacity_kg}

    try:
        result = _run_pipeline(farmers, mandi, vehicle)
        result["cluster_id"] = cluster_id

        # Save route_leg_km per order after optimization
        for step in result.get("route", []):
            if step.get("type") == "farmer" and "leg_km" in step:
                try:
                    supabase_client.table("orders").update({
                        "route_leg_km": step["leg_km"]
                    }).eq("id", step["id"]).execute()
                except Exception as e:
                    print(f"Error updating route_leg_km for order {step['id']}: {e}")

        return result
    except CapacityViolationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except TomTomKeyMissingError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except TomTomError as exc:
        raise HTTPException(status_code=502, detail=f"TomTom error: {exc}")
    except OSRMError as exc:
        raise HTTPException(status_code=502, detail=f"OSRM error: {exc}")
    except RoutingError as exc:
        raise HTTPException(status_code=500, detail=f"Routing error: {exc}")


@router.post("/custom")
def optimize_custom(body: CustomOptimizeRequest):
    """Custom payload optimization — for testing."""
    try:
        result = _run_pipeline(
            farmers=[f.model_dump() for f in body.farmers],
            mandi=body.mandi.model_dump(),
            vehicle=body.vehicle.model_dump(),
        )
        return result
    except CapacityViolationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except TomTomKeyMissingError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except TomTomError as exc:
        raise HTTPException(status_code=502, detail=f"TomTom error: {exc}")
    except OSRMError as exc:
        raise HTTPException(status_code=502, detail=f"OSRM error: {exc}")
    except RoutingError as exc:
        raise HTTPException(status_code=500, detail=f"Routing error: {exc}")
