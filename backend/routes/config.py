"""
routes/config.py

Provides system configuration endpoints for frontend consumption.
"""

from fastapi import APIRouter
from services.rate_config import VEHICLE_CLASSES, MIN_RATE_PER_KG, FALLBACK_RATE_PER_KG
from services.mandi_config import MANDI_COORDS

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/pricing")
def get_pricing_config():
    """
    Returns the single-source-of-truth pricing rules and rate configurations
    so the frontend can calculate individual costs offline.
    """
    return {
        "vehicle_classes": VEHICLE_CLASSES,
        "min_rate_per_kg": MIN_RATE_PER_KG,
        "fallback_rate_per_kg": FALLBACK_RATE_PER_KG,
        "mandi_coords": MANDI_COORDS,
    }
