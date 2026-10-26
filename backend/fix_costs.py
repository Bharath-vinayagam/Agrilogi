#!/usr/bin/env python3
"""
Fix final_cost for existing Driver Assigned orders.
Run: cd backend && python fix_costs.py
"""

import os
from supabase import create_client
from dotenv import load_dotenv
from services.cost_allocation import reallocate_final_costs

load_dotenv(".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ SUPABASE_URL and SUPABASE_KEY must be set in .env")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("\n🔧 Fixing final costs for Driver Assigned orders...\n")

# Get all clusters with Driver Assigned orders
clusters = supabase.table("orders")\
    .select("cluster_id")\
    .eq("status", "Driver Assigned")\
    .not_.is_("cluster_id", "null")\
    .execute()

cluster_ids = list(set([o["cluster_id"] for o in clusters.data if o.get("cluster_id")]))

print(f"📦 Found {len(cluster_ids)} clusters with assigned drivers\n")

for cluster_id in cluster_ids:
    print(f"Cluster: {cluster_id}")
    
    # Get orders in this cluster
    orders_result = supabase.table("orders")\
        .select("*")\
        .eq("cluster_id", cluster_id)\
        .execute()
    
    orders = orders_result.data
    if not orders:
        print("  ⚠️  No orders found\n")
        continue
    
    # Get winning bid for this cluster
    bids_result = supabase.table("bids")\
        .select("*")\
        .eq("bundle_id", cluster_id)\
        .eq("status", "Accepted")\
        .execute()
    
    if not bids_result.data:
        print("  ⚠️  No winning bid found\n")
        continue
    
    winning_bid = bids_result.data[0]
    winning_amount = winning_bid["amount"]
    
    print(f"  Winning bid: ₹{winning_amount}")
    print(f"  Orders: {len(orders)}\n")
    
    # Recalculate costs with the NEW guaranteed savings logic
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
        savings_pct = round(savings/individual*100, 1) if individual > 0 else 0
        
        print(f"  Order {order_id} ({order.get('farmer_name', 'Unknown')}):")
        print(f"    Individual: ₹{individual}")
        print(f"    Old final: ₹{old_final}")
        print(f"    New final: ₹{new_final_cost}")
        print(f"    Savings: ₹{savings} ({savings_pct}%)")
        
        # Update database
        supabase.table("orders").update({
            "final_cost": new_final_cost,
            "shared_cost": new_final_cost
        }).eq("id", order_id).execute()
        
        print(f"    ✅ Updated!\n")

print("\n✅ Done! Refresh the farmer dashboard to see correct costs.\n")
