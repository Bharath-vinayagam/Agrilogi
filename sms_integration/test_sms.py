"""
SMS Integration Testing Script
Test all SMS scenarios before production deployment
"""

import sys
import os
from typing import Dict

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sms_integration.sms_triggers import notify_drivers_cluster_created, notify_bid_winner, get_sms_stats
from sms_integration.message_templates import SMSTemplates, SMSValidator
from backend.database.db import supabase_client


class SMSTester:
    """Test SMS integration scenarios"""
    
    def __init__(self):
        self.test_results = []
    
    def test_scenario_1_cluster_created(self, cluster_ids: list = None):
        """
        Test Scenario 1: Cluster Created → Notify Drivers
        
        Args:
            cluster_ids: List of cluster IDs to test with
        """
        print("\n" + "="*60)
        print("TEST SCENARIO 1: Cluster Created → Notify Drivers")
        print("="*60)
        
        # Use real clusters from database if available
        if not cluster_ids:
            print("\n📦 Fetching recent clusters from database...")
            clusters = self._get_recent_clusters(limit=2)
            if clusters:
                cluster_ids = [c['id'] for c in clusters]
                print(f"Found {len(cluster_ids)} clusters: {cluster_ids}")
            else:
                print("❌ No clusters found in database")
                print("💡 Tip: Run clustering first or provide test cluster IDs")
                return False
        
        print(f"\n🔔 Testing with clusters: {cluster_ids}")
        
        # Execute notification
        result = notify_drivers_cluster_created(cluster_ids)
        
        # Display results
        print("\n" + "-"*60)
        print("RESULTS:")
        print("-"*60)
        print(f"Success: {result.get('success')}")
        print(f"Drivers notified: {result.get('drivers_notified', 0)}")
        print(f"SMS sent: {result.get('sms_sent', 0)}")
        print(f"SMS failed: {result.get('sms_failed', 0)}")
        
        if 'error' in result:
            print(f"Error: {result['error']}")
        
        if 'message' in result:
            print(f"\nMessage sent:")
            print(result['message'])
        
        self.test_results.append({
            'scenario': 'cluster_created',
            'success': result.get('success', False),
            'details': result
        })
        
        return result.get('success', False)
    
    def test_scenario_2_bid_winner(
        self,
        cluster_id: str = None,
        driver_name: str = None,
        driver_phone: str = None,
        bid_amount: int = 4500
    ):
        """
        Test Scenario 2: Bid Winner → Notify Driver & Farmers
        
        Args:
            cluster_id: Cluster ID
            driver_name: Driver name
            driver_phone: Driver phone
            bid_amount: Bid amount
        """
        print("\n" + "="*60)
        print("TEST SCENARIO 2: Bid Winner → Notify Driver & Farmers")
        print("="*60)
        
        # Get real data if not provided
        if not cluster_id:
            print("\n📦 Fetching cluster with orders...")
            cluster_id = self._get_cluster_with_orders()
            if not cluster_id:
                print("❌ No cluster with orders found")
                return False
        
        if not driver_name or not driver_phone:
            print("\n👤 Fetching test driver...")
            driver = self._get_test_driver()
            if driver:
                driver_name = driver.get('name', 'Test Driver')
                driver_phone = driver.get('phone', '+919876543210')
            else:
                print("❌ No drivers found in database")
                return False
        
        print(f"\n🔔 Testing with:")
        print(f"   Cluster: {cluster_id}")
        print(f"   Driver: {driver_name}")
        print(f"   Phone: {driver_phone}")
        print(f"   Amount: ₹{bid_amount}")
        
        # Execute notification
        result = notify_bid_winner(
            cluster_id=cluster_id,
            driver_name=driver_name,
            driver_phone=driver_phone,
            bid_amount=bid_amount
        )
        
        # Display results
        print("\n" + "-"*60)
        print("RESULTS:")
        print("-"*60)
        print(f"Success: {result.get('success')}")
        print(f"Driver notified: {result.get('driver_notified', False)}")
        print(f"Farmers notified: {result.get('farmers_notified', 0)}")
        print(f"SMS sent: {result.get('sms_sent', 0)}")
        print(f"SMS failed: {result.get('sms_failed', 0)}")
        
        if 'error' in result:
            print(f"Error: {result['error']}")
        
        self.test_results.append({
            'scenario': 'bid_winner',
            'success': result.get('success', False),
            'details': result
        })
        
        return result.get('success', False)
    
    def test_message_templates(self):
        """Test all message templates"""
        print("\n" + "="*60)
        print("TEST: Message Templates")
        print("="*60)
        
        templates = [
            {
                'name': 'Cluster Created (Driver)',
                'message': SMSTemplates.cluster_created_driver(3, 2500, "Koyambedu Mandi")
            },
            {
                'name': 'Bid Winner (Driver)',
                'message': SMSTemplates.bid_winner_driver("CL-001", 4500, 3, 1200)
            },
            {
                'name': 'Driver Assigned (Farmer)',
                'message': SMSTemplates.driver_assigned_farmer(
                    "Arumugam", "Kumar", "+919876543210", "KB1046", "Tomorrow 8AM", 2100
                )
            }
        ]
        
        all_valid = True
        
        for template in templates:
            print(f"\n📝 {template['name']}:")
            print("-" * 50)
            print(template['message'])
            
            validation = SMSValidator.validate_message(template['message'])
            print(f"\nValidation:")
            print(f"  Length: {validation['length']} chars")
            print(f"  Segments: {validation['segments']} SMS")
            print(f"  Valid: {validation['valid']}")
            
            if validation['warnings']:
                print(f"  Warnings: {', '.join(validation['warnings'])}")
                all_valid = False
        
        return all_valid
    
    def test_sms_stats(self):
        """Test SMS statistics"""
        print("\n" + "="*60)
        print("TEST: SMS Statistics")
        print("="*60)
        
        for days in [1, 7, 30]:
            stats = get_sms_stats(days)
            print(f"\nLast {days} day(s):")
            print(f"  Sent: {stats.get('sent', 0)}")
            print(f"  Failed: {stats.get('failed', 0)}")
            print(f"  Queued: {stats.get('queued', 0)}")
            print(f"  Total: {stats.get('total', 0)}")
        
        return True
    
    def run_all_tests(self):
        """Run all test scenarios"""
        print("\n" + "="*80)
        print("🧪 RUNNING ALL SMS INTEGRATION TESTS")
        print("="*80)
        
        # Test 1: Message Templates
        print("\n[1/4] Testing message templates...")
        templates_ok = self.test_message_templates()
        
        # Test 2: SMS Stats
        print("\n[2/4] Testing SMS statistics...")
        stats_ok = self.test_sms_stats()
        
        # Test 3: Cluster Created
        print("\n[3/4] Testing Scenario 1: Cluster Created...")
        try:
            scenario1_ok = self.test_scenario_1_cluster_created()
        except Exception as e:
            print(f"❌ Scenario 1 failed: {e}")
            scenario1_ok = False
        
        # Test 4: Bid Winner
        print("\n[4/4] Testing Scenario 2: Bid Winner...")
        try:
            scenario2_ok = self.test_scenario_2_bid_winner()
        except Exception as e:
            print(f"❌ Scenario 2 failed: {e}")
            scenario2_ok = False
        
        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"✅ Message Templates: {'PASS' if templates_ok else 'FAIL'}")
        print(f"✅ SMS Statistics: {'PASS' if stats_ok else 'FAIL'}")
        print(f"✅ Scenario 1 (Cluster Created): {'PASS' if scenario1_ok else 'FAIL'}")
        print(f"✅ Scenario 2 (Bid Winner): {'PASS' if scenario2_ok else 'FAIL'}")
        print("="*80)
        
        all_passed = all([templates_ok, stats_ok, scenario1_ok, scenario2_ok])
        
        if all_passed:
            print("\n🎉 ALL TESTS PASSED! SMS Integration is ready for production.")
        else:
            print("\n⚠️ SOME TESTS FAILED. Review errors above and fix before production.")
        
        return all_passed
    
    # Helper methods
    
    def _get_recent_clusters(self, limit: int = 5):
        """Get recent clusters from database"""
        try:
            response = supabase_client.table("bundles")\
                .select("id, total_weight_kg, destination")\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching clusters: {e}")
            return []
    
    def _get_cluster_with_orders(self):
        """Get a cluster that has orders"""
        try:
            response = supabase_client.table("orders")\
                .select("cluster_id")\
                .not_("cluster_id", "is", "null")\
                .limit(1)\
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]['cluster_id']
            return None
        except Exception as e:
            print(f"Error fetching cluster with orders: {e}")
            return None
    
    def _get_test_driver(self):
        """Get a test driver from database"""
        try:
            response = supabase_client.table("users")\
                .select("name, phone")\
                .eq("role", "driver")\
                .limit(1)\
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error fetching driver: {e}")
            return None


# CLI Interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test SMS Integration")
    parser.add_argument('--scenario', choices=['cluster_created', 'bid_winner', 'templates', 'stats', 'all'], 
                       help='Test scenario to run')
    parser.add_argument('--cluster-ids', nargs='+', help='Cluster IDs for cluster_created test')
    parser.add_argument('--cluster-id', help='Cluster ID for bid_winner test')
    parser.add_argument('--driver-name', help='Driver name for bid_winner test')
    parser.add_argument('--driver-phone', help='Driver phone for bid_winner test')
    parser.add_argument('--bid-amount', type=int, default=4500, help='Bid amount for bid_winner test')
    
    args = parser.parse_args()
    
    tester = SMSTester()
    
    if not args.scenario or args.scenario == 'all':
        # Run all tests
        tester.run_all_tests()
    
    elif args.scenario == 'cluster_created':
        tester.test_scenario_1_cluster_created(args.cluster_ids)
    
    elif args.scenario == 'bid_winner':
        tester.test_scenario_2_bid_winner(
            cluster_id=args.cluster_id,
            driver_name=args.driver_name,
            driver_phone=args.driver_phone,
            bid_amount=args.bid_amount
        )
    
    elif args.scenario == 'templates':
        tester.test_message_templates()
    
    elif args.scenario == 'stats':
        tester.test_sms_stats()
