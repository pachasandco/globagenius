from app.config import DESTINATION_POPULARITY

# V5: hotel rating dropped — flight-only product, accommodation_rating was
# always 0 for flights, capping the effective score at 85/100. Redistributed
# 15 pts as +10 to discount, +5 to popularity.
W_DISCOUNT = 0.60
W_POPULARITY = 0.25
W_FLEXIBILITY = 0.15

DEFAULT_POPULARITY = 30
MAX_FLEXIBILITY = 5
MAX_POPULARITY = max(DESTINATION_POPULARITY.values()) if DESTINATION_POPULARITY else 100


def compute_score(
    discount_pct: float,
    destination_code: str,
    date_flexibility: int,
    accommodation_rating: float | None = None,  # kept for API compat, unused
) -> int:
    discount_score = min(discount_pct / 60.0 * 100.0, 100.0)
    raw_popularity = DESTINATION_POPULARITY.get(destination_code, DEFAULT_POPULARITY)
    popularity_score = min(raw_popularity / MAX_POPULARITY * 100.0, 100.0)
    flexibility_score = min(date_flexibility / MAX_FLEXIBILITY * 100.0, 100.0)

    total = (
        W_DISCOUNT * discount_score
        + W_POPULARITY * popularity_score
        + W_FLEXIBILITY * flexibility_score
    )

    return min(round(total), 100)
