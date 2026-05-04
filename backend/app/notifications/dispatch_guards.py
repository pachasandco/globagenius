"""Dispatch-time guards to prevent alert fatigue.

Two leviers, applied in order at the per-user × per-destination level
*after* the qualifier has already produced a candidate offer:

    Levier 1 — same-destination dedup over 7 days
        For each (user_id, destination) pair, suppress the new alert if
        we already pushed one in the last 7 days, UNLESS the new price
        is below 70% of the previously alerted price (= a real chute
        that's worth re-pinging the user about).

    Levier 2 — rolling 24h cap of 3 notifications per user
        At most 3 alerts are pushed per user in any 24h window.
        Long-haul destinations (`is_long_haul`) bypass the cap entirely.
        A 4th alert is also allowed when its discount is ≥10 points
        above the *minimum* discount of the alerts already sent in the
        rolling window — those are exceptional deals worth interrupting
        for, even past the cap.

Deals filtered out by either levier are NOT discarded — they remain in
qualified_items and surface on /home so the user can browse them on
demand. Only the Telegram push is suppressed.

Both guards fail open on legacy rows that lack price/discount_pct
(pre-migration 037). Rationale: those columns were added the same day
as the guards, and at deploy time every existing sent_alerts row was
NULL on both. Failing closed would silently block all alerts for any
active user with recent history — exactly the regression we observed
on the first run after deploy. Failing open means the guards become
progressively effective as new (populated) rows accumulate, with full
coverage after 24h (Levier 2) and 7 days (Levier 1).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.analysis.route_selector import is_long_haul

# ── Levier 1 ────────────────────────────────────────────────────────────────

DESTINATION_COOLDOWN_DAYS = 7
SIGNIFICANT_DROP_RATIO = 0.70  # new price < 70% of previous alert → override


def levier_1_destination_cooldown_blocks(
    *,
    db,
    user_id: str,
    destination: str,
    new_price: float,
    now: datetime | None = None,
) -> bool:
    """Return True if levier 1 says this destination should NOT be pushed.

    Returns False (= push allowed) when:
      - no alert was sent for (user, destination) in the cooldown window
      - or the new price is < 70% of the most recent alerted price
        (significant drop override)

    Returns True (= block) when an alert was sent recently and the new
    price isn't a meaningful improvement.
    """
    if not db:
        return False  # fail open — never block on missing DB
    now = now or datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=DESTINATION_COOLDOWN_DAYS)).isoformat()

    try:
        resp = (
            db.table("sent_alerts")
            .select("price,created_at")
            .eq("user_id", user_id)
            .eq("destination", destination)
            .gte("created_at", cutoff)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception:
        # On DB error, fail open: better a duplicate alert than silence.
        return False

    rows = resp.data or []
    if not rows:
        return False  # nothing in window → push allowed

    previous_price = rows[0].get("price")
    if previous_price is None:
        # Legacy row from before migration 037 — no prior price to compare
        # against. Fail open: the guard simply doesn't apply to that row.
        # Worst case the user gets one duplicate alert; once new rows land
        # with price populated, the guard becomes effective naturally.
        return False

    if new_price < float(previous_price) * SIGNIFICANT_DROP_RATIO:
        return False  # significant drop → push allowed
    return True  # already alerted, no significant drop → block


# ── Levier 2 ────────────────────────────────────────────────────────────────

DAILY_ALERT_CAP = 3
DAILY_CAP_WINDOW_HOURS = 24
EXCEPTIONAL_DISCOUNT_GAP = 10.0  # +10 points above current min in window


def levier_2_daily_cap_blocks(
    *,
    db,
    user_id: str,
    destination: str,
    new_discount_pct: float,
    pending_in_run_discounts: list[float] | None = None,
    now: datetime | None = None,
) -> bool:
    """Return True if levier 2 says this alert should NOT be pushed.

    The cap is 3 alerts per rolling 24h. Two bypasses:
      - long-haul destinations always pass (rare, high-value deals)
      - a 4th+ alert is also allowed when its discount is ≥10 points
        above the *minimum* discount of the alerts already counted in
        the window (exceptional deal that interrupts even past the cap)

    Notification-only filter: counted alerts include only flight rows
    (no teasers, no system messages — see allowed_alert_types below).

    pending_in_run_discounts: discount_pct values for alerts already
    dispatched to *this user* earlier in the current dispatch run.
    Required because sent_alerts is read at the top of the function and
    won't yet reflect rows we're about to upsert in the same loop. On
    2026-05-04 the guard let through 3 simultaneous alerts for the same
    user (MAD/FAO/BCN) because all three saw "0 in the last 24h" — the
    in-run counter closes that hole.
    """
    if not db:
        return False
    if is_long_haul(destination):
        return False  # bypass cap for long-haul destinations

    now = now or datetime.now(timezone.utc)
    cutoff = (now - timedelta(hours=DAILY_CAP_WINDOW_HOURS)).isoformat()

    # Only count actual deal alerts in the cap, not system / teaser ones.
    allowed_alert_types = ["flight", "one_way", "split_ticket"]

    try:
        resp = (
            db.table("sent_alerts")
            .select("discount_pct")
            .eq("user_id", user_id)
            .in_("alert_type", allowed_alert_types)
            .gte("created_at", cutoff)
            .execute()
        )
    except Exception:
        return False  # fail open

    sent = resp.data or []
    # Only count rows we can actually compare against (have discount_pct).
    # Legacy rows pre-migration 037 are ignored: the guard simply doesn't
    # see them, which means it's progressively effective as new rows land.
    countable_discounts = [
        float(r["discount_pct"]) for r in sent
        if r.get("discount_pct") is not None
    ]
    # Add the in-run pending discounts (alerts dispatched to this user
    # earlier in the current loop). They count against the cap exactly
    # like persisted rows.
    if pending_in_run_discounts:
        countable_discounts.extend(float(d) for d in pending_in_run_discounts)

    if len(countable_discounts) < DAILY_ALERT_CAP:
        return False  # under cap (counting only comparable rows) → allow

    # At cap or over. Check the exceptional-deal exception:
    # is the new discount ≥10 points above the worst already sent?
    min_sent = min(countable_discounts)
    if new_discount_pct >= min_sent + EXCEPTIONAL_DISCOUNT_GAP:
        return False  # exceptional improvement → allow
    return True  # cap reached, not exceptional → block
