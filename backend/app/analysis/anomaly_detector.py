from dataclasses import dataclass
from app.config import settings

# TEMPORARY: lowered to 5% for testing package creation. Revert to 1.0 / 20 after test.
Z_SCORE_THRESHOLD = 0.3
MIN_FREE_DISCOUNT = 5


@dataclass
class QualifiedItem:
    price: float
    baseline_price: float
    discount_pct: float
    z_score: float


def detect_anomaly(price: float, baseline: dict) -> QualifiedItem | None:
    avg_price = baseline["avg_price"]
    std_dev = baseline["std_dev"]

    if std_dev <= 0:
        return None

    if price >= avg_price:
        return None

    z_score = (avg_price - price) / std_dev
    discount_pct = (avg_price - price) / avg_price * 100

    if z_score < Z_SCORE_THRESHOLD:
        return None

    if discount_pct < MIN_FREE_DISCOUNT:
        return None

    return QualifiedItem(
        price=round(price, 2),
        baseline_price=round(avg_price, 2),
        discount_pct=round(discount_pct, 2),
        z_score=round(z_score, 2),
    )
