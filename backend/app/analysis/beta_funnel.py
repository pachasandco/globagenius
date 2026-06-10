"""Beta activation funnel (2026-06-10).

Segments every signed-up user into the activation stage where they
currently sit, so re-engagement is targeted instead of blanket. Born
from a real failure: 60 signups, ~7 active, and generic relance
campaigns landing "en vain" because the silent majority is stuck at
DIFFERENT stages that each need a different message.

Stages (mutually exclusive, in funnel order):

    not_connected        signed up, never linked Telegram
                         → relance: "finish the setup"
    connected_no_alerts  linked, never received a single alert
                         → relance: "your preferences filter everything out"
    received_never_engaged
                         gets alerts, never clicked a link nor tapped
                         a feedback button → relance: value proposition
    dormant              engaged at least once, but nothing for
                         `dormant_days` → relance: impact loop
                         ("your feedback changed X") / lettre de la beta
    active               clicked or gave feedback within `dormant_days`

The segmentation itself is a pure function (segment_users) so it's
unit-testable; build_funnel_report does the DB I/O.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

DEFAULT_DORMANT_DAYS = 14


def segment_users(
    *,
    users: list[dict],
    linked_uids: set[str],
    recipient_uids: set[str],
    last_engagement_by_uid: dict[str, str],
    now: datetime,
    dormant_days: int = DEFAULT_DORMANT_DAYS,
) -> dict[str, list[dict]]:
    """Pure segmentation. `users` rows need id + email;
    `last_engagement_by_uid` maps user_id → most recent ISO timestamp of
    a click OR a feedback tap (absent = never engaged)."""
    cutoff = (now - timedelta(days=dormant_days)).isoformat()
    segments: dict[str, list[dict]] = {
        "not_connected": [],
        "connected_no_alerts": [],
        "received_never_engaged": [],
        "dormant": [],
        "active": [],
    }
    for u in users:
        uid = u.get("id")
        entry = {"id": uid, "email": u.get("email"), "created_at": u.get("created_at")}
        if uid not in linked_uids:
            segments["not_connected"].append(entry)
        elif uid not in recipient_uids:
            segments["connected_no_alerts"].append(entry)
        elif uid not in last_engagement_by_uid:
            segments["received_never_engaged"].append(entry)
        elif last_engagement_by_uid[uid] < cutoff:
            segments["dormant"].append({**entry, "last_engaged_at": last_engagement_by_uid[uid]})
        else:
            segments["active"].append({**entry, "last_engaged_at": last_engagement_by_uid[uid]})
    return segments


def _paginate(query_builder, page_size: int = 1000, max_pages: int = 60) -> list[dict]:
    """Drain a PostgREST query past the 1000-row default cap."""
    rows: list[dict] = []
    offset = 0
    for _ in range(max_pages):
        page = query_builder.range(offset, offset + page_size - 1).execute().data or []
        rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return rows


def build_funnel_report(db, dormant_days: int = DEFAULT_DORMANT_DAYS) -> dict:
    """Assemble the funnel from DB and return counts + per-segment emails."""
    now = datetime.now(timezone.utc)

    users = _paginate(
        db.table("users").select("id,email,created_at").order("created_at")
    )

    prefs = _paginate(
        db.table("user_preferences").select("user_id,telegram_chat_id")
    )
    linked_uids = {p["user_id"] for p in prefs if p.get("telegram_chat_id")}

    alerts = _paginate(
        db.table("sent_alerts").select("user_id,feedback,created_at").order("created_at")
    )
    recipient_uids = {a["user_id"] for a in alerts if a.get("user_id")}

    # Engagement = a tracked click (alert_redirect_tokens.clicked_at)
    # OR a feedback tap (sent_alerts.feedback). Keep the most recent.
    last_engagement: dict[str, str] = {}
    for a in alerts:
        uid = a.get("user_id")
        if uid and a.get("feedback") and a.get("created_at"):
            ts = a["created_at"]
            if ts > last_engagement.get(uid, ""):
                last_engagement[uid] = ts
    clicks = _paginate(
        db.table("alert_redirect_tokens")
        .select("user_id,clicked_at")
        .gt("click_count", 0)
        .order("clicked_at", desc=True)
    )
    for c in clicks:
        uid = c.get("user_id")
        if uid and c.get("clicked_at"):
            ts = c["clicked_at"]
            if ts > last_engagement.get(uid, ""):
                last_engagement[uid] = ts

    segments = segment_users(
        users=users,
        linked_uids=linked_uids,
        recipient_uids=recipient_uids,
        last_engagement_by_uid=last_engagement,
        now=now,
        dormant_days=dormant_days,
    )
    return {
        "generated_at": now.isoformat(),
        "dormant_days": dormant_days,
        "total_users": len(users),
        "counts": {k: len(v) for k, v in segments.items()},
        "segments": segments,
    }
