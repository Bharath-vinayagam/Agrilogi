"""
Run this to:
1. Add missing 'type' column to notifications table
2. Trigger clustering (fires SMS to all drivers)
3. Close the first available cluster bid (fires SMS to winner + farmers)
4. Show all SMS logs in the database
"""
import os, sys, requests
sys.path.insert(0, 'backend')
from dotenv import load_dotenv
load_dotenv('backend/.env')
from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
sb = create_client(url, key)

API = "http://localhost:8000"

print("=" * 60)
print("STEP 1: Add 'type' column to notifications table")
print("=" * 60)
try:
    # Try inserting with type field to check if column exists
    test = sb.table("notifications").insert({
        "phone": "+919999999999",
        "channel": "sms",
        "message": "Test - column check",
        "status": "test",
        "type": "test"
    }).execute()
    # Delete the test row
    if test.data:
        sb.table("notifications").delete().eq("id", test.data[0]["id"]).execute()
    print("✅ 'type' column already exists")
except Exception as e:
    if "type" in str(e).lower() or "schema" in str(e).lower():
        print("❌ 'type' column missing. Please run this SQL in Supabase SQL Editor:")
        print()
        print("   ALTER TABLE notifications ADD COLUMN IF NOT EXISTS type TEXT;")
        print()
        print("Then re-run this script.")
        sys.exit(1)
    else:
        print(f"⚠️  Unexpected error: {e}")

print()
print("=" * 60)
print("STEP 2: Trigger Clustering (sends SMS to all drivers)")
print("=" * 60)
try:
    r = requests.post(f"{API}/api/admin/run-clustering", timeout=30)
    data = r.json()
    print(f"Status: {r.status_code}")
    print(f"Clusters formed: {data.get('clusters_formed', 0)}")
    if data.get('success'):
        print("✅ Clustering triggered")
    else:
        print(f"⚠️  {data.get('error', 'No error info')}")
except Exception as e:
    print(f"❌ Could not reach backend: {e}")
    print("   Make sure backend is running: python backend/main.py")
    sys.exit(1)

print()
print("=" * 60)
print("STEP 3: Close first available cluster bid (sends SMS to winner + farmers)")
print("=" * 60)
try:
    # Find clusters with open bids
    bids_res = sb.table("bids").select("bundle_id").eq("status", "Open").eq("bid_type", "cluster").execute()
    cluster_ids = list(set(b["bundle_id"] for b in (bids_res.data or []) if b.get("bundle_id")))
    
    if not cluster_ids:
        print("⚠️  No open cluster bids found. Create an order, cluster it, place a bid first.")
    else:
        target = cluster_ids[0]
        print(f"Closing cluster: {target}")
        r2 = requests.post(f"{API}/api/bids/cluster/{target}/close", timeout=30)
        data2 = r2.json()
        print(f"Status: {r2.status_code}")
        if data2.get("success"):
            winner = data2.get("winner", {})
            print(f"✅ Winner: {winner.get('driver_name')} @ Rs{winner.get('amount')}")
        else:
            print(f"⚠️  {data2.get('detail', data2)}")
except Exception as e:
    print(f"❌ Error: {e}")

print()
print("=" * 60)
print("STEP 4: SMS logs in database")
print("=" * 60)
res = sb.table("notifications").select("*").order("created_at", desc=True).limit(20).execute()
rows = res.data or []
print(f"Total notifications: {len(rows)}")
print()
for n in rows:
    typ = n.get("type", "?")
    phone = n.get("phone", "?")
    status = n.get("status", "?")
    msg_preview = str(n.get("message", ""))[:60].replace("\n", " ")
    ts = str(n.get("created_at", ""))[:19]
    print(f"  [{ts}] type={typ} | {phone} | status={status}")
    print(f"          msg: {msg_preview}...")
    print()

# Summary
types = [n.get("type") for n in rows]
from collections import Counter
print("Types breakdown:", dict(Counter(types)))
