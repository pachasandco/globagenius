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
