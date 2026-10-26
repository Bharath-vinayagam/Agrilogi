"""
Apply verification schema migration to Supabase database.
Run this script to add OTP, vehicle verification, and license verification fields.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from database.db import supabase_client

def apply_verification_schema():
    """Apply verification fields migration."""
    
    if not supabase_client:
        print("❌ Error: Supabase client not initialized. Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
        return False
    
    migration_file = Path(__file__).parent / "add_verification_fields.sql"
    
    if not migration_file.exists():
        print(f"❌ Error: Migration file not found: {migration_file}")
        return False
    
    print("📋 Reading migration file...")
    sql = migration_file.read_text(encoding='utf-8')
    
    print("🔄 Applying verification schema migration...")
    
    try:
        # Execute migration using Supabase RPC or direct SQL
        # Note: Supabase Python client doesn't directly support raw SQL execution
        # You'll need to run this SQL in Supabase SQL Editor or use psycopg2
        
        print("\n⚠️  MANUAL STEP REQUIRED:")
        print("=" * 60)
        print("Please execute the following SQL in your Supabase SQL Editor:")
        print("=" * 60)
        print(sql)
        print("=" * 60)
        print("\n✅ After running the SQL, verification schema will be ready!")
        print("\nAlternatively, run:")
        print(f"  psql <your-database-url> < {migration_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Agrilogi Verification Schema Migration\n")
    success = apply_verification_schema()
    
    if success:
        print("\n✅ Migration script completed successfully!")
        print("\n📝 Next steps:")
        print("   1. Run the SQL in Supabase SQL Editor")
        print("   2. Verify tables have new columns")
        print("   3. Test OTP functionality")
    else:
        print("\n❌ Migration failed. Please check the error messages above.")
        sys.exit(1)
