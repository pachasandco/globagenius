# Travelpayouts Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken Google Flights scraper (Playwright + Apify) with the Travelpayouts API as the sole flight price source.

**Architecture:** New module `app/scraper/travelpayouts_flights.py` exposes the same `scrape_all_flights()` signature as the old `flights.py`, so `jobs.py` switches with a single import change. Per route, we call the Travelpayouts `prices/calendar` endpoint for 3 consecutive months and normalize each daily quote into a `raw_flights` row. Hotel scraping is untouched.

**Tech Stack:** Python 3.12, FastAPI, Supabase, httpx, pytest, APScheduler. Travelpayouts REST API (`api.travelpayouts.com`).

**Spec:** [docs/superpowers/specs/2026-04-12-travelpayouts-migration-design.md](../specs/2026-04-12-travelpayouts-migration-design.md)

---

## File Structure

**Created:**
- `backend/app/scraper/travelpayouts_flights.py` — new flight scraper module
- `backend/tests/test_travelpayouts_flights.py` — unit tests for the new module

**Modified:**
- `backend/app/scheduler/jobs.py` — change 4 imports from `app.scraper.flights` to `app.scraper.travelpayouts_flights`
- `backend/app/analysis/route_selector.py` — add `LONG_HAUL_DESTINATIONS` set + helper `is_long_haul()`
- `backend/app/scraper/travelpayouts.py` — add `get_calendar_prices()` helper (used by the new scraper)

**Deleted:**
- `backend/app/scraper/flights.py`
- `backend/app/scraper/browser/google_flights.py`

**Untouched** (hotel scraping out of scope):
- `backend/app/scraper/accommodations.py`
- `backend/app/scraper/apify_client.py`
- `backend/app/scraper/browser/google_hotels.py`
- `backend/app/scraper/browser/stealth.py`
- `backend/Dockerfile` and `backend/requirements.txt` (Playwright + Apify still needed by hotels)

---

## Task 1: Add long-haul classification to route_selector

**Why:** The scraper needs to skip long-haul destinations from non-CDG airports. We centralize the rule in `route_selector` so it stays close to the existing seasonal logic.

**Files:**
- Modify: `backend/app/analysis/route_selector.py`
- Test: `backend/tests/test_route_selector.py` (new file)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_route_selector.py`:

```python
from app.analysis.route_selector import is_long_haul, LONG_HAUL_DESTINATIONS


def test_long_haul_set_contains_expected_destinations():
    expected = {"NRT", "JFK", "BKK", "YUL", "DXB", "MIA", "SYD",
                "CUN", "PUJ", "MLE", "MRU", "RUN", "GIG", "LAX"}
    assert expected == LONG_HAUL_DESTINATIONS


def test_is_long_haul_returns_true_for_long_haul_codes():
    assert is_long_haul("JFK") is True
    assert is_long_haul("BKK") is True
    assert is_long_haul("SYD") is True


def test_is_long_haul_returns_false_for_short_haul_codes():
    assert is_long_haul("BCN") is False
    assert is_long_haul("LIS") is False
    assert is_long_haul("RAK") is False


def test_is_long_haul_handles_unknown_codes():
    assert is_long_haul("XXX") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_route_selector.py -v`
Expected: FAIL with `ImportError: cannot import name 'is_long_haul'`

- [ ] **Step 3: Add the constant and helper to route_selector.py**

Add at the end of `backend/app/analysis/route_selector.py`:

```python


LONG_HAUL_DESTINATIONS = {
    "NRT", "JFK", "BKK", "YUL", "DXB", "MIA", "SYD",
    "CUN", "PUJ", "MLE", "MRU", "RUN", "GIG", "LAX",
}


def is_long_haul(destination: str) -> bool:
    return destination in LONG_HAUL_DESTINATIONS
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_route_selector.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/app/analysis/route_selector.py backend/tests/test_route_selector.py
git commit -m "feat(routes): add long-haul destination classification"
```

---

## Task 2: Add calendar endpoint helper to travelpayouts.py

**Why:** The new scraper needs an endpoint that returns one quote per departure day across a whole month (1 API call → ~30 flights). This isn't in `travelpayouts.py` yet.

**Files:**
- Modify: `backend/app/scraper/travelpayouts.py`
- Test: `backend/tests/test_travelpayouts.py` (new file)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_travelpayouts.py`:

```python
from unittest.mock import patch, MagicMock
from app.scraper.travelpayouts import get_calendar_prices


def test_get_calendar_prices_parses_response():
    fake_response = {
        "data": {
            "2026-05-12": {
                "origin": "PAR",
                "destination": "NYC",
                "airline": "AF",
                "departure_at": "2026-05-12T10:00:00+02:00",
                "return_at": "2026-05-19T18:00:00-04:00",
                "expires_at": "2026-04-13T10:00:00Z",
                "price": 412,
                "flight_number": 22,
                "transfers": 0,
            },
            "2026-05-13": {
                "origin": "PAR",
                "destination": "NYC",
                "airline": "DL",
                "departure_at": "2026-05-13T11:00:00+02:00",
                "return_at": "2026-05-20T19:00:00-04:00",
                "expires_at": "2026-04-13T10:00:00Z",
                "price": 398,
                "flight_number": 41,
                "transfers": 1,
            },
        },
        "success": True,
    }
    with patch("app.scraper.travelpayouts._get", return_value=fake_response):
        result = get_calendar_prices("CDG", "JFK", "2026-05")
    assert len(result) == 2
    assert result[0]["price"] == 412
    assert result[0]["airline"] == "AF"
    assert result[0]["departure_at"] == "2026-05-12T10:00:00+02:00"
    assert result[0]["transfers"] == 0


def test_get_calendar_prices_returns_empty_on_no_data():
    with patch("app.scraper.travelpayouts._get", return_value=None):
        assert get_calendar_prices("CDG", "JFK", "2026-05") == []


def test_get_calendar_prices_returns_empty_on_unsuccessful_response():
    with patch("app.scraper.travelpayouts._get", return_value={"success": False}):
        assert get_calendar_prices("CDG", "JFK", "2026-05") == []


def test_get_calendar_prices_returns_empty_on_empty_data_dict():
    with patch("app.scraper.travelpayouts._get", return_value={"success": True, "data": {}}):
        assert get_calendar_prices("CDG", "JFK", "2026-05") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_travelpayouts.py -v`
Expected: FAIL with `ImportError: cannot import name 'get_calendar_prices'`

- [ ] **Step 3: Add `get_calendar_prices` to travelpayouts.py**

Add this function inside `backend/app/scraper/travelpayouts.py`, after `get_month_matrix` (around line 102):

```python
def get_calendar_prices(origin: str, destination: str, depart_month: str) -> list[dict]:
    """Get one cheapest price per departure day over a month.

    `depart_month` format: YYYY-MM (e.g. "2026-05").
    Calls /v1/prices/calendar with calendar_type=departure_date.
    Returns up to ~30 entries (one per day with availability)."""
    params = {
        "origin": origin,
        "destination": destination,
        "depart_date": depart_month,
        "calendar_type": "departure_date",
        "currency": "eur",
    }
    data = _get(f"{REST_URL}/v1/prices/calendar", params)
    if not data or not data.get("success"):
        return []

    entries = data.get("data") or {}
    result = []
    for day, flight in entries.items():
        if not isinstance(flight, dict):
            continue
        result.append({
            "departure_at": flight.get("departure_at", ""),
            "return_at": flight.get("return_at", ""),
            "expires_at": flight.get("expires_at", ""),
            "price": flight.get("price", 0),
            "airline": flight.get("airline", ""),
            "flight_number": flight.get("flight_number", 0),
            "transfers": flight.get("transfers", 0),
        })
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_travelpayouts.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/app/scraper/travelpayouts.py backend/tests/test_travelpayouts.py
git commit -m "feat(travelpayouts): add get_calendar_prices helper"
```

---

## Task 3: Create travelpayouts_flights module — pure parsing helpers

**Why:** Start with the small, pure functions (no I/O). They are easy to test and they form the building blocks of the scraper.

**Files:**
- Create: `backend/app/scraper/travelpayouts_flights.py`
- Test: `backend/tests/test_travelpayouts_flights.py` (new file)

- [ ] **Step 1: Write the failing tests for `_window_label` and `_normalize_calendar_entry`**

Create `backend/tests/test_travelpayouts_flights.py`:

```python
from app.scraper.travelpayouts_flights import (
    _window_label,
    _normalize_calendar_entry,
    SOURCE,
)


def test_window_label_returns_1m_for_short_horizon():
    assert _window_label(5) == "1m"
    assert _window_label(30) == "1m"


def test_window_label_returns_2m_for_two_months():
    assert _window_label(31) == "2m"
    assert _window_label(60) == "2m"


def test_window_label_returns_3m_for_three_months():
    assert _window_label(61) == "3m"
    assert _window_label(90) == "3m"


def test_window_label_returns_4m_for_four_months():
    assert _window_label(91) == "4m"
    assert _window_label(120) == "4m"


def test_window_label_returns_6m_beyond_4_months():
    assert _window_label(121) == "6m"
    assert _window_label(365) == "6m"


def test_normalize_calendar_entry_maps_all_fields():
    entry = {
        "departure_at": "2026-05-12T10:00:00+02:00",
        "return_at": "2026-05-19T18:00:00-04:00",
        "expires_at": "2026-04-13T10:00:00Z",
        "price": 412,
        "airline": "AF",
        "flight_number": 22,
        "transfers": 0,
    }
    result = _normalize_calendar_entry(entry, origin="CDG", destination="JFK")
    assert result is not None
    assert result["origin"] == "CDG"
    assert result["destination"] == "JFK"
    assert result["price"] == 412.0
    assert result["departure_date"] == "2026-05-12"
    assert result["return_date"] == "2026-05-19"
    assert result["airline"] == "AF"
    assert result["stops"] == 0
    assert result["source"] == SOURCE
    assert result["source_url"].startswith("https://www.aviasales.com/search/")


def test_normalize_calendar_entry_falls_back_when_return_at_missing():
    entry = {
        "departure_at": "2026-05-12T10:00:00+02:00",
        "return_at": "",
        "expires_at": "",
        "price": 412,
        "airline": "AF",
        "flight_number": 22,
        "transfers": 1,
    }
    result = _normalize_calendar_entry(entry, origin="CDG", destination="JFK")
    assert result is not None
    assert result["return_date"] == "2026-05-19"  # depart + 7 days
    assert result["stops"] == 1


def test_normalize_calendar_entry_returns_none_for_zero_price():
    entry = {
        "departure_at": "2026-05-12T10:00:00+02:00",
        "return_at": "2026-05-19T18:00:00-04:00",
        "expires_at": "",
        "price": 0,
        "airline": "AF",
        "flight_number": 22,
        "transfers": 0,
    }
    assert _normalize_calendar_entry(entry, origin="CDG", destination="JFK") is None


def test_normalize_calendar_entry_returns_none_for_missing_departure_at():
    entry = {
        "departure_at": "",
        "return_at": "",
        "expires_at": "",
        "price": 412,
        "airline": "AF",
        "flight_number": 22,
        "transfers": 0,
    }
    assert _normalize_calendar_entry(entry, origin="CDG", destination="JFK") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_travelpayouts_flights.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.scraper.travelpayouts_flights'`

- [ ] **Step 3: Create travelpayouts_flights.py with the helpers**

Create `backend/app/scraper/travelpayouts_flights.py`:

```python
"""Flight scraper backed by the Travelpayouts API.

Replaces the previous Google Flights / Playwright / Apify pipeline.
Single source for flight prices, free, no bot detection."""

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from app.config import settings
from app.scraper.normalizer import normalize_flight
from app.scraper.travelpayouts import get_calendar_prices
from app.analysis.route_selector import is_long_haul, get_priority_destinations

logger = logging.getLogger(__name__)

SOURCE = "travelpayouts"

SAMPLE_MONTH_OFFSETS = [1, 2, 3]  # M+1, M+2, M+3
DEFAULT_TRIP_DURATION_DAYS = 7

AIRPORTS_PER_CYCLE = 2


def _window_label(days_ahead: int) -> str:
    if days_ahead <= 30:
        return "1m"
    elif days_ahead <= 60:
        return "2m"
    elif days_ahead <= 90:
        return "3m"
    elif days_ahead <= 120:
        return "4m"
    else:
        return "6m"


def _build_aviasales_url(origin: str, destination: str, dep_date: str, ret_date: str) -> str:
    """Build a deeplink to the Aviasales search results page.

    Format: https://www.aviasales.com/search/CDG1205JFK19051
    where the first date is depart (DDMM) and the second is return (DDMM).
    The trailing "1" is the number of adult passengers."""
    try:
        dep = datetime.strptime(dep_date, "%Y-%m-%d")
        ret = datetime.strptime(ret_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return f"https://www.aviasales.com/search?origin={quote(origin)}&destination={quote(destination)}"
    return (
        f"https://www.aviasales.com/search/"
        f"{origin}{dep.strftime('%d%m')}{destination}{ret.strftime('%d%m')}1"
    )


def _normalize_calendar_entry(entry: dict, origin: str, destination: str) -> dict | None:
    """Map a Travelpayouts calendar entry to the raw_flights row format.
    Returns None if the entry is unusable (missing date, zero price)."""
    departure_at = entry.get("departure_at") or ""
    price = entry.get("price") or 0
    if not departure_at or not price:
        return None

    departure_date = departure_at[:10]
    return_at = entry.get("return_at") or ""
    if return_at:
        return_date = return_at[:10]
    else:
        try:
            dep = datetime.strptime(departure_date, "%Y-%m-%d")
            return_date = (dep + timedelta(days=DEFAULT_TRIP_DURATION_DAYS)).strftime("%Y-%m-%d")
        except ValueError:
            return None

    raw = {
        "price": float(price),
        "currency": "EUR",
        "origin": origin,
        "destination": destination,
        "departureDate": departure_date,
        "returnDate": return_date,
        "airline": entry.get("airline", ""),
        "stops": int(entry.get("transfers", 0) or 0),
        "url": _build_aviasales_url(origin, destination, departure_date, return_date),
    }

    normalized = normalize_flight(raw, source=SOURCE)

    expires_at = entry.get("expires_at") or ""
    if expires_at:
        normalized["expires_at"] = expires_at

    return normalized
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_travelpayouts_flights.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/app/scraper/travelpayouts_flights.py backend/tests/test_travelpayouts_flights.py
git commit -m "feat(scraper): add travelpayouts_flights pure helpers"
```

---

## Task 4: Add `scrape_flights_for_route` — fetches 3 months for one route

**Why:** This is the smallest unit of work that talks to the API. It iterates over the 3 target months and concatenates the normalized flights.

**Files:**
- Modify: `backend/app/scraper/travelpayouts_flights.py`
- Modify: `backend/tests/test_travelpayouts_flights.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_travelpayouts_flights.py`:

```python
from unittest.mock import patch
from datetime import datetime, timezone


def _calendar_entry(price: int, day: int, month: int = 5):
    return {
        "departure_at": f"2026-{month:02d}-{day:02d}T10:00:00+02:00",
        "return_at": f"2026-{month:02d}-{day + 7:02d}T18:00:00+02:00",
        "expires_at": "2026-04-13T10:00:00Z",
        "price": price,
        "airline": "AF",
        "flight_number": 22,
        "transfers": 0,
    }


def test_scrape_flights_for_route_calls_three_months_and_aggregates():
    from app.scraper.travelpayouts_flights import scrape_flights_for_route

    fixed_now = datetime(2026, 4, 12, tzinfo=timezone.utc)

    def fake_get_calendar(origin, destination, month):
        return {
            "2026-05": [_calendar_entry(412, 12), _calendar_entry(398, 13)],
            "2026-06": [_calendar_entry(450, 14, month=6)],
            "2026-07": [_calendar_entry(380, 15, month=7)],
        }.get(month, [])

    with patch("app.scraper.travelpayouts_flights.get_calendar_prices", side_effect=fake_get_calendar), \
         patch("app.scraper.travelpayouts_flights._utcnow", return_value=fixed_now):
        flights = scrape_flights_for_route("CDG", "JFK")

    assert len(flights) == 4
    prices = sorted(f["price"] for f in flights)
    assert prices == [380.0, 398.0, 412.0, 450.0]
    for f in flights:
        assert f["origin"] == "CDG"
        assert f["destination"] == "JFK"
        assert f["source"] == "travelpayouts"


def test_scrape_flights_for_route_skips_unusable_entries():
    from app.scraper.travelpayouts_flights import scrape_flights_for_route

    fixed_now = datetime(2026, 4, 12, tzinfo=timezone.utc)

    def fake_get_calendar(origin, destination, month):
        if month == "2026-05":
            return [_calendar_entry(412, 12), {"departure_at": "", "price": 0}]
        return []

    with patch("app.scraper.travelpayouts_flights.get_calendar_prices", side_effect=fake_get_calendar), \
         patch("app.scraper.travelpayouts_flights._utcnow", return_value=fixed_now):
        flights = scrape_flights_for_route("CDG", "JFK")

    assert len(flights) == 1
    assert flights[0]["price"] == 412.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_travelpayouts_flights.py::test_scrape_flights_for_route_calls_three_months_and_aggregates -v`
Expected: FAIL with `ImportError: cannot import name 'scrape_flights_for_route'`

- [ ] **Step 3: Add `_utcnow` and `scrape_flights_for_route` to travelpayouts_flights.py**

Append to `backend/app/scraper/travelpayouts_flights.py`:

```python


def _utcnow() -> datetime:
    """Indirection for tests to override."""
    return datetime.now(timezone.utc)


def _target_months() -> list[str]:
    now = _utcnow()
    months = []
    for offset in SAMPLE_MONTH_OFFSETS:
        year = now.year + ((now.month - 1 + offset) // 12)
        month = ((now.month - 1 + offset) % 12) + 1
        months.append(f"{year:04d}-{month:02d}")
    return months


def scrape_flights_for_route(origin: str, destination: str) -> list[dict]:
    """Fetch 3 months of daily quotes for one route and normalize them."""
    flights = []
    for month in _target_months():
        entries = get_calendar_prices(origin, destination, month)
        for entry in entries:
            normalized = _normalize_calendar_entry(entry, origin, destination)
            if normalized:
                flights.append(normalized)
    return flights
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_travelpayouts_flights.py -v`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/app/scraper/travelpayouts_flights.py backend/tests/test_travelpayouts_flights.py
git commit -m "feat(scraper): scrape_flights_for_route fetches 3 months from Travelpayouts"
```

---

## Task 5: Add `scrape_flights_for_airport` — filters long-haul for non-CDG

**Why:** Iterates over destinations selected by `route_selector`, filters out long-haul if origin isn't CDG, and aggregates the per-route results.

**Files:**
- Modify: `backend/app/scraper/travelpayouts_flights.py`
- Modify: `backend/tests/test_travelpayouts_flights.py`

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_travelpayouts_flights.py`:

```python
def test_scrape_flights_for_airport_filters_long_haul_from_non_cdg():
    from app.scraper.travelpayouts_flights import scrape_flights_for_airport

    seen_routes = []

    def fake_route(origin, destination):
        seen_routes.append((origin, destination))
        return [{"price": 100.0, "destination": destination}]

    with patch("app.scraper.travelpayouts_flights.get_priority_destinations",
               return_value=["BCN", "JFK", "LIS", "BKK"]), \
         patch("app.scraper.travelpayouts_flights.scrape_flights_for_route", side_effect=fake_route):
        flights = scrape_flights_for_airport("LYS")

    destinations_called = [d for _, d in seen_routes]
    assert "BCN" in destinations_called
    assert "LIS" in destinations_called
    assert "JFK" not in destinations_called  # long-haul, blocked from LYS
    assert "BKK" not in destinations_called  # long-haul, blocked from LYS
    assert len(flights) == 2


def test_scrape_flights_for_airport_keeps_long_haul_from_cdg():
    from app.scraper.travelpayouts_flights import scrape_flights_for_airport

    seen_routes = []

    def fake_route(origin, destination):
        seen_routes.append((origin, destination))
        return [{"price": 100.0, "destination": destination}]

    with patch("app.scraper.travelpayouts_flights.get_priority_destinations",
               return_value=["BCN", "JFK", "BKK"]), \
         patch("app.scraper.travelpayouts_flights.scrape_flights_for_route", side_effect=fake_route):
        flights = scrape_flights_for_airport("CDG")

    destinations_called = [d for _, d in seen_routes]
    assert destinations_called == ["BCN", "JFK", "BKK"]
    assert len(flights) == 3


def test_scrape_flights_for_airport_skips_self_destination():
    from app.scraper.travelpayouts_flights import scrape_flights_for_airport

    seen_routes = []

    def fake_route(origin, destination):
        seen_routes.append((origin, destination))
        return []

    with patch("app.scraper.travelpayouts_flights.get_priority_destinations",
               return_value=["CDG", "BCN"]), \
         patch("app.scraper.travelpayouts_flights.scrape_flights_for_route", side_effect=fake_route):
        scrape_flights_for_airport("CDG")

    destinations_called = [d for _, d in seen_routes]
    assert destinations_called == ["BCN"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_travelpayouts_flights.py -v -k airport`
Expected: 3 FAILs with `ImportError: cannot import name 'scrape_flights_for_airport'`

- [ ] **Step 3: Add `scrape_flights_for_airport`**

Append to `backend/app/scraper/travelpayouts_flights.py`:

```python


def scrape_flights_for_airport(origin: str) -> list[dict]:
    """Scrape all priority destinations for one origin airport.

    Long-haul destinations are only scraped from CDG."""
    destinations = get_priority_destinations(max_count=25)
    all_flights = []
    for dest in destinations:
        if dest == origin:
            continue
        if is_long_haul(dest) and origin != "CDG":
            continue
        try:
            flights = scrape_flights_for_route(origin, dest)
            all_flights.extend(flights)
            if flights:
                logger.info(f"  {origin}->{dest}: {len(flights)} flights")
        except Exception as e:
            logger.warning(f"Failed to scrape {origin}->{dest}: {e}")
    return all_flights
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_travelpayouts_flights.py -v`
Expected: 14 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/app/scraper/travelpayouts_flights.py backend/tests/test_travelpayouts_flights.py
git commit -m "feat(scraper): scrape_flights_for_airport with long-haul CDG-only filter"
```

---

## Task 6: Add `scrape_all_flights` — top-level entry point with rotation

**Why:** This is the function called by `job_scrape_flights`. It must keep the same signature as the old `flights.py:scrape_all_flights` (returns `(flights, errors, baselines)`), so the swap in `jobs.py` is one import change.

**Files:**
- Modify: `backend/app/scraper/travelpayouts_flights.py`
- Modify: `backend/tests/test_travelpayouts_flights.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_travelpayouts_flights.py`:

```python
def test_scrape_all_flights_returns_tuple_of_three():
    from app.scraper.travelpayouts_flights import scrape_all_flights
    import asyncio

    fixed_now = datetime(2026, 4, 12, 10, tzinfo=timezone.utc)

    def fake_airport(origin):
        return [{"origin": origin, "price": 100.0}]

    with patch("app.scraper.travelpayouts_flights.scrape_flights_for_airport", side_effect=fake_airport), \
         patch("app.scraper.travelpayouts_flights._utcnow", return_value=fixed_now), \
         patch("app.scraper.travelpayouts_flights.settings") as mock_settings:
        mock_settings.MVP_AIRPORTS = ["CDG", "ORY", "LYS", "MRS", "NCE", "BOD", "NTE", "TLS"]
        flights, errors, baselines = asyncio.run(scrape_all_flights())

    assert isinstance(flights, list)
    assert isinstance(errors, int)
    assert isinstance(baselines, list)
    assert errors == 0
    assert len(flights) == 2  # AIRPORTS_PER_CYCLE = 2
    assert baselines == []


def test_scrape_all_flights_counts_errors_per_airport():
    from app.scraper.travelpayouts_flights import scrape_all_flights
    import asyncio

    fixed_now = datetime(2026, 4, 12, 10, tzinfo=timezone.utc)

    def fake_airport(origin):
        if origin == "LYS":
            raise RuntimeError("api down")
        return [{"origin": origin, "price": 100.0}]

    with patch("app.scraper.travelpayouts_flights.scrape_flights_for_airport", side_effect=fake_airport), \
         patch("app.scraper.travelpayouts_flights._utcnow", return_value=fixed_now), \
         patch("app.scraper.travelpayouts_flights.settings") as mock_settings:
        mock_settings.MVP_AIRPORTS = ["LYS", "MRS"]
        flights, errors, baselines = asyncio.run(scrape_all_flights())

    assert errors == 1
    assert len(flights) == 1
    assert flights[0]["origin"] == "MRS"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_travelpayouts_flights.py -v -k scrape_all_flights`
Expected: FAIL with `ImportError: cannot import name 'scrape_all_flights'`

- [ ] **Step 3: Add `scrape_all_flights` with rotation**

Append to `backend/app/scraper/travelpayouts_flights.py`:

```python


async def scrape_all_flights() -> tuple[list[dict], int, list[dict]]:
    """Top-level scraper. Rotates over MVP_AIRPORTS using current hour.

    Signature kept compatible with the legacy flights.py module:
    returns (flights, errors, baselines). Baselines are always empty
    here — they are populated by job_travelpayouts_enrichment instead."""
    airports = settings.MVP_AIRPORTS
    hour = _utcnow().hour
    cycle_index = hour // 4  # 0..5, changes every 4 hours
    start_idx = (cycle_index * AIRPORTS_PER_CYCLE) % len(airports)
    cycle_airports = [
        airports[(start_idx + i) % len(airports)]
        for i in range(AIRPORTS_PER_CYCLE)
    ]

    logger.info(f"Cycle (hour={hour}, idx={cycle_index}): scraping airports {cycle_airports}")

    all_flights = []
    errors = 0
    for airport in cycle_airports:
        try:
            flights = scrape_flights_for_airport(airport)
            all_flights.extend(flights)
            logger.info(f"Scraped {len(flights)} flights from {airport}")
        except Exception as e:
            errors += 1
            logger.error(f"Failed to scrape flights from {airport}: {e}")

    return all_flights, errors, []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_travelpayouts_flights.py -v`
Expected: 16 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/app/scraper/travelpayouts_flights.py backend/tests/test_travelpayouts_flights.py
git commit -m "feat(scraper): scrape_all_flights entry point with airport rotation"
```

---

## Task 7: Switch jobs.py to the new module

**Why:** Wire the new scraper into the scheduled job. This is the moment the production behavior changes.

**Files:**
- Modify: `backend/app/scheduler/jobs.py`

- [ ] **Step 1: Update the top-level import**

In `backend/app/scheduler/jobs.py`, change line 5:

```python
# Before:
from app.scraper.flights import scrape_all_flights

# After:
from app.scraper.travelpayouts_flights import scrape_all_flights
```

- [ ] **Step 2: Update the three local imports of `_window_label`**

There are three local imports of `_window_label` inside `jobs.py`:
- Line 132 (inside `_analyze_new_flights`)
- Line 282 (inside `job_scrape_accommodations`)
- Line 496 (inside `job_travelpayouts_enrichment`)

Change each one from:

```python
from app.scraper.flights import _window_label
```

to:

```python
from app.scraper.travelpayouts_flights import _window_label
```

- [ ] **Step 3: Verify nothing else imports from `app.scraper.flights`**

Run: `cd backend && grep -rn "from app.scraper.flights" app/ tests/`
Expected: zero matches.

- [ ] **Step 4: Run the existing job tests**

Run: `cd backend && pytest tests/test_jobs.py -v`
Expected: PASS (or any failure must be unrelated to imports — investigate before continuing).

- [ ] **Step 5: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/app/scheduler/jobs.py
git commit -m "feat(scheduler): switch flight scraper to travelpayouts_flights"
```

---

## Task 8: Delete the old flight scraper code

**Why:** Now that nothing references `flights.py` or `browser/google_flights.py`, we can delete them. We do NOT touch `accommodations.py`, `apify_client.py`, `browser/google_hotels.py`, or `browser/stealth.py` — they belong to the hotel pipeline and stay.

**Files:**
- Delete: `backend/app/scraper/flights.py`
- Delete: `backend/app/scraper/browser/google_flights.py`

- [ ] **Step 1: Confirm there are no remaining references**

Run: `cd backend && grep -rn "scraper.flights\|browser.google_flights" app/ tests/`
Expected: zero matches.

- [ ] **Step 2: Delete the two files**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
rm backend/app/scraper/flights.py
rm backend/app/scraper/browser/google_flights.py
```

- [ ] **Step 3: Run the full backend test suite**

Run: `cd backend && pytest -v`
Expected: all tests pass. If any test fails because it imported from the deleted modules, update the test to import from `app.scraper.travelpayouts_flights` instead, then re-run.

- [ ] **Step 4: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add -A backend/app/scraper/flights.py backend/app/scraper/browser/google_flights.py
git commit -m "chore: remove obsolete Google Flights scraper (Playwright + Apify)"
```

---

## Task 9: End-to-end smoke test against the live Travelpayouts API

**Why:** Unit tests mock everything. Before declaring victory, hit the real API once locally to confirm the full pipeline produces non-empty data.

**Files:**
- None modified. This is a manual verification step.

- [ ] **Step 1: Run an in-process scrape against the live API**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend
python -c "
import asyncio
from app.scraper.travelpayouts_flights import scrape_flights_for_route

flights = scrape_flights_for_route('CDG', 'JFK')
print(f'Got {len(flights)} flights')
for f in flights[:3]:
    print(f)
"
```

Expected: at least 5 flights printed, each with `price > 0`, `departure_date`, `return_date`, `source == 'travelpayouts'`. If you get zero flights, check that `TRAVELPAYOUT_API_KEY` is set in `backend/.env` and that the test for `get_calendar_prices` still passes.

- [ ] **Step 2: Run a full airport rotation locally**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend
python -c "
import asyncio
from app.scraper.travelpayouts_flights import scrape_all_flights

flights, errors, baselines = asyncio.run(scrape_all_flights())
print(f'Total: {len(flights)} flights, {errors} errors')
"
```

Expected: at least ~50 flights, 0 errors. If you see errors, read the log line that named the failing airport and investigate before deploying.

- [ ] **Step 3: Run the full test suite once more**

Run: `cd backend && pytest -v`
Expected: all green.

---

## Task 10: Deploy and verify in production

**Why:** Confirm the fix works on Railway with the real cron schedule.

**Files:**
- None.

- [ ] **Step 1: Push to main**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git push origin main
```

- [ ] **Step 2: Watch the Railway deploy**

Watch the Railway dashboard for the new deploy to go green. Build should be a bit faster than before because nothing playwright-specific changed (we still install it for hotels, so build time is similar).

- [ ] **Step 3: Trigger a manual flight scrape**

```bash
curl -X POST "https://globagenius-production-b887.up.railway.app/api/trigger/scrape_flights" \
  -H "X-Admin-Key: $ADMIN_API_KEY"
```

Expected: `{"status": "triggered", "job": "scrape_flights"}`.

- [ ] **Step 4: Watch the next entry in `/api/status`**

After ~2 minutes:

```bash
curl -s "https://globagenius-production-b887.up.railway.app/api/status" | python3 -m json.tool | head -30
```

Expected: the most recent `recent_scrapes[0]` has `items_count > 0`, `errors_count == 0`, `source == "google_flights"` (the source label in `scrape_logs` is hardcoded — that's a separate cleanup if you want).

- [ ] **Step 5: Confirm Telegram alert path**

If qualified deals exist, the existing pipeline will fire Telegram alerts. Watch the admin chat for the next ~30 minutes to confirm at least one alert lands.

---

## Self-Review

**Spec coverage check:**
- ✅ "Nouveau module `app/scraper/travelpayouts_flights.py`" → Tasks 3-6
- ✅ "Long-courrier uniquement depuis CDG" → Task 1 (rule) + Task 5 (enforcement)
- ✅ "Suppression de flights.py et browser/google_flights.py" → Task 8
- ✅ "Conservation d'apify_client / browser/google_hotels / stealth pour hôtels" → explicit in Task 8
- ✅ "Mapping calendar entry → raw_flights" → Task 3
- ✅ "Saisonnalité conservée" → Task 5 uses `get_priority_destinations`
- ✅ "Signature `scrape_all_flights` compatible" → Task 6 returns `(list, int, list)`
- ✅ "Déploiement et vérification" → Tasks 9 + 10
- ✅ Tests listés dans le spec : `test_scrape_route_calendar_parses_response` (Task 2), `test_scrape_route_calendar_handles_empty_data` (Task 2), `test_scrape_route_calendar_handles_api_error` (Task 2 — covered by `_get` returning None), `test_scrape_flights_for_route_iterates_months` (Task 4), `test_scrape_flights_for_airport_filters_long_haul` (Task 5), `test_scrape_flights_for_airport_includes_long_haul_from_cdg` (Task 5), `test_normalize_calendar_entry_to_raw_flight` (Task 3), `test_scrape_all_flights_signature_compatible` (Task 6).
- ✅ "Marker affilié hors scope" → no marker logic added; URL builder doesn't include marker.

**Type consistency check:**
- `scrape_flights_for_route` is sync (uses `httpx.Client`, no `await`) — consistent across Tasks 4-6.
- `scrape_all_flights` is `async` to keep parity with the old signature called from APScheduler — consistent.
- `_normalize_calendar_entry` returns `dict | None` — checked in `scrape_flights_for_route` before extending.
- `get_calendar_prices` returns `list[dict]` (Task 2) — consumed by `scrape_flights_for_route` (Task 4) as a list.

**Placeholder scan:** No TBD/TODO/"appropriate"/"similar to". All code blocks are concrete.

**Plan is complete.**
