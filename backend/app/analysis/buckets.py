"""Duration bucketing and short/long-haul classification.

Pure functions, no I/O. Used by the flight scraper, the baseline builder,
and the deal analyzer to apply consistent rules across the pipeline."""

DURATION_BUCKETS: dict[str, tuple[int, int]] = {
    "short":  (1, 3),
    "medium": (4, 7),
    "long":   (8, 12),
}

SHORT_HAUL_MAX_MINUTES = 180


def bucket_for_duration(days: int) -> str | None:
    """Return the bucket name for a trip duration, or None if out of range."""
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
