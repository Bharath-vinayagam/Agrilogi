from database.db import supabase_client
from models.schemas import BidCreate


def list_bids() -> list[dict]:
    if not supabase_client:
        return []
    try:
        response = supabase_client.table("bids").select("*").execute()
        bids = []
        for row in response.data:
            bids.append({
                "id": row["id"],
                "driver_name": row["driver_name"],
                "vehicle": row["vehicle"],
                "amount": row["amount"],
                "reliability_score": row["reliability_score"],
                "status": row["status"]
            })
        return sorted(bids, key=lambda bid: (int(bid["amount"]), -int(bid["reliability_score"])))
    except Exception as e:
        print(f"Error listing bids: {e}")
        return []


def create_bid(payload: BidCreate) -> dict:
    if not supabase_client:
        return {}
    try:
        count_res = supabase_client.table("bids").select("id", count="exact").execute()
        count = count_res.count if count_res.count is not None else 0
        bid_id = f"B{801 + count}"
        
        bid_row = {
            "id": bid_id,
            "driver_name": payload.driver_name,
            "vehicle": payload.vehicle,
            "amount": payload.amount,
            "reliability_score": payload.reliability_score,
            "status": "Open"
        }
        
        insert_res = supabase_client.table("bids").insert(bid_row).execute()
        return insert_res.data[0]
    except Exception as e:
        print(f"Error creating bid: {e}")
        return {}


def on_bid_accepted(bid_id: str) -> dict:
    """
    Pass 2: Final Cost Reallocation and Atomic Assignment when bid is accepted.
    1. Validates vehicle capacity >= cluster_total_weight.
    2. Reallocates costs across orders using winning_bid_amount (70% weight, 30% leg distance).
    3. Atomically updates orders (shared_cost, route_pass='final', status='Driver Assigned').
    4. Sets winning bid status='Accepted' and competing bids='Rejected'.
    """
    if not supabase_client:
        return {"success": False, "error": "Database not configured"}

    try:
        # Fetch bid
        bid_res = supabase_client.table("bids").select("*").eq("id", bid_id).execute()
        if not bid_res.data:
            return {"success": False, "error": f"Bid {bid_id} not found"}
        
        winning_bid = bid_res.data[0]
        bundle_id = winning_bid.get("bundle_id")
        driver_name = winning_bid["driver_name"]
        winning_amount = int(winning_bid["amount"])
        vehicle_type = winning_bid.get("vehicle", "Standard")

        # Map vehicle type to capacity
        v_type_lower = vehicle_type.lower()
        if "mini" in v_type_lower:
            vehicle_capacity = 500
        elif "heavy" in v_type_lower or "2500" in v_type_lower:
            vehicle_capacity = 2500
        else:
            vehicle_capacity = 1100

        # Fetch orders for this cluster/bundle
        if bundle_id:
            orders_res = supabase_client.table("orders").select("*").eq("cluster_id", bundle_id).execute()
        else:
            # Fallback to pending/active orders if bundle_id not set
            orders_res = supabase_client.table("orders").select("*").in_("status", ["Pending", "Cluster Forming"]).execute()

        orders = orders_res.data or []
        if not orders:
            return {"success": False, "error": "No orders found to allocate"}

        cluster_total_weight = sum(int(o.get("weight_kg", 0)) for o in orders)

        # Capacity check
        if vehicle_capacity < cluster_total_weight:
            return {
                "success": False,
                "error": f"Capacity violation: Vehicle capacity ({vehicle_capacity}kg) is less than cluster total weight ({cluster_total_weight}kg)"
            }

        # Pass 2: Reallocate costs based on winning bid amount
        from services.cost_allocation import reallocate_final_costs
        reallocations = reallocate_final_costs(orders, winning_amount)
        realloc_map = {r["order_id"]: r["shared_cost"] for r in reallocations}

        # Atomic DB updates for orders
        for o in orders:
            oid = o["id"]
            allocated_cost = realloc_map.get(oid, o.get("shared_cost", 0))
            supabase_client.table("orders").update({
                "shared_cost": allocated_cost,
                "final_cost": allocated_cost,
                "assigned_vehicle_capacity_kg": vehicle_capacity,
                "route_pass": "final",
                "status": "Driver Assigned",
                "assigned_driver": driver_name,
            }).eq("id", oid).execute()

        # Update winning bid
        supabase_client.table("bids").update({"status": "Accepted"}).eq("id", bid_id).execute()

        # Update competing bids to Rejected
        if bundle_id:
            supabase_client.table("bids").update({"status": "Rejected"}).eq("bundle_id", bundle_id).neq("id", bid_id).execute()

        return {
            "success": True,
            "bid_id": bid_id,
            "driver_name": driver_name,
            "winning_amount": winning_amount,
            "vehicle_capacity_kg": vehicle_capacity,
            "orders_updated": len(orders),
            "reallocations": reallocations,
        }

    except Exception as e:
        print(f"Error in on_bid_accepted: {e}")
        return {"success": False, "error": str(e)}


