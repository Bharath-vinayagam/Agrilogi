#!/usr/bin/env python3
"""Apply trip_assignments table to Supabase."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from supabase import create_client
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing Supabase credentials")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

SQL = """
create table if not exists trip_assignments (
  id uuid primary key default uuid_generate_v4(),
  driver_id uuid references users(id) on delete set null,
  bundle_id text references bundles(id) on delete set null,
  trip_status text not null default 'Driver Assigned',
  start_time timestamptz,
  end_time timestamptz,
  created_at timestamptz default now()
);
create index if not exists idx_trip_assignments_driver on trip_assignments(driver_id);
create index if not exists idx_trip_assignments_bundle on trip_assignments(bundle_id);
create index if not exists idx_trip_assignments_status on trip_assignments(trip_status);
"""

statements = [s.strip() for s in SQL.strip().split(";") if s.strip()]
success = 0
for stmt in statements:
    try:
        supabase.rpc("exec_sql", {"query": stmt + ";"}).execute()
        print(f"  ✅ {stmt[:60]}...")
        success += 1
    except Exception as e:
        print(f"  ⚠️  RPC unavailable: {str(e)[:60]}")

if success < len(statements):
    print("\n📋 Run this manually in Supabase SQL Editor:\n")
    print("=" * 60)
    print(SQL)
    print("=" * 60)
    print("\nhttps://supabase.com/dashboard → SQL Editor → New Query")
else:
    print("\n🎉 trip_assignments table applied successfully!")
