"""
SMS Trigger Functions for Agrilogi
Main entry points for triggering SMS notifications
"""

import sys
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.db import supabase_client
from backend.services.sms_service import sms_service
from sms_integration.message_templates import SMSTemplates, SMSValidator
from sms_integration.driver_notifications import DriverNotifier
from sms_integration.farmer_notifications import FarmerNotifier


class SMSTriggers:
    """Main class for triggering SMS notifications"""
    
    def __init__(self):
        self.sms_service = sms_service
        self.driver_notifier = DriverNotifier()
        self.farmer_notifier = FarmerNotifier()
    
    def notify_drivers_cluster_created(self, cluster_ids: List[str]) -> Dict[str, any]:
        """
        Scenario 1: Notify all drivers when clusters are created
        
        Triggered after: Clustering algorithm runs
        Recipients: All active drivers
        
        Args:
            cluster_ids: List of newly created cluster IDs
        
        Returns:
            dict: {
                'success': bool,
                'drivers_notified': int,
                'sms_sent': int,
                'sms_failed': int,
                'details': List[dict]
            }
        """
        print(f"\n🔔 Triggering SMS: Clusters Created")
        print(f"📦 Cluster IDs: {cluster_ids}")
        
        try:
            # Get cluster details
            clusters = self._get_cluster_details(cluster_ids)
            if not clusters:
                print("❌ No valid clusters found")
                return {
                    'success': False,
                    'error': 'No valid clusters found',
                    'drivers_notified': 0,
                    'sms_sent': 0,
                    'sms_failed': 0
                }
            
            # Calculate totals
            total_weight = sum(c.get('total_weight_kg', 0) for c in clusters)
            destinations = list(set(c.get('destination', 'Unknown') for c in clusters))
            destination_text = destinations[0] if len(destinations) == 1 else f"{len(destinations)} locations"
            
            # Get all active drivers
            drivers = self._get_active_drivers()
            if not drivers:
                print("⚠️ No active drivers found")
                return {
                    'success': False,
                    'error': 'No active drivers found',
                    'drivers_notified': 0,
                    'sms_sent': 0,
                    'sms_failed': 0
                }
            
            print(f"👥 Found {len(drivers)} active drivers")
            
            # Generate SMS message
            message = SMSTemplates.cluster_created_driver(
                bundle_count=len(cluster_ids),
                total_weight=total_weight,
                location=destination_text
            )
            
            # Validate message
            validation = SMSValidator.validate_message(message)
            if not validation['valid']:
                print(f"⚠️ Message validation warnings: {validation['warnings']}")
            
            print(f"📝 Message ({validation['length']} chars, {validation['segments']} segments):")
            print(message)
            print()
            
            # Send SMS to each driver
            results = []
            sent = 0
            failed = 0
            
            for driver in drivers:
                driver_name = driver.get('name', 'Driver')
                driver_phone = driver.get('phone', '')
                
                if not driver_phone:
                    print(f"⚠️ Skipping {driver_name}: No phone number")
                    failed += 1
                    results.append({
                        'driver': driver_name,
                        'phone': driver_phone,
                        'success': False,
                        'reason': 'No phone number'
                    })
                    continue
                
                print(f"📤 Sending SMS to {driver_name} ({driver_phone})...")
                
                success = self.sms_service.send_sms(
                    phone=driver_phone,
                    message=message,
                    sms_type="cluster_created"
                )
                
                if success:
                    sent += 1
                    print(f"  ✅ Sent successfully")
                else:
                    failed += 1
                    print(f"  ❌ Failed to send")
                
                results.append({
                    'driver': driver_name,
                    'phone': driver_phone,
                    'success': success
                })
            
            print(f"\n📊 Summary:")
            print(f"   Drivers notified: {len(drivers)}")
            print(f"   SMS sent: {sent}")
            print(f"   SMS failed: {failed}")
            
            return {
                'success': True,
                'drivers_notified': len(drivers),
                'sms_sent': sent,
                'sms_failed': failed,
                'details': results,
                'message': message
            }
            
        except Exception as e:
            print(f"❌ Error in notify_drivers_cluster_created: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'drivers_notified': 0,
                'sms_sent': 0,
                'sms_failed': 0
            }
    
    def notify_bid_winner(
        self,
        cluster_id: str,
        driver_name: str,
        driver_phone: str,
        bid_amount: int
    ) -> Dict[str, any]:
        """
        Scenario 2: Notify winner and farmers when bidding closes
        
        Triggered after: Lowest bid wins
        Recipients:
            1. Winning driver
            2. All farmers in the cluster
        
        Args:
            cluster_id: Cluster ID
            driver_name: Winning driver's name
            driver_phone: Winning driver's phone
            bid_amount: Winning bid amount
        
        Returns:
            dict: {
                'success': bool,
                'driver_notified': bool,
                'farmers_notified': int,
                'sms_sent': int,
                'sms_failed': int,
                'details': dict
            }
        """
        print(f"\n🔔 Triggering SMS: Bid Winner")
        print(f"🏆 Winner: {driver_name}")
        print(f"📦 Cluster: {cluster_id}")
        print(f"💰 Amount: ₹{bid_amount}")
        
        try:
            # Get cluster details
            cluster = self._get_cluster_details([cluster_id])
            if not cluster:
                return {
                    'success': False,
                    'error': f'Cluster {cluster_id} not found'
                }
            cluster = cluster[0]
            
            # Get farmers in this cluster
            farmers = self._get_farmers_in_cluster(cluster_id)
            if not farmers:
                print("⚠️ No farmers found in cluster")
            
            print(f"👥 Found {len(farmers)} farmers in cluster")
            
            sent = 0
            failed = 0
            results = {
                'driver': {},
                'farmers': []
            }
            
            # 1. Notify winning driver
            print(f"\n1️⃣ Notifying Driver: {driver_name}")
            driver_message = SMSTemplates.bid_winner_driver(
                bundle_id=cluster_id,
                amount=bid_amount,
                farmer_count=len(farmers),
                weight=cluster.get('total_weight_kg', 0)
            )
            
            print(f"📝 Driver message ({len(driver_message)} chars):")
            print(driver_message)
            print()
            
            driver_success = self.sms_service.send_sms(
                phone=driver_phone,
                message=driver_message,
                sms_type="bid_winner"
            )
            
            if driver_success:
                sent += 1
                print(f"✅ Driver notified successfully")
            else:
                failed += 1
                print(f"❌ Failed to notify driver")
            
            results['driver'] = {
                'name': driver_name,
                'phone': driver_phone,
                'success': driver_success
            }
            
            # 2. Notify all farmers
            print(f"\n2️⃣ Notifying {len(farmers)} Farmers:")
            
            # Get pickup time from cluster or orders
            pickup_time = self._get_pickup_time(cluster_id)
            
            for farmer in farmers:
                farmer_name = farmer.get('farmer_name', 'Farmer')
                farmer_phone = farmer.get('phone', '')
                order_id = farmer.get('id', 'N/A')
                amount = farmer.get('shared_cost', farmer.get('individual_cost', 0))
                
                if not farmer_phone:
                    print(f"  ⚠️ Skipping {farmer_name}: No phone number")
                    failed += 1
                    results['farmers'].append({
                        'name': farmer_name,
                        'order_id': order_id,
                        'success': False,
                        'reason': 'No phone number'
                    })
                    continue
                
                print(f"  📤 Sending to {farmer_name} ({farmer_phone})...")
                
                farmer_message = SMSTemplates.driver_assigned_farmer(
                    farmer_name=farmer_name,
                    driver_name=driver_name,
                    driver_phone=driver_phone,
                    order_id=order_id,
                    pickup_time=pickup_time,
                    amount=amount
                )
                
                farmer_success = self.sms_service.send_sms(
                    phone=farmer_phone,
                    message=farmer_message,
                    sms_type="driver_assigned"
                )
                
                if farmer_success:
                    sent += 1
                    print(f"    ✅ Sent")
                else:
                    failed += 1
                    print(f"    ❌ Failed")
                
                results['farmers'].append({
                    'name': farmer_name,
                    'order_id': order_id,
                    'phone': farmer_phone,
                    'success': farmer_success
                })
            
            print(f"\n📊 Summary:")
            print(f"   Driver notified: {driver_success}")
            print(f"   Farmers notified: {len([f for f in results['farmers'] if f['success']])}/{len(farmers)}")
            print(f"   Total SMS sent: {sent}")
            print(f"   Total SMS failed: {failed}")
            
            return {
                'success': True,
                'driver_notified': driver_success,
                'farmers_notified': len([f for f in results['farmers'] if f['success']]),
                'sms_sent': sent,
                'sms_failed': failed,
                'details': results
            }
            
        except Exception as e:
            print(f"❌ Error in notify_bid_winner: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_cluster_details(self, cluster_ids: List[str]) -> List[Dict]:
        """Get cluster details from database"""
        try:
            response = supabase_client.table("bundles")\
                .select("*")\
                .in_("id", cluster_ids)\
                .execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching clusters: {e}")
            return []
    
    def _get_active_drivers(self) -> List[Dict]:
        """Get all active drivers from database"""
        try:
            response = supabase_client.table("users")\
                .select("name, phone, id")\
                .eq("role", "driver")\
                .execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching drivers: {e}")
            return []
    
    def _get_farmers_in_cluster(self, cluster_id: str) -> List[Dict]:
        """Get all farmers/orders in a cluster"""
        try:
            response = supabase_client.table("orders")\
                .select("id, farmer_name, phone, shared_cost, individual_cost, crop, weight_kg")\
                .eq("cluster_id", cluster_id)\
                .execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching farmers: {e}")
            return []
    
    def _get_pickup_time(self, cluster_id: str) -> str:
        """Get pickup time for cluster"""
        try:
            response = supabase_client.table("orders")\
                .select("pickup_date, pickup_slot")\
                .eq("cluster_id", cluster_id)\
                .limit(1)\
                .execute()
            
            if response.data and len(response.data) > 0:
                order = response.data[0]
                date = order.get('pickup_date', 'Tomorrow')
                slot = order.get('pickup_slot', '8:00 AM')
                return f"{date} {slot}"
            return "Tomorrow 8:00 AM"
        except Exception as e:
            print(f"Error fetching pickup time: {e}")
            return "Tomorrow 8:00 AM"
    
    def get_sms_stats(self, days: int = 7) -> Dict[str, int]:
        """Get SMS statistics for last N days"""
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            response = supabase_client.table("notifications")\
                .select("status")\
                .eq("channel", "sms")\
                .gte("created_at", since_date)\
                .execute()
            
            if not response.data:
                return {'sent': 0, 'failed': 0, 'queued': 0, 'total': 0}
            
            stats = {
                'sent': len([n for n in response.data if n['status'] == 'sent']),
                'failed': len([n for n in response.data if n['status'] == 'failed']),
                'queued': len([n for n in response.data if n['status'] == 'queued']),
                'total': len(response.data)
            }
            
            return stats
        except Exception as e:
            print(f"Error fetching SMS stats: {e}")
            return {'sent': 0, 'failed': 0, 'queued': 0, 'total': 0}


# Global instance
sms_triggers = SMSTriggers()


# Convenience functions
def notify_drivers_cluster_created(cluster_ids: List[str]) -> Dict[str, any]:
    """Notify all drivers when clusters are created"""
    return sms_triggers.notify_drivers_cluster_created(cluster_ids)


def notify_bid_winner(cluster_id: str, driver_name: str, driver_phone: str, bid_amount: int) -> Dict[str, any]:
    """Notify winner and farmers when bidding closes"""
    return sms_triggers.notify_bid_winner(cluster_id, driver_name, driver_phone, bid_amount)


def get_sms_stats(days: int = 7) -> Dict[str, int]:
    """Get SMS statistics"""
    return sms_triggers.get_sms_stats(days)


# CLI interface for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="SMS Triggers CLI")
    parser.add_argument('--scenario', choices=['cluster_created', 'bid_winner', 'stats'], required=True)
    parser.add_argument('--cluster-ids', nargs='+', help='Cluster IDs for cluster_created scenario')
    parser.add_argument('--cluster-id', help='Cluster ID for bid_winner scenario')
    parser.add_argument('--driver-name', help='Driver name for bid_winner')
    parser.add_argument('--driver-phone', help='Driver phone for bid_winner')
    parser.add_argument('--bid-amount', type=int, help='Bid amount for bid_winner')
    parser.add_argument('--days', type=int, default=7, help='Days for stats')
    
    args = parser.parse_args()
    
    if args.scenario == 'cluster_created':
        if not args.cluster_ids:
            print("Error: --cluster-ids required for cluster_created scenario")
            sys.exit(1)
        result = notify_drivers_cluster_created(args.cluster_ids)
        print(f"\n✅ Result: {result}")
    
    elif args.scenario == 'bid_winner':
        if not all([args.cluster_id, args.driver_name, args.driver_phone, args.bid_amount]):
            print("Error: --cluster-id, --driver-name, --driver-phone, --bid-amount required")
            sys.exit(1)
        result = notify_bid_winner(args.cluster_id, args.driver_name, args.driver_phone, args.bid_amount)
        print(f"\n✅ Result: {result}")
    
    elif args.scenario == 'stats':
        stats = get_sms_stats(args.days)
        print(f"\n📊 SMS Stats (Last {args.days} days):")
        print(f"   Sent: {stats['sent']}")
        print(f"   Failed: {stats['failed']}")
        print(f"   Queued: {stats['queued']}")
        print(f"   Total: {stats['total']}")
