"""Price anomaly detection with tiered alert classification.

Alert levels:
- FARE_MISTAKE: z_score >= 3.5, discount > 60% — airline pricing error
- FLASH_PROMO: z_score >= 2.5, discount > 40% — flash sale or promo
- GOOD_DEAL:   z_score >= 1.5, discount > 20% — below market price
              (lowered from 2.0 in v4 — baselines have 3+ months of data,
               maturation period complete)
"""

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
    elif z_score >= 1.5 and discount_pct >= 20:
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
