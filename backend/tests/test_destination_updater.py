"""Tests for the v8 long-haul force-include policy in compute_priority_destinations.

Audit found that the seasonal/Travelpayouts scorer ranked most long-haul
destinations (LAX, SFO, MLE, MRU, CUN, BOM, DEL, GIG, EZE, LIM…) too low
to make the top-40 cut, so the long-courrier net was effectively limited
to 11 hubs. The fix force-includes a curated list of long-haul IATAs into
the priority list, on top of the seasonal top-N.
"""
from unittest.mock import patch

from app.analysis.destination_updater import (
    LONG_HAUL_GUARANTEED,
    compute_priority_destinations,
)


def _no_tp_signal(*_args, **_kwargs):
    """Stub _fetch_travelpayouts_popular to return zero signal so the
    seasonal-only ranking is deterministic in tests."""
    return {}


def test_long_haul_guaranteed_iatas_are_present_after_force_include():
    """Every IATA from LONG_HAUL_GUARANTEED must end up in the result, even
    if its score wasn't high enough for the seasonal top-N."""
    with patch(
        "app.analysis.destination_updater._fetch_travelpayouts_popular",
        side_effect=_no_tp_signal,
    ):
        result = compute_priority_destinations(max_count=40)

    iatas = {d["iata"] for d in result}
    missing = [iata for iata in LONG_HAUL_GUARANTEED if iata not in iatas]
    assert missing == [], f"Long-haul not force-added: {missing}"


def test_force_include_extends_total_count_beyond_max_count():
    """When seasonal top-40 leaves long-haul out, force-include grows the
    total list past max_count. This is intentional — the cap is on the
    seasonal slice, the long-haul belt is non-negotiable."""
    with patch(
        "app.analysis.destination_updater._fetch_travelpayouts_popular",
        side_effect=_no_tp_signal,
    ):
        result = compute_priority_destinations(max_count=40)

    # We expect at least max_count + a meaningful share of LONG_HAUL_GUARANTEED.
    # Even on a winter run, plenty of long-haul IATAs are not in the seasonal
    # top, so force-include kicks in.
    assert len(result) > 40, f"Expected force-include to push count over 40, got {len(result)}"


def test_no_duplicate_iatas_in_result():
    """A LH IATA already inside the seasonal top-N must not be appended
    twice by force-include."""
    with patch(
        "app.analysis.destination_updater._fetch_travelpayouts_popular",
        side_effect=_no_tp_signal,
    ):
        result = compute_priority_destinations(max_count=40)

    iatas = [d["iata"] for d in result]
    assert len(iatas) == len(set(iatas)), "Duplicate IATAs in result"


def test_force_include_is_silent_when_iata_unknown_to_universe():
    """If LONG_HAUL_GUARANTEED references an IATA missing from
    DESTINATION_UNIVERSE (typo, removal), the function must skip it
    silently rather than crash the weekly job."""
    with patch(
        "app.analysis.destination_updater._fetch_travelpayouts_popular",
        side_effect=_no_tp_signal,
    ), patch(
        "app.analysis.destination_updater.LONG_HAUL_GUARANTEED",
        ["JFK", "TYPO_IATA_123", "DXB"],
    ):
        result = compute_priority_destinations(max_count=40)
    iatas = {d["iata"] for d in result}
    assert "JFK" in iatas
    assert "DXB" in iatas
    assert "TYPO_IATA_123" not in iatas


def test_long_haul_guaranteed_covers_all_major_regions():
    """Sanity check on the curated list: at least one entry from each
    major travel region we promote on the marketing site."""
    region_for = {
        "amerique_nord": ["JFK", "EWR", "MIA", "LAX", "SFO", "YUL", "YYZ", "MEX", "CUN"],
        "caraibes": ["PUJ", "PTP", "FDF"],
        "amerique_sud": ["GIG", "GRU", "EZE", "SCL", "BOG", "LIM"],
        "asie": ["BKK", "NRT", "HND", "ICN", "HKG", "SIN", "KUL", "DEL", "BOM", "DPS"],
        "oceanie": ["SYD"],
        "ocean_indien": ["MLE", "MRU", "RUN", "ZNZ", "SEZ"],
        "afrique": ["JNB", "CPT", "NBO"],
        "moyen_orient": ["DXB", "DOH"],
    }
    guaranteed = set(LONG_HAUL_GUARANTEED)
    missing_regions = []
    for region, iatas in region_for.items():
        if not any(i in guaranteed for i in iatas):
            missing_regions.append(region)
    assert not missing_regions, f"Regions with no guaranteed IATA: {missing_regions}"
