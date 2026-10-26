#!/usr/bin/env python3
"""
Apply database schema directly using Supabase postgREST API
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / "backend" / ".env"
load_dotenv(env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: Missing Supabase credentials")
    exit(1)

print(f"✓ Connected to: {SUPABASE_URL}")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def apply_schema_incremental():
    """Apply schema changes incrementally with error handling"""
    
    print("\n📦 Applying time slot schema updates...\n")
    
    # Changes to apply
    changes = [
        ("pickup_date column", "ALTER TABLE orders ADD COLUMN IF NOT EXISTS pickup_date DATE;"),
        ("pickup_slot column", "ALTER TABLE orders ADD COLUMN IF NOT EXISTS pickup_slot VARCHAR(20);"),
        ("is_time_flexible column", "ALTER TABLE orders ADD COLUMN IF NOT EXISTS is_time_flexible BOOLEAN DEFAULT true;"),
        ("estimated_delivery_time column", "ALTER TABLE orders ADD COLUMN IF NOT EXISTS estimated_delivery_time TIMESTAMP;"),
        ("actual_pickup_time column", "ALTER TABLE orders ADD COLUMN IF NOT EXISTS actual_pickup_time TIMESTAMP;"),
        ("actual_delivery_time column", "ALTER TABLE orders ADD COLUMN IF NOT EXISTS actual_delivery_time TIMESTAMP;"),
        ("date/slot index", "CREATE INDEX IF NOT EXISTS idx_orders_pickup_date_slot ON orders(pickup_date, pickup_slot);"),
    ]
    
    success_count = 0
    
    for name, sql in changes:
        try:
            # Try to execute via RPC (if available)
            result = supabase.rpc("exec_sql", {"query": sql}).execute()
            print(f"  ✅ Added {name}")
            success_count += 1
        except Exception as e:
            # If RPC fails, that's okay - we'll note it
            if "does not exist" in str(e).lower() or "function" in str(e).lower():
                print(f"  ⚠️  {name} - RPC not available (manual application needed)")
            else:
                print(f"  ⚠️  {name} - {str(e)[:50]}...")
    
    print(f"\n{'='*60}")
    print(f"Applied {success_count}/{len(changes)} changes programmatically")
    print(f"{'='*60}\n")
    
    if success_count < len(changes):
        print("⚠️  Some changes need manual application.")
        print("📋 Please run this SQL in Supabase SQL Editor:\n")
        print("="*60)
        
        sql_file = Path(__file__).parent / "add_time_slots.sql"
        with open(sql_file, "r") as f:
            print(f.read())
        
        print("="*60)
        print("\nOR visit: https://supabase.com/dashboard → SQL Editor")
    else:
        print("🎉 All schema changes applied successfully!")
    
    return success_count > 0

if __name__ == "__main__":
    try:
        apply_schema_incremental()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Manual application recommended:")
        print("   1. Go to Supabase Dashboard")
        print("   2. SQL Editor → New Query")
        print("   3. Paste SQL from database/add_time_slots.sql")
        print("   4. Click Run")
        exit(1)
