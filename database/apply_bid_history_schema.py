"""
Apply bid history schema to Supabase database
This adds comprehensive bid tracking for driver audit trails
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load environment from backend/.env
env_path = Path(__file__).parent.parent / 'backend' / '.env'
load_dotenv(env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in backend/.env")
    exit(1)

print("=" * 80)
print("📊 APPLYING BID HISTORY SCHEMA")
print("=" * 80)

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Read SQL file
    sql_file = Path(__file__).parent / 'add_bid_history.sql'
    with open(sql_file, 'r') as f:
        sql_content = f.read()
    
    print("\n📝 SQL Schema:")
    print("-" * 80)
    print(sql_content[:500] + "..." if len(sql_content) > 500 else sql_content)
    print("-" * 80)
    
    # Execute SQL (Note: Supabase Python client doesn't support raw SQL execution)
    # You need to run this SQL manually in Supabase SQL Editor
    print("\n⚠️  MANUAL ACTION REQUIRED:")
    print("=" * 80)
    print("The Supabase Python client doesn't support executing raw SQL.")
    print("Please copy the SQL from 'database/add_bid_history.sql'")
    print("and paste it into your Supabase SQL Editor:")
    print()
    print("1. Go to: https://app.supabase.com/project/YOUR_PROJECT/sql")
    print("2. Create a new query")
    print(f"3. Paste the contents of: {sql_file}")
    print("4. Click 'Run' to execute")
    print("=" * 80)
    
    print("\n✅ Schema file ready at: database/add_bid_history.sql")
    print("   This will add:")
    print("   - bid_history table for tracking all bids")
    print("   - Automatic trigger to log status changes")
    print("   - Indexes for efficient querying")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    print(traceback.format_exc())
