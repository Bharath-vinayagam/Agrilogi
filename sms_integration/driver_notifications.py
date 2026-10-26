"""
Driver-specific SMS notifications
All driver-related SMS logic in one place
"""

import sys
import os
from typing import List, Dict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.db import supabase_client
from backend.services.sms_service import sms_service
from sms_integration.message_templates import SMSTemplates


class DriverNotifier:
    """Handle all driver notifications"""
    
    def __init__(self):
        self.sms_service = sms_service
    
    def notify_new_loads_available(self, driver_phone: str, bundle_count: int, location: str) -> bool:
        """
        Notify individual driver about new loads
        
        Args:
            driver_phone: Driver's phone number
            bundle_count: Number of new bundles
            location: Destination location
        
        Returns:
            bool: True if SMS sent successfully
        """
        message = (
            f"🚛 New Loads Available!\n\n"
            f"{bundle_count} bundle(s) ready for bidding\n"
            f"Location: {location}\n\n"
            f"Login now to place your bid!"
        )
        
        return self.sms_service.send_sms(
            phone=driver_phone,
            message=message,
            sms_type="new_loads"
        )
    
    def notify_outbid(self, driver_name: str, driver_phone: str, cluster_id: str, your_bid: int, lowest_bid: int) -> bool:
        """
        Notify driver they've been outbid
        
        Args:
            driver_name: Driver's name
            driver_phone: Driver's phone
            cluster_id: Cluster ID
            your_bid: Driver's current bid
            lowest_bid: Current lowest bid
        
        Returns:
            bool: True if SMS sent successfully
        """
        message = (
            f"⚠️ Outbid Alert - {driver_name}\n\n"
            f"Bundle: {cluster_id}\n"
            f"Your bid: ₹{your_bid}\n"
            f"Lowest bid: ₹{lowest_bid}\n\n"
            f"Place a lower bid to win!"
        )
        
        return self.sms_service.send_sms(
            phone=driver_phone,
            message=message,
            sms_type="outbid_alert"
        )
    
    def notify_bid_accepted(self, driver_name: str, driver_phone: str, cluster_id: str, amount: int) -> bool:
        """
        Notify driver their bid was accepted
        
        Args:
            driver_name: Driver's name
            driver_phone: Driver's phone
            cluster_id: Cluster ID
            amount: Bid amount
        
        Returns:
            bool: True if SMS sent successfully
        """
        message = (
            f"✅ Bid Accepted - {driver_name}\n\n"
            f"Bundle: {cluster_id}\n"
            f"Amount: ₹{amount}\n\n"
            f"Waiting for bid closing...\n"
            f"Good luck! 🍀"
        )
        
        return self.sms_service.send_sms(
            phone=driver_phone,
            message=message,
            sms_type="bid_accepted"
        )
    
    def notify_bid_lost(self, driver_name: str, driver_phone: str, cluster_id: str, winner_name: str, winning_bid: int) -> bool:
        """
        Notify driver they lost the bid
        
        Args:
            driver_name: Driver's name
            driver_phone: Driver's phone
            cluster_id: Cluster ID
            winner_name: Winner's name
            winning_bid: Winning bid amount
        
        Returns:
            bool: True if SMS sent successfully
        """
        message = (
            f"❌ Bid Closed - {driver_name}\n\n"
            f"Bundle: {cluster_id}\n"
            f"Winner: {winner_name}\n"
            f"Winning bid: ₹{winning_bid}\n\n"
            f"Better luck next time!\n"
            f"New loads coming soon. 🚛"
        )
        
        return self.sms_service.send_sms(
            phone=driver_phone,
            message=message,
            sms_type="bid_lost"
        )
    
    def notify_pickup_reminder(self, driver_name: str, driver_phone: str, cluster_id: str, pickup_time: str, farmer_count: int) -> bool:
        """
        Remind driver about upcoming pickup
        
        Args:
            driver_name: Driver's name
            driver_phone: Driver's phone
            cluster_id: Cluster ID
            pickup_time: Pickup time
            farmer_count: Number of farmers
        
        Returns:
            bool: True if SMS sent successfully
        """
        message = (
            f"⏰ Pickup Reminder - {driver_name}\n\n"
            f"Bundle: {cluster_id}\n"
            f"Time: {pickup_time}\n"
            f"Pickups: {farmer_count} farmers\n\n"
            f"Check app for farmer locations.\n"
            f"Drive safe! 🚛"
        )
        
        return self.sms_service.send_sms(
            phone=driver_phone,
            message=message,
            sms_type="pickup_reminder"
        )
    
    def get_driver_by_name(self, driver_name: str) -> Dict:
        """Get driver details by name"""
        try:
            response = supabase_client.table("users")\
                .select("*")\
                .eq("role", "driver")\
                .eq("name", driver_name)\
                .limit(1)\
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return {}
        except Exception as e:
            print(f"Error fetching driver: {e}")
            return {}
    
    def get_all_drivers(self, active_only: bool = True) -> List[Dict]:
        """Get all drivers from database"""
        try:
            query = supabase_client.table("users")\
                .select("name, phone, id")\
                .eq("role", "driver")
            
            # Add active filter if needed (assuming there's an 'active' field)
            # if active_only:
            #     query = query.eq("active", True)
            
            response = query.execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching drivers: {e}")
            return []


# Example usage
if __name__ == "__main__":
    notifier = DriverNotifier()
    
    print("=== Driver Notification Examples ===\n")
    
    # Test: Get all drivers
    drivers = notifier.get_all_drivers()
    print(f"Found {len(drivers)} drivers in database\n")
    
    if drivers:
        # Test: Notify first driver
        driver = drivers[0]
        print(f"Testing notification to: {driver['name']} ({driver['phone']})")
        
        # Example: New loads available
        success = notifier.notify_new_loads_available(
            driver_phone=driver['phone'],
            bundle_count=3,
            location="Koyambedu Mandi"
        )
        
        if success:
            print("✅ Test SMS sent successfully")
        else:
            print("❌ Test SMS failed (check Twilio config)")
