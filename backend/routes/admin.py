from fastapi import APIRouter
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from database.db import supabase_client
from services.clustering_service import build_clusters, next_slot_time, slot_label, IST
from services.recommendation_service import generate_recommendation
from services.sms_service import sms_service

router = APIRouter()


@router.post("/run-clustering")
def run_clustering():
    """Manually trigger clustering — useful for testing without waiting for slot."""
    try:
        clusters = build_clusters()

        # SMS: notify all drivers about new clusters
        if clusters:
            cluster_ids = [c["id"] for c in clusters if c.get("id")]
            if cluster_ids:
                try:
                    sms_result = sms_service.notify_drivers_cluster_created(cluster_ids)
                    print(f"📱 Cluster SMS — sent: {sms_result.get('sms_sent', 0)}, failed: {sms_result.get('sms_failed', 0)}")
                except Exception as sms_err:
                    print(f"⚠️ Cluster SMS notification failed (non-critical): {sms_err}")

        return {
            "success": True,
            "clusters_formed": len(clusters),
            "clusters": clusters,
            "next_slot": slot_label(next_slot_time()),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/slot-status")
def slot_status():
    """Returns current slot info and how many Pending orders are waiting."""
    pending_count = 0
    if supabase_client:
        try:
            res = supabase_client.table("orders").select("id", count="exact").eq("status", "Pending").execute()
            pending_count = res.count or 0
        except Exception:
            pass

    slot_dt = next_slot_time()
    now_ist = datetime.now(IST)
    wait_seconds = (slot_dt - now_ist).total_seconds()

    return {
        "next_slot": slot_label(slot_dt),
        "next_slot_iso": slot_dt.isoformat(),
        "wait_minutes": round(wait_seconds / 60),
        "pending_orders": pending_count,
    }


def _build_savings_trend(orders: list[dict]) -> list[dict]:
    """
    Build a 7-day savings trend from real order data.
    Groups orders by day of week they were created and sums savings per day.
    """
    DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    daily_savings: dict[int, int] = defaultdict(int)

    for o in orders:
        try:
            created = o.get("created_at", "")
            if created:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                day_index = dt.weekday()  # 0=Mon, 6=Sun
                savings = int(o.get("individual_cost", 0)) - int(o.get("shared_cost", 0))
                if savings > 0:
                    daily_savings[day_index] += savings
        except Exception:
            continue

    return [
        {"label": DAY_LABELS[i], "value": daily_savings.get(i, 0)}
        for i in range(7)
    ]


def _get_last_extraction(orders: list[dict]) -> dict:
    """Return extraction info from the most recent voice booking, or empty dict."""
    voice_orders = [o for o in orders if o.get("source") == "Voice Call" and o.get("confidence")]
    if not voice_orders:
        return {
            "transcript": "No voice bookings yet.",
            "extracted": {"farmer_name": "—", "village": "—", "crop": "—", "weight": "—"},
            "confidence": {"farmer_name": 0, "village": 0, "crop": 0, "weight": 0},
        }
    latest = voice_orders[0]
    return {
        "transcript": f"{latest.get('farmer_name', '—')} from {latest.get('village', '—')} — {latest.get('crop', '—')} {latest.get('weight_kg', '—')} kg",
        "extracted": {
            "farmer_name": latest.get("farmer_name", "—"),
            "village": latest.get("village", "—"),
            "crop": latest.get("crop", "—"),
            "weight": latest.get("weight_kg", "—"),
        },
        "confidence": latest.get("confidence") or {"farmer_name": 90, "village": 90, "crop": 90, "weight": 90},
    }


@router.get("/snapshot")
def snapshot():
    if not supabase_client:
        return {
            "extraction": _get_last_extraction([]),
            "recommendation": generate_recommendation(),
            "orders": [],
            "bids": [],
            "slot": {"next_slot": slot_label(next_slot_time()), "wait_minutes": 0, "pending_orders": 0},
            "savingsTrend": [],
        }

    try:
        orders_res = supabase_client.table("orders").select("*").order("created_at", desc=True).execute()
        orders = orders_res.data

        bids_res = supabase_client.table("bids").select("*").execute()
        bids = bids_res.data

        recommendation = generate_recommendation()
        pending_count = sum(1 for o in orders if o["status"] == "Pending")

        slot_dt = next_slot_time()
        now_ist = datetime.now(IST)
        wait_minutes = round((slot_dt - now_ist).total_seconds() / 60)

        return {
            "extraction": _get_last_extraction(orders),
            "recommendation": recommendation,
            "orders": orders,
            "bids": bids,
            "slot": {
                "next_slot": slot_label(slot_dt),
                "wait_minutes": wait_minutes,
                "pending_orders": pending_count,
            },
            "savingsTrend": _build_savings_trend(orders),
        }
    except Exception as e:
        print(f"Error preparing snapshot: {e}")
        return {
            "extraction": _get_last_extraction([]),
            "recommendation": generate_recommendation(),
            "orders": [],
            "bids": [],
            "slot": {"next_slot": slot_label(next_slot_time()), "wait_minutes": 0, "pending_orders": 0},
            "savingsTrend": [],
        }
