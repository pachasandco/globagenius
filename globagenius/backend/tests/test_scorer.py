from app.analysis.scorer import compute_score


def test_compute_score_high_deal():
    score = compute_score(
        discount_pct=55.0,
        destination_code="BCN",
        date_flexibility=3,
        accommodation_rating=4.5,
    )
    assert 70 <= score <= 100


def test_compute_score_low_deal():
    score = compute_score(
        discount_pct=40.0,
        destination_code="ZAG",
        date_flexibility=0,
        accommodation_rating=4.0,
    )
    assert score < 70


def test_compute_score_max_discount():
    score = compute_score(
        discount_pct=80.0,
        destination_code="BCN",
        date_flexibility=5,
        accommodation_rating=5.0,
    )
    assert score == 100


def test_compute_score_no_rating():
    score = compute_score(
        discount_pct=50.0,
        destination_code="LIS",
        date_flexibility=2,
        accommodation_rating=None,
    )
    assert 0 < score < 100


def test_compute_score_unknown_destination():
    score = compute_score(
        discount_pct=50.0,
        destination_code="XXX",
        date_flexibility=2,
        accommodation_rating=4.0,
    )
    assert 0 < score < 100
