"""
Vehicle Capacity Management Service
Tracks driver's current load and prevents over-capacity bidding
"""

from typing import Dict, List, Optional
from database.db import supabase_client


def get_driver_capacity(driver_name: str) -> Optional[int]:
    """
    Get driver's vehicle capacity in kg from vehicles table via drivers join.
    Returns None if not found.
    """
    if not supabase_client:
        return None
    
    try:
        # Join users -> drivers -> vehicles to get capacity
        user_resp = supabase_client.table("users").select("id").eq("name", driver_name).eq("role", "driver").execute()
        if not user_resp.data:
            return None
        user_id = user_resp.data[0]["id"]

        driver_resp = supabase_client.table("drivers").select("id, vehicle_type").eq("user_id", user_id).execute()
        if not driver_resp.data:
            return None
        driver_id = driver_resp.data[0]["id"]
        vehicle_type = driver_resp.data[0].get("vehicle_type", "")

        vehicle_resp = supabase_client.table("vehicles").select("capacity_kg").eq("driver_id", driver_id).execute()
        if vehicle_resp.data:
            return int(vehicle_resp.data[0]["capacity_kg"])

        # Fallback: estimate from vehicle_type in drivers table
        return estimate_capacity_by_vehicle(vehicle_type.lower())

    except Exception as e:
        print(f"Error getting driver capacity: {e}")
        return None


def estimate_capacity_by_vehicle(vehicle_type: str) -> int:
    """Estimate capacity based on vehicle type if not explicitly set"""
    estimates = {
        "mini truck": 1000,
        "pickup": 500,
        "van": 750,
        "truck": 2000,
        "large truck": 5000
    }
    
    for key, value in estimates.items():
        if key in vehicle_type:
            return value
    
    return 1000  # Default fallback


def get_driver_accepted_bids(driver_name: str) -> List[Dict]:
    """
    Get all accepted bids for a driver (winning bids).
    Returns list of orders with weights.
    """
    if not supabase_client:
        return []
    
    try:
        # Get accepted bids
        response = supabase_client.table("bids").select("order_id").eq("driver_name", driver_name).eq("status", "Accepted").eq("bid_type", "order").execute()
        
        if not response.data:
            return []
        
        order_ids = [bid["order_id"] for bid in response.data]
        
        # Get order details
        orders_response = supabase_client.table("orders").select("id, weight_kg, crop, pickup_date, pickup_slot").in_("id", order_ids).execute()
        
        return orders_response.data if orders_response.data else []
        
    except Exception as e:
        print(f"Error getting accepted bids: {e}")
        return []


def get_driver_pending_bids(driver_name: str) -> List[Dict]:
    """
    Get all open (pending) bids for a driver.
    These might win, so we consider them in capacity calculation.
    """
    if not supabase_client:
        return []
    
    try:
        response = supabase_client.table("bids").select("order_id").eq("driver_name", driver_name).eq("status", "Open").eq("bid_type", "order").execute()
        
        if not response.data:
            return []
        
        order_ids = [bid["order_id"] for bid in response.data]
        
        orders_response = supabase_client.table("orders").select("id, weight_kg, crop, pickup_date, pickup_slot").in_("id", order_ids).execute()
        
        return orders_response.data if orders_response.data else []
        
    except Exception as e:
        print(f"Error getting pending bids: {e}")
        return []


def calculate_capacity_utilization(driver_name: str) -> Dict:
    """
    Calculate driver's current capacity utilization using dynamic real-time approach.
    Returns dict with total capacity, used capacity, available capacity.
    """
    try:
        from services.dynamic_capacity_service import calculate_capacity_at_time, get_driver_schedule
        from datetime import datetime, timezone, timedelta
        
        IST = timezone(timedelta(hours=5, minutes=30))
        
        total_capacity = get_driver_capacity(driver_name) or 1000
        
        # Calculate current load (right now)
        now = datetime.now(IST)
        current_capacity = calculate_capacity_at_time(driver_name, now, total_capacity)
        
        # Get schedule for additional info
        schedule = get_driver_schedule(driver_name)
        
        # Count confirmed (accepted) and pending bids
        confirmed_orders = len([s for s in schedule if not s.get("delivered")])
        
        pending_orders = get_driver_pending_bids(driver_name)
        pending_weight = sum(order["weight_kg"] for order in pending_orders)
        
        current_load = current_capacity["current_load"]
        available = current_capacity["available_capacity"]
        
        # If there are pending bids, reduce available capacity
        available_after_pending = max(0, available - pending_weight)
        total_committed = current_load + pending_weight
        
        utilization_pct = round((total_committed / total_capacity) * 100, 1)
        
        return {
            "total_capacity": total_capacity,
            "confirmed_weight": current_load,
            "pending_weight": pending_weight,
            "total_committed": total_committed,
            "available_capacity": max(0, available_after_pending),
            "utilization_percent": min(100, utilization_pct),
            "at_capacity": available_after_pending <= 0,
            "confirmed_orders": confirmed_orders,
            "pending_bids": len(pending_orders),
            "orders_onboard_now": current_capacity["num_orders_onboard"]
        }
        
    except Exception as e:
        print(f"Error calculating capacity: {e}")
        return {
            "total_capacity": 1000,
            "confirmed_weight": 0,
            "pending_weight": 0,
            "total_committed": 0,
            "available_capacity": 1000,
            "utilization_percent": 0,
            "at_capacity": False,
            "confirmed_orders": 0,
            "pending_bids": 0,
            "orders_onboard_now": 0
        }


def can_bid_on_order(driver_name: str, order_weight: int, pickup_date: str = None, pickup_slot: str = None) -> Dict:
    """
    Check if driver can bid on an order based on dynamic capacity.
    If pickup_date/slot provided, checks capacity at that specific time.
    """
    try:
        if pickup_date and pickup_slot:
            # Use dynamic capacity calculation for specific time
            from services.dynamic_capacity_service import get_capacity_for_new_bid
            capacity_at_pickup = get_capacity_for_new_bid(driver_name, pickup_date, pickup_slot)
            
            available = capacity_at_pickup["available_at_pickup"]
            
            if order_weight > available:
                return {
                    "can_bid": False,
                    "reason": f"Insufficient capacity at pickup time. Need {order_weight}kg but only {available}kg available at {pickup_slot} slot",
                    "available": available,
                    "needed": order_weight,
                    "current_load_at_pickup": capacity_at_pickup["current_load_at_pickup"]
                }
            
            return {
                "can_bid": True,
                "reason": "Sufficient capacity at pickup time",
                "available": available,
                "needed": order_weight,
                "current_load_at_pickup": capacity_at_pickup["current_load_at_pickup"]
            }
        else:
            # Fallback to current capacity
            capacity_info = calculate_capacity_utilization(driver_name)
            
            if capacity_info["at_capacity"]:
                return {
                    "can_bid": False,
                    "reason": "Vehicle at full capacity",
                    "available": 0,
                    "needed": order_weight
                }
            
            if order_weight > capacity_info["available_capacity"]:
                return {
                    "can_bid": False,
                    "reason": f"Order too heavy. Need {order_weight}kg but only {capacity_info['available_capacity']}kg available",
                    "available": capacity_info["available_capacity"],
                    "needed": order_weight
                }
            
            return {
                "can_bid": True,
                "reason": "Sufficient capacity",
                "available": capacity_info["available_capacity"],
                "needed": order_weight
            }
            
    except Exception as e:
        print(f"Error in can_bid_on_order: {e}")
        return {
            "can_bid": True,
            "reason": "Error checking capacity, allowing bid",
            "available": 1000,
            "needed": order_weight
        }
