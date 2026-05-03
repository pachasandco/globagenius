"""Tests for app.notifications.airlines.normalize_airline_name.

The function must:
- map known IATA codes to a French/English brand name
- map Cyrillic agency strings to a Latin-script equivalent
- pass anything we don't know through unchanged
- handle empty / None input cleanly
"""
from app.notifications.airlines import normalize_airline_name


def test_iata_air_france():
    assert normalize_airline_name("AF") == "Air France"


def test_iata_ryanair():
    assert normalize_airline_name("FR") == "Ryanair"


def test_iata_vueling():
    assert normalize_airline_name("VY") == "Vueling"


def test_iata_case_insensitive():
    """A lowercase IATA code from the API should still resolve."""
    assert normalize_airline_name("af") == "Air France"


def test_cyrillic_aviasales():
    """The exact case Moussa flagged in v8 prod alerts."""
    assert normalize_airline_name("Авиасейлс") == "Aviasales"


def test_cyrillic_kupibilet():
    assert normalize_airline_name("Купибилет") == "Kupibilet"


def test_clickavia_lowercased():
    assert normalize_airline_name("Clickavia") == "Clickavia"
    assert normalize_airline_name("clickavia") == "Clickavia"


def test_unknown_brand_passes_through():
    """A carrier we don't have a fixup for must keep its incoming label."""
    assert normalize_airline_name("Some Random Airline") == "Some Random Airline"


def test_empty_input():
    assert normalize_airline_name("") == ""
    assert normalize_airline_name(None) == ""


def test_strips_whitespace():
    assert normalize_airline_name("  AF  ") == "Air France"


def test_three_letter_strings_pass_through_even_if_known_lowercase():
    """A 3+ letter brand isn't an IATA code — fixup table only matches
    if the brand name itself is in _AGENCY_FIXUPS, not the IATA table."""
    # "AFR" is not an IATA code (those are 2 letters), so we pass through.
    assert normalize_airline_name("AFR") == "AFR"
