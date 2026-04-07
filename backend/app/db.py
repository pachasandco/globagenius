from supabase import create_client, Client
from app.config import settings


def get_supabase_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


db = get_supabase_client() if settings.SUPABASE_URL else None
