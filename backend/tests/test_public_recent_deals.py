from app.api.public_recent_deals import (
    build_round_trip_candidates,
    select_showcase_deals,
)


def test_one_way_and_missing_return_are_excluded():
    qualified = [
        {
            "item_id": "one-way",
            "price": 25,
            "baseline_price": 80,
            "discount_pct": 69,
            "created_at": "2026-07-20T10:00:00+00:00",
            "trip_type": "one_way",
        },
        {
            "item_id": "broken-round-trip",
            "price": 120,
            "baseline_price": 260,
            "discount_pct": 54,
            "created_at": "2026-07-20T10:00:00+00:00",
            "trip_type": "round_trip",
        },
        {
            "item_id": "valid-round-trip",
            "price": 520,
            "baseline_price": 1040,
            "discount_pct": 50,
            "created_at": "2026-07-20T10:00:00+00:00",
            "trip_type": "round_trip",
        },
    ]
    raw = [
        {
            "id": "one-way",
            "origin": "CDG",
            "destination": "BCN",
            "trip_type": "one_way",
            "return_date": None,
        },
        {
            "id": "broken-round-trip",
            "origin": "CDG",
            "destination": "LIS",
            "trip_type": "round_trip",
            "return_date": None,
        },
        {
            "id": "valid-round-trip",
            "origin": "CDG",
            "destination": "NRT",
            "trip_type": "round_trip",
            "return_date": "2026-10-18",
        },
    ]

    candidates = build_round_trip_candidates(qualified, raw)

    assert len(candidates) == 1
    assert candidates[0]["destination"] == "NRT"
    assert candidates[0]["trip_type"] == "round_trip"
    assert candidates[0]["return_date"] == "2026-10-18"


def test_valid_round_trips_are_kept_with_real_baseline():
    qualified = [
        {
            "item_id": "tokyo",
            "price": 520,
            "baseline_price": 1040,
            "discount_pct": 50,
            "created_at": "2026-07-20T10:00:00+00:00",
            "trip_type": "round_trip",
        },
        {
            "item_id": "lisbon",
            "price": 72,
            "baseline_price": 180,
            "discount_pct": 60,
            "created_at": "2026-07-21T10:00:00+00:00",
            "trip_type": "round_trip",
        },
    ]
    raw = [
        {
            "id": "tokyo",
            "origin": "CDG",
            "destination": "NRT",
            "trip_type": "round_trip",
            "return_date": "2026-10-18",
        },
        {
            "id": "lisbon",
            "origin": "TLS",
            "destination": "LIS",
            "trip_type": "round_trip",
            "return_date": "2026-09-12",
        },
    ]

    candidates = build_round_trip_candidates(qualified, raw)

    assert len(candidates) == 2
    assert all(item["trip_type"] == "round_trip" for item in candidates)
    assert all(item["return_date"] for item in candidates)
    assert candidates[0]["baseline"] == 1040
    assert candidates[1]["is_province"] is True


def test_suspicious_long_haul_baseline_is_excluded():
    qualified = [
        {
            "item_id": "cheap-tokyo",
            "price": 162,
            "baseline_price": 352,
            "discount_pct": 54,
            "created_at": "2026-07-21T10:00:00+00:00",
            "trip_type": "round_trip",
        }
    ]
    raw = [
        {
            "id": "cheap-tokyo",
            "origin": "CDG",
            "destination": "NRT",
            "trip_type": "round_trip",
            "return_date": "2026-09-12",
        }
    ]

    assert build_round_trip_candidates(qualified, raw) == []


def test_first_showcase_cards_include_long_haul_and_province():
    candidates = [
        {
            "destination": "NRT",
            "discount_pct": 50,
            "is_long_haul": True,
            "is_province": False,
        },
        {
            "destination": "LIS",
            "discount_pct": 63,
            "is_long_haul": False,
            "is_province": True,
        },
        {
            "destination": "BCN",
            "discount_pct": 70,
            "is_long_haul": False,
            "is_province": False,
        },
        {
            "destination": "BKK",
            "discount_pct": 45,
            "is_long_haul": True,
            "is_province": False,
        },
        {
            "destination": "FCO",
            "discount_pct": 58,
            "is_long_haul": False,
            "is_province": True,
        },
    ]

    selected = select_showcase_deals(candidates, limit=5)

    assert len(selected) == 5
    assert any(item["is_long_haul"] for item in selected[:3])
    assert any(item["is_province"] for item in selected[:3])
    assert len({item["destination"] for item in selected}) == len(selected)
