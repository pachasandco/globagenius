"""Deal-level deduplication helper for Telegram alerts."""
import hashlib

# One alert per (user, destination, departure_date, return_date) per week.
# Exact same itinerary won't re-alert for 7 days regardless of which run
# or which origin airport triggered it. A price drop significant enough to
# cross a 50€ bucket boundary generates a new key → new alert immediately.
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
    """Compute a stable dedup key for a (user, itinerary, price_bucket) tuple.

    Keyed on (user, destination, departure_date, return_date, price_bucket).
    Same itinerary from any origin at the same price level → one alert per week.
    If the price drops to a new 50€ bucket, it's a genuinely better deal → new alert.
    Origin excluded: CDG→BCN and ORY→BCN same dates same bucket = one alert.
    """
    bucket = _price_bucket(price)
    dep = departure_date[:10] if departure_date else ""
    ret = return_date[:10] if return_date else ""
    raw = f"{user_id}|{destination}|{dep}|{ret}|{bucket}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def compute_oneway_alert_key(
    user_id: str,
    origin: str,
    destination: str,
    direction: str,
    departure_date: str = "",
    price: float = 0,
) -> str:
    """V5+ P1: dedup key for one-way alerts.

    Direction matters here (CDG→JFK outbound ≠ JFK→CDG inbound), unlike
    round-trip where origin is dropped. Same price-bucket logic as round-trip.
    """
    bucket = _price_bucket(price)
    dep = departure_date[:10] if departure_date else ""
    raw = f"{user_id}|ow|{origin}|{destination}|{direction}|{dep}|{bucket}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def compute_split_ticket_alert_key(
    user_id: str,
    origin: str,
    destination: str,
    outbound_date: str,
    inbound_date: str,
    total_price: float,
) -> str:
    """V5+ P1: dedup key for split-ticket combo alerts.

    A combo is conceptually an A/R sold as 2 tickets — the dedup key
    mirrors round-trip's shape but is namespaced separately so an A/R and
    a combo on the same dates don't collide.
    """
    bucket = _price_bucket(total_price)
    out = outbound_date[:10] if outbound_date else ""
    inb = inbound_date[:10] if inbound_date else ""
    raw = f"{user_id}|st|{destination}|{out}|{inb}|{bucket}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
