from app.analysis.buckets import (
    DURATION_BUCKETS,
    SHORT_HAUL_MAX_MINUTES,
    bucket_for_duration,
    is_short_haul,
    stops_allowed,
)


def test_duration_buckets_constant():
    assert DURATION_BUCKETS == {
        "short":  (1, 3),
        "medium": (4, 9),
        "long":   (10, 21),
    }


def test_short_haul_max_minutes_constant():
    assert SHORT_HAUL_MAX_MINUTES == 180


def test_bucket_for_duration_short_boundaries():
    assert bucket_for_duration(1) == "short"
    assert bucket_for_duration(2) == "short"
    assert bucket_for_duration(3) == "short"


def test_bucket_for_duration_medium_boundaries():
    assert bucket_for_duration(4) == "medium"
    assert bucket_for_duration(7) == "medium"
    assert bucket_for_duration(9) == "medium"


def test_bucket_for_duration_long_boundaries():
    assert bucket_for_duration(10) == "long"
    assert bucket_for_duration(15) == "long"
    assert bucket_for_duration(21) == "long"


def test_bucket_for_duration_outside_range():
    assert bucket_for_duration(0) is None
    assert bucket_for_duration(22) is None
    assert bucket_for_duration(56) is None
    assert bucket_for_duration(-1) is None


def test_is_short_haul_threshold():
    assert is_short_haul(0) is True
    assert is_short_haul(179) is True
    assert is_short_haul(180) is False
    assert is_short_haul(600) is False


def test_stops_allowed_short_haul():
    assert stops_allowed(120) == 0
    assert stops_allowed(179) == 0


def test_stops_allowed_long_haul():
    assert stops_allowed(180) == 1
    assert stops_allowed(720) == 1
