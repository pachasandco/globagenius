"""Duration bucketing and short/long-haul classification.

Pure functions, no I/O. Used by the flight scraper, the baseline builder,
and the deal analyzer to apply consistent rules across the pipeline."""

DURATION_BUCKETS: dict[str, tuple[int, int]] = {
    "short":    (1, 3),
    "medium":   (4, 7),
    "long":     (8, 12),
    "extended": (13, 21),
}

SHORT_HAUL_MAX_MINUTES = 180

# Maximum trip duration we accept, by haul type (2026-07-24).
#
# The single 12-day cap was silently discarding the best long-haul fares:
# airlines price their most aggressive round-trips on 2-3 week stays, which
# is also how people actually travel to the other side of the world.
# Measured on live Travelpayouts data: CDG→Tokyo 449€ on a 14-day stay vs
# 720€ for anything ≤12 days (-38%), Sydney -25%, Johannesburg -11%. Six of
# the eight cheapest CDG→HND round-trips were rejected on duration alone.
#
# Long-haul goes to 21 days; everything else to 14. This only raises the
# CEILING — the founder's minimum-stay rule (MIN_STAY_NIGHTS) is enforced
# elsewhere and is untouched.
MAX_STAY_DAYS_LONG_HAUL = 21
MAX_STAY_DAYS_DEFAULT = 14


def max_stay_days(destination: str | None = None) -> int:
    """Maximum trip duration in days for this destination's haul type.

    Falls back to the conservative default (never the long-haul ceiling)
    when no destination is provided, so legacy callers can't accidentally
    widen the window for Europe."""
    if destination:
        from app.analysis.route_selector import is_long_haul
        if is_long_haul(destination):
            return MAX_STAY_DAYS_LONG_HAUL
    return MAX_STAY_DAYS_DEFAULT


def bucket_for_duration(days: int, destination: str | None = None) -> str | None:
    """Return the bucket name for a trip duration, or None if out of range.

    `destination` decides the upper bound: long-haul stays are accepted up
    to MAX_STAY_DAYS_LONG_HAUL, everything else up to MAX_STAY_DAYS_DEFAULT.
    Omitting it applies the conservative default."""
    if days > max_stay_days(destination):
        return None
    for name, (lo, hi) in DURATION_BUCKETS.items():
        if lo <= days <= hi:
            return name
    return None


def is_short_haul(duration_minutes: int) -> bool:
    """A flight is short-haul if its outbound leg is strictly under 3 hours."""
    return duration_minutes < SHORT_HAUL_MAX_MINUTES


def stops_allowed(duration_minutes: int, destination: str | None = None) -> int:
    """Maximum number of stops we accept for this haul type.

    Europe/short-haul: direct only (0 stops). Long-haul: up to 1 stop.

    2026-07-01 BUG FIX: the haul type was decided from duration_minutes,
    but Travelpayouts leaves that field at 0 on ~100% of multi-stop
    fares — so EVERY flight with a stop was classified short-haul and
    rejected (0 stops allowed), including CDG→Sydney -55%. We now decide
    haul type from the DESTINATION via is_long_haul (the reliable source
    used everywhere else). duration_minutes stays a fallback only when no
    destination is passed (keeps legacy callers working)."""
    if destination:
        from app.analysis.route_selector import is_long_haul
        return 1 if is_long_haul(destination) else 0
    return 0 if is_short_haul(duration_minutes) else 1
