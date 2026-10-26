"""
Slot Bid Closer Service - Automatically closes bids and assigns winners
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from database.db import supabase_client

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

# Slot time mappings (24-hour format) - start and end
SLOT_TIMES = {
    "morning": {"start": 6, "end": 10},      # 6:00 AM - 10:00 AM
    "afternoon": {"start": 11, "end": 15},   # 11:00 AM - 3:00 PM
    "evening": {"start": 16, "end": 20}      # 4:00 PM - 8:00 PM
}

# Slot order for calculating "previous slot"
SLOT_ORDER = ["morning", "afternoon", "evening"]


def get_previous_slot_end_time(slot_date: str, slot_time: str) -> datetime:
    """
    Get the end time of the previous slot.
    This is when bidding closes for the current slot.
    
    Examples:
    - Morning slot → Closes at Evening end (8 PM) previous day
    - Afternoon slot → Closes at Morning end (10 AM) same day
    - Evening slot → Closes at Afternoon end (3 PM) same day
    """
    try:
        date_obj = datetime.fromisoformat(slot_date).date()
        
        current_slot_index = SLOT_ORDER.index(slot_time)
        
        if current_slot_index == 0:
            # Morning slot - close at end of Evening slot previous day
            prev_date = date_obj - timedelta(days=1)
            prev_slot = "evening"
        else:
            # Afternoon/Evening - close at end of previous slot same day
            prev_date = date_obj
            prev_slot = SLOT_ORDER[current_slot_index - 1]
        
        end_hour = SLOT_TIMES[prev_slot]["end"]
        
        closing_time = datetime.combine(prev_date, datetime.min.time()).replace(
            hour=end_hour,
            minute=0,
            second=0,
            tzinfo=IST
        )
        
        return closing_time
        
    except Exception as e:
        print(f"Error calculating previous slot end time: {e}")
        return None


def should_close_slot(slot_date: str, slot_time: str) -> bool:
    """
    Determine if a slot should be closed based on time.
    Closes at the end of the previous slot.
    """
    try:
        closing_time = get_previous_slot_end_time(slot_date, slot_time)
        
        if not closing_time:
            return False
        
        # Current time in IST
        now = datetime.now(IST)
        
        # Should close if we're past the closing time
        return now >= closing_time
        
    except Exception as e:
        print(f"Error checking slot closure time: {e}")
        return False


def get_winning_bid(slot_date: str, slot_time: str) -> Optional[Dict]:
    """
    Get the winning bid (lowest amount) for a specific slot.
    Only considers Open bids.
    """
    if not supabase_client:
        return None
    
    try:
        # Query all open bids for this slot, sorted by amount
        response = supabase_client.table("bids").select("*").eq("pickup_date", slot_date).eq("pickup_slot", slot_time).eq("bid_type", "slot").eq("status", "Open").order("amount", desc=False).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]  # Lowest bid
        
        return None
        
    except Exception as e:
        print(f"Error getting winning bid: {e}")
        return None


def close_slot_and_assign_winner(slot_date: str, slot_time: str) -> Dict:
    """
    Close bidding for a slot and assign the winning driver to all orders.
    Returns summary of actions taken.
    """
    if not supabase_client:
        return {"success": False, "error": "Database not configured"}
    
    try:
        result = {
            "success": False,
            "slot_date": slot_date,
            "slot_time": slot_time,
            "winner": None,
            "orders_assigned": 0,
            "bids_closed": 0,
            "message": ""
        }
        
        # Get the winning bid
        winning_bid = get_winning_bid(slot_date, slot_time)
        
        if not winning_bid:
            # When slot closes without bids, mark pending orders in this slot as Bidding Closed
            supabase_client.table("orders").update({
                "status": "Bidding Closed"
            }).eq("pickup_date", slot_date).eq("pickup_slot", slot_time).in_("status", ["Pending", "Cluster Forming"]).execute()
            
            result["message"] = f"No bids found for {slot_date} {slot_time} slot. Marked orders as Bidding Closed."
            result["success"] = True
            return result
        
        winner_id = winning_bid["id"]
        winner_name = winning_bid["driver_name"]
        winner_amount = winning_bid["amount"]
        
        # 1. Update winning bid status to "Accepted"
        supabase_client.table("bids").update({"status": "Accepted"}).eq("id", winner_id).execute()
        
        # 2. Update losing bids status to "Rejected"
        supabase_client.table("bids").update({"status": "Rejected"}).eq("pickup_date", slot_date).eq("pickup_slot", slot_time).eq("bid_type", "slot").neq("id", winner_id).execute()
        
        # Count total bids
        all_bids = supabase_client.table("bids").select("id").eq("pickup_date", slot_date).eq("pickup_slot", slot_time).eq("bid_type", "slot").execute()
        result["bids_closed"] = len(all_bids.data) if all_bids.data else 0
        
        # 3. Get all orders for this slot
        orders_response = supabase_client.table("orders").select("*").eq("pickup_date", slot_date).eq("pickup_slot", slot_time).in_("status", ["Pending", "Cluster Forming"]).execute()
        
        if not orders_response.data:
            result["message"] = f"No orders found for {slot_date} {slot_time} slot"
            result["winner"] = {"name": winner_name, "amount": winner_amount}
            return result
        
        # 4. Assign winner to all orders
        order_ids = [order["id"] for order in orders_response.data]
        
        supabase_client.table("orders").update({
            "status": "Driver Assigned",
            "assigned_driver": winner_name,
            "final_cost": winner_amount
        }).in_("id", order_ids).execute()
        
        result["orders_assigned"] = len(order_ids)
        result["winner"] = {
            "name": winner_name,
            "amount": winner_amount,
            "bid_id": winner_id
        }
        result["success"] = True
        result["message"] = f"Slot closed. {winner_name} won with ₹{winner_amount}. Assigned to {len(order_ids)} orders."
        
        return result
        
    except Exception as e:
        print(f"Error closing slot: {e}")
        return {
            "success": False,
            "error": str(e),
            "slot_date": slot_date,
            "slot_time": slot_time
        }


def process_all_closable_slots() -> List[Dict]:
    """
    Check all slots with open bids or pending orders and close those that should be closed.
    Called periodically by scheduler.
    """
    if not supabase_client:
        return []
    
    results = []
    
    try:
        # Get slots from open bids
        bid_slots = supabase_client.table("bids").select("pickup_date, pickup_slot").eq("bid_type", "slot").eq("status", "Open").execute()
        # Also get slots from open orders
        order_slots = supabase_client.table("orders").select("pickup_date, pickup_slot").in_("status", ["Pending", "Cluster Forming"]).execute()
        
        all_slot_rows = (bid_slots.data or []) + (order_slots.data or [])
        
        if not all_slot_rows:
            return []
        
        # Get unique date/slot combinations
        slots = {}
        for row in all_slot_rows:
            if not row.get("pickup_date") or not row.get("pickup_slot"):
                continue
            key = f"{row['pickup_date']}_{row['pickup_slot']}"
            if key not in slots:
                slots[key] = {
                    "date": row["pickup_date"],
                    "slot": row["pickup_slot"]
                }
        
        # Check each slot
        for key, slot_info in slots.items():
            slot_date = slot_info["date"]
            slot_time = slot_info["slot"]
            
            if should_close_slot(slot_date, slot_time):
                print(f"[Bid Closer] Closing slot: {slot_date} {slot_time}")
                result = close_slot_and_assign_winner(slot_date, slot_time)
                results.append(result)
            else:
                print(f"[Bid Closer] Slot not ready to close: {slot_date} {slot_time}")
        
        return results
        
    except Exception as e:
        print(f"Error processing closable slots: {e}")
        return []


def get_slot_closing_time(slot_date: str, slot_time: str) -> Optional[datetime]:
    """
    Get the closing time for a specific slot.
    Returns datetime in IST when bidding will close (end of previous slot).
    """
    return get_previous_slot_end_time(slot_date, slot_time)


def close_order_and_assign_winner(order_id: str) -> Dict:
    """
    Close bidding for a specific order and assign the winning driver.
    """
    if not supabase_client:
        return {"success": False, "error": "Database not configured"}
    
    try:
        result = {
            "success": False,
            "order_id": order_id,
            "winner": None,
            "message": ""
        }
        
        # Get order
        order_resp = supabase_client.table("orders").select("*").eq("id", order_id).execute()
        if not order_resp.data:
            result["message"] = f"Order {order_id} not found"
            return result
        
        order = order_resp.data[0]
        
        # Query open bids for this order, sorted by amount (lowest first)
        bids_resp = supabase_client.table("bids").select("*").eq("order_id", order_id).eq("bid_type", "order").eq("status", "Open").order("amount", desc=False).execute()
        
        if not bids_resp.data or len(bids_resp.data) == 0:
            # No bids placed before closing time
            supabase_client.table("orders").update({
                "status": "Bidding Closed"
            }).eq("id", order_id).execute()
            
            result["message"] = f"No bids found for order {order_id}. Marked as Bidding Closed."
            result["success"] = True
            return result
        
        winning_bid = bids_resp.data[0]
        winner_id = winning_bid["id"]
        winner_name = winning_bid["driver_name"]
        winner_amount = winning_bid["amount"]
        
        # 1. Update winning bid to Accepted
        supabase_client.table("bids").update({"status": "Accepted"}).eq("id", winner_id).execute()
        
        # 2. Update other bids for this order to Rejected
        supabase_client.table("bids").update({"status": "Rejected"}).eq("order_id", order_id).eq("bid_type", "order").neq("id", winner_id).execute()
        
        # 3. Update order status and assignment
        supabase_client.table("orders").update({
            "status": "Driver Assigned",
            "assigned_driver": winner_name,
            "final_cost": winner_amount
        }).eq("id", order_id).execute()
        
        result["success"] = True
        result["winner"] = {
            "driver_name": winner_name,
            "amount": winner_amount,
            "bid_id": winner_id
        }
        result["message"] = f"Order {order_id} assigned to {winner_name} for ₹{winner_amount}."
        return result
        
    except Exception as e:
        print(f"Error closing order {order_id}: {e}")
        return {"success": False, "error": str(e), "order_id": order_id}


def process_all_closable_orders() -> List[Dict]:
    """
    Check all orders with open bids and close those whose slots have passed.
    Called periodically by scheduler.
    """
    if not supabase_client:
        return []
    
    results = []
    
    try:
        # Get all orders that are still pending / cluster forming
        response = supabase_client.table("orders").select("*").in_("status", ["Pending", "Cluster Forming"]).execute()
        
        if not response.data:
            return []
        
        for order in response.data:
            if not order.get("pickup_date") or not order.get("pickup_slot"):
                continue
            
            slot_date = order["pickup_date"]
            slot_time = order["pickup_slot"]
            order_id = order["id"]
            
            if should_close_slot(slot_date, slot_time):
                print(f"[Bid Closer] Closing order: {order_id} ({slot_date} {slot_time})")
                result = close_order_and_assign_winner(order_id)
                results.append(result)
        
        return results
        
    except Exception as e:
        print(f"Error processing closable orders: {e}")
        return []
