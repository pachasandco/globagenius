import logging
from supabase import create_client, Client
from app.config import settings

logger = logging.getLogger(__name__)


def get_supabase_client() -> Client | None:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        logger.warning("SUPABASE_URL or SUPABASE_SERVICE_KEY not set, running without database")
        return None
    try:
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")
        return None


db = get_supabase_client()
