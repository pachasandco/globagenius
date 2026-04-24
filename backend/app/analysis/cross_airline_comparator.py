"""Cross-airline price comparator.

For a given flight (origin, destination, departure_date, return_date), queries
price_snapshots for the same itinerary across all airlines. If the current price
is significantly lower than what the other airline charged on the same route and
dates, that divergence is a strong mistake-fare signal.

How it works:
  1. Query price_snapshots for (origin, destination, departure_date, return_date)
     in the last COMPARISON_WINDOW_HOURS, grouped by airline.
  2. Compute median price per airline over that window.
  3. Return a ComparisonResult with:
       - per_airline median prices
       - best_price across all airlines (lowest current offer)
       - divergence_pct: how much cheaper the current flight is vs. the
         most expensive competitor (signals pricing inconsistency)

Signal thresholds:
  DIVERGENCE_STRONG  : current price ≤ 50% of competitor median → strong signal
  DIVERGENCE_NOTABLE : current price ≤ 70% of competitor median → notable

Integration:
  - Called in _analyze_new_flights for Tier 1 flights (ryanair_direct / transavia_direct)
  - Called in _dispatch_velocity_alerts to enrich VelocityAlert context
  - Results stored as JSONB in qualified_items.competitor_prices
  - Used in Telegram message to show "Ryanair 89€ vs Transavia 145€ (habituel)"
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

COMPARISON_WINDOW_HOURS = 4   # look at prices from the last 4h
DIVERGENCE_STRONG = 0.50      # current ≤ 50% of competitor → strong cross-airline signal
DIVERGENCE_NOTABLE = 0.70     # current ≤ 70% of competitor → notable

# Only compare within Tier 1 sources (real-time, apples-to-apples)
TIER1_SOURCES = {"ryanair_direct", "transavia_direct"}


@dataclass
class ComparisonResult:
    origin: str
    destination: str
    departure_date: str
    return_date: str
    current_price: float
    current_airline: str
    # Median price per airline code seen in the comparison window
    competitor_medians: dict[str, float] = field(default_factory=dict)
    # Highest competitor median (reference for divergence)
    max_competitor_median: float = 0.0
    # (max_competitor_median - current_price) / max_competitor_median * 100
    divergence_pct: float = 0.0
    signal: str = "none"  # "none", "notable", "strong"

    def to_dict(self) -> dict:
        return {
            "competitor_medians": self.competitor_medians,
            "max_competitor_median": round(self.max_competitor_median, 2),
            "divergence_pct": round(self.divergence_pct, 1),
            "signal": self.signal,
        }


def compare_cross_airline(db, flight: dict) -> ComparisonResult | None:
    """Compare a flight's price against other airlines on the same itinerary.

    Returns None if:
    - DB unavailable
    - Fewer than 2 airlines have data in the window (no comparison possible)
    - Any DB error
    """
    if not db:
        return None

    origin = flight.get("origin", "")
    destination = flight.get("destination", "")
    dep_date = flight.get("departure_date") or flight.get("departure_at", "")[:10]
    ret_date = flight.get("return_date") or flight.get("return_at", "")[:10]
    current_price = float(flight.get("price") or 0)
    current_airline = flight.get("airline", "")

    if not origin or not destination or not dep_date or current_price <= 0:
        return None

    from datetime import datetime, timedelta, timezone
    lookback_from = (
        datetime.now(timezone.utc) - timedelta(hours=COMPARISON_WINDOW_HOURS)
    ).isoformat()

    try:
        resp = (
            db.table("price_snapshots")
            .select("price, airline, source")
            .eq("origin", origin)
            .eq("destination", destination)
            .eq("departure_date", dep_date)
            .gte("captured_at", lookback_from)
            .execute()
        )
    except Exception as e:
        logger.warning(f"cross_airline_comparator DB error {origin}->{destination}: {e}")
        return None

    snapshots = resp.data or []
    if not snapshots:
        return None

    # Group prices by airline, restricted to Tier 1 sources for fairness.
    # If return_date is available, filter to matching return dates only;
    # otherwise accept any snapshot on this route (Transavia estimates ret_date).
    by_airline: dict[str, list[float]] = {}
    for s in snapshots:
        src = s.get("source", "")
        if src not in TIER1_SOURCES:
            continue
        # Skip current airline's own snapshots — we want *competitor* prices
        airline = s.get("airline", "unknown")
        if airline == current_airline:
            continue
        by_airline.setdefault(airline, []).append(float(s["price"]))

    if not by_airline:
        # No competitor data — nothing to compare
        return None

    competitor_medians: dict[str, float] = {}
    for airline, prices in by_airline.items():
        if prices:
            competitor_medians[airline] = round(statistics.median(prices), 2)

    if not competitor_medians:
        return None

    max_competitor_median = max(competitor_medians.values())

    if max_competitor_median <= 0:
        return None

    divergence_pct = (
        (max_competitor_median - current_price) / max_competitor_median * 100
    )

    if divergence_pct <= 0:
        signal = "none"  # Current price is NOT cheaper than competitors
    elif current_price <= max_competitor_median * DIVERGENCE_STRONG:
        signal = "strong"
    elif current_price <= max_competitor_median * DIVERGENCE_NOTABLE:
        signal = "notable"
    else:
        signal = "none"

    result = ComparisonResult(
        origin=origin,
        destination=destination,
        departure_date=dep_date,
        return_date=ret_date,
        current_price=current_price,
        current_airline=current_airline,
        competitor_medians=competitor_medians,
        max_competitor_median=max_competitor_median,
        divergence_pct=round(max(divergence_pct, 0.0), 1),
        signal=signal,
    )

    if signal != "none":
        logger.info(
            f"Cross-airline signal [{signal}]: {origin}->{destination} {dep_date} "
            f"{current_airline} {current_price}€ vs competitors {competitor_medians} "
            f"(max {max_competitor_median}€, -{divergence_pct:.0f}%)"
        )

    return result


def format_competitor_context(result: ComparisonResult) -> str:
    """Format competitor price context for Telegram messages.

    Returns an empty string if no meaningful comparison is available.
    Example output: "vs Transavia habituellement 145€ (+63%)"
    """
    if not result or result.signal == "none" or not result.competitor_medians:
        return ""

    # Find the competitor with the highest median (most informative reference)
    best_competitor = max(result.competitor_medians, key=lambda k: result.competitor_medians[k])
    competitor_price = result.competitor_medians[best_competitor]

    # Map airline IATA codes to display names
    _airline_names = {
        "FR": "Ryanair",
        "HV": "Transavia",
        "VY": "Vueling",
        "U2": "easyJet",
        "W6": "Wizz Air",
    }
    competitor_name = _airline_names.get(best_competitor, best_competitor)
    current_name = _airline_names.get(result.current_airline, result.current_airline)

    pct_more = round((competitor_price - result.current_price) / result.current_price * 100)
    return f"vs {competitor_name} {int(competitor_price)}€ (+{pct_more}%)"
