from datetime import datetime, timezone
from dateutil.parser import parse as parse_date
import numpy as np

MIN_OBSERVATIONS = 10


def compute_weighted_average(prices: list[float], ages_days: list[float]) -> tuple[float, float]:
    if not prices:
        return 0.0, 0.0

    prices_arr = np.array(prices)
    ages_arr = np.array(ages_days)

    weights = 1.0 / np.maximum(ages_arr, 0.1)
    weights = weights / weights.sum()

    avg = float(np.average(prices_arr, weights=weights))
    variance = float(np.average((prices_arr - avg) ** 2, weights=weights))
    std = float(np.sqrt(variance))

    return round(avg, 2), round(std, 2)


def compute_baseline(
    route_key: str, type_: str, observations: list[dict]
) -> dict | None:
    if len(observations) < MIN_OBSERVATIONS:
        return None

    now = datetime.now(timezone.utc)
    prices = []
    ages = []

    for obs in observations:
        prices.append(obs["price"])
        scraped = parse_date(obs["scraped_at"])
        age_days = max((now - scraped).total_seconds() / 86400, 0.1)
        ages.append(age_days)

    avg_price, std_dev = compute_weighted_average(prices, ages)

    return {
        "route_key": route_key,
        "type": type_,
        "avg_price": avg_price,
        "std_dev": std_dev,
        "sample_count": len(observations),
        "calculated_at": now.isoformat(),
    }
