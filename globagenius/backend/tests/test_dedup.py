"""Tests for compute_alert_key dedup helper."""
from app.notifications.dedup import compute_alert_key


def test_compute_alert_key_deterministic():
    k1 = compute_alert_key("user-1", "CDG", "LIS", "2026-09-01", "2026-09-10", 89.0)
    k2 = compute_alert_key("user-1", "CDG", "LIS", "2026-09-01", "2026-09-10", 89.0)
    assert k1 == k2
    assert len(k1) == 32
    assert isinstance(k1, str)


def test_compute_alert_key_different_prices():
    k1 = compute_alert_key("user-1", "CDG", "LIS", "2026-09-01", "2026-09-10", 89.0)
    k2 = compute_alert_key("user-1", "CDG", "LIS", "2026-09-01", "2026-09-10", 90.0)
    assert k1 != k2


def test_compute_alert_key_price_rounding():
    # Prices within 0.5 of the same integer should round to same key
    k1 = compute_alert_key("user-1", "CDG", "LIS", "2026-09-01", "2026-09-10", 89.3)
    k2 = compute_alert_key("user-1", "CDG", "LIS", "2026-09-01", "2026-09-10", 89.4)
    assert k1 == k2


def test_compute_alert_key_different_users():
    k1 = compute_alert_key("user-1", "CDG", "LIS", "2026-09-01", "2026-09-10", 89.0)
    k2 = compute_alert_key("user-2", "CDG", "LIS", "2026-09-01", "2026-09-10", 89.0)
    assert k1 != k2
