"""
Farmer-specific SMS notifications
All farmer-related SMS logic in one place
"""

import sys
import os
from typing import List, Dict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.db import supabase_client
from backend.services.sms_service import sms_service
from sms_integration.message_templates import SMSTemplates


class FarmerNotifier:
    """Handle all farmer notifications"""
    
    def __init__(self):
        self.sms_service = sms_service
    
    def notify_order_confirmed(self, farmer_name: str, farmer_phone: str, order_id: str, amount: int) -> bool:
        """
        Notify farmer their order is confirmed
        
        Args:
            farmer_name: Farmer's name
            farmer_phone: Farmer's phone
            order_id: Order/booking ID
            amount: Order amount
        
        Returns:
            bool: True if SMS sent successfully
        """
        message = (
            f"✅ Order Confirmed - {farmer_name}\n\n"
            f"Order ID: {order_id}\n"
            f"Amount: ₹{amount}\n\n"
            f"Your order is being processed.\n"
            f"Driver will be assigned soon."
        )
        
        return self.sms_service.send_sms(
            phone=farmer_phone,
            message=message,
            sms_type="order_confirmed"
        )
    
    def notify_clustered(self, farmer_name: str, farmer_phone: str, order_id: str, cluster_id: str, savings: int) -> bool:
        """
        Notify farmer their order has been clustered
        
        Args:
            farmer_name: Farmer's name
            farmer_phone: Farmer's phone
            order_id: Order ID
            cluster_id: Cluster ID
            savings: Estimated savings
        
        Returns:
            bool: True if SMS sent successfully
        """
        message = (
            f"🎉 Cooperative Savings - {farmer_name}\n\n"
            f"Order: {order_id}\n"
            f"Bundled with other farmers\n"
            f"Estimated savings: ₹{savings}\n\n"
            f"Driver bidding in progress..."
        )
        
        return self.sms_service.send_sms(
            phone=farmer_phone,
            message=message,
            sms_type="order_clustered"
        )
    
    def notify_driver_assigned(
        self,
        farmer_name: str,
        farmer_phone: str,
        driver_name: str,
        driver_phone: str,
        order_id: str,
        pickup_time: str,
        amount: int
    ) -> bool:
        """
        Notify farmer that driver has been assigned
        
        Args:
            farmer_name: Farmer's name
            farmer_phone: Farmer's phone
            driver_name: Driver's name
            driver_phone: Driver's phone
            order_id: Order ID
            pickup_time: Pickup time
            amount: Final amount
        
        Returns:
            bool: True if SMS sent successfully
        """
        message = SMSTemplates.driver_assigned_farmer(
            farmer_name=farmer_name,
            driver_name=driver_name,
            driver_phone=driver_phone,
            order_id=order_id,
            pickup_time=pickup_time,
            amount=amount
        )
        
        return self.sms_service.send_sms(
            phone=farmer_phone,
            message=message,
            sms_type="driver_assigned"
        )
    
    def notify_pickup_approaching(self, farmer_name: str, farmer_phone: str, driver_name: str, minutes: int) -> bool:
        """
        Notify farmer that pickup is approaching
        
        Args:
            farmer_name: Farmer's name
            farmer_phone: Farmer's phone
            driver_name: Driver's name
            minutes: Minutes until pickup
        
        Returns:
            bool: True if SMS sent successfully
        """
        message = SMSTemplates.pickup_reminder_farmer(
            farmer_name=farmer_name,
            driver_name=driver_name,
            minutes=minutes
        )
        
        return self.sms_service.send_sms(
            phone=farmer_phone,
            message=message,
            sms_type="pickup_approaching"
        )
    
    def notify_delivery_complete(self, farmer_name: str, farmer_phone: str, order_id: str, amount: int, savings: int) -> bool:
        """
        Notify farmer delivery is complete
        
        Args:
            farmer_name: Farmer's name
            farmer_phone: Farmer's phone
            order_id: Order ID
            amount: Final amount paid
            savings: Amount saved
        
        Returns:
            bool: True if SMS sent successfully
        """
        message = SMSTemplates.delivery_complete_farmer(
            farmer_name=farmer_name,
            order_id=order_id,
            amount=amount,
            savings=savings
        )
        
        return self.sms_service.send_sms(
            phone=farmer_phone,
            message=message,
            sms_type="delivery_complete"
        )
    
    def notify_payment_received(self, farmer_name: str, farmer_phone: str, order_id: str, amount: int) -> bool:
        """
        Notify farmer payment has been received
        
        Args:
            farmer_name: Farmer's name
            farmer_phone: Farmer's phone
            order_id: Order ID
            amount: Payment amount
        
        Returns:
            bool: True if SMS sent successfully
        """
        message = (
            f"💰 Payment Received - {farmer_name}\n\n"
            f"Order: {order_id}\n"
            f"Amount: ₹{amount}\n\n"
            f"Thank you for using Agrilogi!\n"
            f"Rate your experience in the app. ⭐"
        )
        
        return self.sms_service.send_sms(
            phone=farmer_phone,
            message=message,
            sms_type="payment_received"
        )
    
    def get_farmers_in_cluster(self, cluster_id: str) -> List[Dict]:
        """Get all farmers in a cluster"""
        try:
            response = supabase_client.table("orders")\
                .select("id, farmer_name, phone, shared_cost, individual_cost, crop, weight_kg, village")\
                .eq("cluster_id", cluster_id)\
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching farmers: {e}")
            return []
    
    def get_farmer_by_phone(self, phone: str) -> Dict:
        """Get farmer details by phone number"""
        try:
            response = supabase_client.table("users")\
                .select("*")\
                .eq("role", "farmer")\
                .eq("phone", phone)\
                .limit(1)\
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return {}
        except Exception as e:
            print(f"Error fetching farmer: {e}")
            return {}


# Example usage
if __name__ == "__main__":
    notifier = FarmerNotifier()
    
    print("=== Farmer Notification Examples ===\n")
    
    # Test: Get farmers from a test cluster
    test_cluster_id = "CL-1021-25231-1"  # Replace with actual cluster ID
    farmers = notifier.get_farmers_in_cluster(test_cluster_id)
    
    print(f"Found {len(farmers)} farmers in cluster {test_cluster_id}\n")
    
    if farmers:
        # Test: Notify first farmer
        farmer = farmers[0]
        print(f"Testing notification to: {farmer['farmer_name']} ({farmer['phone']})")
        
        # Example: Driver assigned
        success = notifier.notify_driver_assigned(
            farmer_name=farmer['farmer_name'],
            farmer_phone=farmer['phone'],
            driver_name="Kumar",
            driver_phone="+919876543210",
            order_id=farmer['id'],
            pickup_time="Tomorrow 8:00 AM",
            amount=farmer.get('shared_cost', farmer.get('individual_cost', 0))
        )
        
        if success:
            print("✅ Test SMS sent successfully")
        else:
            print("❌ Test SMS failed (check Twilio config)")
    else:
        print(f"No farmers found in cluster {test_cluster_id}")
        print("Try running clustering first or use a different cluster ID")
