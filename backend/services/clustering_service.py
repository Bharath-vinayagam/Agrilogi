"""
services/clustering_service.py

Fixed-slot clustering: runs at 6:00 AM and 6:00 PM IST daily.
All Pending orders are grouped by geography (DBSCAN, 20km radius).

Same-farmer constraint: all orders from the same farmer_id are
always assigned to the same cluster — never split across trucks.

Slot schedule (IST = UTC+5:30):
  Slot A: 06:00 IST  →  00:30 UTC
  Slot B: 18:00 IST  →  12:30 UTC
"""

from datetime import datetime, timezone, timedelta
import time
import numpy as np
from sklearn.cluster import DBSCAN

from database.db import supabase_client
from services.compatibility_service import crops_are_compatible
from services.cost_allocation import allocate_cluster_costs
from services.destination_service import normalize_destination

IST = timezone(timedelta(hours=5, minutes=30))
SLOT_HOURS_IST = [6, 18]          # 6 AM and 6 PM IST
CLUSTER_RADIUS_KM = 20.0
EPS_RAD = CLUSTER_RADIUS_KM / 6371.0


def next_slot_time() -> datetime:
    """Return the next upcoming slot datetime in IST."""
    now_ist = datetime.now(IST)
    for hour in SLOT_HOURS_IST:
        slot = now_ist.replace(hour=hour, minute=0, second=0, microsecond=0)
        if slot > now_ist:
            return slot
    # Both slots passed today — next is first slot tomorrow
    tomorrow = now_ist + timedelta(days=1)
    return tomorrow.replace(hour=SLOT_HOURS_IST[0], minute=0, second=0, microsecond=0)


def slot_label(slot_dt: datetime) -> str:
    """Human readable slot label e.g. 'Today, 6:00 AM'"""
    now_ist = datetime.now(IST)
    day = "Today" if slot_dt.date() == now_ist.date() else "Tomorrow"
    # Use cross-platform formatting (%-I is Linux only, doesn't work on Windows)
    hour = slot_dt.strftime("%I").lstrip("0") or "12"
    minute = slot_dt.strftime("%M")
    ampm = slot_dt.strftime("%p")
    return f"{day}, {hour}:{minute} {ampm}"


def _persist_cluster(
    order_ids: list[str],
    cluster_id: str,
    slot_dt: datetime,
    farmer_costs: list[dict],
    destination: str = "Koyambedu Mandi",
    total_weight: int = 0
) -> None:
    """Update all orders in a cluster and persist bundle record for auctions."""
    if not supabase_client:
        return

    cost_map = {fc["order_id"]: fc.get("shared_cost", fc.get("bundled_cost", 0)) for fc in farmer_costs}
    leg_map = {fc["order_id"]: fc.get("leg_km", 0.0) for fc in farmer_costs}
    pickup = slot_label(slot_dt)
    total_savings = sum(fc.get("savings", 0) for fc in farmer_costs)
    truck_utilization = min(100, round((total_weight / 1100.0) * 100)) if total_weight > 0 else 0

    try:
        supabase_client.table("bundles").upsert({
            "id": cluster_id,
            "destination": destination,
            "total_weight_kg": total_weight,
            "truck_utilization": truck_utilization,
            "estimated_savings": total_savings,
            "spoilage_risk": "Low",
            "suggested_departure_time": pickup,
        }).execute()
    except Exception as e:
        print(f"Error persisting bundle {cluster_id}: {e}")

    for order_id in order_ids:
        try:
            result = supabase_client.table("orders").update({
                "status": "Cluster Forming",
                "cluster_id": cluster_id,
                "cluster_slot": slot_dt.isoformat(),
                "pickup_time": pickup,
                "shared_cost": cost_map.get(order_id, 0),
                "route_leg_km": leg_map.get(order_id, 0.0),
                "route_pass": "provisional",
            }).eq("id", order_id).execute()
            
            print(f"✅ Updated order {order_id}: shared_cost=₹{cost_map.get(order_id, 0)}, status='Cluster Forming'")
            
        except Exception as e:
            print(f"❌ Error persisting cluster for order {order_id}: {e}")


def _enforce_same_farmer_constraint(groups: dict[int, list]) -> dict[int, list]:
    """
    Ensure all orders from the same farmer_id end up in the same cluster.
    If a farmer's orders span multiple DBSCAN groups, merge those groups
    into the one that contains the majority of that farmer's orders.
    """
    # Build farmer_id → set of group labels
    farmer_groups: dict[str, set] = {}
    for label, orders in groups.items():
        for o in orders:
            fid = o.get("farmer_id") or o["id"]  # fallback to order id if no farmer_id
            if fid not in farmer_groups:
                farmer_groups[fid] = set()
            farmer_groups[fid].add(label)

    # For farmers split across groups, merge minority groups into majority
    for fid, labels in farmer_groups.items():
        if len(labels) <= 1:
            continue

        # Find the group with the most of this farmer's orders
        label_counts = {
            lbl: sum(1 for o in groups[lbl] if (o.get("farmer_id") or o["id"]) == fid)
            for lbl in labels
        }
        primary = max(label_counts, key=label_counts.get)

        # Move all this farmer's orders from minority groups into primary
        for lbl in labels:
            if lbl == primary:
                continue
            to_move = [o for o in groups[lbl] if (o.get("farmer_id") or o["id"]) == fid]
            groups[lbl] = [o for o in groups[lbl] if (o.get("farmer_id") or o["id"]) != fid]
            groups[primary].extend(to_move)
            if not groups[lbl]:
                del groups[lbl]
                break  # dict changed size, outer loop will re-check

    return groups


def build_clusters() -> list[dict]:
    """
    Run DBSCAN on all Pending orders, enforce same-farmer constraint,
    allocate costs, and persist results to Supabase.
    Called at each slot time (and manually via the admin endpoint).
    """
    if not supabase_client:
        return []

    try:
        response = supabase_client.table("orders").select("*").execute()
        orders = response.data
        if not orders:
            return []

        pending_orders = [o for o in orders if o["status"] in ("Pending", "Awaiting Cluster", "Cluster Forming")]
        if not pending_orders:
            print("No Pending, Awaiting Cluster, or Cluster Forming orders to cluster.")
            return []

        print(f"Clustering {len(pending_orders)} Pending orders...")

        # Group by normalized destination — farmers going to different markets never share a truck
        destination_groups: dict[str, list] = {}
        for o in pending_orders:
            dest = normalize_destination(o.get("destination") or "Unknown")
            key = dest.strip().lower()
            if key not in destination_groups:
                destination_groups[key] = []
            destination_groups[key].append(o)

        print(f"Found {len(destination_groups)} destination(s): {list(destination_groups.keys())}")

        all_groups: dict[int, list] = {}
        group_counter = 0

        for dest, dest_orders in destination_groups.items():
            dest_groups: dict[int, list] = {}
            geo_orders = [o for o in dest_orders if o.get("lat") and o.get("lng")]
            no_geo_orders = [o for o in dest_orders if not o.get("lat") or not o.get("lng")]

            if geo_orders:
                coords_rad = np.radians([[float(o["lat"]), float(o["lng"])] for o in geo_orders])
                db = DBSCAN(
                    eps=EPS_RAD,
                    min_samples=1,
                    algorithm="ball_tree",
                    metric="haversine",
                ).fit(coords_rad)

                for idx, label in enumerate(db.labels_):
                    if label not in dest_groups:
                        dest_groups[label] = []
                    dest_groups[label].append(geo_orders[idx])

            # Orders without GPS coords each get a solo group
            next_label = (max(dest_groups.keys()) + 1) if dest_groups else 0
            for order in no_geo_orders:
                dest_groups[next_label] = [order]
                next_label += 1
                print(f"Order {order['id']} (no coords, dest={dest}) -> solo cluster")

            # Enforce same-farmer constraint WITHIN this destination
            dest_groups = _enforce_same_farmer_constraint(dest_groups)

            # Assign global group counters
            for _, grp_orders in dest_groups.items():
                all_groups[group_counter] = grp_orders
                group_counter += 1

        groups = all_groups

        slot_dt = next_slot_time()
        clusters = []

        run_tag = int(time.time()) % 100000
        for label, group_orders in groups.items():
            cluster_id = f"CL-{slot_dt.strftime('%m%d')}-{run_tag}-{label}"
            order_ids = [o["id"] for o in group_orders]
            crops = [o["crop"] for o in group_orders]
            villages = list(set(o["village"] for o in group_orders))
            total_weight = sum(int(o["weight_kg"]) for o in group_orders)
            dest = group_orders[0].get("destination") or "Koyambedu Mandi"
            allocation = allocate_cluster_costs(group_orders, dest)
            _persist_cluster(
                order_ids,
                cluster_id,
                slot_dt,
                allocation["farmer_costs"],
                destination=dest,
                total_weight=total_weight
            )

            clusters.append({
                "id": cluster_id,
                "villages": villages,
                "destination": list(set(o.get("destination", "Unknown") for o in group_orders))[0],
                "total_weight_kg": total_weight,
                "compatible": crops_are_compatible(crops),
                "farmers": len(set(o.get("farmer_id") or o["id"] for o in group_orders)),
                "orders": len(group_orders),
                "pickup_time": slot_label(slot_dt),
                "total_distance_km": allocation["total_distance_km"],
                "total_bundle_cost": allocation["total_bundle_cost"],
                "farmer_costs": allocation["farmer_costs"],
            })

            print(f"Cluster {cluster_id}: {len(group_orders)} orders, {villages}, pickup {slot_label(slot_dt)}")

        return clusters

    except Exception as e:
        print(f"Error building clusters: {e}")
        return []
