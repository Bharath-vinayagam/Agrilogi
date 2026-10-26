#!/usr/bin/env python3
"""
Fix final_cost for existing Driver Assigned orders by recalculating from the winning bid.
Run from project root: python fix_final_costs.py
"""

import os
import sys

# Add backend to path so we can import services
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from supabase import create_client
from dotenv import load_dotenv
from services.cost_allocation import reallocate_final_costs

load_dotenv("backend/.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in backend/.env")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Get all clusters with Driver Assigned orders
clusters = supabase.table("orders")\
    .select("cluster_id")\
    .eq("status", "Driver Assigned")\
    .not_.is_("cluster_id", "null")\
    .execute()

cluster_ids = list(set([o["cluster_id"] for o in clusters.data if o.get("cluster_id")]))

print(f"\n🔄 Found {len(cluster_ids)} clusters with assigned drivers")

for cluster_id in cluster_ids:
    print(f"\n📦 Processing cluster: {cluster_id}")
    
    # Get orders in this cluster
    orders_result = supabase.table("orders")\
        .select("*")\
        .eq("cluster_id", cluster_id)\
        .execute()
    
    orders = orders_result.data
    if not orders:
        continue
    
    # Get winning bid for this cluster
    bids_result = supabase.table("bids")\
        .select("*")\
        .eq("bundle_id", cluster_id)\
        .eq("status", "Accepted")\
        .execute()
    
    if not bids_result.data:
        print(f"   ⚠️  No winning bid found")
        continue
    
    winning_bid = bids_result.data[0]
    winning_amount = winning_bid["amount"]
    
    print(f"   Winning bid: ₹{winning_amount}")
    print(f"   Orders: {len(orders)}")
    
    # Recalculate costs
    reallocations = reallocate_final_costs(orders, winning_amount)
    
    # Update each order
    for realloc in reallocations:
        order_id = realloc["order_id"]
        new_final_cost = realloc["shared_cost"]
        
        order = next((o for o in orders if o["id"] == order_id), None)
        if not order:
            continue
        
        old_final = order.get("final_cost", 0)
        individual = order.get("individual_cost", 0)
        savings = individual - new_final_cost
        
        print(f"   Order {order_id}:")
        print(f"      Individual: ₹{individual}")
        print(f"      Old final: ₹{old_final}")
        print(f"      New final: ₹{new_final_cost}")
        print(f"      Savings: ₹{savings} ({round(savings/individual*100,1)}%)")
        
        # Update database
        supabase.table("orders").update({
            "final_cost": new_final_cost,
            "shared_cost": new_final_cost
        }).eq("id", order_id).execute()
        
        print(f"      ✅ Updated!")

print("\n✅ Done! Refresh the farmer dashboard to see correct costs.")
