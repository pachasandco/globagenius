"""Credibility guard for the value claims shown in Freemium emails.

The email block is titled "Meilleure opportunité manquée". It must therefore
rank deals by the verified euro saving, not only by the percentage discount.
It must also avoid turning a one-way fare or an implausibly low long-haul
baseline into a round-trip marketing claim.

This module only changes email statistics. It does not change deal detection,
Telegram alerts, Freemium quotas or the stored qualified items.
"""

from __future__ import annotations

from typing import Any

from app.analysis.route_selector import is_long_haul
from app.thresholds import FREE_TIER_DAILY_BAND_MIN_PCT

# Marketing claims need a stricter guard than alerting. A long-haul round-trip
# reference below this conservative floor is more likely to be a one-way,
# fallback or malformed baseline. The deal can still exist in the product; it
# is simply excluded from the "estimated saving" block until the data is sound.
LONG_HAUL_MARKETING_BASELINE_FLOOR_EUR = 500.0

# Small differences are expected after rounding. Larger gaps mean the stored
# percentage and the price/baseline pair do not describe the same observation.
DISCOUNT_COHERENCE_TOLERANCE_POINTS = 3.0


def _number(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _credible_roundtrip_value(deal: dict) -> dict | None:
    """Return coherent round-trip value metrics, otherwise ``None``.

    The Brevo templates do not currently display the trip type. One-way and
    split-ticket rows are therefore deliberately excluded from this headline
    block so they cannot be mistaken for a normal return fare.
    """

    if (deal.get("trip_type") or "round_trip") != "round_trip":
        return None

    price = _number(deal.get("price"))
    baseline = _number(deal.get("baseline_price"))
    if price is None or baseline is None or baseline <= price:
        return None

    savings = baseline - price
    implied_discount = savings / baseline * 100
    declared_discount = _number(deal.get("discount_pct"))
    if (
        declared_discount is not None
        and abs(declared_discount - implied_discount)
        > DISCOUNT_COHERENCE_TOLERANCE_POINTS
    ):
        return None

    destination = str(deal.get("destination") or "").upper()
    if destination and is_long_haul(destination):
        if baseline < LONG_HAUL_MARKETING_BASELINE_FLOOR_EUR:
            return None

    return {
        "destination": destination,
        "discount_pct": round(implied_discount, 1),
        "price": round(price, 2),
        "baseline_price": round(baseline, 2),
        "savings": round(savings),
    }


def summarize_matching_deals_credible(
    deals: list[dict],
    sent_full_alerts: list[dict],
    prefs: dict,
) -> dict:
    """Summarize a user's matching deals with credible value selection.

    Counts remain identical to the historical implementation. Only the
    selection of ``best_missed`` changes:

    * rank by absolute euro saving first;
    * use a coherent price/baseline pair to recompute the displayed discount;
    * exclude one-way/split rows from a round-trip-looking marketing block;
    * exclude implausibly low long-haul baselines from savings claims.
    """

    airports = set(prefs.get("airport_codes") or [])
    blocked = set(prefs.get("blocked_destinations") or [])
    trip_types = set(
        prefs.get("flight_trip_types") or ["round_trip", "one_way"]
    )

    matching: list[dict] = []
    for deal in deals:
        if deal.get("origin") not in airports:
            continue
        if deal.get("destination") in blocked:
            continue
        if (deal.get("trip_type") or "round_trip") not in trip_types:
            continue
        if (deal.get("discount_pct") or 0) < FREE_TIER_DAILY_BAND_MIN_PCT:
            continue
        matching.append(deal)

    sent_keys = {
        (alert.get("destination"), (alert.get("departure_date") or "")[:10])
        for alert in sent_full_alerts
    }
    received = [
        deal
        for deal in matching
        if (
            deal.get("destination"),
            (deal.get("departure_date") or "")[:10],
        )
        in sent_keys
    ]
    missed = [
        deal
        for deal in matching
        if (
            deal.get("destination"),
            (deal.get("departure_date") or "")[:10],
        )
        not in sent_keys
    ]

    credible = [
        value
        for deal in missed
        if (value := _credible_roundtrip_value(deal)) is not None
    ]
    best = max(
        credible,
        key=lambda value: (value["savings"], value["discount_pct"]),
        default=None,
    )

    return {
        "matching": len(matching),
        "received_full": len(received),
        "missed": len(missed),
        "best_missed": best,
    }


def install_freemium_savings_guard(freemium_digest_module: Any) -> None:
    """Install the guard once on the Freemium email module."""

    if getattr(freemium_digest_module, "_savings_guard_installed", False):
        return

    freemium_digest_module.summarize_matching_deals = (
        summarize_matching_deals_credible
    )

    # Expose auditable values to Brevo. Existing templates ignore these extra
    # params safely; a later template revision can show "X € au lieu de Y €".
    original_digest_params = freemium_digest_module._digest_params

    def digest_params_with_prices(user: dict, stats: dict) -> dict:
        params = original_digest_params(user, stats)
        best = stats.get("best_missed") or {}
        params["BEST_MISSED_PRICE"] = round(best.get("price") or 0)
        params["BEST_MISSED_BASELINE"] = round(
            best.get("baseline_price") or 0
        )
        return params

    freemium_digest_module._digest_params = digest_params_with_prices
    freemium_digest_module._savings_guard_installed = True
