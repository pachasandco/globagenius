"""Deal-level deduplication helper for Telegram alerts."""
import hashlib

# One alert per (user, destination, price_bucket) per week.
# Same destination at the same price level won't re-alert for 7 days.
# If the price drops to a new bucket (every 50€), it's a new deal → new alert.
ALERT_INHIBIT_HOURS = 168  # 7 days

PRICE_BUCKET_SIZE = 50  # €


def _price_bucket(price: float) -> int:
    """Round price down to nearest 50€ bucket. 85€ → 50, 130€ → 100."""
    return int(price // PRICE_BUCKET_SIZE) * PRICE_BUCKET_SIZE


def compute_alert_key(
    user_id: str,
    origin: str,
    destination: str,
    departure_date: str = "",
    return_date: str = "",
    price: float = 0,
) -> str:
    """Compute a stable dedup key for a (user, destination, price_bucket) tuple.

    Keyed on (user, destination, price_bucket) — origin and dates excluded.
    All date variants of CDG→FCO at ~85€ share one key → one alert per week.
    If the price drops from 85€ (bucket 50) to 45€ (bucket 0), that's a new
    bucket → new alert fires immediately regardless of the 7-day window.
    """
    bucket = _price_bucket(price)
    raw = f"{user_id}|{destination}|{bucket}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
