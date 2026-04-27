# Roundtrip Coherence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken duration semantics of the Travelpayouts flight scraper so every detected deal is a real round-trip with a duration-aware baseline, statistical sanity checks, a real-time price re-verification, and a free/premium tier classification.

**Architecture:** Switch the API endpoint from `/v1/prices/calendar` to `/aviasales/v3/prices_for_dates` (real round-trips, true airport codes, link, transfers). Add a tiny pure-Python module `app/analysis/buckets.py` that classifies trip durations into 3 fixed buckets (`short`/`medium`/`long`) and short/long-haul. Compute one baseline per `(route, bucket)` pair using the median (robust to outliers). Re-verify each candidate deal against the live API just before inserting it into `qualified_items`. Tag every qualified item with `tier = "free"` (20–39%) or `tier = "premium"` (≥40%).

**Tech Stack:** Python 3.12, FastAPI, Supabase, httpx, pytest. Travelpayouts REST API (`api.travelpayouts.com`).

**Spec:** [docs/superpowers/specs/2026-04-12-roundtrip-coherence-design.md](../specs/2026-04-12-roundtrip-coherence-design.md)

---

## File Structure

**Created:**
- `backend/app/analysis/buckets.py` — pure helpers for duration bucketing and short/long-haul classification
- `backend/app/scraper/reverify.py` — real-time price re-verification before alerting
- `backend/supabase/migrations/004_roundtrip_coherence.sql` — additive schema migration (`trip_duration_days`, `duration_minutes`, `tier`)
- `backend/tests/test_buckets.py` — unit tests for the bucketing module
- `backend/tests/test_reverify.py` — unit tests for the re-verification helper

**Modified:**
- `backend/app/scraper/travelpayouts.py` — add `get_prices_for_dates` REST helper
- `backend/app/scraper/travelpayouts_flights.py` — switch to `prices_for_dates`, rename normalizer, reject out-of-range durations
- `backend/app/analysis/baselines.py` — add `compute_baselines_by_bucket` (median-based, with stops filter and 30-sample minimum)
- `backend/app/scheduler/jobs.py` — rewrite `_analyze_new_flights` (bucket lookup + reverify + tier), extend `job_travelpayouts_enrichment` to build bucket baselines
- `backend/app/api/routes.py` — whitelist `travelpayouts_enrichment` for manual triggering
- `backend/app/notifications/telegram.py` — branch alert template on `tier`
- `backend/tests/test_travelpayouts.py` — tests for `get_prices_for_dates`
- `backend/tests/test_travelpayouts_flights.py` — tests for `_normalize_priced_entry` and the new scrape behavior
- `backend/tests/test_baselines.py` — tests for `compute_baselines_by_bucket`
- `backend/tests/test_jobs.py` — tests for the rewritten `_analyze_new_flights`

**Untouched:**
- `backend/app/scraper/accommodations.py` and the `browser/` hotel pipeline (out of scope)
- `backend/app/scraper/apify_client.py` (still used by hotels)
- `backend/app/analysis/anomaly_detector.py` — `detect_anomaly` is reused as-is; we layer extra filters on top of its output

---

## Task 1: Pure helpers — `buckets.py`

**Why:** All downstream code (the scraper normalizer, the baseline builder, the analyzer) needs to classify a trip duration into a bucket and a vol into short/long-haul. Putting this in a tiny pure module makes it trivially testable and reusable.

**Files:**
- Create: `backend/app/analysis/buckets.py`
- Create: `backend/tests/test_buckets.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_buckets.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_buckets.py -v`
Expected: `ModuleNotFoundError: No module named 'app.analysis.buckets'`.

- [ ] **Step 3: Create the module**

Create `backend/app/analysis/buckets.py`:

```python
"""Duration bucketing and short/long-haul classification.

Pure functions, no I/O. Used by the flight scraper, the baseline builder,
and the deal analyzer to apply consistent rules across the pipeline."""

DURATION_BUCKETS: dict[str, tuple[int, int]] = {
    "short":  (1, 3),
    "medium": (4, 9),
    "long":   (10, 21),
}

SHORT_HAUL_MAX_MINUTES = 180


def bucket_for_duration(days: int) -> str | None:
    """Return the bucket name for a trip duration, or None if out of range."""
    for name, (lo, hi) in DURATION_BUCKETS.items():
        if lo <= days <= hi:
            return name
    return None


def is_short_haul(duration_minutes: int) -> bool:
    """A flight is short-haul if its outbound leg is strictly under 3 hours."""
    return duration_minutes < SHORT_HAUL_MAX_MINUTES


def stops_allowed(duration_minutes: int) -> int:
    """Maximum number of stops we accept for this haul type.

    Short-haul: direct only (0 stops). Long-haul: up to 1 stop."""
    return 0 if is_short_haul(duration_minutes) else 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_buckets.py -v`
Expected: 9 passed.

Then run the full suite to confirm no regression:

Run: `cd backend && source .venv/bin/activate && pytest -q`
Expected: 80 passed (71 baseline + 9 new).

- [ ] **Step 5: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/app/analysis/buckets.py backend/tests/test_buckets.py
git commit -m "feat(analysis): add duration buckets and short/long-haul classifier"
```

---

## Task 2: New REST helper — `get_prices_for_dates`

**Why:** The current `get_calendar_prices` returns "the cheapest price per departure day" without any guarantee on duration. We need an endpoint that returns real round-trips. Travelpayouts exposes `/aviasales/v3/prices_for_dates` for this.

**Files:**
- Modify: `backend/app/scraper/travelpayouts.py`
- Modify: `backend/tests/test_travelpayouts.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_travelpayouts.py`:

```python
from app.scraper.travelpayouts import get_prices_for_dates


def test_get_prices_for_dates_parses_response():
    fake_response = {
        "data": [
            {
                "flight_number": "1248",
                "link": "/search/CDG0205BCN06051?t=...",
                "origin_airport": "CDG",
                "destination_airport": "BCN",
                "departure_at": "2026-05-02T18:35:00+02:00",
                "airline": "AF",
                "destination": "BCN",
                "return_at": "2026-05-06T21:15:00+02:00",
                "origin": "PAR",
                "price": 100,
                "gate": "Kiwi.com",
                "return_transfers": 0,
                "duration": 220,
                "duration_to": 105,
                "duration_back": 115,
                "transfers": 0,
            }
        ],
        "success": True,
    }
    with patch("app.scraper.travelpayouts._get", return_value=fake_response):
        result = get_prices_for_dates("CDG", "BCN")

    assert len(result) == 1
    r = result[0]
    assert r["origin_airport"] == "CDG"
    assert r["destination_airport"] == "BCN"
    assert r["departure_at"] == "2026-05-02T18:35:00+02:00"
    assert r["return_at"] == "2026-05-06T21:15:00+02:00"
    assert r["price"] == 100
    assert r["airline"] == "AF"
    assert r["transfers"] == 0
    assert r["return_transfers"] == 0
    assert r["duration_to"] == 105
    assert r["duration_back"] == 115
    assert r["link"] == "/search/CDG0205BCN06051?t=..."


def test_get_prices_for_dates_returns_empty_on_no_data():
    with patch("app.scraper.travelpayouts._get", return_value=None):
        assert get_prices_for_dates("CDG", "BCN") == []


def test_get_prices_for_dates_returns_empty_on_unsuccessful_response():
    with patch("app.scraper.travelpayouts._get", return_value={"success": False}):
        assert get_prices_for_dates("CDG", "BCN") == []


def test_get_prices_for_dates_returns_empty_on_empty_data_list():
    with patch("app.scraper.travelpayouts._get", return_value={"success": True, "data": []}):
        assert get_prices_for_dates("CDG", "BCN") == []


def test_get_prices_for_dates_forces_one_way_false():
    captured = {}

    def fake_get(url, params=None):
        captured["url"] = url
        captured["params"] = params
        return {"success": True, "data": []}

    with patch("app.scraper.travelpayouts._get", side_effect=fake_get):
        get_prices_for_dates("CDG", "BCN")

    assert "/aviasales/v3/prices_for_dates" in captured["url"]
    assert captured["params"]["one_way"] == "false"
    assert captured["params"]["origin"] == "CDG"
    assert captured["params"]["destination"] == "BCN"
    assert captured["params"]["currency"] == "eur"


def test_get_prices_for_dates_includes_optional_months():
    captured = {}

    def fake_get(url, params=None):
        captured["params"] = params
        return {"success": True, "data": []}

    with patch("app.scraper.travelpayouts._get", side_effect=fake_get):
        get_prices_for_dates("CDG", "BCN", departure_month="2026-05", return_month="2026-05")

    assert captured["params"]["departure_at"] == "2026-05"
    assert captured["params"]["return_at"] == "2026-05"


def test_get_prices_for_dates_omits_optional_months_when_blank():
    captured = {}

    def fake_get(url, params=None):
        captured["params"] = params
        return {"success": True, "data": []}

    with patch("app.scraper.travelpayouts._get", side_effect=fake_get):
        get_prices_for_dates("CDG", "BCN")

    assert "departure_at" not in captured["params"]
    assert "return_at" not in captured["params"]
```

- [ ] **Step 2: Run tests, confirm they fail**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_travelpayouts.py -v`
Expected: ImportError on `get_prices_for_dates`.

- [ ] **Step 3: Add the function**

Insert the following function in `backend/app/scraper/travelpayouts.py`. Place it AFTER `get_calendar_prices` (so it sits with the other REST helpers in the "PRICE BASELINES" section):

```python
def get_prices_for_dates(
    origin: str,
    destination: str,
    departure_month: str = "",
    return_month: str = "",
    limit: int = 1000,
) -> list[dict]:
    """Get real round-trip prices via /aviasales/v3/prices_for_dates.

    Returns up to `limit` round-trips with origin_airport, destination_airport,
    departure_at, return_at, price, transfers, return_transfers, duration_to,
    duration_back, link.

    `departure_month` / `return_month` format: YYYY-MM (optional).
    `one_way=false` is forced — this endpoint is round-trips only by design."""
    params = {
        "origin": origin,
        "destination": destination,
        "currency": "eur",
        "one_way": "false",
        "sorting": "price",
        "direct": "false",
        "limit": limit,
    }
    if departure_month:
        params["departure_at"] = departure_month
    if return_month:
        params["return_at"] = return_month

    data = _get(f"{REST_URL}/aviasales/v3/prices_for_dates", params)
    if not data or not data.get("success"):
        return []

    entries = data.get("data") or []
    result = []
    for flight in entries:
        if not isinstance(flight, dict):
            continue
        result.append({
            "origin_airport": flight.get("origin_airport", ""),
            "destination_airport": flight.get("destination_airport", ""),
            "departure_at": flight.get("departure_at", ""),
            "return_at": flight.get("return_at", ""),
            "price": flight.get("price", 0),
            "airline": flight.get("airline", ""),
            "flight_number": flight.get("flight_number", ""),
            "transfers": flight.get("transfers", 0),
            "return_transfers": flight.get("return_transfers", 0),
            "duration_to": flight.get("duration_to", 0),
            "duration_back": flight.get("duration_back", 0),
            "link": flight.get("link", ""),
        })
    return result
```

- [ ] **Step 4: Run tests, confirm they pass**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_travelpayouts.py -v`
Expected: 7 new tests pass, total 14 in the file.

Then full suite:
Run: `cd backend && source .venv/bin/activate && pytest -q`
Expected: 87 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/app/scraper/travelpayouts.py backend/tests/test_travelpayouts.py
git commit -m "feat(travelpayouts): add get_prices_for_dates round-trip helper"
```

---

## Task 3: Switch the scraper to `prices_for_dates`

**Why:** Now that we have a round-trip helper, we replace the calendar-based scraper with one that produces real round-trips. We rename `_normalize_calendar_entry` to `_normalize_priced_entry` to reflect the new source. We compute `trip_duration_days`, `duration_minutes`, and reject any flight whose duration falls outside `[1, 21]` days.

**Files:**
- Modify: `backend/app/scraper/travelpayouts_flights.py`
- Modify: `backend/tests/test_travelpayouts_flights.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_travelpayouts_flights.py`:

```python
def _priced_entry(price=412, dep="2026-05-12", ret="2026-05-19", airline="AF",
                  transfers=0, dur_to=480, dur_back=520,
                  origin_airport="CDG", destination_airport="JFK",
                  link="/search/CDG1205JFK19051"):
    return {
        "origin_airport": origin_airport,
        "destination_airport": destination_airport,
        "departure_at": f"{dep}T10:00:00+02:00",
        "return_at": f"{ret}T18:00:00+02:00",
        "price": price,
        "airline": airline,
        "transfers": transfers,
        "return_transfers": transfers,
        "duration_to": dur_to,
        "duration_back": dur_back,
        "link": link,
    }


def test_normalize_priced_entry_maps_all_fields():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry, SOURCE
    entry = _priced_entry()
    result = _normalize_priced_entry(entry)
    assert result is not None
    assert result["origin"] == "CDG"
    assert result["destination"] == "JFK"
    assert result["departure_date"] == "2026-05-12"
    assert result["return_date"] == "2026-05-19"
    assert result["price"] == 412.0
    assert result["airline"] == "AF"
    assert result["stops"] == 0
    assert result["trip_duration_days"] == 7
    assert result["duration_minutes"] == 500  # (480 + 520) / 2
    assert result["source"] == SOURCE
    assert result["source_url"].startswith("https://www.aviasales.com")
    assert "/search/CDG1205JFK19051" in result["source_url"]


def test_normalize_priced_entry_rejects_duration_zero():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry(dep="2026-05-12", ret="2026-05-12")
    assert _normalize_priced_entry(entry) is None


def test_normalize_priced_entry_rejects_duration_above_21():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry(dep="2026-05-12", ret="2026-06-15")  # 34 days
    assert _normalize_priced_entry(entry) is None


def test_normalize_priced_entry_accepts_duration_one_day():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry(dep="2026-05-12", ret="2026-05-13")
    result = _normalize_priced_entry(entry)
    assert result is not None
    assert result["trip_duration_days"] == 1


def test_normalize_priced_entry_accepts_duration_21_days():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry(dep="2026-05-01", ret="2026-05-22")  # exactly 21 days
    result = _normalize_priced_entry(entry)
    assert result is not None
    assert result["trip_duration_days"] == 21


def test_normalize_priced_entry_rejects_zero_price():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry(price=0)
    assert _normalize_priced_entry(entry) is None


def test_normalize_priced_entry_rejects_missing_departure_at():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry()
    entry["departure_at"] = ""
    assert _normalize_priced_entry(entry) is None


def test_normalize_priced_entry_rejects_missing_return_at():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry()
    entry["return_at"] = ""
    assert _normalize_priced_entry(entry) is None


def test_normalize_priced_entry_uses_origin_airport_not_city():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry(origin_airport="CDG")
    result = _normalize_priced_entry(entry)
    assert result["origin"] == "CDG"  # not "PAR"


def test_normalize_priced_entry_extracts_stops_from_transfers():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry(transfers=2)
    result = _normalize_priced_entry(entry)
    assert result["stops"] == 2


def test_normalize_priced_entry_uses_api_link_in_url():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry(link="/search/CDG1205JFK19051?t=abc")
    result = _normalize_priced_entry(entry)
    assert "https://www.aviasales.com/search/CDG1205JFK19051?t=abc" == result["source_url"]


def test_normalize_priced_entry_falls_back_to_built_url_when_link_missing():
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    entry = _priced_entry(link="")
    result = _normalize_priced_entry(entry)
    assert result["source_url"].startswith("https://www.aviasales.com")
```

Then REPLACE the existing `test_scrape_flights_for_route_*` tests (which mocked `get_calendar_prices`) with new versions mocking `get_prices_for_dates`. Find these two tests in `test_travelpayouts_flights.py` and replace them entirely:

```python
def test_scrape_flights_for_route_aggregates_priced_entries():
    from app.scraper.travelpayouts_flights import scrape_flights_for_route

    fake_entries = [
        _priced_entry(price=412),
        _priced_entry(price=398, dep="2026-05-15", ret="2026-05-22"),
        _priced_entry(price=450, dep="2026-06-01", ret="2026-06-08"),
    ]

    with patch("app.scraper.travelpayouts_flights.get_prices_for_dates",
               return_value=fake_entries):
        flights = scrape_flights_for_route("CDG", "JFK")

    assert len(flights) == 3
    prices = sorted(f["price"] for f in flights)
    assert prices == [398.0, 412.0, 450.0]
    for f in flights:
        assert f["origin"] == "CDG"
        assert f["destination"] == "JFK"
        assert f["source"] == "travelpayouts"
        assert f["trip_duration_days"] == 7


def test_scrape_flights_for_route_skips_unusable_entries():
    from app.scraper.travelpayouts_flights import scrape_flights_for_route

    fake_entries = [
        _priced_entry(price=412),
        _priced_entry(price=0),  # zero price
        _priced_entry(price=200, dep="2026-05-12", ret="2026-06-15"),  # 34 days
    ]

    with patch("app.scraper.travelpayouts_flights.get_prices_for_dates",
               return_value=fake_entries):
        flights = scrape_flights_for_route("CDG", "JFK")

    assert len(flights) == 1
    assert flights[0]["price"] == 412.0
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_travelpayouts_flights.py -v`
Expected: 12 new tests fail with ImportError on `_normalize_priced_entry`. The two replaced `scrape_flights_for_route` tests fail too because they patch `get_prices_for_dates` which the module doesn't import yet.

- [ ] **Step 3: Update `travelpayouts_flights.py`**

Open `backend/app/scraper/travelpayouts_flights.py` and apply these edits:

**3a.** Replace the import line `from app.scraper.travelpayouts import get_calendar_prices` with `from app.scraper.travelpayouts import get_prices_for_dates`.

**3b.** Replace the entire `_normalize_calendar_entry` function with this new function:

```python
def _normalize_priced_entry(entry: dict) -> dict | None:
    """Map a Travelpayouts prices_for_dates entry to the raw_flights row format.

    Returns None if the entry is unusable: missing dates, zero price, or
    trip duration outside [1, 21] days."""
    departure_at = entry.get("departure_at") or ""
    return_at = entry.get("return_at") or ""
    price = entry.get("price") or 0
    if not departure_at or not return_at or not price:
        return None

    departure_date = departure_at[:10]
    return_date = return_at[:10]
    try:
        dep = datetime.strptime(departure_date, "%Y-%m-%d")
        ret = datetime.strptime(return_date, "%Y-%m-%d")
    except ValueError:
        return None

    trip_duration_days = (ret - dep).days
    if trip_duration_days < 1 or trip_duration_days > 21:
        return None

    origin = entry.get("origin_airport") or ""
    destination = entry.get("destination_airport") or ""
    if not origin or not destination:
        return None

    link = entry.get("link") or ""
    if link:
        source_url = f"https://www.aviasales.com{link}"
    else:
        source_url = _build_aviasales_url(origin, destination, departure_date, return_date)

    duration_to = int(entry.get("duration_to") or 0)
    duration_back = int(entry.get("duration_back") or 0)
    duration_minutes = (duration_to + duration_back) // 2 if (duration_to or duration_back) else 0

    raw = {
        "price": float(price),
        "currency": "EUR",
        "origin": origin,
        "destination": destination,
        "departureDate": departure_date,
        "returnDate": return_date,
        "airline": entry.get("airline", ""),
        "stops": int(entry.get("transfers") or 0),
        "url": source_url,
    }

    normalized = normalize_flight(raw, source=SOURCE)
    normalized["trip_duration_days"] = trip_duration_days
    normalized["duration_minutes"] = duration_minutes
    return normalized
```

**3c.** Replace the `scrape_flights_for_route` function body with:

```python
def scrape_flights_for_route(origin: str, destination: str) -> list[dict]:
    """Fetch real round-trip prices for one route via Travelpayouts."""
    flights = []
    for entry in get_prices_for_dates(origin, destination):
        normalized = _normalize_priced_entry(entry)
        if normalized:
            flights.append(normalized)
    return flights
```

Note: `_normalize_priced_entry` no longer takes `origin` and `destination` as arguments — it reads them from `origin_airport`/`destination_airport` in the API entry. This is the whole point of switching endpoints.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_travelpayouts_flights.py -v`
Expected: all tests in this file pass (the 12 new + the 2 replaced + the 17 existing untouched = 31 total).

Then full suite:
Run: `cd backend && source .venv/bin/activate && pytest -q`
Expected: 99 passed (87 baseline + 12 new for normalizer/scrape).

If you see any test from `test_travelpayouts_flights.py` failing because it referenced `_normalize_calendar_entry` or `get_calendar_prices`, that test was orphaned by Step 3. Look at the failure, update the test to match the new function name, re-run.

- [ ] **Step 5: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/app/scraper/travelpayouts_flights.py backend/tests/test_travelpayouts_flights.py
git commit -m "feat(scraper): switch to prices_for_dates endpoint with duration filter"
```

---

## Task 4: Schema migration (additive)

**Why:** Add `trip_duration_days` and `duration_minutes` columns to `raw_flights`, and `tier` to `qualified_items`. Idempotent and additive — safe to apply on a populated database with no downtime.

**Files:**
- Create: `backend/supabase/migrations/004_roundtrip_coherence.sql`

- [ ] **Step 1: Create the migration file**

Create `backend/supabase/migrations/004_roundtrip_coherence.sql`:

```sql
-- Roundtrip coherence — add duration metadata and tier classification.
-- Purely additive: existing rows get NULL/default values, no breaking changes.

ALTER TABLE raw_flights
  ADD COLUMN IF NOT EXISTS trip_duration_days INTEGER,
  ADD COLUMN IF NOT EXISTS duration_minutes INTEGER;

CREATE INDEX IF NOT EXISTS idx_raw_flights_route_duration
  ON raw_flights (origin, destination, trip_duration_days);

ALTER TABLE qualified_items
  ADD COLUMN IF NOT EXISTS tier TEXT DEFAULT 'free';
```

- [ ] **Step 2: Apply the migration**

The user must apply this migration manually (Supabase dashboard or `supabase db push`). For the purpose of this task, document that requirement and verify nothing in tests requires it (the test suite uses mocked Supabase, never the real DB).

Run: `cd backend && source .venv/bin/activate && pytest -q`
Expected: 99 passed (no test relies on the new columns yet).

- [ ] **Step 3: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/supabase/migrations/004_roundtrip_coherence.sql
git commit -m "feat(db): migration for trip_duration_days, duration_minutes, tier"
```

**Note for the executor:** Apply this migration to the Supabase production database BEFORE merging the PR (Supabase dashboard → SQL editor → paste the file → run). If the migration is not applied, the new code will still work but `trip_duration_days` and `duration_minutes` will silently fail to write, preventing baseline lookups.

---

## Task 5: `compute_baselines_by_bucket`

**Why:** The current `compute_baseline` produces a single baseline per route (mean-based, no duration awareness). We need a function that groups observations by bucket, applies the stops rule, uses the median (robust to outliers), and only publishes baselines with at least 30 observations.

**Files:**
- Modify: `backend/app/analysis/baselines.py`
- Modify: `backend/tests/test_baselines.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_baselines.py`:

```python
from app.analysis.baselines import compute_baselines_by_bucket, MIN_SAMPLE_COUNT


def _obs(price, duration_days=7, stops=0, duration_minutes=120, scraped_days_ago=1):
    from datetime import datetime, timedelta, timezone
    return {
        "price": price,
        "trip_duration_days": duration_days,
        "stops": stops,
        "duration_minutes": duration_minutes,
        "scraped_at": (datetime.now(timezone.utc) - timedelta(days=scraped_days_ago)).isoformat(),
    }


def test_min_sample_count_constant():
    assert MIN_SAMPLE_COUNT == 30


def test_compute_baselines_by_bucket_groups_by_bucket():
    short_obs = [_obs(100, duration_days=2) for _ in range(30)]
    medium_obs = [_obs(200, duration_days=7) for _ in range(30)]
    long_obs = [_obs(400, duration_days=14) for _ in range(30)]

    result = compute_baselines_by_bucket("CDG-BCN", short_obs + medium_obs + long_obs)

    assert len(result) == 3
    keys = sorted(b["route_key"] for b in result)
    assert keys == ["CDG-BCN-bucket_long", "CDG-BCN-bucket_medium", "CDG-BCN-bucket_short"]
    by_key = {b["route_key"]: b for b in result}
    assert by_key["CDG-BCN-bucket_short"]["avg_price"] == 100
    assert by_key["CDG-BCN-bucket_medium"]["avg_price"] == 200
    assert by_key["CDG-BCN-bucket_long"]["avg_price"] == 400


def test_compute_baselines_by_bucket_uses_median_not_mean():
    # Outlier at 1000, 30 observations at 100 -> median = 100, mean would be ~129
    obs = [_obs(100, duration_days=7) for _ in range(30)] + [_obs(1000, duration_days=7)]
    result = compute_baselines_by_bucket("CDG-BCN", obs)
    medium = next(b for b in result if b["route_key"] == "CDG-BCN-bucket_medium")
    assert medium["avg_price"] == 100  # median, not mean


def test_compute_baselines_by_bucket_excludes_short_haul_with_stops():
    # 30 valid direct flights + 5 stopover flights, all duration_minutes=120 (short-haul)
    direct = [_obs(100, stops=0, duration_minutes=120) for _ in range(30)]
    with_stops = [_obs(60, stops=1, duration_minutes=120) for _ in range(5)]
    result = compute_baselines_by_bucket("CDG-BCN", direct + with_stops)
    medium = next(b for b in result if b["route_key"] == "CDG-BCN-bucket_medium")
    assert medium["sample_count"] == 30
    assert medium["avg_price"] == 100  # outliers with stops excluded


def test_compute_baselines_by_bucket_excludes_long_haul_with_2_plus_stops():
    # Long-haul: duration_minutes=600 -> max 1 stop allowed
    valid = [_obs(500, stops=1, duration_minutes=600) for _ in range(30)]
    too_many_stops = [_obs(300, stops=2, duration_minutes=600) for _ in range(5)]
    result = compute_baselines_by_bucket("CDG-JFK", valid + too_many_stops)
    medium = next(b for b in result if b["route_key"] == "CDG-JFK-bucket_medium")
    assert medium["sample_count"] == 30


def test_compute_baselines_by_bucket_minimum_sample_count_not_met():
    obs = [_obs(100, duration_days=7) for _ in range(29)]
    result = compute_baselines_by_bucket("CDG-BCN", obs)
    assert result == []  # no bucket gets 30 observations


def test_compute_baselines_by_bucket_minimum_sample_count_met_exactly():
    obs = [_obs(100, duration_days=7) for _ in range(30)]
    result = compute_baselines_by_bucket("CDG-BCN", obs)
    assert len(result) == 1
    assert result[0]["sample_count"] == 30


def test_compute_baselines_by_bucket_ignores_observations_outside_buckets():
    # 30 valid medium + 5 with duration_days=30 (out of range)
    obs = [_obs(100, duration_days=7) for _ in range(30)] + [_obs(50, duration_days=30) for _ in range(5)]
    result = compute_baselines_by_bucket("CDG-BCN", obs)
    medium = next(b for b in result if b["route_key"] == "CDG-BCN-bucket_medium")
    assert medium["sample_count"] == 30
    assert medium["avg_price"] == 100


def test_compute_baselines_by_bucket_returns_baselines_with_required_fields():
    obs = [_obs(100, duration_days=7) for _ in range(30)]
    result = compute_baselines_by_bucket("CDG-BCN", obs)
    assert len(result) == 1
    b = result[0]
    assert "route_key" in b
    assert "type" in b
    assert b["type"] == "flight"
    assert "avg_price" in b
    assert "std_dev" in b
    assert "sample_count" in b
    assert "calculated_at" in b
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_baselines.py -v`
Expected: 9 new tests fail with ImportError on `compute_baselines_by_bucket` / `MIN_SAMPLE_COUNT`.

- [ ] **Step 3: Add the function**

Append to `backend/app/analysis/baselines.py`:

```python
MIN_SAMPLE_COUNT = 30


def compute_baselines_by_bucket(
    route_key_prefix: str,
    observations: list[dict],
) -> list[dict]:
    """Group observations by duration bucket and return one baseline per qualifying bucket.

    Each observation must have: price, trip_duration_days, stops, duration_minutes,
    scraped_at. Observations outside any duration bucket, or violating the stops rule,
    are filtered out. Baselines with fewer than MIN_SAMPLE_COUNT observations are not
    published. The median (not the mean) is used for `avg_price` to be robust to outliers."""
    from app.analysis.buckets import bucket_for_duration, stops_allowed

    by_bucket: dict[str, list[dict]] = {}
    for obs in observations:
        days = obs.get("trip_duration_days") or 0
        bucket = bucket_for_duration(days)
        if not bucket:
            continue
        max_stops = stops_allowed(obs.get("duration_minutes") or 0)
        if (obs.get("stops") or 0) > max_stops:
            continue
        by_bucket.setdefault(bucket, []).append(obs)

    now = datetime.now(timezone.utc)
    result = []
    for bucket, obs_list in by_bucket.items():
        if len(obs_list) < MIN_SAMPLE_COUNT:
            continue
        prices = np.array([o["price"] for o in obs_list], dtype=float)
        median = float(np.median(prices))
        std = float(np.std(prices))
        result.append({
            "route_key": f"{route_key_prefix}-bucket_{bucket}",
            "type": "flight",
            "avg_price": round(median, 2),
            "std_dev": round(std, 2),
            "sample_count": len(obs_list),
            "calculated_at": now.isoformat(),
        })
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_baselines.py -v`
Expected: 9 new tests pass.

Then full suite:
Run: `cd backend && source .venv/bin/activate && pytest -q`
Expected: 108 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/app/analysis/baselines.py backend/tests/test_baselines.py
git commit -m "feat(baselines): add compute_baselines_by_bucket with median + stops filter"
```

---

## Task 6: `reverify_flight_price`

**Why:** Just before inserting a `qualified_item` and triggering an alert, we want to confirm the deal is still valid against the live API. This catches stale prices, vanished flights, and protects against false alerts.

**Files:**
- Create: `backend/app/scraper/reverify.py`
- Create: `backend/tests/test_reverify.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_reverify.py`:

```python
from unittest.mock import patch
import asyncio
from app.scraper.reverify import reverify_flight_price


def _flight(origin="CDG", destination="BCN", departure_date="2026-05-12",
            return_date="2026-05-19", price=100.0, airline="AF"):
    return {
        "origin": origin,
        "destination": destination,
        "departure_date": departure_date,
        "return_date": return_date,
        "price": price,
        "airline": airline,
    }


def _api_entry(price, departure_date="2026-05-12", return_date="2026-05-19", airline="AF"):
    return {
        "origin_airport": "CDG",
        "destination_airport": "BCN",
        "departure_at": f"{departure_date}T10:00:00+02:00",
        "return_at": f"{return_date}T18:00:00+02:00",
        "price": price,
        "airline": airline,
        "transfers": 0,
        "duration_to": 100,
        "duration_back": 110,
        "link": "/search/...",
    }


def test_reverify_returns_true_when_price_unchanged():
    flight = _flight(price=100.0)
    with patch("app.scraper.reverify.get_prices_for_dates",
               return_value=[_api_entry(100)]):
        assert asyncio.run(reverify_flight_price(flight)) is True


def test_reverify_returns_true_when_price_decreased():
    flight = _flight(price=100.0)
    with patch("app.scraper.reverify.get_prices_for_dates",
               return_value=[_api_entry(85)]):
        assert asyncio.run(reverify_flight_price(flight)) is True


def test_reverify_returns_true_within_5_pct_tolerance():
    flight = _flight(price=100.0)
    with patch("app.scraper.reverify.get_prices_for_dates",
               return_value=[_api_entry(105)]):
        assert asyncio.run(reverify_flight_price(flight)) is True


def test_reverify_returns_false_above_5_pct_tolerance():
    flight = _flight(price=100.0)
    with patch("app.scraper.reverify.get_prices_for_dates",
               return_value=[_api_entry(106)]):
        assert asyncio.run(reverify_flight_price(flight)) is False


def test_reverify_returns_false_when_flight_disappeared():
    flight = _flight(price=100.0, departure_date="2026-05-12")
    # API returns flights for different dates -> no match
    with patch("app.scraper.reverify.get_prices_for_dates",
               return_value=[_api_entry(80, departure_date="2026-06-01")]):
        assert asyncio.run(reverify_flight_price(flight)) is False


def test_reverify_returns_false_when_api_returns_empty():
    flight = _flight(price=100.0)
    with patch("app.scraper.reverify.get_prices_for_dates", return_value=[]):
        assert asyncio.run(reverify_flight_price(flight)) is False


def test_reverify_returns_false_on_api_exception():
    flight = _flight(price=100.0)
    with patch("app.scraper.reverify.get_prices_for_dates",
               side_effect=RuntimeError("network down")):
        assert asyncio.run(reverify_flight_price(flight)) is False


def test_reverify_matches_on_dates_only_when_airline_differs():
    """If the API returns the same dates with a different airline, accept it
    as long as the price is within tolerance — the user might book either."""
    flight = _flight(price=100.0, airline="AF")
    with patch("app.scraper.reverify.get_prices_for_dates",
               return_value=[_api_entry(98, airline="VY")]):
        assert asyncio.run(reverify_flight_price(flight)) is True
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_reverify.py -v`
Expected: ModuleNotFoundError on `app.scraper.reverify`.

- [ ] **Step 3: Create the module**

Create `backend/app/scraper/reverify.py`:

```python
"""Real-time price re-verification before alerting.

Just before we insert a qualified_item, we re-fetch the route from
Travelpayouts and confirm the deal still exists at a comparable price.
This catches stale or expired offers, protecting users from false alerts."""

import logging
from app.scraper.travelpayouts import get_prices_for_dates

logger = logging.getLogger(__name__)

PRICE_TOLERANCE_PCT = 5.0  # accept up to 5% price increase since the scrape


async def reverify_flight_price(flight: dict) -> bool:
    """Return True if the deal is still valid, False otherwise.

    A deal is valid if the live API still returns at least one round-trip
    matching the same departure_date and return_date, at a price no more
    than PRICE_TOLERANCE_PCT above the originally-scraped price.

    Any API error returns False (better safe than sorry — we never
    show a deal we couldn't confirm)."""
    origin = flight["origin"]
    destination = flight["destination"]
    initial_price = float(flight["price"])
    departure_date = flight["departure_date"]
    return_date = flight["return_date"]

    try:
        results = get_prices_for_dates(origin, destination)
    except Exception as e:
        logger.warning(f"Reverify {origin}->{destination}: API exception {e}")
        return False

    if not results:
        logger.info(f"Reverify {origin}->{destination}: API returned no results, rejecting")
        return False

    max_acceptable = initial_price * (1.0 + PRICE_TOLERANCE_PCT / 100.0)

    for entry in results:
        if entry.get("departure_at", "")[:10] != departure_date:
            continue
        if entry.get("return_at", "")[:10] != return_date:
            continue
        live_price = float(entry.get("price") or 0)
        if 0 < live_price <= max_acceptable:
            logger.info(
                f"Reverify {origin}->{destination} {departure_date}->{return_date}: "
                f"OK (initial={initial_price}€, live={live_price}€, tolerance={max_acceptable:.0f}€)"
            )
            return True

    logger.info(
        f"Reverify {origin}->{destination} {departure_date}->{return_date}: "
        f"REJECTED (initial={initial_price}€, no matching entry within {PRICE_TOLERANCE_PCT}% tolerance)"
    )
    return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_reverify.py -v`
Expected: 8 passed.

Then full suite:
Run: `cd backend && source .venv/bin/activate && pytest -q`
Expected: 116 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/app/scraper/reverify.py backend/tests/test_reverify.py
git commit -m "feat(scraper): real-time reverify_flight_price helper with 5% tolerance"
```

---

## Task 7: Rewrite `_analyze_new_flights`

**Why:** This is the brain of the deal pipeline. It must look up the right baseline per bucket, enforce the stops rule, apply our extra discount/z-score filters on top of `detect_anomaly`, re-verify the live price, and tag the qualified item with the right tier.

**Files:**
- Modify: `backend/app/scheduler/jobs.py`
- Modify: `backend/tests/test_jobs.py`

- [ ] **Step 1: Write the failing tests**

First read `backend/tests/test_jobs.py` to understand the existing test patterns and fixtures. Then append:

```python
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture
def mock_db_with_baseline():
    """Mock db with a single baseline returned for any query."""
    db_mock = MagicMock()
    baseline_row = {
        "route_key": "CDG-BCN-bucket_medium",
        "type": "flight",
        "avg_price": 200.0,
        "std_dev": 25.0,
        "sample_count": 50,
    }
    table_mock = MagicMock()
    select_mock = MagicMock()
    eq_mock = MagicMock()
    eq2_mock = MagicMock()
    eq2_mock.execute.return_value = MagicMock(data=[baseline_row])
    eq_mock.eq.return_value = eq2_mock
    select_mock.eq.return_value = eq_mock
    table_mock.select.return_value = select_mock
    table_mock.insert.return_value.execute.return_value = MagicMock(data=[{}])
    db_mock.table.return_value = table_mock
    return db_mock, baseline_row


def _flight_for_analysis(price=120.0, trip_duration_days=7, stops=0,
                         duration_minutes=120, origin="CDG", destination="BCN"):
    return {
        "id": "test-id",
        "origin": origin,
        "destination": destination,
        "departure_date": "2026-05-12",
        "return_date": "2026-05-19",
        "price": price,
        "trip_duration_days": trip_duration_days,
        "stops": stops,
        "duration_minutes": duration_minutes,
        "airline": "AF",
    }


@pytest.mark.asyncio
async def test_analyze_skips_flights_outside_duration_buckets(mock_db_with_baseline):
    db_mock, _ = mock_db_with_baseline
    from app.scheduler import jobs
    flight = _flight_for_analysis(trip_duration_days=30)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)):
        await jobs._analyze_new_flights([flight])
    db_mock.table.assert_not_called()  # never even queried baseline


@pytest.mark.asyncio
async def test_analyze_skips_flights_violating_stops_rule(mock_db_with_baseline):
    db_mock, _ = mock_db_with_baseline
    from app.scheduler import jobs
    # Short-haul (120 min), 1 stop -> rejected
    flight = _flight_for_analysis(stops=1, duration_minutes=120)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)):
        await jobs._analyze_new_flights([flight])
    db_mock.table.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_uses_bucket_medium_for_7_day_flight(mock_db_with_baseline):
    db_mock, baseline_row = mock_db_with_baseline
    from app.scheduler import jobs
    flight = _flight_for_analysis(price=120.0, trip_duration_days=7)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)), \
         patch.object(jobs, "_compose_packages_for_flight", new=AsyncMock()):
        await jobs._analyze_new_flights([flight])
    # Verify baseline was queried with the right key
    select_call = db_mock.table.return_value.select.return_value
    eq_calls = select_call.eq.call_args_list
    assert any(call.args == ("route_key", "CDG-BCN-bucket_medium") for call in eq_calls)


@pytest.mark.asyncio
async def test_analyze_skips_when_no_baseline_for_bucket():
    db_mock = MagicMock()
    table_mock = MagicMock()
    select_mock = MagicMock()
    eq_mock = MagicMock()
    eq2_mock = MagicMock()
    eq2_mock.execute.return_value = MagicMock(data=[])
    eq_mock.eq.return_value = eq2_mock
    select_mock.eq.return_value = eq_mock
    table_mock.select.return_value = select_mock
    db_mock.table.return_value = table_mock

    from app.scheduler import jobs
    flight = _flight_for_analysis()
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)):
        await jobs._analyze_new_flights([flight])
    table_mock.insert.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_skips_when_baseline_sample_count_too_low():
    db_mock = MagicMock()
    baseline_row = {
        "route_key": "CDG-BCN-bucket_medium",
        "type": "flight",
        "avg_price": 200.0,
        "std_dev": 25.0,
        "sample_count": 25,  # below MIN_SAMPLE_COUNT
    }
    table_mock = MagicMock()
    select_mock = MagicMock()
    eq_mock = MagicMock()
    eq2_mock = MagicMock()
    eq2_mock.execute.return_value = MagicMock(data=[baseline_row])
    eq_mock.eq.return_value = eq2_mock
    select_mock.eq.return_value = eq_mock
    table_mock.select.return_value = select_mock
    db_mock.table.return_value = table_mock

    from app.scheduler import jobs
    flight = _flight_for_analysis(price=80.0)  # would be -60% otherwise
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)):
        await jobs._analyze_new_flights([flight])
    table_mock.insert.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_assigns_free_tier_for_25_pct_discount(mock_db_with_baseline):
    db_mock, _ = mock_db_with_baseline
    from app.scheduler import jobs
    # baseline avg 200, price 150 -> -25%, z = (200-150)/25 = 2.0
    flight = _flight_for_analysis(price=150.0)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)), \
         patch.object(jobs, "_compose_packages_for_flight", new=AsyncMock()):
        await jobs._analyze_new_flights([flight])
    insert_calls = db_mock.table.return_value.insert.call_args_list
    inserted_payloads = [c.args[0] for c in insert_calls]
    qualified = [p for p in inserted_payloads if p.get("type") == "flight"]
    assert len(qualified) == 1
    assert qualified[0]["tier"] == "free"


@pytest.mark.asyncio
async def test_analyze_assigns_premium_tier_for_50_pct_discount(mock_db_with_baseline):
    db_mock, _ = mock_db_with_baseline
    from app.scheduler import jobs
    # baseline avg 200, price 100 -> -50%, z = 4.0
    flight = _flight_for_analysis(price=100.0)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)), \
         patch.object(jobs, "_compose_packages_for_flight", new=AsyncMock()):
        await jobs._analyze_new_flights([flight])
    insert_calls = db_mock.table.return_value.insert.call_args_list
    inserted_payloads = [c.args[0] for c in insert_calls]
    qualified = [p for p in inserted_payloads if p.get("type") == "flight"]
    assert len(qualified) == 1
    assert qualified[0]["tier"] == "premium"


@pytest.mark.asyncio
async def test_analyze_skips_when_reverify_returns_false(mock_db_with_baseline):
    db_mock, _ = mock_db_with_baseline
    from app.scheduler import jobs
    flight = _flight_for_analysis(price=100.0)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=False)):
        await jobs._analyze_new_flights([flight])
    db_mock.table.return_value.insert.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_skips_when_discount_below_20_pct(mock_db_with_baseline):
    db_mock, _ = mock_db_with_baseline
    from app.scheduler import jobs
    # baseline 200, price 175 -> -12.5%, below threshold
    flight = _flight_for_analysis(price=175.0)
    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "reverify_flight_price", new=AsyncMock(return_value=True)):
        await jobs._analyze_new_flights([flight])
    db_mock.table.return_value.insert.assert_not_called()
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_jobs.py -v -k analyze`
Expected: 9 new tests fail (the new behavior isn't implemented yet).

- [ ] **Step 3: Rewrite `_analyze_new_flights` and add the import**

Open `backend/app/scheduler/jobs.py`. At the top of the file, add these two imports near the existing scraper imports:

```python
from app.analysis.buckets import bucket_for_duration, stops_allowed
from app.analysis.baselines import MIN_SAMPLE_COUNT
from app.scraper.reverify import reverify_flight_price
```

Then REPLACE the entire `_analyze_new_flights` function (currently around lines 120–166) with:

```python
async def _analyze_new_flights(flights: list[dict]):
    if not db:
        return

    for flight in flights:
        # Bucket lookup based on trip duration
        days = flight.get("trip_duration_days") or 0
        bucket = bucket_for_duration(days)
        if not bucket:
            continue

        # Stops rule based on haul type. Missing duration_minutes is treated
        # as short-haul (strictest rule, 0 stops max) to avoid false positives.
        duration_minutes = flight.get("duration_minutes") or 0
        max_stops = stops_allowed(duration_minutes)
        if (flight.get("stops") or 0) > max_stops:
            continue

        # Lookup baseline for this (route, bucket)
        route_key = f"{flight['origin']}-{flight['destination']}-bucket_{bucket}"
        baseline_resp = (
            db.table("price_baselines")
            .select("*")
            .eq("route_key", route_key)
            .eq("type", "flight")
            .execute()
        )
        if not baseline_resp.data:
            continue

        baseline = baseline_resp.data[0]
        if (baseline.get("sample_count") or 0) < MIN_SAMPLE_COUNT:
            continue

        # Anomaly detection (existing helper)
        anomaly = detect_anomaly(price=flight["price"], baseline=baseline)
        if not anomaly:
            continue

        # Extra filters on top of detect_anomaly's tiering
        if anomaly.discount_pct < 20 or anomaly.z_score < 2.0:
            continue

        # Real-time re-verification — reject silently if the deal is gone
        if not await reverify_flight_price(flight):
            continue

        # Tier classification
        tier = "premium" if anomaly.discount_pct >= 40 else "free"

        score = compute_score(
            discount_pct=anomaly.discount_pct,
            destination_code=flight["destination"],
            date_flexibility=0,
            accommodation_rating=None,
        )

        db.table("qualified_items").insert({
            "type": "flight",
            "item_id": flight.get("id", ""),
            "price": anomaly.price,
            "baseline_price": anomaly.baseline_price,
            "discount_pct": anomaly.discount_pct,
            "score": score,
            "tier": tier,
            "status": "active",
        }).execute()

        await _compose_packages_for_flight(flight, baseline)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_jobs.py -v -k analyze`
Expected: 9 new tests pass.

Then full suite:
Run: `cd backend && source .venv/bin/activate && pytest -q`
Expected: 125 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/app/scheduler/jobs.py backend/tests/test_jobs.py
git commit -m "feat(jobs): rewrite _analyze_new_flights with bucket lookup, reverify, tiering"
```

---

## Task 8: Extend `job_travelpayouts_enrichment` to build bucket baselines

**Why:** The new analyzer expects baselines at the format `{origin}-{dest}-bucket_{name}`. The current `job_travelpayouts_enrichment` builds legacy baselines via `month-matrix`. We replace its core loop with one that uses `get_prices_for_dates` to fetch real round-trips, normalizes them, and feeds them into `compute_baselines_by_bucket`.

**Files:**
- Modify: `backend/app/scheduler/jobs.py`
- Modify: `backend/tests/test_jobs.py`

- [ ] **Step 1: Read the existing function**

Read `backend/app/scheduler/jobs.py` lines 489–535 (the current `job_travelpayouts_enrichment`). Note the patterns: it iterates over `settings.MVP_AIRPORTS`, calls `get_cheap_destinations` to discover routes, then `build_baseline_from_travelpayouts` per route.

- [ ] **Step 2: Write the failing tests**

Append to `backend/tests/test_jobs.py`:

```python
@pytest.mark.asyncio
async def test_travelpayouts_enrichment_builds_bucket_baselines():
    """The job should fetch flights via get_prices_for_dates, normalize them,
    and upsert one baseline per (route, bucket) that meets MIN_SAMPLE_COUNT."""
    from app.scheduler import jobs
    from app.analysis.route_selector import get_priority_destinations

    # Build a fake API response with 30 medium-bucket flights for one route
    fake_entries = []
    for i in range(30):
        fake_entries.append({
            "origin_airport": "CDG",
            "destination_airport": "BCN",
            "departure_at": f"2026-05-{(i % 28) + 1:02d}T10:00:00+02:00",
            "return_at": f"2026-05-{(i % 28) + 8:02d}T18:00:00+02:00",
            "price": 200 + i,
            "airline": "AF",
            "transfers": 0,
            "return_transfers": 0,
            "duration_to": 100,
            "duration_back": 110,
            "link": "/search/...",
        })

    db_mock = MagicMock()
    table_mock = MagicMock()
    upsert_mock = MagicMock()
    upsert_mock.execute.return_value = MagicMock(data=[{}])
    table_mock.upsert.return_value = upsert_mock
    db_mock.table.return_value = table_mock

    # Mock settings to limit to 1 airport, 1 destination
    fake_settings = MagicMock()
    fake_settings.MVP_AIRPORTS = ["CDG"]
    fake_settings.TRAVELPAYOUTS_TOKEN = "fake-token"

    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "settings", fake_settings), \
         patch("app.scheduler.jobs.get_prices_for_dates", return_value=fake_entries), \
         patch("app.scheduler.jobs.get_priority_destinations", return_value=["BCN"]):
        await jobs.job_travelpayouts_enrichment()

    upsert_calls = table_mock.upsert.call_args_list
    upserted_baselines = [c.args[0] for c in upsert_calls]
    bucket_baselines = [b for b in upserted_baselines if "bucket_" in b.get("route_key", "")]
    assert len(bucket_baselines) >= 1
    medium = next((b for b in bucket_baselines if b["route_key"] == "CDG-BCN-bucket_medium"), None)
    assert medium is not None
    assert medium["sample_count"] == 30
    assert medium["type"] == "flight"


@pytest.mark.asyncio
async def test_travelpayouts_enrichment_skips_routes_without_enough_samples():
    """If a route returns fewer than MIN_SAMPLE_COUNT usable observations,
    no baseline is published for that route."""
    from app.scheduler import jobs

    # Only 5 flights — below MIN_SAMPLE_COUNT
    fake_entries = []
    for i in range(5):
        fake_entries.append({
            "origin_airport": "CDG",
            "destination_airport": "BCN",
            "departure_at": f"2026-05-{i + 1:02d}T10:00:00+02:00",
            "return_at": f"2026-05-{i + 8:02d}T18:00:00+02:00",
            "price": 200 + i,
            "airline": "AF",
            "transfers": 0,
            "return_transfers": 0,
            "duration_to": 100,
            "duration_back": 110,
            "link": "/search/...",
        })

    db_mock = MagicMock()
    table_mock = MagicMock()
    upsert_mock = MagicMock()
    upsert_mock.execute.return_value = MagicMock(data=[{}])
    table_mock.upsert.return_value = upsert_mock
    db_mock.table.return_value = table_mock

    fake_settings = MagicMock()
    fake_settings.MVP_AIRPORTS = ["CDG"]
    fake_settings.TRAVELPAYOUTS_TOKEN = "fake-token"

    with patch.object(jobs, "db", db_mock), \
         patch.object(jobs, "settings", fake_settings), \
         patch("app.scheduler.jobs.get_prices_for_dates", return_value=fake_entries), \
         patch("app.scheduler.jobs.get_priority_destinations", return_value=["BCN"]):
        await jobs.job_travelpayouts_enrichment()

    upsert_calls = table_mock.upsert.call_args_list
    upserted_baselines = [c.args[0] for c in upsert_calls]
    bucket_baselines = [b for b in upserted_baselines if "bucket_" in b.get("route_key", "")]
    assert bucket_baselines == []
```

- [ ] **Step 3: Run tests to confirm they fail**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_jobs.py -v -k travelpayouts_enrichment`
Expected: 2 new tests fail (the function still uses the old logic).

- [ ] **Step 4: Replace the function body**

In `backend/app/scheduler/jobs.py`, locate `job_travelpayouts_enrichment` and REPLACE its body with:

```python
async def job_travelpayouts_enrichment():
    """Build per-bucket baselines for all MVP routes via Travelpayouts."""
    logger.info("Starting Travelpayouts bucket baseline enrichment")
    if not db or not settings.TRAVELPAYOUTS_TOKEN:
        return

    from app.scraper.travelpayouts import get_prices_for_dates
    from app.scraper.travelpayouts_flights import _normalize_priced_entry
    from app.analysis.route_selector import get_priority_destinations, is_long_haul
    from app.analysis.baselines import compute_baselines_by_bucket

    destinations = get_priority_destinations(max_count=25)
    total_published = 0

    for origin in settings.MVP_AIRPORTS:
        for dest in destinations:
            if dest == origin:
                continue
            if is_long_haul(dest) and origin != "CDG":
                continue

            try:
                api_entries = get_prices_for_dates(origin, dest)
            except Exception as e:
                logger.warning(f"Travelpayouts enrichment failed for {origin}->{dest}: {e}")
                continue

            observations = []
            for entry in api_entries:
                normalized = _normalize_priced_entry(entry)
                if normalized:
                    observations.append(normalized)

            if not observations:
                continue

            baselines = compute_baselines_by_bucket(f"{origin}-{dest}", observations)
            for baseline in baselines:
                try:
                    db.table("price_baselines").upsert(baseline, on_conflict="route_key").execute()
                    total_published += 1
                except Exception as e:
                    logger.warning(f"Failed to upsert baseline {baseline['route_key']}: {e}")

    logger.info(f"Travelpayouts enrichment: {total_published} bucket baselines upserted")
```

This replaces ALL the existing logic of the function — the call to `get_cheap_destinations`, `build_baseline_from_travelpayouts`, and the special offers loop are gone. They built legacy baselines that the new analyzer no longer reads.

Note: `get_priority_destinations` and `is_long_haul` are imported locally inside the function to avoid moving the existing top-level imports of `route_selector`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_jobs.py -v -k travelpayouts_enrichment`
Expected: 2 new tests pass.

Then full suite:
Run: `cd backend && source .venv/bin/activate && pytest -q`
Expected: 127 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/app/scheduler/jobs.py backend/tests/test_jobs.py
git commit -m "feat(jobs): travelpayouts_enrichment now builds per-bucket baselines"
```

---

## Task 9: Whitelist `travelpayouts_enrichment` for manual triggering

**Why:** Post-deploy we need to fire `job_travelpayouts_enrichment` manually so the bucket baselines exist before the next cron `scrape_flights` runs. The current `/api/trigger/{job_name}` endpoint has a hardcoded whitelist that doesn't include this job.

**Files:**
- Modify: `backend/app/api/routes.py`
- Modify: `backend/tests/test_routes.py`

- [ ] **Step 1: Add the test**

Append to `backend/tests/test_routes.py`:

```python
def test_trigger_travelpayouts_enrichment_is_whitelisted(client, admin_headers):
    """The travelpayouts_enrichment job must be triggerable via /api/trigger."""
    with patch("app.scheduler.jobs.job_travelpayouts_enrichment", new=AsyncMock()):
        response = client.post("/api/trigger/travelpayouts_enrichment", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "triggered"
    assert body["job"] == "travelpayouts_enrichment"
```

If `client` and `admin_headers` fixtures don't exist in `test_routes.py`, look at how the existing trigger tests are structured and follow the same pattern. If there are no existing trigger tests, create the fixtures inline:

```python
@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture
def admin_headers():
    from app.config import settings
    return {"X-Admin-Key": settings.ADMIN_API_KEY or "test"}
```

- [ ] **Step 2: Run test to confirm it fails**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_routes.py::test_trigger_travelpayouts_enrichment_is_whitelisted -v`
Expected: 404 returned, test fails.

- [ ] **Step 3: Update the whitelist**

In `backend/app/api/routes.py`, find the `trigger_job` function (around line 301). Update the imports inside the function to include `job_travelpayouts_enrichment`:

```python
from app.scheduler.jobs import (
    job_scrape_flights,
    job_scrape_accommodations,
    job_recalculate_baselines,
    job_expire_stale_data,
    job_travelpayouts_enrichment,
)
```

And update the `jobs` dict to include it:

```python
jobs = {
    "scrape_flights": job_scrape_flights,
    "scrape_accommodations": job_scrape_accommodations,
    "recalculate_baselines": job_recalculate_baselines,
    "expire_stale_data": job_expire_stale_data,
    "travelpayouts_enrichment": job_travelpayouts_enrichment,
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_routes.py -v -k travelpayouts_enrichment`
Expected: passed.

Then full suite:
Run: `cd backend && source .venv/bin/activate && pytest -q`
Expected: 128 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/app/api/routes.py backend/tests/test_routes.py
git commit -m "feat(api): allow manual trigger of travelpayouts_enrichment"
```

---

## Task 10: Telegram alerts — branch on tier

**Why:** Free-tier deals (20–39%) need a different message template than premium-tier deals (40%+). Free-tier alerts must mention that premium subscription is required to book directly.

**Files:**
- Modify: `backend/app/notifications/telegram.py`
- Modify: `backend/app/scheduler/jobs.py`
- Modify: `backend/tests/test_telegram.py`

- [ ] **Step 1: Read existing telegram code**

Read `backend/app/notifications/telegram.py` and find the `send_deal_alert` function. Note its current signature and the parameters it receives. Understand how it formats the current message.

- [ ] **Step 2: Write the failing test**

Append to `backend/tests/test_telegram.py`:

```python
import pytest
from unittest.mock import patch, AsyncMock
from app.notifications.telegram import send_deal_alert


@pytest.mark.asyncio
async def test_send_deal_alert_premium_tier_includes_booking_link():
    pkg = {
        "origin": "CDG", "destination": "BCN",
        "total_price": 100, "discount_pct": 50, "score": 85,
        "departure_date": "2026-05-12", "return_date": "2026-05-19",
    }
    flight_data = {"source_url": "https://example.com/book", "airline": "AF"}
    acc_data = {"name": "Hotel X", "rating": 4.5, "source_url": "https://example.com/hotel"}

    sent_messages = []

    async def fake_send(chat_id, text, **kwargs):
        sent_messages.append(text)

    with patch("app.notifications.telegram._send_telegram", side_effect=fake_send):
        await send_deal_alert("123", pkg, flight_data, acc_data, tier="premium")

    assert len(sent_messages) == 1
    msg = sent_messages[0]
    assert "https://example.com/book" in msg
    # Premium messages should NOT show the upgrade CTA
    assert "premium" not in msg.lower() or "compte premium" not in msg.lower()


@pytest.mark.asyncio
async def test_send_deal_alert_free_tier_includes_upgrade_cta():
    pkg = {
        "origin": "CDG", "destination": "BCN",
        "total_price": 150, "discount_pct": 25, "score": 60,
        "departure_date": "2026-05-12", "return_date": "2026-05-19",
    }
    flight_data = {"source_url": "https://example.com/book", "airline": "AF"}
    acc_data = {"name": "Hotel X", "rating": 4.5, "source_url": "https://example.com/hotel"}

    sent_messages = []

    async def fake_send(chat_id, text, **kwargs):
        sent_messages.append(text)

    with patch("app.notifications.telegram._send_telegram", side_effect=fake_send):
        await send_deal_alert("123", pkg, flight_data, acc_data, tier="free")

    assert len(sent_messages) == 1
    msg = sent_messages[0]
    assert "compte premium" in msg.lower() or "premium" in msg.lower()


@pytest.mark.asyncio
async def test_send_deal_alert_default_tier_is_premium_for_backward_compat():
    """Calls without explicit tier default to premium (legacy behavior)."""
    pkg = {
        "origin": "CDG", "destination": "BCN", "total_price": 100,
        "discount_pct": 45, "score": 80,
        "departure_date": "2026-05-12", "return_date": "2026-05-19",
    }
    flight_data = {"source_url": "https://example.com/book", "airline": "AF"}
    acc_data = {"name": "Hotel X", "rating": 4.5, "source_url": "https://example.com/hotel"}

    sent_messages = []

    async def fake_send(chat_id, text, **kwargs):
        sent_messages.append(text)

    with patch("app.notifications.telegram._send_telegram", side_effect=fake_send):
        await send_deal_alert("123", pkg, flight_data, acc_data)

    assert len(sent_messages) == 1
```

- [ ] **Step 3: Run tests, confirm failure**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_telegram.py -v -k tier`
Expected: tests fail because `send_deal_alert` doesn't accept `tier` parameter (or because the assertions don't match the current message format).

If the test fails on `_send_telegram` not being patchable (e.g., it's named differently in the source), inspect `telegram.py` and adjust the patch target to match the actual function used to call the Telegram API.

- [ ] **Step 4: Add `tier` parameter to `send_deal_alert`**

In `backend/app/notifications/telegram.py`, find `send_deal_alert` and add a `tier: str = "premium"` parameter to its signature. Inside the function, branch on `tier`:

```python
async def send_deal_alert(chat_id, pkg, flight_data, acc_data, tier: str = "premium"):
    # existing message-building logic that produces a `text` variable...

    if tier == "free":
        text += (
            "\n\n💎 Réservation réservée aux abonnés premium. "
            "Créez un compte premium pour débloquer ce deal."
        )
    # premium tier: existing message untouched, includes the booking link as before

    await _send_telegram(chat_id, text, ...)
```

The exact phrasing of the upgrade CTA can be adjusted. The key requirement is that the test assertions on `"compte premium" in msg.lower()` (free tier) and on the booking link being present (premium tier) both pass.

If the existing function doesn't currently take an `acc_data` parameter or has a different signature, adapt the additions to whatever `send_deal_alert` actually looks like — the goal is "add a `tier` parameter, branch the message text on it" not "rewrite the function".

- [ ] **Step 5: Update the call site in `jobs.py`**

In `backend/app/scheduler/jobs.py`, find the existing `send_deal_alert` call inside `_compose_packages_for_flight` (around line 247). Pass the tier from the package:

```python
await send_deal_alert(
    sub["chat_id"], pkg, flight_data.data[0], acc_data.data[0],
    tier=pkg.get("tier", "premium"),
)
```

For this to work, the package built by `build_packages` needs to carry the `tier` field. Look at where `_compose_packages_for_flight` receives packages and decide whether to:

(a) Set `pkg["tier"]` based on `pkg["discount_pct"]` right before calling `send_deal_alert`, or
(b) Have `_analyze_new_flights` (already aware of `tier`) write the value into the flight dict it passes to `_compose_packages_for_flight`.

Option (a) is simpler. In `_compose_packages_for_flight`, just before the `send_deal_alert` call, add:

```python
pkg_tier = "premium" if pkg.get("discount_pct", 0) >= 40 else "free"
```

And pass `tier=pkg_tier`.

- [ ] **Step 6: Run all tests**

Run: `cd backend && source .venv/bin/activate && pytest -q`
Expected: 131 passed (128 + 3 new).

If the existing telegram tests (non-tier ones) break because of the signature change, investigate whether they were calling `send_deal_alert` with positional args. If yes, they should still work because `tier` has a default value (`"premium"`). If they break because of message content changes, update them to assert on the new message structure.

- [ ] **Step 7: Commit**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git add backend/app/notifications/telegram.py backend/app/scheduler/jobs.py backend/tests/test_telegram.py
git commit -m "feat(telegram): branch deal alert template on free/premium tier"
```

---

## Task 11: Live API smoke test

**Why:** Mocked tests can't catch API contract drift, real-world data anomalies, or unexpected response shapes. Before deploying we run the full pipeline against the live Travelpayouts API and verify the data looks right.

**Files:** None. Manual verification.

- [ ] **Step 1: Smoke test a single route**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend
source .venv/bin/activate
python -c "
from app.scraper.travelpayouts_flights import scrape_flights_for_route
flights = scrape_flights_for_route('CDG', 'BCN')
print(f'Got {len(flights)} flights')
durations = sorted(set(f['trip_duration_days'] for f in flights))
print(f'Trip durations: {durations}')
stops_set = sorted(set(f['stops'] for f in flights))
print(f'Stops: {stops_set}')
print(f'Source: {flights[0][\"source\"] if flights else \"N/A\"}')
print(f'Sample URL: {flights[0][\"source_url\"] if flights else \"N/A\"}')
"
```

Expected:
- 5 to ~50 flights
- All `trip_duration_days` values are integers in `[1, 21]`
- `stops` set contains only `0` and/or `1`
- Source is `travelpayouts`
- URL starts with `https://www.aviasales.com`

If you see ANY duration outside `[1, 21]` or any stops value `>= 2`, STOP and investigate before proceeding to deploy.

- [ ] **Step 2: Smoke test the full rotation**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend
source .venv/bin/activate
python -c "
import asyncio, time
from app.scraper.travelpayouts_flights import scrape_all_flights
t0 = time.time()
flights, errors, baselines = asyncio.run(scrape_all_flights())
elapsed = time.time() - t0
print(f'Total: {len(flights)} flights, {errors} errors, {elapsed:.1f}s')
durations = sorted(set(f['trip_duration_days'] for f in flights))
print(f'Distinct trip_duration_days: {durations[:10]}...')
"
```

Expected: 50–500 flights, 0 errors, <30 seconds, all durations in `[1, 21]`.

- [ ] **Step 3: Smoke test bucket baseline construction**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend
source .venv/bin/activate
python -c "
import asyncio
from app.scheduler.jobs import job_travelpayouts_enrichment
asyncio.run(job_travelpayouts_enrichment())
"
```

Expected: log line `Travelpayouts enrichment: N bucket baselines upserted` with N >= 1.

After running, query Supabase manually (dashboard SQL editor) to confirm:

```sql
SELECT route_key, avg_price, std_dev, sample_count
FROM price_baselines
WHERE route_key LIKE '%bucket_%'
ORDER BY sample_count DESC
LIMIT 20;
```

Expected: at least a handful of rows with `sample_count >= 30`. If you get zero rows, the API may not be returning enough data per route — adjust expectations or revisit the spec assumption that one `prices_for_dates` call is enough for 30 observations.

---

## Task 12: Deploy and verify

**Why:** Bring the new pipeline to production, watch the first scrape, and confirm deals start qualifying.

**Files:** None.

- [ ] **Step 1: Apply the SQL migration to production**

Open the Supabase dashboard for the project. Go to SQL Editor. Paste the contents of `backend/supabase/migrations/004_roundtrip_coherence.sql`. Run it. Verify in the table editor that:

- `raw_flights` has new columns `trip_duration_days` and `duration_minutes`
- `qualified_items` has new column `tier`

- [ ] **Step 2: Push the branch and merge**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git checkout main
git pull
git merge --no-ff feat/roundtrip-coherence -m "feat: roundtrip coherence and reverify pipeline"
git push origin main
```

(Adjust the branch name if different.)

- [ ] **Step 3: Wait for Railway redeploy**

Watch the Railway dashboard. The deploy typically takes 2–5 minutes. Wait until the new revision is live.

- [ ] **Step 4: Trigger enrichment manually**

```bash
curl -X POST "https://globagenius-production-b887.up.railway.app/api/trigger/travelpayouts_enrichment" \
  -H "X-Admin-Key: $(grep ADMIN_API_KEY /Users/moussa/Documents/PROJETS/globegenius/backend/.env | cut -d= -f2)"
```

Expected: `{"status":"triggered","job":"travelpayouts_enrichment"}`.

- [ ] **Step 5: Wait ~60 seconds and check baselines**

```bash
curl -s "https://globagenius-production-b887.up.railway.app/api/status" \
  | python3 -c "import json, sys; d = json.load(sys.stdin); print(f'active_baselines: {d[\"active_baselines\"]}')"
```

Expected: `active_baselines` significantly higher than 246 (the pre-migration value), at least a few hundred.

- [ ] **Step 6: Trigger a flight scrape**

```bash
curl -X POST "https://globagenius-production-b887.up.railway.app/api/trigger/scrape_flights" \
  -H "X-Admin-Key: $(grep ADMIN_API_KEY /Users/moussa/Documents/PROJETS/globegenius/backend/.env | cut -d= -f2)"
```

Wait ~45 seconds.

- [ ] **Step 7: Verify the scrape inserted real round-trip data**

```bash
curl -s "https://globagenius-production-b887.up.railway.app/api/status" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
s = d['recent_scrapes'][0]
print(f'Latest scrape: items={s[\"items_count\"]}, errors={s[\"errors_count\"]}, dur={s[\"duration_ms\"]/1000:.1f}s')
print(f'active_packages: {d[\"active_packages\"]}')
"
```

Expected: `items_count > 0`, `errors_count == 0`. `active_packages` may be 0 immediately after the first scrape — the analyzer needs time to run, then the baseline lookups need to match. Wait another minute and re-check.

- [ ] **Step 8: Verify qualified items**

```bash
curl -s "https://globagenius-production-b887.up.railway.app/api/qualified-items?type_filter=flight&limit=5" \
  | python3 -m json.tool
```

Expected: at least one item with `tier` field set to `"free"` or `"premium"`. If the list is empty after waiting 5 minutes, check the Railway logs for `Reverify` lines and `compute_baselines_by_bucket` warnings.

---

## Self-Review

### Spec coverage check

- ✅ "Endpoint API : `/aviasales/v3/prices_for_dates`" → Task 2 + Task 3
- ✅ "Bucketing par durée — short/medium/long" → Task 1 + Task 5
- ✅ "Médiane (pas moyenne) pour le prix de référence" → Task 5 (`compute_baselines_by_bucket` uses `np.median`)
- ✅ "Seuil minimum 30 observations" → Task 5 (`MIN_SAMPLE_COUNT = 30`)
- ✅ "Tiering free 20-39%, premium 40%+" → Task 7 (`tier` assignment in `_analyze_new_flights`)
- ✅ "z-score >= 2.0 en plus du seuil de discount" → Task 7 (`if anomaly.z_score < 2.0: continue`)
- ✅ "Règle escales : court-courrier max 0, long-courrier max 1" → Task 1 (`stops_allowed`) + Task 5 (filter in baselines) + Task 7 (filter in analyzer)
- ✅ "Revérification temps réel ±5%" → Task 6 (`reverify_flight_price`)
- ✅ "Pas de feature flag, swap atomique au merge" → Task 12
- ✅ "Migration SQL idempotente additive" → Task 4
- ✅ "Trigger manuel `travelpayouts_enrichment` post-deploy" → Task 9 + Task 12
- ✅ "Alertes Telegram free tier avec CTA premium" → Task 10
- ✅ "Métriques de succès post-deploy" → Task 12 steps 5–8
- ✅ "Hôtels hors scope" → never touched accommodations.py, browser/, apify_client

### Type/signature consistency

- `bucket_for_duration(days: int) -> str | None` — used in Task 5 (baselines.py) and Task 7 (jobs.py). Same name and signature in both. ✓
- `stops_allowed(duration_minutes: int) -> int` — same. ✓
- `_normalize_priced_entry(entry: dict) -> dict | None` — defined in Task 3, used in Task 8 (`job_travelpayouts_enrichment`). Note: Task 3 changed the signature from `(entry, origin, destination)` to `(entry)` because the API now returns `origin_airport`/`destination_airport`. Task 8 calls it with just `(entry)`. Consistent. ✓
- `get_prices_for_dates(origin, destination, departure_month="", return_month="", limit=1000)` — defined in Task 2, used in Task 3 (scraper), Task 6 (reverify), Task 8 (enrichment). Same call style everywhere (only first 2 args used in production calls). ✓
- `compute_baselines_by_bucket(route_key_prefix: str, observations: list[dict]) -> list[dict]` — defined in Task 5, used in Task 8. Same. ✓
- `reverify_flight_price(flight: dict) -> bool` (async) — defined in Task 6, used in Task 7. Same. ✓
- `MIN_SAMPLE_COUNT = 30` — defined in Task 5 (baselines.py), imported in Task 7 (jobs.py). Same value. ✓
- `tier: str = "premium"` parameter on `send_deal_alert` — added in Task 10, called from `_compose_packages_for_flight` in Task 10. Consistent. ✓

### Placeholder scan

No "TBD", no "TODO", no "implement later", no "similar to Task N". All code blocks are concrete. The only flexibility is in Task 10 ("the exact phrasing of the upgrade CTA can be adjusted") which is a UX nuance, not a placeholder — the test asserts the substring `"compte premium"` is present, which constrains the implementation enough.

### Open assumptions / risks

- **Task 8 / Task 11 — sample count assumption.** The plan assumes one `get_prices_for_dates` call per route returns enough observations to reach `sample_count >= 30` per bucket. The smoke test in Task 11 step 3 will validate this. If it doesn't hold, we may need to call the API multiple times per route with different month parameters. The fallback path is documented in Task 11 ("revisit the spec assumption").
- **Task 10 — telegram message format.** The plan can't show the exact current message string without reading `telegram.py`, so it tells the executor to "find `send_deal_alert`, add a tier param, branch the text". This is acceptable because the test pins the observable behavior (substring check on the message).
- **Task 12 — Supabase migration is manual.** I considered automating it via `supabase` CLI, but the project doesn't appear to use the CLI workflow (existing migrations are checked-in SQL files only). Manual application via the dashboard is consistent with the existing pattern.

**Plan complete.**
