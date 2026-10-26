#!/usr/bin/env python3
"""
Check the actual cost values stored in the database for recent orders.
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv("backend/.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Get recent orders
result = supabase.table("orders")\
    .select("id, farmer_name, crop, weight_kg, individual_cost, shared_cost, final_cost, status, cluster_id")\
    .order("created_at", desc=True)\
    .limit(10)\
    .execute()

print("\n" + "="*100)
print("RECENT ORDERS - COST BREAKDOWN")
print("="*100)

for order in result.data:
    indiv = order.get('individual_cost', 0)
    shared = order.get('shared_cost', 0)
    final = order.get('final_cost', 0)
    savings = indiv - (final or shared)
    savings_pct = round((savings / indiv * 100), 1) if indiv > 0 else 0
    
    issue = ""
    if shared > indiv:
        issue = " ⚠️ SHARED > SOLO!"
    elif final and final > indiv:
        issue = " ⚠️ FINAL > SOLO!"
    elif savings < 0:
        issue = " ⚠️ NEGATIVE SAVINGS!"
    
    print(f"\n📦 Order: {order['id']}")
    print(f"   Farmer: {order['farmer_name']} | {order['crop']} | {order['weight_kg']}kg")
    print(f"   Solo Cost:   ₹{indiv:,}")
    print(f"   Shared Cost: ₹{shared:,}")
    print(f"   Final Cost:  ₹{final:,}" if final else "   Final Cost:  (not set)")
    print(f"   Savings:     ₹{savings:,} ({savings_pct}%){issue}")
    print(f"   Status:      {order['status']}")
    print(f"   Cluster:     {order.get('cluster_id', 'None')}")

print("\n" + "="*100)
