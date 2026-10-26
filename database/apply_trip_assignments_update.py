#!/usr/bin/env python3
"""
Apply trip_assignments table updates to add missing columns.
Run this from the project root: python database/apply_trip_assignments_update.py
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv("backend/.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in backend/.env")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def main():
    print("🔄 Updating trip_assignments table schema...")
    
    # Read the SQL file
    with open("database/update_trip_assignments.sql", "r") as f:
        sql = f.read()
    
    # Split into individual statements
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    
    for i, statement in enumerate(statements, 1):
        try:
            print(f"\n📝 Executing statement {i}/{len(statements)}...")
            print(f"   {statement[:80]}...")
            
            # Execute via RPC (if you have a custom function) or use psycopg2
            # For Supabase, we need to execute raw SQL via the SQL editor or use PostgREST
            # Since Supabase Python client doesn't support raw SQL directly,
            # we'll need to use psycopg2 or execute via Supabase dashboard
            
            print(f"   ⚠️  Please execute this SQL manually in Supabase SQL Editor:")
            print(f"   {statement}")
            
        except Exception as e:
            print(f"❌ Error executing statement {i}: {e}")
    
    print("\n" + "="*60)
    print("⚠️  MANUAL STEP REQUIRED:")
    print("="*60)
    print("\n1. Open your Supabase Dashboard")
    print("2. Go to SQL Editor")
    print("3. Copy and paste the contents of 'database/update_trip_assignments.sql'")
    print("4. Click 'RUN' to execute the migration")
    print("\nOR use psql directly:")
    print(f"\n  psql {SUPABASE_URL} -f database/update_trip_assignments.sql")
    print("\n✅ After migration, existing trips will be visible in the driver trips view.")

if __name__ == "__main__":
    main()
