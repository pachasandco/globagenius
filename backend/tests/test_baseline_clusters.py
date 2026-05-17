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


from app.analysis.baseline_clusters import compute_rate_per_day


def test_rate_per_day_concrete_origin():
    """For (CDG, LIS), divide samples by 7."""
    samples_by_route = {("CDG", "LIS"): 70, ("CDG", "BCN"): 14}
    rate = compute_rate_per_day(
        origin="CDG",
        destination="LIS",
        samples_by_route=samples_by_route,
        known_origins={"CDG", "ORY"},
    )
    assert rate == 10.0


def test_rate_per_day_unknown_route_is_zero():
    """A baseline whose (origin, dest) doesn't appear in the
    7-day query result → rate 0 (no recent scrapes)."""
    rate = compute_rate_per_day(
        origin="CDG",
        destination="NRT",
        samples_by_route={},
        known_origins={"CDG"},
    )
    assert rate == 0.0


def test_rate_per_day_wildcard_origin_sums_across_known_origins():
    """origin=None means 'all origins toward dest'. Sum all matches
    and divide by 7."""
    samples_by_route = {
        ("CDG", "HKT"): 14,
        ("ORY", "HKT"): 7,
        ("BVA", "HKT"): 0,
    }
    rate = compute_rate_per_day(
        origin=None,
        destination="HKT",
        samples_by_route=samples_by_route,
        known_origins={"CDG", "ORY", "BVA"},
    )
    # (14 + 7 + 0) / 7 = 3.0
    assert rate == 3.0


from app.analysis.baseline_clusters import mature_coverage_pct


def test_mature_coverage_excludes_dormants_from_denominator():
    """(100 hot, 100 warm, 100 cold, 100 dormant) → 200/300 = 66.7%,
    NOT 200/400 = 50%. Dormants are zombies, not failing baselines,
    so they're not in the denominator."""
    counts = {"hot": 100, "warm": 100, "cold": 100, "dormant": 100}
    assert round(mature_coverage_pct(counts), 1) == 66.7


def test_mature_coverage_returns_zero_when_no_active_baselines():
    """All dormants → 0 / 0 → return 0.0 (not a crash)."""
    counts = {"hot": 0, "warm": 0, "cold": 0, "dormant": 100}
    assert mature_coverage_pct(counts) == 0.0


from app.analysis.baseline_clusters import eta_cold_to_warm, median_cold_eta_days


def test_eta_cold_to_warm_basic():
    """At 0 samples + 0.5/day, need 10 samples → 20 days."""
    assert eta_cold_to_warm(samples=0, rate_per_day=0.5) == 20


def test_eta_cold_to_warm_partial_progress():
    """At 5 samples + 0.5/day, need 5 more → 10 days."""
    assert eta_cold_to_warm(samples=5, rate_per_day=0.5) == 10


def test_eta_cold_to_warm_zero_rate_is_none():
    """rate_per_day == 0 → ETA undefined (don't divide by zero)."""
    assert eta_cold_to_warm(samples=5, rate_per_day=0.0) is None


def test_median_cold_eta_returns_int_when_5_or_more_baselines():
    """At least 5 cold baselines with defined ETAs → median is an int."""
    etas = [10, 20, 30, 40, 50]
    assert median_cold_eta_days(etas) == 30


def test_median_cold_eta_returns_none_when_under_5_samples():
    """Fewer than 5 cold baselines with defined ETAs → return None.
    The Telegram report renders this as '—'."""
    assert median_cold_eta_days([10, 20, 30]) is None
    assert median_cold_eta_days([]) is None


def test_median_cold_eta_ignores_none_values():
    """None entries (zero-rate baselines) are filtered out before
    the count threshold is checked."""
    # 4 defined ETAs + 1 None → under threshold → None
    assert median_cold_eta_days([10, None, 20, None, 30, None, 40]) is None


from app.analysis.baseline_clusters import build_cluster_report


def test_build_cluster_report_counts_per_cluster_and_unknowns():
    """End-to-end of the aggregation step: given baselines + a
    samples_by_route map, build a report dict with cluster counts,
    mature_coverage_pct, median cold ETA, and parsing diagnostics."""
    baselines = [
        # 2 hot
        {"route_key": "CDG-LIS-1m", "sample_count": 50},
        {"route_key": "CDG-BCN-1m", "sample_count": 35},
        # 1 warm
        {"route_key": "CDG-MAD-1m", "sample_count": 15},
        # 6 cold (so median ETA is reported). 3-letter alpha dest
        # codes required by the regex; we use a ZAx series to keep
        # them parseable yet distinct from the warm/hot ones.
        {"route_key": "CDG-ZAA-1m", "sample_count": 5},
        {"route_key": "CDG-ZAB-1m", "sample_count": 5},
        {"route_key": "CDG-ZAC-1m", "sample_count": 5},
        {"route_key": "CDG-ZAD-1m", "sample_count": 5},
        {"route_key": "CDG-ZAE-1m", "sample_count": 5},
        {"route_key": "CDG-ZAF-1m", "sample_count": 5},
        # 2 dormant
        {"route_key": "CDG-ZOM-1m", "sample_count": 2},
        {"route_key": "CDG-ZON-1m", "sample_count": 3},
        # 1 unparseable
        {"route_key": "MALFORMED", "sample_count": 99},
    ]
    # 6 cold baselines have rate=4/7=0.57/day (>0.1 → cold).
    # ZOM/ZON absent from map → rate 0 → dormant.
    samples_by_route = {
        ("CDG", "ZAA"): 4,
        ("CDG", "ZAB"): 4,
        ("CDG", "ZAC"): 4,
        ("CDG", "ZAD"): 4,
        ("CDG", "ZAE"): 4,
        ("CDG", "ZAF"): 4,
    }
    known_origins = {"CDG"}

    report = build_cluster_report(
        baselines=baselines,
        samples_by_route=samples_by_route,
        known_origins=known_origins,
    )

    assert report["counts"] == {
        "hot": 2,
        "warm": 1,
        "cold": 6,
        "dormant": 2,
    }
    assert report["unknown_count"] == 1
    assert report["total_parsed"] == 11
    assert report["total_with_unknown"] == 12
    # mature = (2+1)/(2+1+6) = 3/9 = 33.3%
    assert round(report["mature_coverage_pct"], 1) == 33.3
    # 6 cold ETAs all = (10-5) / (4/7) = 8.75 → int = 8
    assert report["median_cold_eta_days"] == 8


from app.analysis.baseline_clusters import format_cluster_report_for_telegram


def test_format_cluster_report_fits_in_under_12_lines():
    """The Telegram template must stay compact: ≤12 lines. Also
    verify all four cluster rows + season + parsing diagnostic
    are present."""
    report = {
        "counts": {"hot": 162, "warm": 487, "cold": 542, "dormant": 1123},
        "unknown_count": 4,
        "total_parsed": 2314,
        "total_with_unknown": 2318,
        "mature_coverage_pct": 54.5,
        "median_cold_eta_days": 45,
    }
    text = format_cluster_report_for_telegram(
        report=report,
        season="spring",
        median_samples_per_baseline=0.17,
    )
    lines = text.splitlines()
    assert len(lines) <= 12, f"Expected ≤12 lines, got {len(lines)}: {text}"
    assert "Couverture mature" in text
    assert "54" in text  # %
    assert "Hot" in text and "162" in text
    assert "Warm" in text and "487" in text
    assert "Cold" in text and "542" in text
    assert "Dormant" in text and "1123" in text
    assert "spring" in text
    assert "2314/2318" in text or "2314" in text  # parsing diagnostic


def test_format_renders_median_eta_dash_when_none():
    """When fewer than 5 cold baselines, median_cold_eta_days is None
    → the Cold line shows '—' instead of a number."""
    report = {
        "counts": {"hot": 0, "warm": 0, "cold": 2, "dormant": 0},
        "unknown_count": 0,
        "total_parsed": 2,
        "total_with_unknown": 2,
        "mature_coverage_pct": 0.0,
        "median_cold_eta_days": None,
    }
    text = format_cluster_report_for_telegram(
        report=report,
        season="summer",
        median_samples_per_baseline=0.0,
    )
    assert "—" in text  # em dash for undefined median


from app.analysis.baseline_clusters import build_dormants_csv


def test_build_dormants_csv_contains_expected_columns_and_season():
    """CSV header + rows: every dormant baseline becomes one row
    with route_key, sample_count, last_scrape_at, rate_per_day_7d,
    last_seen_in_season."""
    dormants = [
        {
            "route_key": "CDG-ZOM-1m",
            "sample_count": 2,
            "last_scrape_at": "2026-04-15T10:00:00+00:00",
            "rate_per_day_7d": 0.0,
        },
        {
            "route_key": "*-NRT-bucket_long",
            "sample_count": 3,
            "last_scrape_at": None,
            "rate_per_day_7d": 0.05,
        },
    ]
    csv_text = build_dormants_csv(dormants=dormants, current_season="spring")
    lines = csv_text.strip().splitlines()
    assert lines[0] == "route_key,sample_count,last_scrape_at,rate_per_day_7d,last_seen_in_season"
    assert len(lines) == 3  # header + 2 rows
    assert "CDG-ZOM-1m" in lines[1]
    assert ",spring" in lines[1]
    # NULL last_scrape_at renders as empty field, not the literal "None"
    assert ",,0.05,spring" in lines[2]
