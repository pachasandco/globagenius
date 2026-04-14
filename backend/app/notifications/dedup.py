"""Deal-level deduplication helper for Telegram alerts."""
import hashlib


def compute_alert_key(
    user_id: str,
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    price: float,
) -> str:
    """Compute a stable 32-char SHA256-based key identifying a unique deal
    for a given user. Follows the pipe-delimited SHA256 pattern from
    scraper/normalizer.py. Price is rounded to int so micro-fluctuations
    don't create duplicate keys.
    """
    raw = f"{user_id}|{origin}|{destination}|{departure_date}|{return_date}|{round(price)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
