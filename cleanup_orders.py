"""
Delete orders KB1040 and KB1041 so new orders start from KB1040
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
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing Supabase credentials")
    sys.exit(1)

print("=" * 80)
print("🗑️  CLEANING UP ORDERS AFTER KB1039")
print("=" * 80)

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Check current orders
    print("\n📋 Current orders after KB1039:")
    response = supabase.table("orders").select("id, farmer_name, phone").gte("id", "KB1040").execute()
    
    if not response.data:
        print("✅ No orders found after KB1039 - already clean!")
    else:
        print(f"Found {len(response.data)} order(s) to delete:")
        for order in response.data:
            print(f"   {order['id']} | {order['farmer_name']} | {order['phone']}")
        
        # Delete them
        print("\n🗑️  Deleting orders...")
        for order in response.data:
            order_id = order['id']
            delete_response = supabase.table("orders").delete().eq("id", order_id).execute()
            print(f"   ✅ Deleted {order_id}")
    
    # Verify final state
    print("\n📊 Final verification:")
    all_orders = supabase.table("orders").select("id").order("id").execute()
    
    if all_orders.data:
        kb_numbers = []
        for o in all_orders.data:
            if o['id'].startswith("KB"):
                try:
                    kb_numbers.append(int(o['id'][2:]))
                except:
                    pass
        
        if kb_numbers:
            print(f"   Last order: KB{max(kb_numbers)}")
            print(f"   Next order will be: KB{max(kb_numbers) + 1}")
            
            if max(kb_numbers) == 1039:
                print("\n✅ SUCCESS! Last order is KB1039")
                print("   Next order will be KB1040 (Arun Madurai)")
            else:
                print(f"\n⚠️  WARNING: Last order is KB{max(kb_numbers)}, not KB1039")
    
    print("\n" + "=" * 80)
    print("✅ CLEANUP COMPLETE!")
    print("=" * 80)
    print("Now restart backend and create your test orders:")
    print("1. KB1040 - Arun Madurai (+919876543201)")
    print("2. KB1041 - Kumar TPK (+919876543202)")
    print("3. KB1042 - Lakshmi Coimbatore (+919876543203)")
    print("=" * 80)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    print(traceback.format_exc())
