"""Contributor scoring — "real" feedback contributions for the OG badge
and the weekly leaderboard.

A *real* contribution is one distinct alert (message_id) that the user
gave feedback on, where the click landed at least MIN_FEEDBACK_DELAY_S
seconds after the alert was sent. The delay filters out the click-reflex
("tap 👍 without reading") that would otherwise inflate the stats — the
whole point of the badge is to reward people who actually read the deal.

Grouped alerts produce N sent_alerts rows per Telegram message that all
share the same feedback (see bot_handler._record_feedback), so we count
distinct message_id, not rows.

Both the badge cron and the leaderboard cron consume count_real_contributions()
so the badge threshold and the ranking always use the same definition.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# A click sooner than this after the alert was sent is treated as a reflex
# tap, not a considered judgement, and doesn't count toward the badge.
MIN_FEEDBACK_DELAY_S = 20

# Distinct real contributions required to earn the founder ("OG") badge.
BADGE_THRESHOLD = 10

# Supabase/PostgREST caps a single select; paginate to scan the whole
# feedback history without a row limit silently truncating the count.
_PAGE = 1000


def _parse_ts(value) -> datetime | None:
    """Parse a timestamptz string from PostgREST into an aware datetime.

    Returns None on anything unparseable so a single bad row can't crash
    the whole scan."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        s = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def count_real_contributions(db) -> dict[str, int]:
    """Scan sent_alerts and return {user_id: count} of real contributions.

    Real = distinct message_id with non-null feedback where
    feedback_at - sent_at >= MIN_FEEDBACK_DELAY_S. Users with zero real
    contributions are omitted from the result.
    """
    if not db:
        return {}

    # (user_id, message_id) pairs already counted, so a grouped alert's
    # N rows count once.
    seen: set[tuple[str, str]] = set()
    counts: dict[str, int] = {}

    offset = 0
    while True:
        rows = (
            db.table("sent_alerts")
            .select("user_id,message_id,sent_at,feedback_at,feedback")
            .not_.is_("feedback", "null")
            .range(offset, offset + _PAGE - 1)
            .execute()
            .data
            or []
        )
        if not rows:
            break

        for r in rows:
            uid = r.get("user_id")
            mid = r.get("message_id")
            if not uid or not mid:
                continue
            key = (uid, mid)
            if key in seen:
                continue
            sent = _parse_ts(r.get("sent_at"))
            clicked = _parse_ts(r.get("feedback_at"))
            if not sent or not clicked:
                continue
            if (clicked - sent).total_seconds() < MIN_FEEDBACK_DELAY_S:
                continue
            seen.add(key)
            counts[uid] = counts.get(uid, 0) + 1

        if len(rows) < _PAGE:
            break
        offset += _PAGE

    return counts


def eligible_for_badge(counts: dict[str, int]) -> list[str]:
    """User ids that have reached the badge threshold."""
    return [uid for uid, n in counts.items() if n >= BADGE_THRESHOLD]


_MEDALS = ["🥇", "🥈", "🥉"]


def build_leaderboard(
    counts: dict[str, int],
    names_by_uid: dict[str, str],
    *,
    limit: int = 10,
) -> list[dict]:
    """Build a ranked leaderboard for the weekly email.

    Only users with a known display_name appear (names_by_uid) — we never
    expose an email or an un-named user in a mail sent to all founders.
    Ties are broken by name for a stable order.

    Returns a list of {rank, name, count, medal} dicts, top `limit`.
    """
    named = [
        (uid, n)
        for uid, n in counts.items()
        if names_by_uid.get(uid) and n > 0
    ]
    named.sort(key=lambda kv: (-kv[1], names_by_uid[kv[0]].lower()))

    board: list[dict] = []
    for i, (uid, n) in enumerate(named[:limit]):
        board.append({
            "rank": i + 1,
            "name": names_by_uid[uid],
            "count": n,
            "medal": _MEDALS[i] if i < len(_MEDALS) else f"{i + 1}.",
        })
    return board
