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


MIN_SAMPLE_COUNT = 10  # See spec note: relaxed from 30 because the API
                        # returns ~10-50 round-trips total per route, often
                        # under 30 once split into 3 duration buckets.
                        # Future work: cumulative baselines from raw_flights
                        # history to safely raise this back to 30+.


def compute_baselines_by_bucket(
    route_key_prefix: str,
    observations: list[dict],
) -> list[dict]:
    """Group observations by duration bucket and return one baseline per qualifying bucket.

    Each observation must have: price, trip_duration_days, stops, duration_minutes,
    scraped_at. Observations outside any duration bucket, or violating the stops rule,
    are filtered out. Baselines with fewer than MIN_SAMPLE_COUNT observations are not
    published. The median (not the mean) is used for `avg_price` to be robust to outliers."""
    from app.analysis.buckets import bucket_for_duration, stops_allowed

    by_bucket: dict[str, list[dict]] = {}
    for obs in observations:
        days = obs.get("trip_duration_days") or 0
        bucket = bucket_for_duration(days)
        if not bucket:
            continue
        max_stops = stops_allowed(obs.get("duration_minutes") or 0)
        if (obs.get("stops") or 0) > max_stops:
            continue
        by_bucket.setdefault(bucket, []).append(obs)

    now = datetime.now(timezone.utc)
    result = []
    for bucket, obs_list in by_bucket.items():
        if len(obs_list) < MIN_SAMPLE_COUNT:
            continue
        prices = np.array([o["price"] for o in obs_list], dtype=float)
        median = float(np.median(prices))
        std = float(np.std(prices))
        result.append({
            "route_key": f"{route_key_prefix}-bucket_{bucket}",
            "type": "flight",
            "avg_price": round(median, 2),
            "std_dev": round(std, 2),
            "sample_count": len(obs_list),
            "calculated_at": now.isoformat(),
        })
    return result
