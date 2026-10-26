"""
Route Optimizer — CVRP using Google OR-Tools.
Minimises sum of TomTom travelTimeInSeconds along the pickup route.
"""

from typing import List, Dict
from ortools.constraint_solver import pywrapcp, routing_enums_pb2


class CapacityViolationError(Exception):
    pass


class RoutingError(Exception):
    pass


def optimize_route(
    farmers: List[Dict],
    mandi: Dict,
    vehicle: Dict,
    duration_matrix: List[List[float]],
    distance_matrix: List[List[float]],
) -> Dict:
    """
    Solve CVRP and return optimised farmer pickup sequence.
    Node 0 = mandi (depot), nodes 1..n = farmers.
    """
    total_demand = sum(f["quantity_kg"] for f in farmers)
    capacity     = vehicle["capacity_kg"]

    if total_demand > capacity:
        raise CapacityViolationError(
            f"Total bundle quantity ({total_demand} kg) exceeds "
            f"vehicle capacity ({capacity} kg)."
        )

    n_nodes     = len(farmers) + 1
    depot_index = 0
    SCALE       = 1000

    int_duration = [[int(duration_matrix[i][j] * SCALE) for j in range(n_nodes)]
                    for i in range(n_nodes)]
    demands = [0] + [int(f["quantity_kg"]) for f in farmers]

    manager = pywrapcp.RoutingIndexManager(n_nodes, 1, depot_index)
    routing = pywrapcp.RoutingModel(manager)

    def duration_callback(from_index, to_index):
        return int_duration[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit_cb = routing.RegisterTransitCallback(duration_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_cb)

    def demand_callback(from_index):
        return demands[manager.IndexToNode(from_index)]

    demand_cb = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(demand_cb, 0, [int(capacity)], True, "Capacity")

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_params.time_limit.seconds = 10

    solution = routing.SolveWithParameters(search_params)
    if not solution:
        raise RoutingError("OR-Tools could not find a feasible route.")

    index         = routing.Start(0)
    ordered_nodes = []
    while not routing.IsEnd(index):
        ordered_nodes.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))
    ordered_nodes.append(manager.IndexToNode(index))

    route_steps  = []
    seq          = 1
    total_dist_m = 0.0
    total_dur_s  = 0.0

    for step_idx, node in enumerate(ordered_nodes):
        if node == depot_index:
            step = {
                "sequence":    seq,
                "type":        "mandi",
                "id":          mandi["mandi_id"],
                "name":        mandi["name"],
                "latitude":    mandi["latitude"],
                "longitude":   mandi["longitude"],
                "quantity_kg": None,
            }
        else:
            farmer = farmers[node - 1]
            step = {
                "sequence":    seq,
                "type":        "farmer",
                "id":          farmer["farmer_id"],
                "name":        farmer["name"],
                "latitude":    farmer["latitude"],
                "longitude":   farmer["longitude"],
                "quantity_kg": farmer["quantity_kg"],
            }

        leg_km = 0.0
        if step_idx > 0:
            prev = ordered_nodes[step_idx - 1]
            total_dist_m += distance_matrix[prev][node]
            total_dur_s  += duration_matrix[prev][node]
            leg_km = round(distance_matrix[prev][node] / 1000.0, 3)

        step["leg_km"] = leg_km
        route_steps.append(step)
        seq += 1

    return {
        "route":               route_steps,
        "total_distance_m":    total_dist_m,
        "total_duration_s":    total_dur_s,
        "total_load_kg":       total_demand,
        "vehicle_capacity_kg": capacity,
    }


def individual_trips_baseline(
    farmers: List[Dict],
    duration_matrix: List[List[float]],
    distance_matrix: List[List[float]],
) -> Dict:
    """
    Calculate baseline as unbundled individual direct trips.
    Each farmer makes an independent round-trip between Mandi and their farm:
    Mandi -> Farmer_i -> Mandi (the real-world baseline before KrishiBundle consolidation).
    Distinct farm locations are counted to avoid double-counting same-farmer orders.
    """
    total_dist_m = 0.0
    total_dur_s  = 0.0
    seen_locations = set()

    for i, farmer in enumerate(farmers, start=1):
        loc_key = (round(farmer["latitude"], 4), round(farmer["longitude"], 4))
        if loc_key in seen_locations:
            continue
        seen_locations.add(loc_key)
        total_dist_m += distance_matrix[0][i] + distance_matrix[i][0]
        total_dur_s  += duration_matrix[0][i] + duration_matrix[i][0]

    return {
        "total_distance_m": total_dist_m,
        "total_duration_s": total_dur_s,
    }


def baseline_route(
    farmers: List[Dict],
    mandi: Dict,
    duration_matrix: List[List[float]],
    distance_matrix: List[List[float]],
) -> Dict:
    """Visit farmers in original list order (comparison baseline)."""
    ordered_nodes = [0] + list(range(1, len(farmers) + 1)) + [0]
    route_steps   = []
    total_dist_m  = 0.0
    total_dur_s   = 0.0
    seq           = 1

    for step_idx, node in enumerate(ordered_nodes):
        if node == 0:
            step = {
                "sequence":    seq,
                "type":        "mandi",
                "id":          mandi["mandi_id"],
                "name":        mandi["name"],
                "latitude":    mandi["latitude"],
                "longitude":   mandi["longitude"],
                "quantity_kg": None,
            }
        else:
            farmer = farmers[node - 1]
            step = {
                "sequence":    seq,
                "type":        "farmer",
                "id":          farmer["farmer_id"]  ,
                "name":        farmer["name"],
                "latitude":    farmer["latitude"],
                "longitude":   farmer["longitude"],
                "quantity_kg": farmer["quantity_kg"],
            }
        route_steps.append(step)
        seq += 1

        if step_idx > 0:
            prev = ordered_nodes[step_idx - 1]
            total_dist_m += distance_matrix[prev][node]
            total_dur_s  += duration_matrix[prev][node]

    return {
        "route":            route_steps,
        "total_distance_m": total_dist_m,
        "total_duration_s": total_dur_s,
    }

