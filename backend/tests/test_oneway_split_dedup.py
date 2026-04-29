"""V5+ P1: tests for the V5+ dedup keys (one-way + split-ticket).

Both share the existing 50€ price-bucket logic of compute_alert_key but
have their own namespace so an A/R and a combo on the same dates don't
collide.
"""
from app.notifications.dedup import (
    compute_alert_key,
    compute_oneway_alert_key,
    compute_split_ticket_alert_key,
)


# ─── compute_oneway_alert_key ───

def test_oneway_key_is_deterministic():
    k1 = compute_oneway_alert_key(
        "user-1", "CDG", "JFK", "outbound", "2026-06-15", 220.0
    )
    k2 = compute_oneway_alert_key(
        "user-1", "CDG", "JFK", "outbound", "2026-06-15", 220.0
    )
    assert k1 == k2
    assert len(k1) == 32


def test_oneway_key_distinct_per_direction():
    k_out = compute_oneway_alert_key(
        "user-1", "CDG", "JFK", "outbound", "2026-06-15", 220.0
    )
    k_in = compute_oneway_alert_key(
        "user-1", "CDG", "JFK", "inbound", "2026-06-15", 220.0
    )
    # Direction is part of the key — outbound CDG→JFK ≠ inbound CDG→JFK.
    assert k_out != k_in


def test_oneway_key_distinct_from_round_trip_key():
    k_ow = compute_oneway_alert_key(
        "user-1", "CDG", "JFK", "outbound", "2026-06-15", 220.0
    )
    k_rt = compute_alert_key(
        "user-1", "CDG", "JFK", "2026-06-15", "2026-06-22", 220.0
    )
    # Even with same user, dest, dep_date, price → namespaces must differ.
    assert k_ow != k_rt


def test_oneway_key_buckets_price_in_50eur_steps():
    k1 = compute_oneway_alert_key(
        "user-1", "CDG", "JFK", "outbound", "2026-06-15", 220.0
    )
    k2 = compute_oneway_alert_key(
        "user-1", "CDG", "JFK", "outbound", "2026-06-15", 240.0
    )
    # Both fall in bucket 200 → same key.
    assert k1 == k2

    k3 = compute_oneway_alert_key(
        "user-1", "CDG", "JFK", "outbound", "2026-06-15", 199.0
    )
    # Bucket 150 ≠ 200 → new alert.
    assert k1 != k3


def test_oneway_key_distinct_per_user():
    k1 = compute_oneway_alert_key(
        "user-1", "CDG", "JFK", "outbound", "2026-06-15", 220.0
    )
    k2 = compute_oneway_alert_key(
        "user-2", "CDG", "JFK", "outbound", "2026-06-15", 220.0
    )
    assert k1 != k2


# ─── compute_split_ticket_alert_key ───

def test_split_key_is_deterministic():
    k1 = compute_split_ticket_alert_key(
        "user-1", "CDG", "BKK", "2026-04-04", "2026-04-22", 540.0
    )
    k2 = compute_split_ticket_alert_key(
        "user-1", "CDG", "BKK", "2026-04-04", "2026-04-22", 540.0
    )
    assert k1 == k2


def test_split_key_distinct_from_round_trip_key():
    k_st = compute_split_ticket_alert_key(
        "user-1", "CDG", "BKK", "2026-04-04", "2026-04-22", 540.0
    )
    k_rt = compute_alert_key(
        "user-1", "CDG", "BKK", "2026-04-04", "2026-04-22", 540.0
    )
    # Combos and A/Rs on same dates must NEVER collide — the user might
    # receive both flavours and we want both to track independently.
    assert k_st != k_rt


def test_split_key_buckets_total_price():
    k1 = compute_split_ticket_alert_key(
        "user-1", "CDG", "BKK", "2026-04-04", "2026-04-22", 540.0
    )
    k2 = compute_split_ticket_alert_key(
        "user-1", "CDG", "BKK", "2026-04-04", "2026-04-22", 549.0
    )
    # Both in bucket 500 → same key.
    assert k1 == k2

    k3 = compute_split_ticket_alert_key(
        "user-1", "CDG", "BKK", "2026-04-04", "2026-04-22", 499.0
    )
    # Bucket 450 → new alert.
    assert k1 != k3


def test_split_key_distinct_per_dates():
    k1 = compute_split_ticket_alert_key(
        "user-1", "CDG", "BKK", "2026-04-04", "2026-04-22", 540.0
    )
    k2 = compute_split_ticket_alert_key(
        "user-1", "CDG", "BKK", "2026-04-05", "2026-04-22", 540.0
    )
    assert k1 != k2
