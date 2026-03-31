from supabase import create_client, Client
from .config import get_settings

settings = get_settings()

# Public client (anon key) — respects RLS
supabase: Client = create_client(settings.supabase_url, settings.supabase_anon_key)

# Admin client (service role key) — bypasses RLS
supabase_admin: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)
