"""Deal-level deduplication helper for Telegram alerts."""
import hashlib

# After an alert is sent, suppress re-alerts for the same itinerary for
# this many hours — regardless of source (Tier 1 or Travelpayouts) or
# minor price variations. Covers the full Travelpayouts refresh cycle (2h)
# plus a safety margin.
ALERT_INHIBIT_HOURS = 6


def compute_alert_key(
    user_id: str,
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    price: float = 0,  # kept for backward compat but ignored in key
) -> str:
    """Compute a stable 32-char key identifying a unique deal for a user.

    Keyed on (user, destination, departure_date, return_date) — origin is
    intentionally excluded so that CDG→FCO and ORY→FCO on the same dates
    share the same key. Whichever is dispatched first (cheapest) blocks the
    duplicate from the other airport within ALERT_INHIBIT_HOURS.

    Price is also excluded so that minor fluctuations between scrapes don't
    generate duplicates.

    Dedup window: ALERT_INHIBIT_HOURS (6h). After that, the deal is
    considered stale enough that a renewed alert is legitimate.
    """
    raw = f"{user_id}|{destination}|{departure_date}|{return_date}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
