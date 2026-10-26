"""
Slot Bidding Routes - Handle time slot specific bidding
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

from database.db import supabase_client

router = APIRouter()


class SlotBidCreate(BaseModel):
    """Request model for creating a slot bid"""
    driver_id: str
    driver_name: str
    pickup_date: date
    pickup_slot: str  # morning, afternoon, evening
    amount: int  # Changed to int to match DB column type (INTEGER)
    vehicle: str
    reliability_score: Optional[int] = 94


class SlotBid(BaseModel):
    """Response model for slot bid"""
    id: str
    driver_id: Optional[str] = None  # Made optional since it can be NULL
    driver_name: str
    pickup_date: Optional[date] = None  # Made optional for order bids
    pickup_slot: Optional[str] = None  # Made optional for order bids
    amount: int  # Changed to int to match DB column type (INTEGER)
    vehicle: str
    reliability_score: int
    bid_type: str
    status: str
    created_at: datetime


@router.post("/slot", response_model=SlotBid)
def create_slot_bid(payload: SlotBidCreate):
    """
    Create a bid for a specific time slot (date + slot combination).
    Drivers bid on all orders within that time slot as a bundle.
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Database client not configured")
    
    try:
        # Validate slot value
        if payload.pickup_slot not in ["morning", "afternoon", "evening"]:
            raise HTTPException(status_code=400, detail="Invalid pickup_slot. Must be: morning, afternoon, or evening")
        
        # Check if slot bidding has already closed
        from services.slot_bid_closer import should_close_slot
        if should_close_slot(payload.pickup_date.isoformat(), payload.pickup_slot):
            raise HTTPException(status_code=400, detail=f"Bidding for {payload.pickup_date} {payload.pickup_slot} slot has already closed.")
        
        # Check if orders exist for this slot
        orders_response = supabase_client.table("orders").select("id").eq("pickup_date", payload.pickup_date.isoformat()).eq("pickup_slot", payload.pickup_slot).in_("status", ["Pending", "Cluster Forming"]).execute()
        
        if not orders_response.data or len(orders_response.data) == 0:
            raise HTTPException(status_code=404, detail=f"No available orders for {payload.pickup_date} {payload.pickup_slot} slot")
        
        # Generate bid ID
        bid_id = f"SB-{int(datetime.now().timestamp() * 1000)}"
        
        # Insert bid record
        # driver_id can be NULL per schema (references drivers(id) on delete set null)
        # We rely on driver_name for display, not the foreign key
        bid_data = {
            "id": bid_id,
            "driver_id": None,  # NULL is allowed by schema
            "driver_name": payload.driver_name,
            "pickup_date": payload.pickup_date.isoformat(),
            "pickup_slot": payload.pickup_slot,
            "amount": int(payload.amount),
            "vehicle": payload.vehicle,
            "reliability_score": int(payload.reliability_score),
            "bid_type": "slot",
            "status": "Open",
            "bundle_id": None
        }
        
        insert_response = supabase_client.table("bids").insert(bid_data).execute()
        
        if not insert_response.data:
            raise HTTPException(status_code=500, detail="Failed to create slot bid")
        
        row = insert_response.data[0]
        
        return SlotBid(
            id=row["id"],
            driver_id=row.get("driver_id"),  # Can be None
            driver_name=row["driver_name"],
            pickup_date=datetime.fromisoformat(row["pickup_date"]).date(),
            pickup_slot=row["pickup_slot"],
            amount=row["amount"],  # Use amount (matches DB column)
            vehicle=row["vehicle"],
            reliability_score=row["reliability_score"],
            bid_type=row["bid_type"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating slot bid: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/slot/{pickup_date}/{pickup_slot}")
def get_slot_bids(pickup_date: str, pickup_slot: str):
    """
    Get all bids for a specific time slot (date + slot combination).
    Returns bids sorted by amount (lowest first).
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Database client not configured")
    
    try:
        # Validate slot value
        if pickup_slot not in ["morning", "afternoon", "evening"]:
            raise HTTPException(status_code=400, detail="Invalid pickup_slot. Must be: morning, afternoon, or evening")
        
        # Query bids for this slot
        response = supabase_client.table("bids").select("*").eq("pickup_date", pickup_date).eq("pickup_slot", pickup_slot).eq("bid_type", "slot").order("amount", desc=False).execute()
        
        bids = []
        for row in response.data:
            bids.append({
                "id": row["id"],
                "driver_id": row.get("driver_id"),  # Can be None
                "driver_name": row["driver_name"],
                "pickup_date": row["pickup_date"],
                "pickup_slot": row["pickup_slot"],
                "amount": row["amount"],  # Use amount (matches DB column)
                "vehicle": row["vehicle"],
                "reliability_score": row["reliability_score"],
                "bid_type": row["bid_type"],
                "status": row["status"],
                "created_at": row["created_at"]
            })
        
        return bids
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching slot bids: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/slot/summary")
def get_all_slot_bids_summary():
    """
    Get summary of all slot bids grouped by date and slot.
    Useful for analytics and monitoring.
    """
    if not supabase_client:
        return []
    
    try:
        from collections import defaultdict
        
        # Get all slot bids
        response = supabase_client.table("bids").select("*").eq("bid_type", "slot").execute()
        
        # Group by date and slot
        summary = defaultdict(lambda: defaultdict(lambda: {
            "bid_count": 0,
            "lowest_bid": None,
            "highest_bid": None,
            "avg_bid": 0,
            "bids": []
        }))
        
        for row in response.data:
            pickup_date = row["pickup_date"]
            pickup_slot = row["pickup_slot"]
            amount = row["amount"]  # Use amount (matches DB column)
            
            slot_data = summary[pickup_date][pickup_slot]
            slot_data["bid_count"] += 1
            slot_data["bids"].append(amount)
            
            if slot_data["lowest_bid"] is None or amount < slot_data["lowest_bid"]:
                slot_data["lowest_bid"] = amount
            if slot_data["highest_bid"] is None or amount > slot_data["highest_bid"]:
                slot_data["highest_bid"] = amount
        
        # Calculate averages and format result
        result = []
        for pickup_date in sorted(summary.keys()):
            for pickup_slot in ["morning", "afternoon", "evening"]:
                if pickup_slot in summary[pickup_date]:
                    slot_data = summary[pickup_date][pickup_slot]
                    slot_data["avg_bid"] = sum(slot_data["bids"]) / len(slot_data["bids"]) if slot_data["bids"] else 0
                    del slot_data["bids"]  # Remove raw bids list
                    
                    result.append({
                        "date": pickup_date,
                        "slot": pickup_slot,
                        **slot_data
                    })
        
        return result
        
    except Exception as e:
        print(f"Error getting slot bids summary: {e}")
        return []


@router.get("/slot/status/{pickup_date}/{pickup_slot}")
def get_slot_status(pickup_date: str, pickup_slot: str):
    """
    Get the status of a specific slot including:
    - Whether bidding is still open
    - When it closes
    - Current winning bid
    - Time remaining until close
    """
    try:
        from services.slot_bid_closer import should_close_slot, get_winning_bid, get_slot_closing_time
        from datetime import datetime
        
        # Check if slot should be closed
        should_close = should_close_slot(pickup_date, pickup_slot)
        
        # Get closing time
        closing_time = get_slot_closing_time(pickup_date, pickup_slot)
        
        # Get current winning bid
        winning_bid = get_winning_bid(pickup_date, pickup_slot)
        
        # Calculate time remaining
        from services.slot_bid_closer import IST
        now = datetime.now(IST)
        time_remaining = None
        if closing_time and closing_time > now:
            diff = closing_time - now
            hours = int(diff.total_seconds() // 3600)
            minutes = int((diff.total_seconds() % 3600) // 60)
            time_remaining = f"{hours}h {minutes}m"
        
        status = {
            "slot_date": pickup_date,
            "slot_time": pickup_slot,
            "bidding_open": not should_close,
            "should_close": should_close,
            "closing_time": closing_time.isoformat() if closing_time else None,
            "time_remaining": time_remaining,
            "current_winner": {
                "driver_name": winning_bid["driver_name"],
                "amount": winning_bid["amount"],
                "bid_id": winning_bid["id"]
            } if winning_bid else None
        }
        
        return status
        
    except Exception as e:
        print(f"Error getting slot status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/slot/close/{pickup_date}/{pickup_slot}")
def manually_close_slot(pickup_date: str, pickup_slot: str):
    """
    Manually close a slot and assign winner (admin/testing use).
    Bypasses automatic time-based closing.
    """
    try:
        from services.slot_bid_closer import close_slot_and_assign_winner
        
        result = close_slot_and_assign_winner(pickup_date, pickup_slot)
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "Failed to close slot"))
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error manually closing slot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class OrderBidCreate(BaseModel):
    """Request model for creating an order-level bid"""
    driver_id: str
    driver_name: str
    order_id: str
    amount: int
    vehicle: str
    reliability_score: Optional[int] = 94


@router.post("/order", response_model=SlotBid)
def create_order_bid(payload: OrderBidCreate):
    """
    DEPRECATED: Order-level bidding is disabled to prevent conflicts.
    
    Drivers should bid on CLUSTERS after clustering completes, not on individual orders.
    
    Why disabled:
    - Prevents conflicts when orders get clustered together
    - Example: Driver bids on KB1040 and KB1041 separately, then they cluster into CL-1021-21338-0
    - Result: Assignment conflicts and capacity issues
    
    Use /cluster endpoint instead to bid on formed clusters.
    """
    raise HTTPException(
        status_code=410, 
        detail="Order-level bidding is disabled. Please bid on clusters after clustering completes. Use POST /api/bids/cluster endpoint instead."
    )
    
    # OLD IMPLEMENTATION KEPT FOR REFERENCE (DO NOT UNCOMMENT)
    # if not supabase_client:
    #     raise HTTPException(status_code=500, detail="Database client not configured")
    # 
    # try:
    #     # Check if order exists
    #     order_response = supabase_client.table("orders").select("*").eq("id", payload.order_id).execute()
    #     
    #     if not order_response.data or len(order_response.data) == 0:
    #         raise HTTPException(status_code=404, detail=f"Order {payload.order_id} not found")
    #     
    #     order = order_response.data[0]
    #     
    #     # Check if order is still open for bidding
    #     if order["status"] not in ["Pending", "Cluster Forming"]:
    #         raise HTTPException(status_code=400, detail=f"Order {payload.order_id} is not available for bidding (status: {order['status']})")
    #     
    #     # Check if slot bidding has already closed
    #     from services.slot_bid_closer import should_close_slot
    #     if order.get("pickup_date") and order.get("pickup_slot"):
    #         if should_close_slot(order["pickup_date"], order["pickup_slot"]):
    #             raise HTTPException(status_code=400, detail=f"Bidding for this slot ({order['pickup_date']} {order['pickup_slot']}) has already closed.")
    #     
    #     # Check if driver already bid on this order
    #     existing_bid = supabase_client.table("bids").select("id").eq("driver_name", payload.driver_name).eq("order_id", payload.order_id).eq("bid_type", "order").execute()
    #     
    #     if existing_bid.data and len(existing_bid.data) > 0:
    #         raise HTTPException(status_code=400, detail=f"You have already bid on order {payload.order_id}")
    #     
    #     # Check capacity using dynamic calculation (at pickup time)
    #     from services.capacity_service import can_bid_on_order
    #     capacity_check = can_bid_on_order(
    #         payload.driver_name, 
    #         order["weight_kg"],
    #         order.get("pickup_date"),
    #         order.get("pickup_slot")
    #     )
    #     
    #     if not capacity_check["can_bid"]:
    #         raise HTTPException(
    #             status_code=400, 
    #             detail=f"Cannot bid: {capacity_check['reason']}"
    #         )
    #     
    #     # Generate bid ID
    #     bid_id = f"OB-{int(datetime.now().timestamp() * 1000)}"
    #     
    #     # Insert bid record
    #     bid_data = {
    #         "id": bid_id,
    #         "driver_id": None,
    #         "driver_name": payload.driver_name,
    #         "order_id": payload.order_id,
    #         "pickup_date": order.get("pickup_date"),
    #         "pickup_slot": order.get("pickup_slot"),
    #         "amount": int(payload.amount),
    #         "vehicle": payload.vehicle,
    #         "reliability_score": int(payload.reliability_score),
    #         "bid_type": "order",
    #         "status": "Open",
    #         "bundle_id": None
    #     }
    #     
    #     insert_response = supabase_client.table("bids").insert(bid_data).execute()
    #     
    #     if not insert_response.data:
    #         raise HTTPException(status_code=500, detail="Failed to create order bid")
    #     
    #     row = insert_response.data[0]
    #     
    #     return SlotBid(
    #         id=row["id"],
    #         driver_id=row.get("driver_id"),
    #         driver_name=row["driver_name"],
    #         pickup_date=datetime.fromisoformat(row["pickup_date"]).date() if row.get("pickup_date") and isinstance(row.get("pickup_date"), str) and len(row.get("pickup_date")) > 8 else None,
    #         pickup_slot=row.get("pickup_slot"),
    #         amount=row["amount"],
    #         vehicle=row["vehicle"],
    #         reliability_score=row["reliability_score"],
    #         bid_type=row["bid_type"],
    #         status=row["status"],
    #         created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
    #     )


@router.post("/order/close/{order_id}")
def manually_close_order(order_id: str):
    """
    Manually close bidding for a specific order and assign the winning driver.
    Admin/testing use — bypasses automatic time-based closing.
    """
    try:
        from services.slot_bid_closer import close_order_and_assign_winner
        result = close_order_and_assign_winner(order_id)
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "Failed to close order"))
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error manually closing order {order_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/order/{order_id}")
def get_order_bids(order_id: str):
    """
    Get all bids for a specific order.
    Returns bids sorted by amount (lowest first).
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Database client not configured")
    
    try:
        # Query bids for this order
        response = supabase_client.table("bids").select("*").eq("order_id", order_id).eq("bid_type", "order").order("amount", desc=False).execute()
        
        bids = []
        for row in response.data:
            bids.append({
                "id": row["id"],
                "driver_id": row.get("driver_id"),
                "driver_name": row["driver_name"],
                "order_id": row["order_id"],
                "amount": row["amount"],
                "vehicle": row["vehicle"],
                "reliability_score": row["reliability_score"],
                "bid_type": row["bid_type"],
                "status": row["status"],
                "created_at": row["created_at"]
            })
        
        return bids
        
    except Exception as e:
        print(f"Error fetching order bids: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/capacity/{driver_name}")
def get_driver_capacity_info(driver_name: str):
    """
    Get driver's capacity utilization and load information.
    Shows current committed weight vs vehicle capacity.
    """
    try:
        from services.capacity_service import calculate_capacity_utilization
        
        capacity_info = calculate_capacity_utilization(driver_name)
        return capacity_info
        
    except Exception as e:
        print(f"Error getting capacity info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/capacity/check")
def check_capacity_for_bid(payload: dict):
    """
    Check if driver can bid on an order based on capacity.
    Payload: {driver_name: str, order_weight: int}
    """
    try:
        from services.capacity_service import can_bid_on_order
        
        driver_name = payload.get("driver_name")
        order_weight = payload.get("order_weight")
        
        if not driver_name or not order_weight:
            raise HTTPException(status_code=400, detail="Missing driver_name or order_weight")
        
        result = can_bid_on_order(driver_name, order_weight)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error checking capacity: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/capacity/timeline/{driver_name}")
def get_capacity_timeline(driver_name: str):
    """
    Get driver's capacity timeline showing how load changes throughout the day.
    Useful for visualizing when capacity becomes available.
    """
    try:
        from services.dynamic_capacity_service import get_driver_capacity_timeline
        
        timeline = get_driver_capacity_timeline(driver_name)
        return timeline
        
    except Exception as e:
        print(f"Error getting capacity timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# CLUSTER-BASED BIDDING (Recommended approach)
# ===================================================================

def _create_trip_assignment(cluster_id: str, driver_name: str, bid_id: str):
    """
    Insert a trip_assignments row for the winning driver so the trip page
    shows an active trip immediately after bidding closes.
    trip_assignments.driver_id is a FK to drivers.id (not users.id).
    """
    try:
        # Resolve users.id from driver name
        user_resp = supabase_client.table("users").select("id").eq("name", driver_name).eq("role", "driver").execute()
        if not user_resp.data:
            print(f"[Trip Assignment] No user found for driver name: {driver_name}")
            return
        user_id = user_resp.data[0]["id"]

        # Resolve drivers.id (FK target) from user_id
        drv_resp = supabase_client.table("drivers").select("id").eq("user_id", user_id).execute()
        if not drv_resp.data:
            print(f"[Trip Assignment] No drivers row found for user_id: {user_id}")
            return
        driver_id = drv_resp.data[0]["id"]

        # Get bid details for contract value
        bid_resp = supabase_client.table("bids").select("amount").eq("id", bid_id).execute()
        contract_value = bid_resp.data[0]["amount"] if bid_resp.data else 0

        # Avoid duplicate trip assignments for same driver + bundle
        existing = supabase_client.table("trip_assignments")\
            .select("id")\
            .eq("driver_id", driver_id)\
            .eq("cluster_id", cluster_id)\
            .execute()

        if existing.data:
            print(f"[Trip Assignment] Already exists for driver {driver_name} + cluster {cluster_id}")
            return

        supabase_client.table("trip_assignments").insert({
            "driver_id": driver_id,
            "driver_name": driver_name,
            "cluster_id": cluster_id,
            "bid_id": bid_id,
            "contract_value": contract_value,
            "status": "Assigned",
            "trip_status": "Driver Assigned",
        }).execute()

        print(f"[Trip Assignment] Created for {driver_name} (driver_id={driver_id}) → cluster {cluster_id} @ ₹{contract_value}")

    except Exception as e:
        print(f"[Trip Assignment] Failed to create: {e}")

class ClusterBidCreate(BaseModel):
    """Request model for bidding on a formed cluster"""
    driver_id: str
    driver_name: str
    cluster_id: str
    amount: int
    vehicle: str
    reliability_score: Optional[int] = 94


@router.post("/cluster", response_model=SlotBid)
def create_cluster_bid(payload: ClusterBidCreate):
    """
    Create a bid for a formed cluster.
    
    This is the RECOMMENDED bidding approach that prevents conflicts.
    Drivers bid on complete clusters after clustering algorithm runs.
    
    Benefits:
    - No conflicts: Each cluster is a single unit
    - Accurate capacity: Total cluster weight is known
    - Fair pricing: Drivers bid on the complete bundle
    
    Workflow:
    1. Orders get created (status: Pending)
    2. Clustering runs (status: Cluster Forming, cluster_id assigned)
    3. Drivers bid on clusters (this endpoint)
    4. Lowest bid wins (or best bid based on reliability)
    5. Winner gets assigned (status: Driver Assigned)
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Database client not configured")
    
    try:
        # Check if cluster exists
        cluster_response = supabase_client.table("bundles").select("*").eq("id", payload.cluster_id).execute()
        
        if not cluster_response.data or len(cluster_response.data) == 0:
            raise HTTPException(status_code=404, detail=f"Cluster {payload.cluster_id} not found. Make sure clustering has been run.")
        
        cluster = cluster_response.data[0]
        total_weight = cluster.get("total_weight_kg", 0)
        
        # Check if orders in this cluster are still available for bidding
        orders_response = supabase_client.table("orders").select("id, status, weight_kg").eq("cluster_id", payload.cluster_id).execute()
        
        if not orders_response.data:
            raise HTTPException(status_code=404, detail=f"No orders found for cluster {payload.cluster_id}")
        
        # Verify all orders are in "Cluster Forming" status
        unavailable_orders = [o for o in orders_response.data if o["status"] not in ["Cluster Forming", "Pending"]]
        if unavailable_orders:
            raise HTTPException(
                status_code=400, 
                detail=f"Cluster {payload.cluster_id} is no longer available for bidding. Some orders are already assigned."
            )
        
        # Check if driver already bid on this cluster
        existing_bid = supabase_client.table("bids")\
            .select("id")\
            .eq("driver_name", payload.driver_name)\
            .eq("bundle_id", payload.cluster_id)\
            .eq("bid_type", "cluster")\
            .execute()
        
        if existing_bid.data and len(existing_bid.data) > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"You have already bid on cluster {payload.cluster_id}. Each driver can only bid once per cluster."
            )
        
        # Check if driver's vehicle has enough capacity for this cluster
        if payload.vehicle.lower() == "mini truck" and total_weight > 500:
            raise HTTPException(
                status_code=400,
                detail=f"Cluster weight ({total_weight}kg) exceeds Mini Truck capacity (500kg). Use Standard or Heavy truck."
            )
        elif payload.vehicle.lower() == "standard truck" and total_weight > 1100:
            raise HTTPException(
                status_code=400,
                detail=f"Cluster weight ({total_weight}kg) exceeds Standard Truck capacity (1100kg). Use Heavy truck."
            )
        elif payload.vehicle.lower() == "heavy truck" and total_weight > 2500:
            raise HTTPException(
                status_code=400,
                detail=f"Cluster weight ({total_weight}kg) exceeds Heavy Truck capacity (2500kg). Cannot accept this cluster."
            )
        
        # Validate minimum bid (should cover at least fuel + driver cost)
        min_bid = total_weight * 2  # Minimum ₹2/kg
        if payload.amount < min_bid:
            raise HTTPException(
                status_code=400,
                detail=f"Bid amount (₹{payload.amount}) is too low. Minimum bid for {total_weight}kg cluster: ₹{min_bid}"
            )
        
        # Generate bid ID
        bid_id = f"CB-{int(datetime.now().timestamp() * 1000)}"
        
        # Insert bid record
        bid_data = {
            "id": bid_id,
            "driver_id": None,  # NULL allowed by schema
            "driver_name": payload.driver_name,
            "bundle_id": payload.cluster_id,
            "order_id": None,  # NULL for cluster bids
            "pickup_date": None,  # Cluster already has pickup time
            "pickup_slot": None,  # Cluster already has pickup time
            "amount": int(payload.amount),
            "vehicle": payload.vehicle,
            "reliability_score": int(payload.reliability_score),
            "bid_type": "cluster",
            "status": "Open",
        }
        
        insert_response = supabase_client.table("bids").insert(bid_data).execute()
        
        if not insert_response.data:
            raise HTTPException(status_code=500, detail="Failed to create cluster bid")
        
        row = insert_response.data[0]
        
        print(f"✅ Cluster bid created: {bid_id} by {payload.driver_name} for cluster {payload.cluster_id} (₹{payload.amount}, {total_weight}kg)")
        
        return SlotBid(
            id=row["id"],
            driver_id=row.get("driver_id"),
            driver_name=row["driver_name"],
            pickup_date=None,  # Cluster bids don't have date/slot
            pickup_slot=None,
            amount=row["amount"],
            vehicle=row["vehicle"],
            reliability_score=row["reliability_score"],
            bid_type=row["bid_type"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creating cluster bid: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cluster/{cluster_id}")
def get_cluster_bids(cluster_id: str):
    """
    Get all bids for a specific cluster.
    
    Returns list of bids sorted by:
    1. Amount (lowest first)
    2. Reliability score (highest first)
    
    Useful for drivers to see competition and admin to select winner.
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Database client not configured")
    
    try:
        # Get all bids for this cluster (accept both "cluster" and "bundle" bid_type)
        bids_response = supabase_client.table("bids")\
            .select("*")\
            .eq("bundle_id", cluster_id)\
            .in_("bid_type", ["cluster", "bundle"])\
            .order("amount", desc=False)\
            .order("reliability_score", desc=True)\
            .execute()
        
        if not bids_response.data:
            return {
                "cluster_id": cluster_id,
                "bids": [],
                "total_bids": 0,
                "lowest_bid": None,
                "highest_reliability": None
            }
        
        bids = bids_response.data
        lowest_bid = min(b["amount"] for b in bids)
        highest_reliability = max(b["reliability_score"] for b in bids)
        
        return {
            "cluster_id": cluster_id,
            "bids": bids,
            "total_bids": len(bids),
            "lowest_bid": lowest_bid,
            "highest_reliability": highest_reliability,
            "recommended_winner": bids[0]["id"] if bids else None  # First after sorting
        }
        
    except Exception as e:
        print(f"Error fetching cluster bids: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cluster/{cluster_id}/close")
def close_cluster_bidding(cluster_id: str, winner_bid_id: Optional[str] = None):
    """
    Close bidding for a cluster and optionally assign winner.
    
    If winner_bid_id is provided, that bid wins.
    If not provided, automatically selects lowest bid with highest reliability.
    
    Updates:
    - All bids for this cluster to "Closed" (except winner -> "Accepted")
    - All orders in cluster to "Driver Assigned"
    - Assigns driver to orders
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Database client not configured")
    
    try:
        # Get all bids for this cluster (accept both "cluster" and "bundle" bid_type)
        bids_response = supabase_client.table("bids")\
            .select("*")\
            .eq("bundle_id", cluster_id)\
            .in_("bid_type", ["cluster", "bundle"])\
            .eq("status", "Open")\
            .execute()
        
        if not bids_response.data:
            raise HTTPException(status_code=404, detail=f"No open bids found for cluster {cluster_id}")
        
        bids = bids_response.data
        
        # Select winner
        if winner_bid_id:
            winner = next((b for b in bids if b["id"] == winner_bid_id), None)
            if not winner:
                raise HTTPException(status_code=404, detail=f"Bid {winner_bid_id} not found for cluster {cluster_id}")
        else:
            # Auto-select: lowest amount, then highest reliability
            winner = min(bids, key=lambda b: (b["amount"], -b["reliability_score"]))
        
        winner_driver = winner["driver_name"]
        winner_amount = winner["amount"]
        
        # Mark winner bid as Accepted
        supabase_client.table("bids")\
            .update({"status": "Accepted"})\
            .eq("id", winner["id"])\
            .execute()
        
        # Mark all other bids as Closed
        for bid in bids:
            if bid["id"] != winner["id"]:
                supabase_client.table("bids")\
                    .update({"status": "Closed"})\
                    .eq("id", bid["id"])\
                    .execute()
        
        # Update all orders in cluster
        orders_response = supabase_client.table("orders")\
            .select("id")\
            .eq("cluster_id", cluster_id)\
            .execute()
        
        if orders_response.data:
            for order in orders_response.data:
                supabase_client.table("orders")\
                    .update({
                        "status": "Driver Assigned",
                        "assigned_driver": winner_driver,
                        "final_cost": winner_amount  # Could be split proportionally later
                    })\
                    .eq("id", order["id"])\
                    .execute()
        
        print(f"✅ Cluster {cluster_id} bidding closed. Winner: {winner_driver} (₹{winner_amount})")

        # Create trip assignment so driver sees active trip immediately
        _create_trip_assignment(cluster_id, winner_driver, winner["id"])

        # SMS: notify winning driver + all farmers
        try:
            from services.sms_service import sms_service

            # Get driver phone number
            driver_user = supabase_client.table("users")\
                .select("phone")\
                .eq("name", winner_driver)\
                .eq("role", "driver")\
                .limit(1)\
                .execute()
            driver_phone = driver_user.data[0]["phone"] if driver_user.data else ""

            sms_result = sms_service.notify_bid_winner(
                cluster_id=cluster_id,
                driver_name=winner_driver,
                driver_phone=driver_phone,
                bid_amount=winner_amount,
            )
            print(f"📱 Bid Winner SMS — sent: {sms_result.get('sms_sent', 0)}, failed: {sms_result.get('sms_failed', 0)}")
        except Exception as sms_err:
            print(f"⚠️ Bid winner SMS notification failed (non-critical): {sms_err}")

        return {
            "success": True,
            "cluster_id": cluster_id,
            "winner": {
                "bid_id": winner["id"],
                "driver_name": winner_driver,
                "amount": winner_amount,
                "vehicle": winner["vehicle"],
                "reliability_score": winner["reliability_score"]
            },
            "total_bids": len(bids),
            "orders_assigned": len(orders_response.data) if orders_response.data else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error closing cluster bidding: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))



# ===================================================================
# MULTIPLE CLUSTER WIN HANDLING
# ===================================================================

@router.get("/driver/{driver_name}/assignments")
def get_driver_assignments(driver_name: str):
    """
    Get all cluster assignments for a driver.
    
    Shows:
    - All clusters they've won
    - Total weight across all assignments
    - Pickup times to check for conflicts
    - Whether they can handle all assignments
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Database client not configured")
    
    try:
        # Get all accepted bids for this driver
        accepted_bids = supabase_client.table("bids")\
            .select("*, bundles(*)")\
            .eq("driver_name", driver_name)\
            .eq("status", "Accepted")\
            .eq("bid_type", "cluster")\
            .execute()
        
        if not accepted_bids.data:
            return {
                "driver_name": driver_name,
                "total_clusters": 0,
                "assignments": [],
                "total_weight": 0,
                "has_conflicts": False,
                "conflicts": []
            }
        
        assignments = []
        total_weight = 0
        conflicts = []
        
        for bid in accepted_bids.data:
            cluster_id = bid.get("bundle_id")
            
            # Get orders in this cluster
            orders = supabase_client.table("orders")\
                .select("id, weight_kg, pickup_date, pickup_slot, cluster_slot")\
                .eq("cluster_id", cluster_id)\
                .execute()
            
            cluster_weight = sum(o["weight_kg"] for o in orders.data) if orders.data else 0
            total_weight += cluster_weight
            
            pickup_time = orders.data[0].get("cluster_slot") if orders.data else None
            
            assignments.append({
                "cluster_id": cluster_id,
                "bid_id": bid["id"],
                "amount": bid["amount"],
                "vehicle": bid["vehicle"],
                "cluster_weight": cluster_weight,
                "num_orders": len(orders.data) if orders.data else 0,
                "pickup_time": pickup_time,
                "orders": [o["id"] for o in orders.data] if orders.data else []
            })
        
        # Check for timing conflicts (same pickup time)
        pickup_times = {}
        for assignment in assignments:
            pickup = assignment.get("pickup_time")
            if pickup:
                if pickup in pickup_times:
                    conflicts.append({
                        "type": "timing_conflict",
                        "message": f"Cannot pickup clusters {pickup_times[pickup]} and {assignment['cluster_id']} at the same time ({pickup})",
                        "clusters": [pickup_times[pickup], assignment["cluster_id"]],
                        "pickup_time": pickup
                    })
                else:
                    pickup_times[pickup] = assignment["cluster_id"]
        
        # Check for capacity conflicts (if using one vehicle for multiple clusters)
        # Note: This assumes sequential delivery, not simultaneous
        vehicle_types = set(a["vehicle"] for a in assignments)
        if len(vehicle_types) == 1:
            vehicle = list(vehicle_types)[0]
            capacity = {
                "Mini Truck": 500,
                "Standard Truck": 1100,
                "Heavy Truck": 2500
            }.get(vehicle, 1100)
            
            # Check if any single cluster exceeds capacity
            for assignment in assignments:
                if assignment["cluster_weight"] > capacity:
                    conflicts.append({
                        "type": "capacity_exceeded",
                        "message": f"Cluster {assignment['cluster_id']} weight ({assignment['cluster_weight']}kg) exceeds {vehicle} capacity ({capacity}kg)",
                        "cluster_id": assignment["cluster_id"],
                        "weight": assignment["cluster_weight"],
                        "capacity": capacity
                    })
        
        return {
            "driver_name": driver_name,
            "total_clusters": len(assignments),
            "assignments": assignments,
            "total_weight": total_weight,
            "has_conflicts": len(conflicts) > 0,
            "conflicts": conflicts,
            "note": "If there are timing conflicts, driver cannot fulfill both clusters. Admin must reassign one cluster to another driver."
        }
        
    except Exception as e:
        print(f"Error fetching driver assignments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-multiple-wins")
def validate_multiple_cluster_wins(driver_name: str, cluster_ids: list[str]):
    """
    Validate if a driver can win multiple clusters without conflicts.
    
    Checks:
    1. Timing conflicts: Same pickup time for multiple clusters
    2. Capacity conflicts: Total weight exceeds vehicle capacity
    3. Route feasibility: Can complete all deliveries in reasonable time
    
    Returns:
    - can_handle: bool
    - conflicts: list of detected conflicts
    - recommendations: suggested solutions
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Database client not configured")
    
    try:
        conflicts = []
        recommendations = []
        
        # Get all clusters' details
        cluster_details = []
        for cluster_id in cluster_ids:
            orders = supabase_client.table("orders")\
                .select("id, weight_kg, pickup_date, pickup_slot, cluster_slot")\
                .eq("cluster_id", cluster_id)\
                .execute()
            
            if orders.data:
                cluster_weight = sum(o["weight_kg"] for o in orders.data)
                pickup_time = orders.data[0].get("cluster_slot")
                pickup_date = orders.data[0].get("pickup_date")
                pickup_slot = orders.data[0].get("pickup_slot")
                
                cluster_details.append({
                    "cluster_id": cluster_id,
                    "weight": cluster_weight,
                    "pickup_time": pickup_time,
                    "pickup_date": pickup_date,
                    "pickup_slot": pickup_slot,
                    "num_orders": len(orders.data)
                })
        
        # Check 1: Timing conflicts
        pickup_groups = {}
        for cluster in cluster_details:
            key = (cluster["pickup_date"], cluster["pickup_slot"])
            if key not in pickup_groups:
                pickup_groups[key] = []
            pickup_groups[key].append(cluster["cluster_id"])
        
        for (date, slot), clusters in pickup_groups.items():
            if len(clusters) > 1:
                conflicts.append({
                    "type": "timing_conflict",
                    "severity": "critical",
                    "message": f"Multiple clusters scheduled for same time slot: {date} {slot}",
                    "clusters": clusters,
                    "solution": "Driver can only accept ONE of these clusters"
                })
                recommendations.append(f"Reassign {len(clusters)-1} cluster(s) from {date} {slot} to another driver")
        
        # Check 2: Capacity check (assuming Standard Truck = 1100kg)
        total_weight = sum(c["weight"] for c in cluster_details)
        for cluster in cluster_details:
            if cluster["weight"] > 1100:
                conflicts.append({
                    "type": "capacity_exceeded",
                    "severity": "critical",
                    "message": f"Cluster {cluster['cluster_id']} ({cluster['weight']}kg) exceeds Standard Truck capacity (1100kg)",
                    "cluster_id": cluster["cluster_id"],
                    "weight": cluster["weight"],
                    "solution": "Requires Heavy Truck (2500kg capacity)"
                })
                recommendations.append(f"Use Heavy Truck for cluster {cluster['cluster_id']}")
        
        # Check 3: Route feasibility (simple check: max 2 clusters per day)
        dates = {}
        for cluster in cluster_details:
            date = cluster["pickup_date"]
            if date not in dates:
                dates[date] = []
            dates[date].append(cluster["cluster_id"])
        
        for date, clusters in dates.items():
            if len(clusters) > 2:
                conflicts.append({
                    "type": "route_overload",
                    "severity": "warning",
                    "message": f"Too many clusters on {date}: {len(clusters)} clusters. Driver may not complete all deliveries.",
                    "clusters": clusters,
                    "solution": "Spread deliveries across multiple days or drivers"
                })
                recommendations.append(f"Consider reassigning some clusters from {date}")
        
        can_handle = len([c for c in conflicts if c["severity"] == "critical"]) == 0
        
        return {
            "driver_name": driver_name,
            "cluster_ids": cluster_ids,
            "can_handle": can_handle,
            "total_clusters": len(cluster_details),
            "total_weight": sum(c["weight"] for c in cluster_details),
            "conflicts": conflicts,
            "recommendations": recommendations if not can_handle else ["No conflicts detected. Driver can handle all clusters."],
            "status": "approved" if can_handle else "rejected"
        }
        
    except Exception as e:
        print(f"Error validating multiple wins: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cluster/{cluster_id}/close-with-validation")
def close_cluster_with_conflict_check(cluster_id: str, winner_bid_id: Optional[str] = None):
    """
    Enhanced cluster closing that checks if winner already has conflicting assignments.
    
    If winner has timing conflicts with other clusters, either:
    1. Reject the assignment and select next best bid
    2. Return warning for admin to manually resolve
    
    This prevents a driver from winning multiple clusters at the same pickup time.
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Database client not configured")
    
    try:
        # Get all bids for this cluster (accept both "cluster" and "bundle" bid_type)
        bids_response = supabase_client.table("bids")\
            .select("*")\
            .eq("bundle_id", cluster_id)\
            .in_("bid_type", ["cluster", "bundle"])\
            .eq("status", "Open")\
            .order("amount", desc=False)\
            .order("reliability_score", desc=True)\
            .execute()
        
        if not bids_response.data:
            raise HTTPException(status_code=404, detail=f"No open bids found for cluster {cluster_id}")
        
        bids = bids_response.data
        
        # Get cluster pickup time
        cluster_orders = supabase_client.table("orders")\
            .select("pickup_date, pickup_slot, cluster_slot")\
            .eq("cluster_id", cluster_id)\
            .execute()
        
        if not cluster_orders.data:
            raise HTTPException(status_code=404, detail=f"No orders found for cluster {cluster_id}")
        
        cluster_pickup_date = cluster_orders.data[0].get("pickup_date")
        cluster_pickup_slot = cluster_orders.data[0].get("pickup_slot")
        
        # Try to find a winner without conflicts
        winner = None
        conflicts_detected = []
        
        for bid in bids:
            if winner_bid_id and bid["id"] != winner_bid_id:
                continue  # Skip if specific winner requested
            
            driver_name = bid["driver_name"]
            
            # Check if this driver has other accepted bids with same pickup time
            other_assignments = supabase_client.table("bids")\
                .select("*, orders!inner(pickup_date, pickup_slot)")\
                .eq("driver_name", driver_name)\
                .eq("status", "Accepted")\
                .eq("bid_type", "cluster")\
                .execute()
            
            has_conflict = False
            if other_assignments.data:
                for assignment in other_assignments.data:
                    # Check through orders associated with that cluster
                    assigned_orders = supabase_client.table("orders")\
                        .select("pickup_date, pickup_slot")\
                        .eq("cluster_id", assignment.get("bundle_id"))\
                        .execute()
                    
                    if assigned_orders.data:
                        assigned_date = assigned_orders.data[0].get("pickup_date")
                        assigned_slot = assigned_orders.data[0].get("pickup_slot")
                        
                        if assigned_date == cluster_pickup_date and assigned_slot == cluster_pickup_slot:
                            has_conflict = True
                            conflicts_detected.append({
                                "driver": driver_name,
                                "reason": f"Already assigned to cluster at {assigned_date} {assigned_slot}",
                                "conflicting_cluster": assignment.get("bundle_id")
                            })
                            break
            
            if not has_conflict:
                winner = bid
                break
        
        if not winner:
            # No bid without conflicts found
            return {
                "success": False,
                "message": "All bidders have timing conflicts with existing assignments",
                "cluster_id": cluster_id,
                "conflicts": conflicts_detected,
                "recommendation": "Manually reassign or open bidding to more drivers"
            }
        
        # Proceed with winner assignment (same as original close_cluster_bidding)
        winner_driver = winner["driver_name"]
        winner_amount = winner["amount"]
        
        supabase_client.table("bids")\
            .update({"status": "Accepted"})\
            .eq("id", winner["id"])\
            .execute()
        
        for bid in bids:
            if bid["id"] != winner["id"]:
                supabase_client.table("bids")\
                    .update({"status": "Closed"})\
                    .eq("id", bid["id"])\
                    .execute()
        
        orders_response = supabase_client.table("orders")\
            .select("id")\
            .eq("cluster_id", cluster_id)\
            .execute()
        
        if orders_response.data:
            for order in orders_response.data:
                supabase_client.table("orders")\
                    .update({
                        "status": "Driver Assigned",
                        "assigned_driver": winner_driver,
                        "final_cost": winner_amount
                    })\
                    .eq("id", order["id"])\
                    .execute()
        
        print(f"✅ Cluster {cluster_id} assigned to {winner_driver} (no conflicts)")

        # Create trip assignment so driver sees active trip immediately
        _create_trip_assignment(cluster_id, winner_driver, winner["id"])

        return {
            "success": True,
            "cluster_id": cluster_id,
            "winner": {
                "bid_id": winner["id"],
                "driver_name": winner_driver,
                "amount": winner_amount,
                "vehicle": winner["vehicle"],
                "reliability_score": winner["reliability_score"]
            },
            "conflicts_resolved": len(conflicts_detected),
            "orders_assigned": len(orders_response.data) if orders_response.data else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error closing cluster with validation: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))



# ===================================================================
# BID HISTORY & DRIVER ACTIVITY TRACKING
# ===================================================================

@router.get("/history/driver/{driver_name}")
def get_driver_bid_history(
    driver_name: str,
    limit: int = 50,
    status: Optional[str] = None,
    won_only: bool = False
):
    """
    Get complete bidding history for a driver.
    
    Shows all bids (past and present) with outcomes:
    - Total bids placed
    - Bids won vs lost
    - Win rate percentage
    - Average bid amount
    - Recent activity
    
    Query params:
    - limit: Max results to return (default 50)
    - status: Filter by status (Open, Accepted, Closed, Rejected, Withdrawn)
    - won_only: Only show winning bids (status=Accepted)
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Database client not configured")
    
    try:
        # Build query
        query = supabase_client.table("bid_history")\
            .select("*")\
            .eq("driver_name", driver_name)\
            .order("created_at", desc=True)\
            .limit(limit)
        
        if status:
            query = query.eq("bid_status", status)
        
        if won_only:
            query = query.eq("won", True)
        
        history_response = query.execute()
        
        if not history_response.data:
            return {
                "driver_name": driver_name,
                "total_bids": 0,
                "bids_won": 0,
                "bids_lost": 0,
                "win_rate": 0,
                "history": []
            }
        
        history = history_response.data
        
        # Calculate statistics
        total_bids = len(history)
        bids_won = sum(1 for h in history if h.get("won"))
        bids_lost = sum(1 for h in history if h.get("bid_status") == "Closed")
        win_rate = round((bids_won / total_bids * 100), 1) if total_bids > 0 else 0
        
        bid_amounts = [h["bid_amount"] for h in history if h.get("bid_amount")]
        avg_bid = round(sum(bid_amounts) / len(bid_amounts)) if bid_amounts else 0
        
        winning_bids = [h for h in history if h.get("won")]
        avg_winning_bid = round(sum(h["bid_amount"] for h in winning_bids) / len(winning_bids)) if winning_bids else 0
        
        return {
            "driver_name": driver_name,
            "statistics": {
                "total_bids": total_bids,
                "bids_won": bids_won,
                "bids_lost": bids_lost,
                "bids_open": sum(1 for h in history if h.get("bid_status") == "Open"),
                "win_rate": win_rate,
                "average_bid_amount": avg_bid,
                "average_winning_bid": avg_winning_bid,
                "lowest_winning_bid": min((h["bid_amount"] for h in winning_bids), default=0),
                "highest_winning_bid": max((h["bid_amount"] for h in winning_bids), default=0)
            },
            "recent_activity": history[:10],  # Last 10 bids
            "history": history
        }
        
    except Exception as e:
        print(f"Error fetching bid history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/cluster/{cluster_id}")
def get_cluster_bid_history(cluster_id: str):
    """
    Get all bidding activity for a specific cluster.
    
    Shows:
    - All drivers who bid on this cluster
    - Bid amounts and outcomes
    - Winner (if bidding closed)
    - Timeline of bids
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Database client not configured")
    
    try:
        history_response = supabase_client.table("bid_history")\
            .select("*")\
            .eq("cluster_id", cluster_id)\
            .order("created_at", desc=False)\
            .execute()
        
        if not history_response.data:
            return {
                "cluster_id": cluster_id,
                "total_bids": 0,
                "winner": None,
                "history": []
            }
        
        history = history_response.data
        
        winner = next((h for h in history if h.get("won")), None)
        
        return {
            "cluster_id": cluster_id,
            "total_bids": len(set(h["driver_name"] for h in history)),  # Unique drivers
            "winner": {
                "driver_name": winner["driver_name"],
                "bid_amount": winner["bid_amount"],
                "vehicle": winner["vehicle"],
                "won_at": winner["status_changed_at"]
            } if winner else None,
            "bidding_closed": any(h.get("bid_status") in ["Accepted", "Closed"] for h in history),
            "lowest_bid": min(h["bid_amount"] for h in history),
            "highest_bid": max(h["bid_amount"] for h in history),
            "average_bid": round(sum(h["bid_amount"] for h in history) / len(history)),
            "history": history
        }
        
    except Exception as e:
        print(f"Error fetching cluster bid history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/summary")
def get_bidding_summary(days: int = 7):
    """
    Get overall bidding summary across all drivers and clusters.
    
    Useful for admin dashboard to see:
    - Total bidding activity
    - Most active drivers
    - Average win rates
    - Pricing trends
    
    Query params:
    - days: Look back period (default 7 days)
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Database client not configured")
    
    try:
        from datetime import datetime, timedelta
        
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        history_response = supabase_client.table("bid_history")\
            .select("*")\
            .gte("created_at", since_date)\
            .execute()
        
        if not history_response.data:
            return {
                "period_days": days,
                "total_bids": 0,
                "total_drivers": 0,
                "total_clusters": 0,
                "summary": {}
            }
        
        history = history_response.data
        
        # Calculate metrics
        total_bids = len(history)
        unique_drivers = len(set(h["driver_name"] for h in history))
        unique_clusters = len(set(h.get("cluster_id") for h in history if h.get("cluster_id")))
        total_won = sum(1 for h in history if h.get("won"))
        
        # Per-driver stats
        driver_stats = {}
        for h in history:
            driver = h["driver_name"]
            if driver not in driver_stats:
                driver_stats[driver] = {
                    "driver_name": driver,
                    "total_bids": 0,
                    "bids_won": 0,
                    "total_bid_amount": 0
                }
            
            driver_stats[driver]["total_bids"] += 1
            if h.get("won"):
                driver_stats[driver]["bids_won"] += 1
            driver_stats[driver]["total_bid_amount"] += h.get("bid_amount", 0)
        
        # Top drivers by activity
        top_drivers = sorted(
            driver_stats.values(),
            key=lambda d: (d["bids_won"], d["total_bids"]),
            reverse=True
        )[:10]
        
        # Calculate win rates
        for driver in top_drivers:
            driver["win_rate"] = round((driver["bids_won"] / driver["total_bids"] * 100), 1) if driver["total_bids"] > 0 else 0
            driver["avg_bid"] = round(driver["total_bid_amount"] / driver["total_bids"]) if driver["total_bids"] > 0 else 0
        
        return {
            "period_days": days,
            "since_date": since_date,
            "summary": {
                "total_bids": total_bids,
                "total_drivers": unique_drivers,
                "total_clusters": unique_clusters,
                "bids_won": total_won,
                "bids_lost": total_bids - total_won,
                "overall_win_rate": round((total_won / total_bids * 100), 1) if total_bids > 0 else 0,
                "avg_bid_amount": round(sum(h["bid_amount"] for h in history) / total_bids) if total_bids else 0
            },
            "top_drivers": top_drivers,
            "daily_activity": []  # Could add daily breakdown if needed
        }
        
    except Exception as e:
        print(f"Error fetching bidding summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/history/log-manual")
def log_manual_bid_history(
    bid_id: str,
    status: str,
    rejection_reason: Optional[str] = None
):
    """
    Manually log a bid history entry.
    
    Useful when:
    - Correcting bid outcomes
    - Logging external bid rejections
    - Audit trail maintenance
    
    NOTE: Normally bid_history is auto-populated by database trigger.
    This is for manual corrections only.
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Database client not configured")
    
    try:
        # Get bid details
        bid_response = supabase_client.table("bids")\
            .select("*")\
            .eq("id", bid_id)\
            .execute()
        
        if not bid_response.data:
            raise HTTPException(status_code=404, detail=f"Bid {bid_id} not found")
        
        bid = bid_response.data[0]
        
        # Insert manual history entry
        history_entry = {
            "bid_id": bid_id,
            "driver_id": bid.get("driver_id"),
            "driver_name": bid["driver_name"],
            "cluster_id": bid.get("bundle_id"),
            "order_id": bid.get("order_id"),
            "pickup_date": bid.get("pickup_date"),
            "pickup_slot": bid.get("pickup_slot"),
            "bid_amount": bid["amount"],
            "vehicle": bid["vehicle"],
            "reliability_score": bid.get("reliability_score", 94),
            "bid_type": bid["bid_type"],
            "bid_status": status,
            "won": (status == "Accepted"),
            "rejection_reason": rejection_reason
        }
        
        insert_response = supabase_client.table("bid_history")\
            .insert(history_entry)\
            .execute()
        
        print(f"✅ Manual history entry logged for bid {bid_id}: {status}")
        
        return {
            "success": True,
            "bid_id": bid_id,
            "status": status,
            "history_id": insert_response.data[0]["id"] if insert_response.data else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error logging manual history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
