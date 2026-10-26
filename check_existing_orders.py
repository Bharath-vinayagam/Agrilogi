"""
Check what orders exist in Supabase and diagnose the KB1041 duplicate issue
"""
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from dotenv import load_dotenv
from supabase import create_client

# Load environment variables from backend/.env
env_path = Path(__file__).parent / 'backend' / '.env'
load_dotenv(env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing Supabase credentials in backend/.env")
    print(f"   SUPABASE_URL: {'✅ Found' if SUPABASE_URL else '❌ Missing'}")
    print(f"   SUPABASE_SERVICE_ROLE_KEY: {'✅ Found' if os.getenv('SUPABASE_SERVICE_ROLE_KEY') else '❌ Missing'}")
    sys.exit(1)

print("=" * 80)
print("🔍 CHECKING EXISTING ORDERS IN SUPABASE")
print("=" * 80)

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get all orders
    print("\n📋 Fetching all orders...")
    response = supabase.table("orders").select("id, farmer_name, phone, village, individual_cost, created_at").order("id").execute()
    
    orders = response.data
    print(f"✅ Found {len(orders)} orders\n")
    
    print("=" * 80)
    print("EXISTING ORDERS:")
    print("=" * 80)
    
    kb_numbers = []
    for order in orders:
        order_id = order['id']
        farmer_name = order['farmer_name']
        phone = order['phone']
        village = order['village'][:50] + "..." if len(order['village']) > 50 else order['village']
        cost = order.get('individual_cost', 0)
        
        print(f"{order_id} | {farmer_name:20} | {phone:15} | ₹{cost:,} | {village}")
        
        # Extract KB number
        if order_id.startswith("KB"):
            try:
                kb_numbers.append(int(order_id[2:]))
            except ValueError:
                pass
    
    print("=" * 80)
    
    # Check for Kumar's order specifically
    print("\n🔍 Searching for Kumar TPK orders:")
    kumar_orders = [o for o in orders if 'kumar' in o['farmer_name'].lower() or '3202' in o.get('phone', '')]
    
    if kumar_orders:
        print(f"✅ Found {len(kumar_orders)} Kumar-related order(s):")
        for order in kumar_orders:
            print(f"   {order['id']} | {order['farmer_name']} | {order['phone']}")
    else:
        print("❌ No Kumar TPK order found")
    
    # Show KB number analysis
    print("\n📊 KB Number Analysis:")
    if kb_numbers:
        kb_numbers.sort()
        print(f"   Lowest KB:  KB{min(kb_numbers)}")
        print(f"   Highest KB: KB{max(kb_numbers)}")
        print(f"   Next KB should be: KB{max(kb_numbers) + 1}")
        
        # Check for gaps
        gaps = []
        for i in range(min(kb_numbers), max(kb_numbers)):
            if i not in kb_numbers:
                gaps.append(i)
        
        if gaps:
            print(f"   ⚠️  Gaps found: KB{gaps} (deleted orders?)")
        else:
            print(f"   ✅ No gaps in sequence")
    
    # Check if KB1041 exists
    print("\n🎯 Checking KB1041 specifically:")
    kb1041 = [o for o in orders if o['id'] == 'KB1041']
    if kb1041:
        order = kb1041[0]
        print(f"   ⚠️  KB1041 EXISTS!")
        print(f"   Farmer: {order['farmer_name']}")
        print(f"   Phone: {order['phone']}")
        print(f"   Village: {order['village']}")
        print(f"   Cost: ₹{order.get('individual_cost', 0)}")
        print(f"\n   This is why Kumar's order is failing - KB1041 is already taken!")
    else:
        print(f"   ✅ KB1041 does NOT exist (should work after backend restart)")
    
    print("\n" + "=" * 80)
    print("🔧 SOLUTION:")
    print("=" * 80)
    print("1. Restart the backend server to load the fixed ID generation code")
    print("2. The new code will use KB{} (next available number)".format(max(kb_numbers) + 1 if kb_numbers else 1024))
    print("3. Then try creating Kumar's order again")
    print("=" * 80)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    print(traceback.format_exc())
