"""Deal scorer — weights revised for v4.

Old weights (v3):  discount 50%, popularity 20%, flexibility 15%, accommodation_rating 15%
New weights (v4):  discount 40%, popularity 30%, freshness 15%, trust_source 15%

Changes:
- accommodation_rating removed (always 0 for flight-only deals)
- popularity weight raised (better signal for flight deals)
- freshness added: recent deals score higher (urgency driver)
- trust_source added: tier1 direct > travelpayouts > apify
"""
from datetime import datetime, timezone

from app.config import DESTINATION_POPULARITY

W_DISCOUNT = 0.40
W_POPULARITY = 0.30
W_FRESHNESS = 0.15
W_TRUST = 0.15

DEFAULT_POPULARITY = 30
MAX_POPULARITY = max(DESTINATION_POPULARITY.values()) if DESTINATION_POPULARITY else 100

# Freshness decay: full score at 0h, zero at FRESHNESS_DECAY_HOURS
FRESHNESS_DECAY_HOURS = 48

# Trust scores per source
TRUST_SCORES: dict[str, float] = {
    "ryanair_direct": 1.0,
    "vueling_direct": 1.0,
    "transavia_direct": 1.0,
    "travelpayouts": 0.75,
    "apify": 0.80,
    "google_flights": 0.85,
}
DEFAULT_TRUST = 0.70


def compute_score(
    discount_pct: float,
    destination_code: str,
    # Legacy params kept for backward compat — ignored in v4
    date_flexibility: int = 0,
    accommodation_rating: float | None = None,
    # New v4 params
    scraped_at: str | None = None,
    source: str | None = None,
) -> int:
    discount_score = min(discount_pct / 60.0 * 100.0, 100.0)

    raw_popularity = DESTINATION_POPULARITY.get(destination_code, DEFAULT_POPULARITY)
    popularity_score = min(raw_popularity / MAX_POPULARITY * 100.0, 100.0)

    if scraped_at:
        try:
            ts = datetime.fromisoformat(scraped_at.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            freshness_score = max(0.0, 1.0 - age_hours / FRESHNESS_DECAY_HOURS) * 100.0
        except Exception:
            freshness_score = 50.0
    else:
        freshness_score = 50.0

    trust_ratio = TRUST_SCORES.get(source or "", DEFAULT_TRUST)
    trust_score = trust_ratio * 100.0

    total = (
        W_DISCOUNT * discount_score
        + W_POPULARITY * popularity_score
        + W_FRESHNESS * freshness_score
        + W_TRUST * trust_score
    )

    return min(round(total), 100)
