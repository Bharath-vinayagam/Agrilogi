#!/usr/bin/env python3
"""
Apply slot bidding schema changes to Supabase database
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
# Try to load from backend/.env if not found
if not os.getenv("SUPABASE_URL"):
    backend_env = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
    load_dotenv(backend_env)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def main():
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
        return
    
    print(f"🔌 Connecting to Supabase: {SUPABASE_URL}")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    
    # Read SQL file
    sql_file = "add_slot_bidding.sql"
    with open(sql_file, "r") as f:
        sql_statements = f.read()
    
    print(f"📄 Read {len(sql_statements)} characters from {sql_file}")
    
    # Split and execute each statement
    statements = [s.strip() for s in sql_statements.split(";") if s.strip() and not s.strip().startswith("--")]
    
    for i, statement in enumerate(statements, 1):
        if statement.startswith("COMMENT"):
            # Skip COMMENT statements as they may not work via client
            print(f"⏭️  Skipping statement {i}: {statement[:50]}...")
            continue
            
        print(f"⚙️  Executing statement {i}/{len(statements)}: {statement[:60]}...")
        try:
            # Execute via RPC to the database
            result = supabase.rpc("exec_sql", {"sql_query": statement}).execute()
            print(f"✅ Statement {i} executed successfully")
        except Exception as e:
            # Try direct execution if RPC doesn't exist
            print(f"⚠️  RPC failed, trying alternative method: {e}")
            try:
                # Use postgrest to execute SQL (this may not work for all statements)
                print(f"⚠️  Note: Schema changes require direct database access")
                print(f"   Please run this SQL manually in Supabase SQL Editor:")
                print(f"\n{statement}\n")
            except Exception as e2:
                print(f"❌ Failed: {e2}")
    
    print("\n✅ Schema update process complete!")
    print("\n📝 Manual Step Required:")
    print("   1. Go to your Supabase dashboard: https://supabase.com/dashboard/project/krenzgkwgusmpauxuloe")
    print("   2. Click 'SQL Editor' in the left sidebar")
    print("   3. Copy and paste the contents of database/add_slot_bidding.sql")
    print("   4. Click 'Run' to execute the schema changes")

if __name__ == "__main__":
    main()
