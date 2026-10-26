"""
services/order_status.py

Single source of truth for active and valid order statuses across the backend.
"""

from typing import List

ACTIVE_STATUSES: List[str] = [
    "Pending",
    "Cluster Forming",
    "Driver Assigned",
    "In Transit",
]

COMPLETED_STATUSES: List[str] = [
    "Completed",
]

INACTIVE_STATUSES: List[str] = [
    "Completed",
    "Bidding Closed",
    "Expired",
    "Cancelled",
]


def is_active_status(status: str) -> bool:
    return status in ACTIVE_STATUSES
