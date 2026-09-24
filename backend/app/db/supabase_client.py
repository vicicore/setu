from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_supabase_admin() -> Client:
    """Service-role client — bypasses RLS. Use only from trusted backend
    code paths (orchestration engine, connectors, admin endpoints), never
    forwarded to the frontend."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_supabase_as_user(access_token: str) -> Client:
    """Client scoped to a citizen's/official's own JWT — RLS applies."""
    settings = get_settings()
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(access_token)
    return client
