from database.db import supabase_client
from services.clustering_service import next_slot_time, slot_label
from services.order_status import ACTIVE_STATUSES
from services.rate_config import get_vehicle_class_for_weight

TRUCK_CAPACITY_KG = 1100  # Standard cooperative truck capacity


def generate_recommendation() -> dict:
    if not supabase_client:
        return {
            "farmers": 0,
            "total_weight_kg": 0,
            "truck_utilization": 0,
            "estimated_savings": 0,
            "spoilage_risk": "Low",
            "departure_time": slot_label(next_slot_time()),
        }
    try:
        # Only count active orders (not completed/cancelled)
        response = supabase_client.table("orders").select("*").in_(
            "status", ACTIVE_STATUSES
        ).execute()
        orders = response.data

        if not orders:
            return {
                "farmers": 0,
                "total_weight_kg": 0,
                "truck_utilization": 0,
                "estimated_savings": 0,
                "spoilage_risk": "Low",
                "departure_time": slot_label(next_slot_time()),
            }

        total_weight = sum(int(o["weight_kg"]) for o in orders)
        individual_cost = sum(int(o["individual_cost"]) for o in orders)
        shared_cost = sum(int(o["shared_cost"]) for o in orders)

        # Spoilage risk based on crops present
        crops = set(o["crop"].lower() for o in orders)
        has_tomato = "tomato" in crops or "tomatoes" in crops
        has_sensitive = any(c in crops for c in ["spinach", "leafy", "green", "cabbage", "cauliflower"])

        if has_tomato and has_sensitive:
            spoilage_risk = "High"
        elif has_tomato or len(orders) > 4:
            spoilage_risk = "Medium"
        else:
            spoilage_risk = "Low"

        unique_farmers = len(set(o.get("farmer_id") or o["id"] for o in orders))

        return {
            "farmers": unique_farmers,
            "total_weight_kg": total_weight,
            "truck_utilization": min(100, round((total_weight / TRUCK_CAPACITY_KG) * 100)),
            "estimated_savings": max(0, individual_cost - shared_cost),
            "spoilage_risk": spoilage_risk,
            "departure_time": slot_label(next_slot_time()),
        }
    except Exception as e:
        print(f"Error generating recommendation: {e}")
        return {
            "farmers": 0,
            "total_weight_kg": 0,
            "truck_utilization": 0,
            "estimated_savings": 0,
            "spoilage_risk": "Low",
            "departure_time": slot_label(next_slot_time()),
        }
