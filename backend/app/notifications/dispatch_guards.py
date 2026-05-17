"""Dispatch-time guards to prevent alert fatigue.

Two leviers, applied in order at the per-user × per-destination level
*after* the qualifier has already produced a candidate offer:

    Levier 1 — same-destination dedup over 7 days
        For each (user_id, destination) pair, suppress the new alert if
        we already pushed one in the last 7 days, UNLESS the new price
        is below 70% of the previously alerted price (= a real chute
        that's worth re-pinging the user about).

    Levier 2 — rolling 24h cap of 5 total notifications per user
        At most 3 short-haul + 2 long-haul alerts per user in any 24h
        window, POOLED into a strict total of 5. Long-haul over-spend
        eats into the short-haul budget and vice versa. No exception
        path — the previous "+1 if exceptional discount" bypass made
        the real worst case 6/day, breaking the "3+2" promise users
        rely on. With reverification at ~95%, every alert that lands
        is already high-quality; an extra bypass slot adds noise more
        than signal.

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

# Pooled 5/24h cap, broken down as 3 short-haul + 2 long-haul.
# Each lane has its own ceiling, but the TOTAL across both is also
# capped — so 2 long-haul + 3 short = 5 (allowed), but 2 long + 4 short
# = 6 (blocked) even if the short lane individually had room.
DAILY_ALERT_CAP = 3            # short-haul ceiling
LONG_HAUL_DAILY_CAP = 2        # long-haul ceiling
TOTAL_DAILY_CAP = DAILY_ALERT_CAP + LONG_HAUL_DAILY_CAP  # 5
DAILY_CAP_WINDOW_HOURS = 24
# Granularity (minutes) for collapsing sent_alerts rows that belong to the
# same Telegram message. The dispatcher writes ONE row per offer-key for
# the 168h dedup, but a grouped alert containing N offers is still ONE
# notification event. Counting rows would let a single 3-offer message
# saturate the cap by itself, which is exactly the "radio silence" bug
# we observed on 2026-05-05. 5 min is wide enough to absorb a slow
# dispatch run, narrow enough that two genuinely distinct messages
# don't collapse.
MESSAGE_BUCKET_MINUTES = 5


def _message_bucket_key(row: dict, minutes: int = MESSAGE_BUCKET_MINUTES) -> tuple[str, str] | None:
    """Group sent_alerts rows that belong to the same Telegram message.

    A grouped flight alert flushes N offers per (user, destination)
    bucket and writes N sent_alerts rows — one per offer's alert_key
    so the 168h dedup query can find each future re-emission. From
    L2's perspective those N rows represent ONE notification event.
    Two rows share a "message" when they share `destination` and fall
    in the same `minutes`-wide window of `created_at`.

    Returns None when the row lacks `created_at` or `destination`. The
    caller treats those rows as their own bucket (legacy fail-open
    contract: never silently swallow rows we can't classify).
    """
    dest = row.get("destination") or ""
    created = row.get("created_at")
    if not created or not dest:
        return None
    try:
        dt = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    bucketed = dt.replace(
        minute=(dt.minute // minutes) * minutes,
        second=0,
        microsecond=0,
    )
    return (dest, bucketed.isoformat())


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

    Pooled 5/24h cap, broken down as 3 short-haul + 2 long-haul:

      1. Short-haul lane ceiling   = DAILY_ALERT_CAP (3)
      2. Long-haul lane ceiling    = LONG_HAUL_DAILY_CAP (2)
      3. Total across both lanes   = TOTAL_DAILY_CAP (5)

    All three must be under their respective ceiling for the new alert
    to pass. Worst case: 5 notifications per user per 24h. There is no
    exceptional-discount bypass — with reverification at ~95%, every
    alert that lands is already a vetted deal, and the previous "+1"
    slot pushed the real ceiling to 6 while breaking the "3+2" promise.

    Notification-only filter: counted alerts include only flight rows
    (no teasers, no system messages — see allowed_alert_types below).

    Multi-row dedup: a grouped alert containing N offers writes N rows
    to `sent_alerts` (one per offer key). Without dedup, a single
    3-offer message saturates DAILY_ALERT_CAP by itself, producing
    radio silence for 24h. We collapse rows sharing
    `(destination, created_at-rounded-to-MESSAGE_BUCKET_MINUTES)`
    before binning, so every grouped alert counts as exactly one
    notification event.

    pending_in_run_alerts: list of `{"discount_pct": float,
    "destination": str}` dicts for alerts already dispatched to *this*
    user earlier in the current dispatch run. Each successful
    Telegram send appends ONE entry, so this list is already
    one-per-message — no dedup needed on this side.

    Bug history
    -----------
    - 2026-05-05 (cap leak): the previous version compared the new
      discount against `min(countable_discounts) + EXCEPTIONAL_GAP`.
      Once one ≥40% alert had fired, the threshold stayed anchored to
      the lowest discount in the window, letting subsequent ≥40%
      alerts slip through with no upper bound.
    - 2026-05-05 (long-haul bypass): long-haul previously bypassed
      the cap entirely. Replaced by `LONG_HAUL_DAILY_CAP`.
    - 2026-05-05 (multi-row inflation): each grouped alert wrote N
      rows for N offers, and L2 counted rows. A single 3-offer
      message could saturate the cap. Fixed by collapsing rows on
      `(destination, MESSAGE_BUCKET_MINUTES bucket)` before binning.
    - 2026-05-16 (lane independence + bypass): the short and long caps
      were independent and a 4th short alert could slip through past
      the cap on an "exceptional discount" rule. Worst case was 6/day,
      not 5. Replaced by a pooled TOTAL_DAILY_CAP=5 with no exception
      slot — the cap now matches the "3+2" the product promises.
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
            .select("discount_pct,destination,created_at,message_id")
            .eq("user_id", user_id)
            .in_("alert_type", allowed_alert_types)
            .gte("created_at", cutoff)
            .execute()
        )
    except Exception:
        return False  # fail open

    sent = resp.data or []

    # Collapse rows belonging to the same Telegram message into one
    # entry. A grouped alert with 3 offers writes 3 rows, but L2
    # counts notification events, not rows. Rows missing created_at
    # or destination keep their own bucket (fail-open).
    # Two dedup mechanisms, applied in order:
    # 1. `message_id` (chantier 1, 2026-05-17): authoritative — rows
    #    sharing a UUID belong to one Telegram message regardless of
    #    timing.
    # 2. `(destination, 5-min bucket)` fallback: kept for pre-migration
    #    rows where message_id is NULL. Removed once the backfill +
    #    CHECK constraint guarantee no NULL rows remain.
    seen_message_ids: set[str] = set()
    seen_buckets: set[tuple[str, str]] = set()
    unique_messages: list[dict] = []
    for r in sent:
        if r.get("discount_pct") is None:
            continue
        mid = r.get("message_id")
        if mid is not None:
            if mid in seen_message_ids:
                continue
            seen_message_ids.add(mid)
            unique_messages.append(r)
            continue
        bucket = _message_bucket_key(r)
        if bucket is None:
            unique_messages.append(r)
            continue
        if bucket in seen_buckets:
            continue
        seen_buckets.add(bucket)
        unique_messages.append(r)

    # Bin existing rows by destination class.
    short_haul_discounts: list[float] = []
    long_haul_discounts: list[float] = []
    for r in unique_messages:
        d = float(r["discount_pct"])
        dest = r.get("destination") or ""
        if is_long_haul(dest):
            long_haul_discounts.append(d)
        else:
            short_haul_discounts.append(d)

    # Add the in-run pending alerts (dispatched to this user earlier in
    # the current loop). Already one-per-message — each successful send
    # appends exactly one entry.
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
    short_count = len(short_haul_discounts)
    long_count = len(long_haul_discounts)
    total_count = short_count + long_count

    # Hit the total pool first — the strictest of the three checks
    # whenever both lanes have already contributed.
    if total_count >= TOTAL_DAILY_CAP:
        return True

    if new_is_long_haul:
        if long_count >= LONG_HAUL_DAILY_CAP:
            return True
        return False

    if short_count >= DAILY_ALERT_CAP:
        return True
    return False
