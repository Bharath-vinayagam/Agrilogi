#!/usr/bin/env python3
"""
Apply time slot schema updates to Supabase database
"""
import os
import sys
from pathlib import Path

# Add backend to path to use its .env
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from backend/.env
env_path = Path(__file__).parent.parent / "backend" / ".env"
load_dotenv(env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not found in environment")
    print(f"   Looked in: {env_path}")
    exit(1)

print(f"✓ Using Supabase URL: {SUPABASE_URL}")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def apply_schema():
    print("📦 Reading time slot schema updates...")
    
    sql_file = Path(__file__).parent / "add_time_slots.sql"
    with open(sql_file, "r") as f:
        sql = f.read()
    
    print("\n" + "="*60)
    print("SUPABASE SQL TO EXECUTE")
    print("="*60)
    print("\nPlease execute the following SQL in Supabase SQL Editor:")
    print("(Dashboard → SQL Editor → New Query)\n")
    print(sql)
    print("\n" + "="*60)
    
    print("\n✅ SQL script displayed above.")
    print("📋 Copy and paste it into Supabase SQL Editor to apply the schema.")
    print("\n💡 Alternative: The backend will auto-create missing columns when you create a booking.")
    
    return True

if __name__ == "__main__":
    apply_schema()
