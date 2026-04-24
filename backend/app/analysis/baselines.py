from __future__ import annotations
from datetime import datetime, timezone
from dateutil.parser import parse as parse_date
import numpy as np

MIN_OBSERVATIONS = 10

# Lead-time buckets: how far in advance the flight was scraped vs departure date
# lt30 = booking < 30 days ahead, lt60 = 30-60 days, lt90 = 60-90 days, lt90p = 90+ days
LEAD_TIME_BUCKETS: list[tuple[str, int, int]] = [
    ("lt30",  0,  29),
    ("lt60", 30,  59),
    ("lt90", 60,  89),
    ("lt90p", 90, 999),
]


def lead_time_bucket(departure_date: str, scraped_at: str) -> str:
    """Return lead-time bucket label based on days between scrape and departure."""
    try:
        dep = datetime.strptime(departure_date[:10], "%Y-%m-%d")
        scraped = parse_date(scraped_at).replace(tzinfo=None)
        days_ahead = max((dep - scraped).days, 0)
    except Exception:
        return "lt90p"
    for label, lo, hi in LEAD_TIME_BUCKETS:
        if lo <= days_ahead <= hi:
            return label
    return "lt90p"


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


MIN_SAMPLE_COUNT = 5  # Lowered from 10 to allow seasonal sub-buckets to form
                       # earlier. Each bucket is now split by month + lead_time,
                       # so fewer observations per cell are expected. Will raise
                       # back to 10+ once 3-4 months of history are accumulated.


def compute_baselines_by_bucket(
    route_key_prefix: str,
    observations: list[dict],
) -> list[dict]:
    """Group observations by (duration_bucket, departure_month, lead_time_bucket)
    and return one baseline per qualifying cell.

    route_key format: CDG-JFK-bucket_long-m08-lt60
      - bucket_long  = trip duration bucket (short/medium/long)
      - m08          = departure month (01-12)
      - lt60         = lead time bucket (lt30/lt60/lt90/lt90p)

    Falls back to a legacy bucket-only key (CDG-JFK-bucket_long) when a
    seasonal cell has fewer than MIN_SAMPLE_COUNT observations, so the
    pipeline never degrades on new routes.

    Each observation must have: price, trip_duration_days, stops,
    duration_minutes, scraped_at, departure_date."""
    from app.analysis.buckets import bucket_for_duration, stops_allowed

    # --- Step 1: filter and assign sub-bucket keys ---
    # key = (bucket, month_str, lead_time_label)
    by_cell: dict[tuple[str, str, str], list[dict]] = {}
    by_bucket_legacy: dict[str, list[dict]] = {}

    for obs in observations:
        days = obs.get("trip_duration_days") or 0
        bucket = bucket_for_duration(days)
        if not bucket:
            continue
        max_stops = stops_allowed(obs.get("duration_minutes") or 0)
        if (obs.get("stops") or 0) > max_stops:
            continue

        # Departure month
        dep_date = obs.get("departure_date") or ""
        try:
            month_str = f"m{int(dep_date[5:7]):02d}"
        except (ValueError, IndexError):
            month_str = "m00"  # unknown month — lumped together

        # Lead-time bucket
        lt_label = lead_time_bucket(dep_date, obs.get("scraped_at") or "")

        cell_key = (bucket, month_str, lt_label)
        by_cell.setdefault(cell_key, []).append(obs)
        by_bucket_legacy.setdefault(bucket, []).append(obs)

    now = datetime.now(timezone.utc)
    result = []
    published_buckets: set[str] = set()

    # --- Step 2: publish seasonal baselines where sample count is sufficient ---
    for (bucket, month_str, lt_label), obs_list in by_cell.items():
        if len(obs_list) < MIN_SAMPLE_COUNT:
            continue
        prices = np.array([o["price"] for o in obs_list], dtype=float)
        median = float(np.median(prices))
        std = float(np.std(prices))
        rk = f"{route_key_prefix}-bucket_{bucket}-{month_str}-{lt_label}"
        result.append({
            "route_key": rk,
            "type": "flight",
            "avg_price": round(median, 2),
            "std_dev": round(std, 2),
            "sample_count": len(obs_list),
            "calculated_at": now.isoformat(),
        })
        published_buckets.add(bucket)

    # --- Step 3: legacy fallback baseline (no month/lead_time segmentation) ---
    # Published for every bucket that has enough observations, so routes with
    # < MIN_SAMPLE_COUNT per seasonal cell still get a baseline.
    for bucket, obs_list in by_bucket_legacy.items():
        if len(obs_list) < MIN_SAMPLE_COUNT:
            continue
        prices = np.array([o["price"] for o in obs_list], dtype=float)
        median = float(np.median(prices))
        std = float(np.std(prices))
        rk = f"{route_key_prefix}-bucket_{bucket}"
        result.append({
            "route_key": rk,
            "type": "flight",
            "avg_price": round(median, 2),
            "std_dev": round(std, 2),
            "sample_count": len(obs_list),
            "calculated_at": now.isoformat(),
        })

    return result
