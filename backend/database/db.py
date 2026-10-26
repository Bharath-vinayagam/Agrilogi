import sys
import time
from supabase import create_client, Client
from settings import settings


def create_supabase_client_with_retry(url: str, key: str, retries: int = 3, delay: float = 2.0) -> Client:
    """Create Supabase client, retrying on initial connection failure."""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            client = create_client(url, key)
            # Warm up: run a lightweight ping to confirm the connection
            client.table("users").select("id").limit(1).execute()
            print(f"Supabase connected successfully (attempt {attempt})")
            return client
        except Exception as e:
            last_error = e
            print(f"Supabase connection attempt {attempt} failed: {e}", file=sys.stderr)
            if attempt < retries:
                time.sleep(delay)
    print(f"WARNING: Could not connect to Supabase after {retries} attempts: {last_error}", file=sys.stderr)
    return None


if not settings.supabase_url or not settings.supabase_service_role_key:
    print("WARNING: supabase_url or supabase_service_role_key is missing in settings.", file=sys.stderr)
    supabase_client: Client = None
else:
    supabase_client: Client = create_supabase_client_with_retry(
        settings.supabase_url,
        settings.supabase_service_role_key
    )
