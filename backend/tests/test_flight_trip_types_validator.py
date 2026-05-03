"""V5: tests for the PreferencesRequest.flight_trip_types validator."""
import pytest
from pydantic import ValidationError
from app.api.routes import PreferencesRequest


def _base_payload(**overrides) -> dict:
    return {
        "airport_codes": ["CDG"],
        "offer_types": ["flight"],
        **overrides,
    }


def test_default_is_round_trip_only():
    req = PreferencesRequest(**_base_payload())
    assert req.flight_trip_types == ["round_trip"]


def test_accepts_round_trip_and_one_way():
    req = PreferencesRequest(
        **_base_payload(flight_trip_types=["round_trip", "one_way"])
    )
    assert req.flight_trip_types == ["round_trip", "one_way"]


def test_rejects_unknown_trip_type():
    with pytest.raises(ValidationError) as exc:
        PreferencesRequest(**_base_payload(flight_trip_types=["round_trip", "lol"]))
    assert "lol" in str(exc.value)


def test_empty_list_falls_back_to_round_trip():
    req = PreferencesRequest(**_base_payload(flight_trip_types=[]))
    assert req.flight_trip_types == ["round_trip"]


def test_dedups_duplicates_preserving_order():
    req = PreferencesRequest(
        **_base_payload(flight_trip_types=["one_way", "round_trip", "one_way"])
    )
    assert req.flight_trip_types == ["one_way", "round_trip"]


def test_one_way_only_is_accepted():
    req = PreferencesRequest(**_base_payload(flight_trip_types=["one_way"]))
    assert req.flight_trip_types == ["one_way"]


# ─── include_split_tickets ───

def test_include_split_tickets_default_false():
    req = PreferencesRequest(**_base_payload())
    assert req.include_split_tickets is False


def test_include_split_tickets_can_be_enabled():
    req = PreferencesRequest(**_base_payload(include_split_tickets=True))
    assert req.include_split_tickets is True


def test_include_split_tickets_independent_from_flight_trip_types():
    # Pydantic accepts any combo; the gating (must have round_trip) lives
    # in the dispatch layer, not the schema.
    req = PreferencesRequest(
        **_base_payload(flight_trip_types=["one_way"], include_split_tickets=True)
    )
    assert req.include_split_tickets is True
    assert req.flight_trip_types == ["one_way"]
