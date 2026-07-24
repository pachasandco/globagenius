from app.analysis.buckets import (
    DURATION_BUCKETS,
    SHORT_HAUL_MAX_MINUTES,
    bucket_for_duration,
    is_short_haul,
    stops_allowed,
)


def test_duration_buckets_constant():
    assert DURATION_BUCKETS == {
        "short":    (1, 3),
        "medium":   (4, 7),
        "long":     (8, 12),
        "extended": (13, 21),
    }


def test_short_haul_max_minutes_constant():
    assert SHORT_HAUL_MAX_MINUTES == 180


def test_bucket_for_duration_short_boundaries():
    assert bucket_for_duration(1) == "short"
    assert bucket_for_duration(2) == "short"
    assert bucket_for_duration(3) == "short"


def test_bucket_for_duration_medium_boundaries():
    assert bucket_for_duration(4) == "medium"
    assert bucket_for_duration(5) == "medium"
    assert bucket_for_duration(7) == "medium"


def test_bucket_for_duration_long_boundaries():
    assert bucket_for_duration(8) == "long"
    assert bucket_for_duration(10) == "long"
    assert bucket_for_duration(12) == "long"


def test_bucket_for_duration_outside_range():
    assert bucket_for_duration(0) is None
    assert bucket_for_duration(-1) is None
    # 22+ is out of range for every destination
    assert bucket_for_duration(22) is None
    assert bucket_for_duration(22, destination="NRT") is None


# ── Plafond de durée par type de vol (2026-07-24) ───────────────────────────
# Le plafond à 12j coupait les meilleurs tarifs long-courriers : les
# compagnies placent leurs prix agressifs sur des séjours de 2-3 semaines
# (mesuré : CDG→Tokyo 449€ sur 14j vs 720€ sur ≤12j = -38%, Sydney -25%,
# Johannesburg -11%). Long-courrier → 21j, reste → 14j.

def test_bucket_long_haul_allows_extended_stays():
    # Long-courrier : jusqu'à 21 jours
    assert bucket_for_duration(13, destination="NRT") == "extended"
    assert bucket_for_duration(14, destination="HND") == "extended"
    assert bucket_for_duration(21, destination="SYD") == "extended"


def test_bucket_short_haul_capped_at_14_days():
    # Europe/court-courrier : plafond 14j, donc 13-14 OK mais pas au-delà
    assert bucket_for_duration(13, destination="BCN") == "extended"
    assert bucket_for_duration(14, destination="BCN") == "extended"
    assert bucket_for_duration(15, destination="BCN") is None
    assert bucket_for_duration(21, destination="BCN") is None


def test_bucket_without_destination_uses_short_haul_cap():
    # Rétro-compatibilité : sans destination, on applique le plafond
    # conservateur (14j) — jamais celui du long-courrier.
    assert bucket_for_duration(14) == "extended"
    assert bucket_for_duration(15) is None


def test_bucket_min_stay_rule_untouched():
    # La règle fondateur du minimum de nuits n'est pas affectée par
    # l'élargissement du plafond.
    assert bucket_for_duration(1) == "short"
    assert bucket_for_duration(0) is None


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
