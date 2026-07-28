"""Tests for the beta activation funnel segmentation (pure logic)."""
from datetime import datetime, timezone

from app.analysis.beta_funnel import segment_users

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


def _u(uid: str) -> dict:
    return {"id": uid, "email": f"{uid}@test.fr", "created_at": "2026-05-01T00:00:00+00:00"}


def test_segments_are_mutually_exclusive_and_exhaustive():
    users = [_u("a"), _u("b"), _u("c"), _u("d"), _u("e")]
    segments = segment_users(
        users=users,
        linked_uids={"b", "c", "d", "e"},
        recipient_uids={"c", "d", "e"},
        last_engagement_by_uid={
            "d": "2026-05-01T10:00:00+00:00",  # > 14 days ago → dormant
            "e": "2026-06-09T10:00:00+00:00",  # yesterday → active
        },
        now=NOW,
    )
    assert [x["id"] for x in segments["not_connected"]] == ["a"]
    assert [x["id"] for x in segments["connected_no_alerts"]] == ["b"]
    assert [x["id"] for x in segments["received_never_engaged"]] == ["c"]
    assert [x["id"] for x in segments["dormant"]] == ["d"]
    assert [x["id"] for x in segments["active"]] == ["e"]
    total = sum(len(v) for v in segments.values())
    assert total == len(users)


def test_dormant_boundary_uses_dormant_days_param():
    users = [_u("u")]
    base = dict(
        users=users,
        linked_uids={"u"},
        recipient_uids={"u"},
        last_engagement_by_uid={"u": "2026-06-01T00:00:00+00:00"},  # 9.5 days ago
        now=NOW,
    )
    # 14-day window → still active
    assert segment_users(**base)["active"]
    # 7-day window → dormant
    assert segment_users(**base, dormant_days=7)["dormant"]


def test_dormant_entries_carry_last_engaged_at():
    segments = segment_users(
        users=[_u("u")],
        linked_uids={"u"},
        recipient_uids={"u"},
        last_engagement_by_uid={"u": "2026-04-01T00:00:00+00:00"},
        now=NOW,
    )
    assert segments["dormant"][0]["last_engaged_at"] == "2026-04-01T00:00:00+00:00"
