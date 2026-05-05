"""Dispatch-time guards to prevent alert fatigue.

Two leviers, applied in order at the per-user × per-destination level
*after* the qualifier has already produced a candidate offer:

    Levier 1 — same-destination dedup over 7 days
        For each (user_id, destination) pair, suppress the new alert if
        we already pushed one in the last 7 days, UNLESS the new price
        is below 70% of the previously alerted price (= a real chute
        that's worth re-pinging the user about).

    Levier 2 — rolling 24h cap of 3 notifications per user
        At most 3 short-haul alerts are pushed per user in any 24h
        window. Long-haul destinations (`is_long_haul`) have their own
        smaller cap — `LONG_HAUL_DAILY_CAP=2` per 24h, no exception
        path — because real long-haul mistake fares are rare and the
        cap is itself a feature (the bypass that existed before could
        let a chatty week breach the user's notification budget).
        A 4th short-haul alert is also allowed when its discount is
        ≥10 points above the *best* discount already alerted in the
        rolling window — bounded by `EXCEPTIONAL_BYPASS_CEILING=1`.

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

# Short-haul cap (typical European deal alerts). 3 baseline + 1 exception.
DAILY_ALERT_CAP = 3
# Long-haul cap. No exception slot — long-haul deals are individually rare
# enough that 2 high-quality alerts in a day already cover almost every
# realistic mistake-fare scenario, and a hard cap is what the user
# actually wants from the notification stream.
LONG_HAUL_DAILY_CAP = 2
DAILY_CAP_WINDOW_HOURS = 24
# A 4th short-haul alert is allowed past the cap when its discount beats
# the BEST (highest) discount already alerted in the window by this many
# points. Comparing against the MAX (not the MIN) keeps the bar genuinely
# high: once a great alert has fired, every subsequent exception must
# beat it.
EXCEPTIONAL_DISCOUNT_GAP = 10.0
# Hard ceiling on exceptional bypasses per rolling 24h (short-haul only).
# Without this, even a "must beat the max" rule would let an arbitrarily
# long sequence of monotonically increasing discounts slip through. With
# ceiling=1, the worst case is DAILY_ALERT_CAP + 1 = 4 short-haul alerts
# per user per 24h. Long-haul has no exception path at all.
EXCEPTIONAL_BYPASS_CEILING = 1


def levier_2_daily_cap_blocks(
    *,
    db,
    user_id: str,
    destination: str,
    new_discount_pct: float,
    pending_in_run_alerts: list[dict] | None = None,
    now: datetime | None = None,
) -> bool:
    """Return True if levier 2 says this alert should NOT be pushed.

    Two separate caps apply, depending on the destination class:

    Short-haul (everything not in `LONG_HAUL_DESTINATIONS`):
        Cap = `DAILY_ALERT_CAP` (3) per rolling 24h. Past the cap, a
        single "exceptional" alert is allowed when its discount exceeds
        the BEST already-sent discount in the window by at least
        `EXCEPTIONAL_DISCOUNT_GAP` (10) points. Bounded by
        `EXCEPTIONAL_BYPASS_CEILING` (1). Worst case: 4 alerts / 24h.

    Long-haul (`is_long_haul(destination)` is True):
        Cap = `LONG_HAUL_DAILY_CAP` (2) per rolling 24h, no exception
        slot. Long-haul mistake fares are rare enough that 2 alerts per
        day saturates the user's appetite — the previous "always pass"
        bypass let chatty weeks (Christmas / June Asia promos) leak
        far above what the user actually wants.

    The two caps are independent: a user can receive 3 short-haul +
    2 long-haul alerts in the same 24h window. They are NOT pooled.

    Notification-only filter: counted alerts include only flight rows
    (no teasers, no system messages — see allowed_alert_types below).

    pending_in_run_alerts: list of `{"discount_pct": float,
    "destination": str}` dicts for alerts already dispatched to *this*
    user earlier in the current dispatch run. Required because
    sent_alerts is read at the top of the function and won't yet
    reflect rows we're about to upsert in the same loop. On 2026-05-04
    the guard let through 3 simultaneous alerts for the same user
    (MAD/FAO/BCN) because all three saw "0 in the last 24h" — the
    in-run counter closes that hole.

    Bug history
    -----------
    - 2026-05-05: the previous version compared the new discount
      against `min(countable_discounts) + EXCEPTIONAL_DISCOUNT_GAP`.
      Once one ≥40% alert had fired, the threshold stayed anchored to
      the lowest discount in the window (e.g. 30%), making "min+10 =
      40%" the permanent floor — every subsequent ≥40% alert slipped
      through with no upper bound. Switching to `max(...)` plus the
      hard ceiling closed that leak.
    - 2026-05-05: long-haul previously bypassed the cap entirely
      (`if is_long_haul(destination): return False`). Replaced by a
      dedicated `LONG_HAUL_DAILY_CAP` to honour the user-set "max 2
      long-haul / 24h" preference.
    """
    if not db:
        return False

    now = now or datetime.now(timezone.utc)
    cutoff = (now - timedelta(hours=DAILY_CAP_WINDOW_HOURS)).isoformat()

    # Only count actual deal alerts in the cap, not system / teaser ones.
    allowed_alert_types = ["flight", "one_way", "split_ticket"]

    try:
        resp = (
            db.table("sent_alerts")
            .select("discount_pct,destination")
            .eq("user_id", user_id)
            .in_("alert_type", allowed_alert_types)
            .gte("created_at", cutoff)
            .execute()
        )
    except Exception:
        return False  # fail open

    sent = resp.data or []
    # Bin existing rows by destination class. Rows missing discount_pct
    # are pre-migration 037 — they fail open (don't count), so the guard
    # becomes progressively effective as fresh rows land.
    short_haul_discounts: list[float] = []
    long_haul_discounts: list[float] = []
    for r in sent:
        if r.get("discount_pct") is None:
            continue
        d = float(r["discount_pct"])
        dest = r.get("destination") or ""
        if is_long_haul(dest):
            long_haul_discounts.append(d)
        else:
            short_haul_discounts.append(d)

    # Add the in-run pending alerts (dispatched to this user earlier in
    # the current loop). They count against the cap exactly like
    # persisted rows.
    if pending_in_run_alerts:
        for entry in pending_in_run_alerts:
            d = entry.get("discount_pct")
            if d is None:
                continue
            dest = entry.get("destination") or ""
            if is_long_haul(dest):
                long_haul_discounts.append(float(d))
            else:
                short_haul_discounts.append(float(d))

    new_is_long_haul = is_long_haul(destination)

    if new_is_long_haul:
        # Long-haul: pure hard cap, no exception path.
        if len(long_haul_discounts) < LONG_HAUL_DAILY_CAP:
            return False  # under long-haul cap → allow
        return True  # at or past long-haul cap → block

    # Short-haul lane (existing behaviour).
    if len(short_haul_discounts) < DAILY_ALERT_CAP:
        return False  # under cap → allow

    # At or past cap. Hard ceiling first: deterministic worst-case
    # regardless of how discounts are distributed.
    if len(short_haul_discounts) >= DAILY_ALERT_CAP + EXCEPTIONAL_BYPASS_CEILING:
        return True

    # Exceptional-deal exception: the new discount must beat the BEST
    # already-sent short-haul discount by EXCEPTIONAL_DISCOUNT_GAP
    # points. Comparing against the MAX (not the MIN) keeps the bar
    # high — once one outstanding deal lands, only a strictly better
    # one can interrupt the user past the cap.
    max_sent = max(short_haul_discounts)
    if new_discount_pct >= max_sent + EXCEPTIONAL_DISCOUNT_GAP:
        return False  # exceptional improvement over the best → allow
    return True  # cap reached, not exceptional → block
