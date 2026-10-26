"""
SMS Integration Package for Agrilogi
Handles automated SMS notifications for clustering and bidding events
"""

from sms_integration.sms_triggers import (
    notify_drivers_cluster_created,
    notify_bid_winner,
    get_sms_stats
)

from sms_integration.message_templates import (
    SMSTemplates,
    SMSValidator
)

__version__ = "1.0.0"
__all__ = [
    "notify_drivers_cluster_created",
    "notify_bid_winner",
    "get_sms_stats",
    "SMSTemplates",
    "SMSValidator"
]
