"""V5+ P1: one-way deal qualification (option C — pre-baseline).

Until we have a mature one-way baseline (~4-6 weeks of data), we qualify
one-way deals on raw discount vs the median price seen on the same
(origin, destination, direction) over the last N days.

This is intentionally a pure function: callers fetch the history from the
DB and pass it in. Easier to test, easier to reason about, easier to swap
for a baseline-driven version once the data has matured.
"""

from dataclasses import dataclass
from statistics import median

from app.thresholds import (
    ONEWAY_DISCOUNT_PCT_FLOOR,
    ONEWAY_MIN_OBSERVATIONS,
)


@dataclass(frozen=True)
class OnewayQualification:
    price: float
    median: float
    discount_pct: float


def qualify_oneway(
    price: float,
    recent_prices: list[float],
    discount_floor_pct: float = ONEWAY_DISCOUNT_PCT_FLOOR,
    min_observations: int = ONEWAY_MIN_OBSERVATIONS,
) -> OnewayQualification | None:
    """Decide whether a one-way candidate price beats its recent history hard
    enough to be a real deal. Returns None when the candidate doesn't qualify.

    Args:
        price: candidate one-way price in EUR.
        recent_prices: prices observed on the same route+direction over the
            last ONEWAY_MEDIAN_LOOKBACK_DAYS days. Zero/negative values are
            stripped (Travelpayouts can return 0 for unavailable rows).
        discount_floor_pct: minimum discount vs median to qualify (default 60).
        min_observations: minimum number of valid history points (default 5).
    """
    if price <= 0:
        return None

    valid_history = [p for p in recent_prices if p > 0]
    if len(valid_history) < min_observations:
        return None

    med = float(median(valid_history))
    if med <= 0:
        return None
    if price > med:
        return None

    discount_pct = (med - price) / med * 100.0
    if discount_pct < discount_floor_pct:
        return None

    return OnewayQualification(
        price=round(price, 2),
        median=round(med, 2),
        discount_pct=round(discount_pct, 2),
    )
