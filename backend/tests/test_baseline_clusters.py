"""Tests for the cluster-based baseline maturity logic.

We test the units in isolation (parser, classifier, aggregator).
The full report builder hits the DB and is exercised separately
via a thin integration test."""
from app.analysis.baseline_clusters import parse_route_key


def test_parse_simple_route_key():
    """Format: 'CDG-LIS-1m' → ('CDG', 'LIS')"""
    assert parse_route_key("CDG-LIS-1m") == ("CDG", "LIS")


def test_parse_route_key_with_bucket():
    """Format: 'CDG-HKT-bucket_long' → ('CDG', 'HKT')"""
    assert parse_route_key("CDG-HKT-bucket_long") == ("CDG", "HKT")


def test_parse_route_key_with_wildcard_origin():
    """Format: '*-HKT-bucket_medium' → (None, 'HKT')

    The wildcard means 'all origins toward HKT' — the rate-per-day
    will be summed across known origins by the caller.
    """
    assert parse_route_key("*-HKT-bucket_medium") == (None, "HKT")


def test_parse_route_key_with_extra_suffixes():
    """Format: 'CDG-HKT-bucket_long-m09-lt90p' → ('CDG', 'HKT')

    Extra hyphenated suffixes (month, lead-time) don't break parsing
    because the regex only consumes the first two IATA-shaped tokens.
    """
    assert parse_route_key("CDG-HKT-bucket_long-m09-lt90p") == ("CDG", "HKT")


def test_parse_malformed_route_key_returns_none_pair():
    """Anything that doesn't start with two IATA-shaped tokens
    → (None, None). Caller logs WARNING and classifies the
    baseline as 'unknown'."""
    assert parse_route_key("MALFORMED") == (None, None)
    assert parse_route_key("CDG-LIS") == (None, None)  # no third segment
    assert parse_route_key("cdg-lis-1m") == (None, None)  # lowercase rejected


from app.analysis.baseline_clusters import cluster_baseline


def test_cluster_hot_when_samples_at_or_above_30():
    assert cluster_baseline(samples=30, rate_per_day=0.0) == "hot"
    assert cluster_baseline(samples=150, rate_per_day=10.0) == "hot"


def test_cluster_warm_when_samples_between_10_and_29():
    assert cluster_baseline(samples=10, rate_per_day=0.0) == "warm"
    assert cluster_baseline(samples=29, rate_per_day=0.0) == "warm"


def test_cluster_cold_when_samples_below_10_and_rate_above_0_1():
    assert cluster_baseline(samples=5, rate_per_day=0.5) == "cold"
    assert cluster_baseline(samples=0, rate_per_day=5.0) == "cold"


def test_cluster_dormant_when_samples_below_10_and_rate_at_or_below_0_1():
    assert cluster_baseline(samples=5, rate_per_day=0.05) == "dormant"
    assert cluster_baseline(samples=5, rate_per_day=0.0) == "dormant"


def test_cluster_boundary_rate_exactly_0_1_is_dormant():
    """rate_per_day == 0.1 exact → dormant (strict > 0.1 → cold).

    This locks the boundary so a future refactor that changes >
    to >= doesn't silently widen the cold population."""
    assert cluster_baseline(samples=5, rate_per_day=0.1) == "dormant"
    assert cluster_baseline(samples=5, rate_per_day=0.10001) == "cold"
