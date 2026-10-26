#!/usr/bin/env python3
"""
Quick script to delete a specific order by ID so you can test with fresh data.
Usage: python delete_test_order.py KB1234
"""

import sys
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv("backend/.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in backend/.env")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def delete_order(order_id: str):
    """Delete an order and its related data"""
    try:
        # Delete the order (cascades to related tables)
        result = supabase.table("orders").delete().eq("id", order_id).execute()
        
        if result.data:
            print(f"✅ Deleted order: {order_id}")
            return True
        else:
            print(f"⚠️  Order not found: {order_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error deleting order: {e}")
        return False

def list_recent_orders():
    """Show recent orders"""
    try:
        result = supabase.table("orders")\
            .select("id, farmer_name, crop, weight_kg, individual_cost, shared_cost, status")\
            .order("created_at", desc=True)\
            .limit(10)\
            .execute()
        
        if result.data:
            print("\n📋 Recent Orders:")
            print("-" * 80)
            for order in result.data:
                print(f"ID: {order['id']:<12} | {order['farmer_name']:<15} | {order['crop']:<10} | "
                      f"{order['weight_kg']}kg | Solo: ₹{order.get('individual_cost', 0)} | "
                      f"Shared: ₹{order.get('shared_cost', 0)} | {order['status']}")
            print("-" * 80)
        else:
            print("No orders found")
            
    except Exception as e:
        print(f"❌ Error listing orders: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python delete_test_order.py <ORDER_ID>")
        print("   or: python delete_test_order.py list")
        print("\nExample: python delete_test_order.py KB1234")
        sys.exit(1)
    
    if sys.argv[1].lower() == "list":
        list_recent_orders()
    else:
        order_id = sys.argv[1]
        if delete_order(order_id):
            print("\n✨ Now create a new order to test the updated pricing!")
        list_recent_orders()
