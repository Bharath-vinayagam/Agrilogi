"""
Dynamic Real-Time Capacity Management
Tracks driver's load throughout the day, accounting for pickups and deliveries
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from database.db import supabase_client

IST = timezone(timedelta(hours=5, minutes=30))

# Slot time mappings for estimated delivery times
SLOT_TIMES = {
    "morning": {"start": 6, "end": 10, "avg_delivery": 8},
    "afternoon": {"start": 11, "end": 15, "avg_delivery": 13},
    "evening": {"start": 16, "end": 20, "avg_delivery": 18}
}


def estimate_delivery_time(pickup_date: str, pickup_slot: str) -> datetime:
    """
    Estimate when an order will be delivered.
    Assumes delivery happens mid-slot + 2 hours travel time.
    """
    try:
        date_obj = datetime.fromisoformat(pickup_date).date()
        slot_info = SLOT_TIMES.get(pickup_slot, {"avg_delivery": 12})
        
        # Delivery time = pickup time + 2 hours
        delivery_hour = slot_info["avg_delivery"] + 2
        
        delivery_time = datetime.combine(date_obj, datetime.min.time()).replace(
            hour=min(23, delivery_hour),
            minute=0,
            tzinfo=IST
        )
        
        return delivery_time
        
    except Exception as e:
        print(f"Error estimating delivery time: {e}")
        # Default: same day 6 PM
        return datetime.now(IST).replace(hour=18, minute=0, second=0, microsecond=0)


def _get_client():
    """Return supabase_client, re-importing to pick up any reconnection."""
    from database.db import supabase_client as _client
    return _client


def get_driver_schedule(driver_name: str) -> List[Dict]:
    """
    Get driver's complete schedule: all accepted orders sorted by time.
    Returns list of orders with pickup/delivery times and weights.
    """
    client = _get_client()
    if not client:
        return []
    
    try:
        # Get all accepted bids (won orders)
        response = client.table("bids").select("order_id").eq("driver_name", driver_name).eq("status", "Accepted").eq("bid_type", "order").execute()
        
        if not response.data:
            return []
        
        order_ids = [bid["order_id"] for bid in response.data]
        
        # Get order details
        orders_response = client.table("orders").select("*").in_("id", order_ids).execute()
        
        if not orders_response.data:
            return []
        
        # Build schedule with estimated times
        schedule = []
        for order in orders_response.data:
            if not order.get("pickup_date") or not order.get("pickup_slot"):
                continue
            
            pickup_date = order["pickup_date"]
            pickup_slot = order["pickup_slot"]
            
            # Calculate pickup time (slot start)
            slot_start_hour = SLOT_TIMES[pickup_slot]["start"]
            pickup_time = datetime.fromisoformat(pickup_date).replace(
                hour=slot_start_hour,
                minute=0,
                tzinfo=IST
            )
            
            # Calculate delivery time
            delivery_time = estimate_delivery_time(pickup_date, pickup_slot)
            
            schedule.append({
                "order_id": order["id"],
                "crop": order["crop"],
                "weight_kg": order["weight_kg"],
                "status": order["status"],
                "pickup_time": pickup_time,
                "delivery_time": delivery_time,
                "pickup_slot": pickup_slot,
                "delivered": order.get("status") == "Completed"
            })
        
        # Sort by pickup time
        schedule.sort(key=lambda x: x["pickup_time"])
        
        return schedule
        
    except Exception as e:
        print(f"Error getting driver schedule: {e}")
        return []


def calculate_capacity_at_time(driver_name: str, target_time: datetime, vehicle_capacity: int) -> Dict:
    """
    Calculate driver's available capacity at a specific time.
    Accounts for:
    - Orders picked up before target_time (adds weight)
    - Orders delivered before target_time (removes weight)
    """
    schedule = get_driver_schedule(driver_name)
    
    if not schedule:
        return {
            "available_capacity": vehicle_capacity,
            "current_load": 0,
            "orders_onboard": [],
            "num_orders_onboard": 0
        }
    
    current_load = 0
    orders_onboard = []
    
    for item in schedule:
        # If picked up but not delivered by target_time, it's on the truck
        if item["pickup_time"] <= target_time and item["delivery_time"] > target_time:
            if not item["delivered"]:
                current_load += item["weight_kg"]
                orders_onboard.append({
                    "order_id": item["order_id"],
                    "weight_kg": item["weight_kg"],
                    "crop": item["crop"]
                })
    
    available = vehicle_capacity - current_load
    
    return {
        "available_capacity": max(0, available),
        "current_load": current_load,
        "orders_onboard": orders_onboard,
        "num_orders_onboard": len(orders_onboard)
    }


def get_capacity_for_new_bid(driver_name: str, new_order_pickup_date: str, new_order_pickup_slot: str) -> Dict:
    """
    Calculate if driver has capacity for a new order at specific date/slot.
    Checks capacity at the pickup time of the new order.
    """
    try:
        # Get vehicle capacity
        from services.capacity_service import get_driver_capacity
        vehicle_capacity = get_driver_capacity(driver_name) or 1000
        
        # Calculate pickup time for the new order
        slot_start_hour = SLOT_TIMES[new_order_pickup_slot]["start"]
        pickup_time = datetime.fromisoformat(new_order_pickup_date).replace(
            hour=slot_start_hour,
            minute=0,
            tzinfo=IST
        )
        
        # Calculate capacity at that time
        capacity_info = calculate_capacity_at_time(driver_name, pickup_time, vehicle_capacity)
        
        return {
            "vehicle_capacity": vehicle_capacity,
            "pickup_time": pickup_time.isoformat(),
            "available_at_pickup": capacity_info["available_capacity"],
            "current_load_at_pickup": capacity_info["current_load"],
            "orders_onboard_at_pickup": capacity_info["orders_onboard"],
            "can_accept_order": capacity_info["available_capacity"] > 0
        }
        
    except Exception as e:
        print(f"Error calculating capacity for new bid: {e}")
        return {
            "vehicle_capacity": 1000,
            "available_at_pickup": 1000,
            "current_load_at_pickup": 0,
            "orders_onboard_at_pickup": [],
            "can_accept_order": True
        }


def get_driver_capacity_timeline(driver_name: str) -> List[Dict]:
    """
    Get driver's capacity throughout the day as a timeline.
    Shows how capacity changes with each pickup and delivery.
    """
    try:
        from services.capacity_service import get_driver_capacity
        vehicle_capacity = get_driver_capacity(driver_name) or 1000
        
        schedule = get_driver_schedule(driver_name)
        
        if not schedule:
            return [{
                "time": datetime.now(IST).isoformat(),
                "event": "Current",
                "load": 0,
                "available": vehicle_capacity
            }]
        
        timeline = []
        current_load = 0
        
        # Add initial state
        timeline.append({
            "time": datetime.now(IST).isoformat(),
            "event": "Current",
            "load": 0,
            "available": vehicle_capacity
        })
        
        # Process all events (pickups and deliveries)
        events = []
        for item in schedule:
            events.append({
                "time": item["pickup_time"],
                "type": "pickup",
                "order_id": item["order_id"],
                "weight": item["weight_kg"],
                "crop": item["crop"]
            })
            events.append({
                "time": item["delivery_time"],
                "type": "delivery",
                "order_id": item["order_id"],
                "weight": item["weight_kg"],
                "crop": item["crop"]
            })
        
        # Sort events by time
        events.sort(key=lambda x: x["time"])
        
        # Build timeline
        for event in events:
            if event["type"] == "pickup":
                current_load += event["weight"]
                timeline.append({
                    "time": event["time"].isoformat(),
                    "event": f"Pickup {event['order_id']} ({event['crop']})",
                    "load": current_load,
                    "available": vehicle_capacity - current_load,
                    "weight_change": f"+{event['weight']}kg"
                })
            else:  # delivery
                current_load -= event["weight"]
                timeline.append({
                    "time": event["time"].isoformat(),
                    "event": f"Deliver {event['order_id']} ({event['crop']})",
                    "load": max(0, current_load),
                    "available": vehicle_capacity - max(0, current_load),
                    "weight_change": f"-{event['weight']}kg"
                })
        
        return timeline
        
    except Exception as e:
        print(f"Error generating capacity timeline: {e}")
        return []
