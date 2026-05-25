"""Tests for contributor scoring (OG badge + leaderboard).

The DB is faked with a tiny stub that mimics the PostgREST builder
chain used by count_real_contributions: select/not_.is_/range/execute.
"""
from datetime import datetime, timedelta, timezone

from app.analysis.contributors import (
    count_real_contributions,
    eligible_for_badge,
    build_leaderboard,
    BADGE_THRESHOLD,
    MIN_FEEDBACK_DELAY_S,
)


class _FakeQuery:
    """Mimics the PostgREST builder chain:
    select(...).not_.is_(...).range(...).execute()
    Every method returns self; `.not_` is an attribute (not a call)."""

    def __init__(self, rows):
        self._rows = rows
        self._range = (0, len(rows) - 1)

    def select(self, *_a, **_k):
        return self

    @property
    def not_(self):
        return self

    def is_(self, *_a, **_k):
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def execute(self):
        start, end = self._range
        page = self._rows[start : end + 1]
        return type("Resp", (), {"data": page})()


class _FakeDB:
    def __init__(self, rows):
        self._rows = rows

    def table(self, _name):
        return _FakeQuery(self._rows)


def _row(uid, mid, delay_s, sent=None):
    sent = sent or datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    clicked = sent + timedelta(seconds=delay_s)
    return {
        "user_id": uid,
        "message_id": mid,
        "sent_at": sent.isoformat(),
        "feedback_at": clicked.isoformat(),
        "feedback": "good",
    }


def test_counts_distinct_messages_with_sufficient_delay():
    rows = [
        _row("u1", "m1", 60),
        _row("u1", "m2", 30),
        _row("u2", "m3", 25),
    ]
    counts = count_real_contributions(_FakeDB(rows))
    assert counts == {"u1": 2, "u2": 1}


def test_reflex_click_below_delay_is_excluded():
    rows = [
        _row("u1", "m1", MIN_FEEDBACK_DELAY_S - 1),  # too fast → ignored
        _row("u1", "m2", MIN_FEEDBACK_DELAY_S),       # exactly threshold → kept
    ]
    counts = count_real_contributions(_FakeDB(rows))
    assert counts == {"u1": 1}


def test_grouped_alert_rows_count_once():
    # Same message_id, multiple offer rows → one contribution.
    rows = [_row("u1", "m1", 60), _row("u1", "m1", 60), _row("u1", "m1", 60)]
    counts = count_real_contributions(_FakeDB(rows))
    assert counts == {"u1": 1}


def test_missing_timestamps_are_skipped():
    bad = {
        "user_id": "u1",
        "message_id": "m1",
        "sent_at": None,
        "feedback_at": None,
        "feedback": "bad",
    }
    counts = count_real_contributions(_FakeDB([bad]))
    assert counts == {}


def test_eligible_for_badge_uses_threshold():
    counts = {"a": BADGE_THRESHOLD, "b": BADGE_THRESHOLD - 1, "c": BADGE_THRESHOLD + 5}
    assert set(eligible_for_badge(counts)) == {"a", "c"}


def test_empty_db_returns_empty():
    assert count_real_contributions(None) == {}
    assert count_real_contributions(_FakeDB([])) == {}


def test_leaderboard_ranks_named_users_with_medals():
    counts = {"u1": 42, "u2": 31, "u3": 28, "u4": 5}
    names = {"u1": "Marie", "u2": "Paul", "u3": "Lucie", "u4": "Léa"}
    board = build_leaderboard(counts, names, limit=10)
    assert [r["name"] for r in board] == ["Marie", "Paul", "Lucie", "Léa"]
    assert [r["medal"] for r in board[:3]] == ["🥇", "🥈", "🥉"]
    assert board[3]["medal"] == "4."
    assert board[0]["count"] == 42


def test_leaderboard_excludes_unnamed_users():
    # u2 has the most contributions but no display_name → not shown.
    counts = {"u1": 10, "u2": 99}
    names = {"u1": "Marie"}
    board = build_leaderboard(counts, names)
    assert [r["name"] for r in board] == ["Marie"]


def test_leaderboard_breaks_ties_by_name():
    counts = {"u1": 10, "u2": 10}
    names = {"u1": "Zoe", "u2": "Anna"}
    board = build_leaderboard(counts, names)
    assert [r["name"] for r in board] == ["Anna", "Zoe"]


def test_leaderboard_respects_limit():
    counts = {f"u{i}": 100 - i for i in range(20)}
    names = {f"u{i}": f"Name{i}" for i in range(20)}
    board = build_leaderboard(counts, names, limit=5)
    assert len(board) == 5
