"""Tests for compute_alert_key dedup helper."""
from app.notifications.dedup import compute_alert_key


def test_compute_alert_key_deterministic():
    k1 = compute_alert_key("user-1", "CDG", "LIS", "2026-09-01", "2026-09-10", 89.0)
    k2 = compute_alert_key("user-1", "CDG", "LIS", "2026-09-01", "2026-09-10", 89.0)
    assert k1 == k2
    assert len(k1) == 32
    assert isinstance(k1, str)


def test_compute_alert_key_different_prices():
    """Keys differ only when the price crosses a 50€ bucket boundary —
    89€ vs 90€ share the [50,100) bucket (same key, no re-alert spam),
    89€ vs 49€ don't (genuine drop → new key → re-alert)."""
    k_89 = compute_alert_key("user-1", "CDG", "LIS", "2026-09-01", "2026-09-10", 89.0)
    k_90 = compute_alert_key("user-1", "CDG", "LIS", "2026-09-01", "2026-09-10", 90.0)
    assert k_89 == k_90
    k_49 = compute_alert_key("user-1", "CDG", "LIS", "2026-09-01", "2026-09-10", 49.0)
    assert k_49 != k_89


def test_compute_alert_key_price_rounding():
    # Prices within 0.5 of the same integer should round to same key
    k1 = compute_alert_key("user-1", "CDG", "LIS", "2026-09-01", "2026-09-10", 89.3)
    k2 = compute_alert_key("user-1", "CDG", "LIS", "2026-09-01", "2026-09-10", 89.4)
    assert k1 == k2


def test_compute_alert_key_different_users():
    k1 = compute_alert_key("user-1", "CDG", "LIS", "2026-09-01", "2026-09-10", 89.0)
    k2 = compute_alert_key("user-2", "CDG", "LIS", "2026-09-01", "2026-09-10", 89.0)
    assert k1 != k2
