from fastapi import APIRouter

from database.db import supabase_client
from models.schemas import Driver

router = APIRouter()


@router.get("", response_model=list[Driver])
def list_drivers():
    if not supabase_client:
        return []
    try:
        response = supabase_client.table("drivers").select("*, users(name, phone)").execute()
        drivers = []
        for row in response.data:
            user_info = row.get("users", {}) or {}
            drivers.append(Driver(
                id=str(row["id"]),
                name=user_info.get("name", "Unknown Driver"),
                phone=user_info.get("phone", ""),
                vehicle_number=row["vehicle_number"],
                vehicle_type=row["vehicle_type"],
                license_number=row["license_number"],
                reliability_score=row["reliability_score"]
            ))
        return drivers
    except Exception as e:
        print(f"Error querying drivers from Supabase: {e}")
        return []




# ===================================================================
# DRIVER PROFILE & STATISTICS
# ===================================================================

from fastapi import HTTPException
from typing import Optional

@router.get("/{driver_name}/profile")
def get_driver_profile(driver_name: str):
    """
    Get complete driver profile including statistics and current status.
    
    Returns:
    - Basic info (name, phone, vehicle, license)
    - Performance stats (reliability score, completed trips, rating)
    - Current assignments and capacity
    - Recent bidding activity
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Database client not configured")
    
    try:
        # Get user info
        user_response = supabase_client.table("users")\
            .select("*")\
            .eq("name", driver_name)\
            .eq("role", "driver")\
            .execute()
        
        if not user_response.data:
            raise HTTPException(status_code=404, detail=f"Driver {driver_name} not found")
        
        user = user_response.data[0]
        user_id = user["id"]
        
        # Get driver details
        driver_response = supabase_client.table("drivers")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        
        if not driver_response.data:
            raise HTTPException(status_code=404, detail=f"Driver record not found for {driver_name}")
        
        driver = driver_response.data[0]
        
        # Get vehicle info
        vehicle_response = supabase_client.table("vehicles")\
            .select("*")\
            .eq("driver_id", driver["id"])\
            .execute()
        
        vehicle = vehicle_response.data[0] if vehicle_response.data else None
        
        # Get current assignments (accepted bids)
        assignments_response = supabase_client.table("bids")\
            .select("*, bundles(*)")\
            .eq("driver_name", driver_name)\
            .eq("status", "Accepted")\
            .eq("bid_type", "cluster")\
            .execute()
        
        current_assignments = len(assignments_response.data) if assignments_response.data else 0
        
        # Get bidding statistics (from bid_history if available, else from bids table)
        try:
            stats_response = supabase_client.table("bid_history")\
                .select("bid_status, won")\
                .eq("driver_name", driver_name)\
                .execute()
            
            if stats_response.data:
                total_bids = len(stats_response.data)
                bids_won = sum(1 for b in stats_response.data if b.get("won"))
                win_rate = round((bids_won / total_bids * 100), 1) if total_bids > 0 else 0
            else:
                total_bids = 0
                bids_won = 0
                win_rate = 0
        except:
            # Fallback if bid_history table doesn't exist yet
            bids_response = supabase_client.table("bids")\
                .select("status")\
                .eq("driver_name", driver_name)\
                .execute()
            
            total_bids = len(bids_response.data) if bids_response.data else 0
            bids_won = sum(1 for b in bids_response.data if b.get("status") == "Accepted") if bids_response.data else 0
            win_rate = round((bids_won / total_bids * 100), 1) if total_bids > 0 else 0
        
        # Get capacity info
        from services.capacity_service import calculate_capacity_utilization
        capacity_info = calculate_capacity_utilization(driver_name)
        
        return {
            "driver_name": driver_name,
            "profile": {
                "phone": user.get("phone"),
                "village": user.get("village"),
                "preferred_language": user.get("preferred_language", "ta"),
                "created_at": user.get("created_at")
            },
            "vehicle": {
                "vehicle_number": driver.get("vehicle_number"),
                "vehicle_type": driver.get("vehicle_type"),
                "license_number": driver.get("license_number"),
                "capacity_kg": vehicle.get("capacity_kg") if vehicle else None
            },
            "performance": {
                "reliability_score": driver.get("reliability_score", 90),
                "completed_trips": driver.get("completed_trips", 0),
                "rating": float(driver.get("rating", 4.5)),
                "total_bids": total_bids,
                "bids_won": bids_won,
                "win_rate": win_rate
            },
            "current_status": {
                "active_assignments": current_assignments,
                "capacity_used": capacity_info.get("utilization_percent", 0),
                "available_capacity": capacity_info.get("available_capacity", 0),
                "at_capacity": capacity_info.get("at_capacity", False)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching driver profile: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{driver_name}/availability")
def check_driver_availability(
    driver_name: str,
    pickup_date: Optional[str] = None,
    pickup_slot: Optional[str] = None
):
    """
    Check if driver is available for a specific date/slot.
    
    Returns:
    - Is available (boolean)
    - Reason if not available
    - Conflicting assignments
    - Available capacity at that time
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Database client not configured")
    
    try:
        # Get all accepted bids for this driver
        accepted_response = supabase_client.table("bids")\
            .select("*, bundles(*)")\
            .eq("driver_name", driver_name)\
            .eq("status", "Accepted")\
            .eq("bid_type", "cluster")\
            .execute()
        
        conflicts = []
        
        if accepted_response.data and pickup_date and pickup_slot:
            # Check for timing conflicts
            for bid in accepted_response.data:
                cluster_id = bid.get("bundle_id")
                
                # Get orders in this cluster
                orders_response = supabase_client.table("orders")\
                    .select("pickup_date, pickup_slot")\
                    .eq("cluster_id", cluster_id)\
                    .execute()
                
                if orders_response.data:
                    for order in orders_response.data:
                        if order.get("pickup_date") == pickup_date and order.get("pickup_slot") == pickup_slot:
                            conflicts.append({
                                "cluster_id": cluster_id,
                                "bid_id": bid["id"],
                                "pickup_date": pickup_date,
                                "pickup_slot": pickup_slot
                            })
        
        is_available = len(conflicts) == 0
        
        # Get capacity at that time if date/slot provided
        available_capacity = None
        if pickup_date and pickup_slot:
            from services.capacity_service import can_bid_on_order
            # Check with 0 weight just to get available capacity
            capacity_check = can_bid_on_order(driver_name, 0, pickup_date, pickup_slot)
            available_capacity = capacity_check.get("available", 0)
        
        return {
            "driver_name": driver_name,
            "is_available": is_available,
            "pickup_date": pickup_date,
            "pickup_slot": pickup_slot,
            "conflicts": conflicts,
            "available_capacity": available_capacity,
            "reason": "Already assigned to another cluster" if conflicts else "Available"
        }
        
    except Exception as e:
        print(f"Error checking availability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leaderboard")
def get_driver_leaderboard(metric: str = "win_rate", limit: int = 10):
    """
    Get driver leaderboard ranked by various metrics.
    
    Metrics:
    - win_rate: Highest bid win rate
    - trips: Most completed trips
    - rating: Highest customer rating
    - reliability: Highest reliability score
    - bids: Most bids placed
    
    Useful for:
    - Showing top performers
    - Driver gamification
    - Performance benchmarking
    """
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Database client not configured")
    
    try:
        # Get all drivers
        drivers_response = supabase_client.table("drivers")\
            .select("*, users(name, phone)")\
            .execute()
        
        if not drivers_response.data:
            return {
                "metric": metric,
                "leaderboard": []
            }
        
        leaderboard = []
        
        for driver_row in drivers_response.data:
            user_info = driver_row.get("users", {}) or {}
            driver_name = user_info.get("name", "Unknown")
            
            # Get bidding stats if using win_rate or bids metric
            if metric in ["win_rate", "bids"]:
                try:
                    stats_response = supabase_client.table("bid_history")\
                        .select("won")\
                        .eq("driver_name", driver_name)\
                        .execute()
                    
                    total_bids = len(stats_response.data) if stats_response.data else 0
                    bids_won = sum(1 for b in stats_response.data if b.get("won")) if stats_response.data else 0
                    win_rate = round((bids_won / total_bids * 100), 1) if total_bids > 0 else 0
                except:
                    total_bids = 0
                    win_rate = 0
            else:
                total_bids = 0
                win_rate = 0
            
            leaderboard.append({
                "driver_name": driver_name,
                "phone": user_info.get("phone"),
                "vehicle_type": driver_row.get("vehicle_type"),
                "completed_trips": driver_row.get("completed_trips", 0),
                "rating": float(driver_row.get("rating", 4.5)),
                "reliability_score": driver_row.get("reliability_score", 90),
                "total_bids": total_bids,
                "win_rate": win_rate
            })
        
        # Sort by requested metric
        if metric == "win_rate":
            leaderboard.sort(key=lambda d: d["win_rate"], reverse=True)
        elif metric == "trips":
            leaderboard.sort(key=lambda d: d["completed_trips"], reverse=True)
        elif metric == "rating":
            leaderboard.sort(key=lambda d: d["rating"], reverse=True)
        elif metric == "reliability":
            leaderboard.sort(key=lambda d: d["reliability_score"], reverse=True)
        elif metric == "bids":
            leaderboard.sort(key=lambda d: d["total_bids"], reverse=True)
        
        return {
            "metric": metric,
            "total_drivers": len(leaderboard),
            "leaderboard": leaderboard[:limit]
        }
        
    except Exception as e:
        print(f"Error generating leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))
