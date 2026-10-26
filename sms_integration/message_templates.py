"""
SMS Message Templates for Agrilogi
All SMS message formats in one place for easy customization
"""

from typing import Dict, List


class SMSTemplates:
    """SMS message templates for various notifications"""
    
    @staticmethod
    def cluster_created_driver(bundle_count: int, total_weight: int, location: str) -> str:
        """
        SMS to drivers when new clusters are created
        
        Args:
            bundle_count: Number of new bundles
            total_weight: Total weight across all bundles (kg)
            location: Destination location
        """
        return (
            f"🚛 Agrilogi: New Loads Available!\n\n"
            f"{bundle_count} new bundle(s) ready for bidding\n"
            f"Total: {total_weight}kg\n"
            f"Destination: {location}\n\n"
            f"Login to place your bid now!\n"
            f"First come, best bid wins. 🏆"
        )
    
    @staticmethod
    def bid_winner_driver(bundle_id: str, amount: int, farmer_count: int, weight: int) -> str:
        """
        SMS to driver who won the bid
        
        Args:
            bundle_id: Cluster/bundle ID
            amount: Winning bid amount
            farmer_count: Number of farmers in bundle
            weight: Total weight (kg)
        """
        return (
            f"🎉 Congratulations! You Won!\n\n"
            f"Bundle: {bundle_id}\n"
            f"Amount: ₹{amount}\n"
            f"Pickups: {farmer_count} farmers\n"
            f"Total: {weight}kg\n\n"
            f"Check app for farmer details and pickup locations.\n"
            f"Good luck with delivery! 🚛"
        )
    
    @staticmethod
    def driver_assigned_farmer(
        farmer_name: str,
        driver_name: str,
        driver_phone: str,
        order_id: str,
        pickup_time: str,
        amount: int
    ) -> str:
        """
        SMS to farmer when driver is assigned
        
        Args:
            farmer_name: Name of farmer
            driver_name: Name of assigned driver
            driver_phone: Driver's contact number
            order_id: Order/booking ID
            pickup_time: Expected pickup time
            amount: Farmer's cost (shared/cooperative)
        """
        return (
            f"🚚 Driver Assigned - {farmer_name}\n\n"
            f"Order: {order_id}\n"
            f"Driver: {driver_name}\n"
            f"Contact: {driver_phone}\n"
            f"Pickup: {pickup_time}\n"
            f"Cost: ₹{amount} (Cooperative)\n\n"
            f"Driver will call you before pickup.\n"
            f"Keep your produce ready! 🌾"
        )
    
    @staticmethod
    def pickup_reminder_farmer(farmer_name: str, driver_name: str, minutes: int) -> str:
        """
        SMS reminder before pickup (optional, for future)
        
        Args:
            farmer_name: Name of farmer
            driver_name: Driver's name
            minutes: Minutes until pickup
        """
        return (
            f"⏰ Pickup Reminder - {farmer_name}\n\n"
            f"Driver {driver_name} will arrive in {minutes} minutes.\n\n"
            f"Please keep your produce ready for quick loading.\n"
            f"Thank you! 🙏"
        )
    
    @staticmethod
    def delivery_complete_farmer(farmer_name: str, order_id: str, amount: int, savings: int) -> str:
        """
        SMS after successful delivery (optional, for future)
        
        Args:
            farmer_name: Name of farmer
            order_id: Order ID
            amount: Final amount paid
            savings: Amount saved through cooperation
        """
        return (
            f"✅ Delivery Complete - {farmer_name}\n\n"
            f"Order {order_id} delivered successfully!\n\n"
            f"Amount: ₹{amount}\n"
            f"You saved: ₹{savings}\n\n"
            f"Thank you for using Agrilogi! 🌾"
        )
    
    @staticmethod
    def no_bids_received(bundle_id: str, weight: int, destination: str) -> str:
        """
        SMS to admin when no bids received (optional)
        
        Args:
            bundle_id: Bundle ID
            weight: Total weight
            destination: Destination
        """
        return (
            f"⚠️ No Bids Received\n\n"
            f"Bundle: {bundle_id}\n"
            f"Weight: {weight}kg\n"
            f"Destination: {destination}\n\n"
            f"Consider adjusting pricing or re-clustering."
        )
    
    @staticmethod
    def custom_message(title: str, body: str, recipient_name: str = "") -> str:
        """
        Generic custom message template
        
        Args:
            title: Message title/subject
            body: Message content
            recipient_name: Optional recipient name
        """
        greeting = f"{recipient_name}\n\n" if recipient_name else ""
        return (
            f"Agrilogi: {title}\n\n"
            f"{greeting}"
            f"{body}\n\n"
            f"For support, contact: 1800-XXX-XXXX"
        )


class SMSValidator:
    """Validate SMS messages before sending"""
    
    MAX_LENGTH = 1600  # Maximum SMS length (multiple segments)
    MAX_SINGLE_SEGMENT = 160  # Single SMS segment length
    
    @staticmethod
    def validate_message(message: str) -> Dict[str, any]:
        """
        Validate SMS message
        
        Returns:
            dict: {
                'valid': bool,
                'length': int,
                'segments': int,
                'warnings': List[str]
            }
        """
        length = len(message)
        segments = (length // SMSValidator.MAX_SINGLE_SEGMENT) + 1
        warnings = []
        
        if length > SMSValidator.MAX_LENGTH:
            warnings.append(f"Message too long ({length} chars). Max: {SMSValidator.MAX_LENGTH}")
        
        if segments > 3:
            warnings.append(f"Message will be split into {segments} SMS. Consider shortening.")
        
        return {
            'valid': length <= SMSValidator.MAX_LENGTH,
            'length': length,
            'segments': segments,
            'warnings': warnings
        }
    
    @staticmethod
    def truncate_message(message: str, max_length: int = MAX_LENGTH) -> str:
        """Truncate message to max length with ellipsis"""
        if len(message) <= max_length:
            return message
        return message[:max_length - 3] + "..."


# Example usage and testing
if __name__ == "__main__":
    print("=== SMS Template Examples ===\n")
    
    # Cluster created
    msg1 = SMSTemplates.cluster_created_driver(
        bundle_count=3,
        total_weight=2500,
        location="Koyambedu Mandi"
    )
    print("1. Cluster Created (Driver):")
    print(msg1)
    print(f"Length: {len(msg1)} chars\n")
    
    # Bid winner
    msg2 = SMSTemplates.bid_winner_driver(
        bundle_id="CL-1021-25231-1",
        amount=4500,
        farmer_count=3,
        weight=1200
    )
    print("2. Bid Winner (Driver):")
    print(msg2)
    print(f"Length: {len(msg2)} chars\n")
    
    # Driver assigned
    msg3 = SMSTemplates.driver_assigned_farmer(
        farmer_name="Arumugam",
        driver_name="Kumar",
        driver_phone="+919876543210",
        order_id="KB1046",
        pickup_time="Tomorrow 8:00 AM",
        amount=2100
    )
    print("3. Driver Assigned (Farmer):")
    print(msg3)
    print(f"Length: {len(msg3)} chars\n")
    
    # Validation
    print("=== Message Validation ===\n")
    validation = SMSValidator.validate_message(msg1)
    print(f"Valid: {validation['valid']}")
    print(f"Length: {validation['length']} chars")
    print(f"Segments: {validation['segments']} SMS")
    print(f"Warnings: {validation['warnings']}")
