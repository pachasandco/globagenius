"""Price anomaly detection with tiered alert classification.

Alert levels:
- FARE_MISTAKE: z_score >= 3.5, discount > 60% — airline pricing error
- FLASH_PROMO: z_score >= 2.5, discount > 40% — flash sale or promo
- GOOD_DEAL:   z_score >= 2.0, discount > 20% — below market price
              (raised from 1.0 while baselines mature — revert after 3 months
               of price_observations accumulation)
"""

import statistics
from dataclasses import dataclass
from app.config import settings


@dataclass
class QualifiedItem:
    price: float
    baseline_price: float
    discount_pct: float
    z_score: float
    alert_level: str  # "fare_mistake", "flash_promo", "good_deal"


def detect_anomaly(price: float, baseline: dict) -> QualifiedItem | None:
    avg_price = baseline["avg_price"]
    std_dev = baseline["std_dev"]

    if std_dev <= 0:
        return None

    if price >= avg_price:
        return None

    z_score = (avg_price - price) / std_dev
    discount_pct = (avg_price - price) / avg_price * 100

    # Tiered classification
    if z_score >= 3.5 and discount_pct >= 60:
        alert_level = "fare_mistake"
    elif z_score >= 2.5 and discount_pct >= 40:
        alert_level = "flash_promo"
    elif z_score >= 2.0 and discount_pct >= 20:
        alert_level = "good_deal"
    else:
        return None

    return QualifiedItem(
        price=round(price, 2),
        baseline_price=round(avg_price, 2),
        discount_pct=round(discount_pct, 2),
        z_score=round(z_score, 2),
        alert_level=alert_level,
    )


def is_generalized_floor(
    candidate_price: float,
    neighbor_prices: list[float],
    *,
    min_neighbors: int = 3,
    ratio_threshold: float = 0.90,
) -> bool:
    """True when the candidate price is NOT meaningfully below its
    neighboring departure dates — i.e. it's a generalized price floor for
    the period, not a punctual dip, so it should not be alerted as a deal.

    The anomaly detector compares a candidate against a *historical*
    baseline (a median over past scrapes). That catches "cheaper than
    usual" but not "cheaper than the days around it". A route whose whole
    week sits at 18€ while the stored baseline still says 104€ produces a
    fake -83% — the price is normal, the baseline is just stale/mis-bucketed.
    This guard compares the candidate to the actual prices scraped for the
    ±N adjacent departure dates.

    Conservative by design:
      - Returns False (don't reject) when fewer than `min_neighbors`
        neighboring prices exist — we never suppress a deal for lack of
        data. Measured 2026-07-22: ~62% of deals have <3 neighbors scraped,
        so a stricter default would silence most alerts.
      - Rejects only when candidate_price >= ratio_threshold × median of
        neighbors, i.e. the "deal" fails to beat its neighbors by more
        than (1 - ratio_threshold).

    Args:
        candidate_price: the alerted flight's price.
        neighbor_prices: prices scraped for adjacent departure dates on the
            same route + duration bucket (excluding the candidate's own date).
        min_neighbors: minimum neighbor prices required to decide.
        ratio_threshold: candidate/median at or above which it's a floor.

    Returns True → reject (generalized floor). False → keep (real dip or
    undecidable).
    """
    if len(neighbor_prices) < min_neighbors:
        return False
    median = statistics.median(neighbor_prices)
    if median <= 0:
        return False
    return (candidate_price / median) >= ratio_threshold
