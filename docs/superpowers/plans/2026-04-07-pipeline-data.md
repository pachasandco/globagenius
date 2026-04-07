# Globe Genius — Pipeline de Donnees Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend data pipeline that scrapes flight and accommodation data via Apify, detects price anomalies, composes travel packages, and sends Telegram alerts.

**Architecture:** Single Python worker (FastAPI + APScheduler) running on Railway/Render. Apify SDK for scraping, Supabase for storage, numpy for statistical analysis, python-telegram-bot for notifications. All in one process.

**Tech Stack:** Python 3.12, FastAPI, APScheduler, apify-client, supabase-py, numpy, python-telegram-bot, httpx, pytest

**Spec:** `docs/superpowers/specs/2026-04-07-pipeline-data-design.md`

---

## File Structure

```
backend/
├── app/
│   ├── __init__.py              # Empty
│   ├── main.py                  # FastAPI app, lifespan (scheduler start/stop)
│   ├── config.py                # Settings from env vars, IATA_TO_CITY, DESTINATION_POPULARITY
│   ├── db.py                    # Supabase client singleton
│   ├── scraper/
│   │   ├── __init__.py          # Empty
│   │   ├── apify_client.py      # Wrapper: run actor, poll, fetch dataset
│   │   ├── flights.py           # Launch flight actors, parse results
│   │   ├── accommodations.py    # Launch accommodation actors, parse results
│   │   └── normalizer.py        # Clean, deduplicate, upsert to Supabase
│   ├── analysis/
│   │   ├── __init__.py          # Empty
│   │   ├── baselines.py         # Calculate 30-day weighted averages
│   │   ├── anomaly_detector.py  # Z-score detection, qualification check
│   │   └── scorer.py            # Composite score (0-100)
│   ├── composer/
│   │   ├── __init__.py          # Empty
│   │   └── package_builder.py   # Match flights + accommodations into packages
│   ├── notifications/
│   │   ├── __init__.py          # Empty
│   │   └── telegram.py          # Send alerts (user + admin)
│   ├── scheduler/
│   │   ├── __init__.py          # Empty
│   │   └── jobs.py              # Define all APScheduler jobs
│   └── api/
│       ├── __init__.py          # Empty
│       └── routes.py            # /health, /api/status, /api/trigger, /api/packages
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures (mock Supabase, mock Apify)
│   ├── test_config.py
│   ├── test_normalizer.py
│   ├── test_baselines.py
│   ├── test_anomaly_detector.py
│   ├── test_scorer.py
│   ├── test_package_builder.py
│   ├── test_telegram.py
│   ├── test_routes.py
│   └── test_jobs.py
├── requirements.txt
├── .env.example
└── Dockerfile
```

---

## Task 1: Project scaffolding and config

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_config.py`

- [ ] **Step 1: Create `requirements.txt`**

```
fastapi==0.115.0
uvicorn==0.34.0
apify-client==1.8.1
supabase==2.13.0
apscheduler==3.10.4
python-telegram-bot==21.10
httpx==0.28.1
numpy==2.2.4
python-dateutil==2.9.0
python-dotenv==1.0.1
pytest==8.3.4
pytest-asyncio==0.25.3
```

- [ ] **Step 2: Create `.env.example`**

```
APIFY_API_TOKEN=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_ADMIN_CHAT_ID=
APP_ENV=development
SCRAPE_FLIGHTS_INTERVAL_HOURS=2
SCRAPE_ACCOMMODATIONS_INTERVAL_HOURS=4
BASELINE_RECALC_HOUR=3
DIGEST_HOUR=8
MIN_DISCOUNT_PCT=40
MIN_SCORE_ALERT=70
MIN_SCORE_DIGEST=50
DATA_FRESHNESS_HOURS=2
MVP_AIRPORTS=CDG,ORY,LYS,MRS,NCE,BOD,NTE,TLS
```

- [ ] **Step 3: Write failing test for config**

```python
# backend/tests/test_config.py
from app.config import Settings

def test_settings_defaults():
    s = Settings()
    assert s.MIN_DISCOUNT_PCT == 40
    assert s.MIN_SCORE_ALERT == 70
    assert s.MIN_SCORE_DIGEST == 50
    assert s.DATA_FRESHNESS_HOURS == 2
    assert s.MVP_AIRPORTS == ["CDG", "ORY", "LYS", "MRS", "NCE", "BOD", "NTE", "TLS"]

def test_iata_to_city_has_major_destinations():
    from app.config import IATA_TO_CITY
    assert "LIS" in IATA_TO_CITY
    assert "BCN" in IATA_TO_CITY
    assert "FCO" in IATA_TO_CITY

def test_destination_popularity_scores():
    from app.config import DESTINATION_POPULARITY
    assert all(0 <= v <= 100 for v in DESTINATION_POPULARITY.values())
    assert "BCN" in DESTINATION_POPULARITY
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 5: Implement config**

```python
# backend/app/__init__.py
```

```python
# backend/app/config.py
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ADMIN_CHAT_ID: str = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    SCRAPE_FLIGHTS_INTERVAL_HOURS: int = int(os.getenv("SCRAPE_FLIGHTS_INTERVAL_HOURS", "2"))
    SCRAPE_ACCOMMODATIONS_INTERVAL_HOURS: int = int(os.getenv("SCRAPE_ACCOMMODATIONS_INTERVAL_HOURS", "4"))
    BASELINE_RECALC_HOUR: int = int(os.getenv("BASELINE_RECALC_HOUR", "3"))
    DIGEST_HOUR: int = int(os.getenv("DIGEST_HOUR", "8"))
    MIN_DISCOUNT_PCT: int = int(os.getenv("MIN_DISCOUNT_PCT", "40"))
    MIN_SCORE_ALERT: int = int(os.getenv("MIN_SCORE_ALERT", "70"))
    MIN_SCORE_DIGEST: int = int(os.getenv("MIN_SCORE_DIGEST", "50"))
    DATA_FRESHNESS_HOURS: int = int(os.getenv("DATA_FRESHNESS_HOURS", "2"))
    MVP_AIRPORTS: list = field(default_factory=lambda: os.getenv(
        "MVP_AIRPORTS", "CDG,ORY,LYS,MRS,NCE,BOD,NTE,TLS"
    ).split(","))


IATA_TO_CITY = {
    "LIS": "Lisbon",
    "BCN": "Barcelona",
    "FCO": "Rome",
    "ATH": "Athens",
    "NAP": "Naples",
    "OPO": "Porto",
    "AMS": "Amsterdam",
    "BER": "Berlin",
    "PRG": "Prague",
    "BUD": "Budapest",
    "DUB": "Dublin",
    "EDI": "Edinburgh",
    "IST": "Istanbul",
    "MAD": "Madrid",
    "MXP": "Milan",
    "VCE": "Venice",
    "VIE": "Vienna",
    "WAW": "Warsaw",
    "ZAG": "Zagreb",
    "CPH": "Copenhagen",
    "HEL": "Helsinki",
    "OSL": "Oslo",
    "ARN": "Stockholm",
    "RAK": "Marrakech",
    "TUN": "Tunis",
    "CMN": "Casablanca",
    "CAI": "Cairo",
    "TLV": "Tel Aviv",
    "AGP": "Malaga",
    "PMI": "Palma de Mallorca",
    "TFS": "Tenerife",
    "HER": "Heraklion",
    "SPU": "Split",
    "DBV": "Dubrovnik",
}

DESTINATION_POPULARITY = {
    "BCN": 95, "LIS": 90, "FCO": 88, "ATH": 85, "AMS": 87,
    "MAD": 86, "IST": 82, "PRG": 80, "BUD": 78, "RAK": 83,
    "NAP": 75, "OPO": 72, "MXP": 77, "VCE": 74, "DUB": 70,
    "BER": 76, "VIE": 73, "CPH": 68, "EDI": 65, "HEL": 60,
    "OSL": 58, "ARN": 62, "WAW": 55, "ZAG": 50, "TUN": 52,
    "CMN": 56, "CAI": 64, "TLV": 66, "AGP": 79, "PMI": 81,
    "TFS": 77, "HER": 71, "SPU": 69, "DBV": 73,
}

settings = Settings()
```

- [ ] **Step 6: Create conftest with shared fixtures**

```python
# backend/tests/__init__.py
```

```python
# backend/tests/conftest.py
import pytest


@pytest.fixture
def sample_flight_raw():
    """Raw flight data as returned by Apify actor."""
    return {
        "price": 89.0,
        "currency": "EUR",
        "origin": "CDG",
        "destination": "LIS",
        "departureDate": "2026-05-10",
        "returnDate": "2026-05-17",
        "airline": "TAP Portugal",
        "stops": 0,
        "url": "https://www.skyscanner.fr/transport/flights/cdg/lis/260510/260517",
    }


@pytest.fixture
def sample_accommodation_raw():
    """Raw accommodation data as returned by Apify actor."""
    return {
        "name": "Hotel Lisboa Plaza",
        "city": "Lisbon",
        "pricePerNight": 60.0,
        "totalPrice": 420.0,
        "currency": "EUR",
        "rating": 4.3,
        "checkIn": "2026-05-10",
        "checkOut": "2026-05-17",
        "url": "https://www.booking.com/hotel/pt/lisboa-plaza.html",
        "source": "booking",
    }


@pytest.fixture
def sample_baseline_flight():
    """Baseline for CDG-LIS route."""
    return {
        "route_key": "CDG-LIS",
        "type": "flight",
        "avg_price": 198.0,
        "std_dev": 45.0,
        "sample_count": 25,
    }


@pytest.fixture
def sample_baseline_accommodation():
    """Baseline for Lisbon-booking accommodations."""
    return {
        "route_key": "lisbon-booking",
        "type": "accommodation",
        "avg_price": 780.0,
        "std_dev": 120.0,
        "sample_count": 30,
    }
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 8: Commit**

```bash
cd backend
git add -A
git commit -m "feat: project scaffolding with config, env, and test fixtures"
```

---

## Task 2: Supabase client and database setup

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/supabase/migrations/001_create_tables.sql`

- [ ] **Step 1: Create Supabase client module**

```python
# backend/app/db.py
from supabase import create_client, Client
from app.config import settings


def get_supabase_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


db = get_supabase_client() if settings.SUPABASE_URL else None
```

- [ ] **Step 2: Create SQL migration file**

```sql
-- backend/supabase/migrations/001_create_tables.sql
-- Run this in Supabase SQL Editor

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE raw_flights (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    hash varchar UNIQUE NOT NULL,
    origin varchar(3) NOT NULL,
    destination varchar(3) NOT NULL,
    departure_date date NOT NULL,
    return_date date NOT NULL,
    price decimal NOT NULL,
    airline varchar,
    stops int DEFAULT 0,
    source_url text,
    source varchar NOT NULL,
    scraped_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL
);

CREATE INDEX idx_flights_origin ON raw_flights(origin);
CREATE INDEX idx_flights_destination ON raw_flights(destination);
CREATE INDEX idx_flights_dates ON raw_flights(departure_date, return_date);
CREATE INDEX idx_flights_expires ON raw_flights(expires_at);
CREATE INDEX idx_flights_scraped ON raw_flights(scraped_at);

CREATE TABLE raw_accommodations (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    hash varchar UNIQUE NOT NULL,
    city varchar NOT NULL,
    name varchar NOT NULL,
    price_per_night decimal NOT NULL,
    total_price decimal NOT NULL,
    rating decimal,
    check_in date NOT NULL,
    check_out date NOT NULL,
    source_url text,
    source varchar NOT NULL,
    scraped_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL
);

CREATE INDEX idx_accommodations_city ON raw_accommodations(city);
CREATE INDEX idx_accommodations_dates ON raw_accommodations(check_in, check_out);
CREATE INDEX idx_accommodations_expires ON raw_accommodations(expires_at);
CREATE INDEX idx_accommodations_rating ON raw_accommodations(rating);

CREATE TABLE price_baselines (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    route_key varchar UNIQUE NOT NULL,
    type varchar NOT NULL CHECK (type IN ('flight', 'accommodation')),
    avg_price decimal NOT NULL,
    std_dev decimal NOT NULL,
    sample_count int NOT NULL,
    calculated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE packages (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    flight_id uuid REFERENCES raw_flights(id),
    origin varchar(3) NOT NULL,
    destination varchar(3) NOT NULL,
    departure_date date NOT NULL,
    return_date date NOT NULL,
    flight_price decimal NOT NULL,
    accommodation_id uuid REFERENCES raw_accommodations(id),
    accommodation_price decimal NOT NULL,
    total_price decimal NOT NULL,
    baseline_total decimal NOT NULL,
    discount_pct decimal NOT NULL,
    score int NOT NULL,
    status varchar NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired')),
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL
);

CREATE INDEX idx_packages_status ON packages(status);
CREATE INDEX idx_packages_score ON packages(score DESC);
CREATE INDEX idx_packages_expires ON packages(expires_at);

CREATE TABLE qualified_items (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    type varchar NOT NULL CHECK (type IN ('flight', 'accommodation')),
    item_id uuid NOT NULL,
    price decimal NOT NULL,
    baseline_price decimal NOT NULL,
    discount_pct decimal NOT NULL,
    score int NOT NULL,
    status varchar NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_qualified_status ON qualified_items(status);
CREATE INDEX idx_qualified_type ON qualified_items(type);

CREATE TABLE scrape_logs (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_id varchar,
    source varchar NOT NULL,
    type varchar NOT NULL CHECK (type IN ('flights', 'accommodations')),
    items_count int DEFAULT 0,
    errors_count int DEFAULT 0,
    duration_ms int,
    status varchar NOT NULL CHECK (status IN ('success', 'partial', 'failed')),
    started_at timestamptz NOT NULL,
    completed_at timestamptz
);

CREATE INDEX idx_scrape_logs_type ON scrape_logs(type);
CREATE INDEX idx_scrape_logs_started ON scrape_logs(started_at DESC);

CREATE TABLE telegram_subscribers (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    chat_id bigint UNIQUE NOT NULL,
    airport_code varchar(3) NOT NULL,
    min_score int NOT NULL DEFAULT 50,
    created_at timestamptz NOT NULL DEFAULT now()
);
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/db.py backend/supabase/
git commit -m "feat: Supabase client and SQL migration for all tables"
```

---

## Task 3: Normalizer (clean, deduplicate, insert)

**Files:**
- Create: `backend/app/scraper/__init__.py`
- Create: `backend/app/scraper/normalizer.py`
- Create: `backend/tests/test_normalizer.py`

- [ ] **Step 1: Write failing tests for normalizer**

```python
# backend/tests/test_normalizer.py
import hashlib
from app.scraper.normalizer import (
    normalize_flight,
    normalize_accommodation,
    compute_flight_hash,
    compute_accommodation_hash,
)


def test_normalize_flight(sample_flight_raw):
    result = normalize_flight(sample_flight_raw, source="skyscanner")
    assert result["origin"] == "CDG"
    assert result["destination"] == "LIS"
    assert result["price"] == 89.0
    assert result["source"] == "skyscanner"
    assert result["hash"] is not None
    assert result["expires_at"] is not None


def test_normalize_flight_converts_currency(sample_flight_raw):
    sample_flight_raw["currency"] = "USD"
    sample_flight_raw["price"] = 100.0
    result = normalize_flight(sample_flight_raw, source="skyscanner")
    # USD to EUR approximate conversion — price should be different from 100
    assert result["price"] != 100.0
    assert result["price"] > 0


def test_normalize_accommodation(sample_accommodation_raw):
    result = normalize_accommodation(sample_accommodation_raw)
    assert result["city"] == "Lisbon"
    assert result["name"] == "Hotel Lisboa Plaza"
    assert result["total_price"] == 420.0
    assert result["rating"] == 4.3
    assert result["source"] == "booking"
    assert result["hash"] is not None


def test_normalize_accommodation_lowercases_city():
    raw = {
        "name": "Test Hotel",
        "city": "LISBON",
        "pricePerNight": 50.0,
        "totalPrice": 350.0,
        "currency": "EUR",
        "rating": 4.0,
        "checkIn": "2026-05-10",
        "checkOut": "2026-05-17",
        "url": "https://example.com",
        "source": "airbnb",
    }
    result = normalize_accommodation(raw)
    assert result["city"] == "Lisbon"


def test_compute_flight_hash():
    h = compute_flight_hash("CDG", "LIS", "2026-05-10", "2026-05-17", 89.0, "skyscanner")
    expected = hashlib.sha256("CDG|LIS|2026-05-10|2026-05-17|89.0|skyscanner".encode()).hexdigest()
    assert h == expected


def test_compute_accommodation_hash():
    h = compute_accommodation_hash("Lisbon", "Hotel Lisboa Plaza", "2026-05-10", "2026-05-17", 420.0, "booking")
    expected = hashlib.sha256("Lisbon|Hotel Lisboa Plaza|2026-05-10|2026-05-17|420.0|booking".encode()).hexdigest()
    assert h == expected
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_normalizer.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement normalizer**

```python
# backend/app/scraper/__init__.py
```

```python
# backend/app/scraper/normalizer.py
import hashlib
from datetime import datetime, timedelta, timezone
from app.config import settings

# Approximate conversion rates to EUR (MVP — static rates)
CURRENCY_TO_EUR = {
    "EUR": 1.0,
    "USD": 0.92,
    "GBP": 1.16,
    "CHF": 1.04,
}


def _to_eur(price: float, currency: str) -> float:
    rate = CURRENCY_TO_EUR.get(currency.upper(), 1.0)
    return round(price * rate, 2)


def _title_case_city(city: str) -> str:
    return city.strip().title()


def compute_flight_hash(
    origin: str, destination: str, departure_date: str, return_date: str, price: float, source: str
) -> str:
    raw = f"{origin}|{destination}|{departure_date}|{return_date}|{price}|{source}"
    return hashlib.sha256(raw.encode()).hexdigest()


def compute_accommodation_hash(
    city: str, name: str, check_in: str, check_out: str, total_price: float, source: str
) -> str:
    raw = f"{city}|{name}|{check_in}|{check_out}|{total_price}|{source}"
    return hashlib.sha256(raw.encode()).hexdigest()


def normalize_flight(raw: dict, source: str) -> dict:
    price = _to_eur(raw["price"], raw.get("currency", "EUR"))
    now = datetime.now(timezone.utc)
    return {
        "hash": compute_flight_hash(
            raw["origin"], raw["destination"],
            raw["departureDate"], raw["returnDate"],
            price, source,
        ),
        "origin": raw["origin"],
        "destination": raw["destination"],
        "departure_date": raw["departureDate"],
        "return_date": raw["returnDate"],
        "price": price,
        "airline": raw.get("airline"),
        "stops": raw.get("stops", 0),
        "source_url": raw.get("url"),
        "source": source,
        "scraped_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=settings.DATA_FRESHNESS_HOURS)).isoformat(),
    }


def normalize_accommodation(raw: dict) -> dict:
    price_per_night = _to_eur(raw["pricePerNight"], raw.get("currency", "EUR"))
    total_price = _to_eur(raw["totalPrice"], raw.get("currency", "EUR"))
    city = _title_case_city(raw["city"])
    now = datetime.now(timezone.utc)
    return {
        "hash": compute_accommodation_hash(
            city, raw["name"],
            raw["checkIn"], raw["checkOut"],
            total_price, raw["source"],
        ),
        "city": city,
        "name": raw["name"],
        "price_per_night": price_per_night,
        "total_price": total_price,
        "rating": raw.get("rating"),
        "check_in": raw["checkIn"],
        "check_out": raw["checkOut"],
        "source_url": raw.get("url"),
        "source": raw["source"],
        "scraped_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=settings.DATA_FRESHNESS_HOURS)).isoformat(),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_normalizer.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/scraper/ backend/tests/test_normalizer.py
git commit -m "feat: flight and accommodation normalizer with deduplication hashing"
```

---

## Task 4: Baselines calculator

**Files:**
- Create: `backend/app/analysis/__init__.py`
- Create: `backend/app/analysis/baselines.py`
- Create: `backend/tests/test_baselines.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_baselines.py
from app.analysis.baselines import compute_weighted_average, compute_baseline


def test_compute_weighted_average_simple():
    # All same age -> simple average
    prices = [100.0, 200.0, 300.0]
    ages_days = [1.0, 1.0, 1.0]
    avg, std = compute_weighted_average(prices, ages_days)
    assert avg == 200.0
    assert std > 0


def test_compute_weighted_average_recent_bias():
    # Recent price (age=1) should weigh more than old price (age=30)
    prices = [100.0, 300.0]
    ages_days = [1.0, 30.0]
    avg, _ = compute_weighted_average(prices, ages_days)
    # With weights 1/1=1.0 and 1/30=0.033, avg should be close to 100
    assert avg < 200.0  # Biased toward 100 (recent)


def test_compute_weighted_average_empty():
    avg, std = compute_weighted_average([], [])
    assert avg == 0.0
    assert std == 0.0


def test_compute_baseline_returns_dict():
    observations = [
        {"price": 150.0, "scraped_at": "2026-04-06T10:00:00+00:00"},
        {"price": 180.0, "scraped_at": "2026-04-05T10:00:00+00:00"},
        {"price": 200.0, "scraped_at": "2026-04-01T10:00:00+00:00"},
        {"price": 170.0, "scraped_at": "2026-03-30T10:00:00+00:00"},
        {"price": 190.0, "scraped_at": "2026-03-28T10:00:00+00:00"},
        {"price": 160.0, "scraped_at": "2026-03-25T10:00:00+00:00"},
        {"price": 210.0, "scraped_at": "2026-03-22T10:00:00+00:00"},
        {"price": 175.0, "scraped_at": "2026-03-20T10:00:00+00:00"},
        {"price": 195.0, "scraped_at": "2026-03-18T10:00:00+00:00"},
        {"price": 185.0, "scraped_at": "2026-03-15T10:00:00+00:00"},
    ]
    result = compute_baseline("CDG-LIS", "flight", observations)
    assert result["route_key"] == "CDG-LIS"
    assert result["type"] == "flight"
    assert result["avg_price"] > 0
    assert result["std_dev"] > 0
    assert result["sample_count"] == 10


def test_compute_baseline_insufficient_data():
    observations = [
        {"price": 150.0, "scraped_at": "2026-04-06T10:00:00+00:00"},
    ]
    result = compute_baseline("CDG-LIS", "flight", observations)
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_baselines.py -v`
Expected: FAIL

- [ ] **Step 3: Implement baselines**

```python
# backend/app/analysis/__init__.py
```

```python
# backend/app/analysis/baselines.py
from datetime import datetime, timezone
from dateutil.parser import parse as parse_date
import numpy as np

MIN_OBSERVATIONS = 10


def compute_weighted_average(prices: list[float], ages_days: list[float]) -> tuple[float, float]:
    if not prices:
        return 0.0, 0.0

    prices_arr = np.array(prices)
    ages_arr = np.array(ages_days)

    # Weight = 1 / age_in_days (more recent = higher weight)
    # Clamp minimum age to 0.1 to avoid division by zero
    weights = 1.0 / np.maximum(ages_arr, 0.1)
    weights = weights / weights.sum()

    avg = float(np.average(prices_arr, weights=weights))
    # Weighted standard deviation
    variance = float(np.average((prices_arr - avg) ** 2, weights=weights))
    std = float(np.sqrt(variance))

    return round(avg, 2), round(std, 2)


def compute_baseline(
    route_key: str, type_: str, observations: list[dict]
) -> dict | None:
    if len(observations) < MIN_OBSERVATIONS:
        return None

    now = datetime.now(timezone.utc)
    prices = []
    ages = []

    for obs in observations:
        prices.append(obs["price"])
        scraped = parse_date(obs["scraped_at"])
        age_days = max((now - scraped).total_seconds() / 86400, 0.1)
        ages.append(age_days)

    avg_price, std_dev = compute_weighted_average(prices, ages)

    return {
        "route_key": route_key,
        "type": type_,
        "avg_price": avg_price,
        "std_dev": std_dev,
        "sample_count": len(observations),
        "calculated_at": now.isoformat(),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_baselines.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/analysis/ backend/tests/test_baselines.py
git commit -m "feat: weighted baseline calculator with 30-day price averaging"
```

---

## Task 5: Anomaly detector

**Files:**
- Create: `backend/app/analysis/anomaly_detector.py`
- Create: `backend/tests/test_anomaly_detector.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_anomaly_detector.py
from app.analysis.anomaly_detector import detect_anomaly, QualifiedItem


def test_detect_anomaly_qualifies(sample_baseline_flight):
    # Price 89, baseline avg 198, std 45
    # z_score = (198 - 89) / 45 = 2.42 > 2.0
    # discount = (198 - 89) / 198 * 100 = 55.05% >= 40%
    result = detect_anomaly(price=89.0, baseline=sample_baseline_flight)
    assert result is not None
    assert isinstance(result, QualifiedItem)
    assert result.discount_pct >= 40.0
    assert result.z_score > 2.0


def test_detect_anomaly_below_z_threshold(sample_baseline_flight):
    # Price 170, baseline avg 198, std 45
    # z_score = (198 - 170) / 45 = 0.62 < 2.0
    result = detect_anomaly(price=170.0, baseline=sample_baseline_flight)
    assert result is None


def test_detect_anomaly_below_discount_threshold(sample_baseline_flight):
    # Price 130, baseline avg 198, std 45
    # z_score = (198 - 130) / 45 = 1.51 < 2.0
    # discount = (198 - 130) / 198 * 100 = 34.3% < 40%
    result = detect_anomaly(price=130.0, baseline=sample_baseline_flight)
    assert result is None


def test_detect_anomaly_zero_std_dev():
    baseline = {"avg_price": 200.0, "std_dev": 0.0, "sample_count": 15}
    result = detect_anomaly(price=100.0, baseline=baseline)
    # std_dev=0 means no variation — should not qualify (division by zero guard)
    assert result is None


def test_detect_anomaly_price_higher_than_baseline():
    baseline = {"avg_price": 100.0, "std_dev": 20.0, "sample_count": 15}
    result = detect_anomaly(price=150.0, baseline=baseline)
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_anomaly_detector.py -v`
Expected: FAIL

- [ ] **Step 3: Implement anomaly detector**

```python
# backend/app/analysis/anomaly_detector.py
from dataclasses import dataclass
from app.config import settings

Z_SCORE_THRESHOLD = 2.0


@dataclass
class QualifiedItem:
    price: float
    baseline_price: float
    discount_pct: float
    z_score: float


def detect_anomaly(price: float, baseline: dict) -> QualifiedItem | None:
    avg_price = baseline["avg_price"]
    std_dev = baseline["std_dev"]

    if std_dev <= 0:
        return None

    if price >= avg_price:
        return None

    z_score = (avg_price - price) / std_dev
    discount_pct = (avg_price - price) / avg_price * 100

    if z_score < Z_SCORE_THRESHOLD:
        return None

    if discount_pct < settings.MIN_DISCOUNT_PCT:
        return None

    return QualifiedItem(
        price=round(price, 2),
        baseline_price=round(avg_price, 2),
        discount_pct=round(discount_pct, 2),
        z_score=round(z_score, 2),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_anomaly_detector.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/analysis/anomaly_detector.py backend/tests/test_anomaly_detector.py
git commit -m "feat: z-score anomaly detector with discount qualification"
```

---

## Task 6: Scorer

**Files:**
- Create: `backend/app/analysis/scorer.py`
- Create: `backend/tests/test_scorer.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_scorer.py
from app.analysis.scorer import compute_score


def test_compute_score_high_deal():
    # 55% discount, popular destination (BCN=95), 3 alternatives, rating 4.5
    score = compute_score(
        discount_pct=55.0,
        destination_code="BCN",
        date_flexibility=3,
        accommodation_rating=4.5,
    )
    assert 70 <= score <= 100


def test_compute_score_low_deal():
    # 40% discount, unpopular destination, 0 alternatives, rating 4.0
    score = compute_score(
        discount_pct=40.0,
        destination_code="ZAG",
        date_flexibility=0,
        accommodation_rating=4.0,
    )
    assert score < 70


def test_compute_score_max_discount():
    # 60%+ discount should cap the discount component at 100
    score = compute_score(
        discount_pct=80.0,
        destination_code="BCN",
        date_flexibility=5,
        accommodation_rating=5.0,
    )
    assert score == 100


def test_compute_score_no_rating():
    # No accommodation rating (flight-only) — rating component = 0
    score = compute_score(
        discount_pct=50.0,
        destination_code="LIS",
        date_flexibility=2,
        accommodation_rating=None,
    )
    assert 0 < score < 100


def test_compute_score_unknown_destination():
    # Unknown destination gets popularity 30 (default)
    score = compute_score(
        discount_pct=50.0,
        destination_code="XXX",
        date_flexibility=2,
        accommodation_rating=4.0,
    )
    assert 0 < score < 100
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_scorer.py -v`
Expected: FAIL

- [ ] **Step 3: Implement scorer**

```python
# backend/app/analysis/scorer.py
from app.config import DESTINATION_POPULARITY

# Weights
W_DISCOUNT = 0.50
W_POPULARITY = 0.20
W_FLEXIBILITY = 0.15
W_RATING = 0.15

DEFAULT_POPULARITY = 30
MAX_FLEXIBILITY = 5  # 5+ alternatives = max flexibility score


def compute_score(
    discount_pct: float,
    destination_code: str,
    date_flexibility: int,
    accommodation_rating: float | None,
) -> int:
    # Discount component: 60% discount = max score
    discount_score = min(discount_pct / 60.0 * 100.0, 100.0)

    # Popularity component: from static table
    popularity_score = DESTINATION_POPULARITY.get(destination_code, DEFAULT_POPULARITY)

    # Flexibility component: number of alternative return dates with similar price
    flexibility_score = min(date_flexibility / MAX_FLEXIBILITY * 100.0, 100.0)

    # Rating component: rating / 5 * 100
    if accommodation_rating is not None:
        rating_score = (accommodation_rating / 5.0) * 100.0
    else:
        rating_score = 0.0

    total = (
        W_DISCOUNT * discount_score
        + W_POPULARITY * popularity_score
        + W_FLEXIBILITY * flexibility_score
        + W_RATING * rating_score
    )

    return min(round(total), 100)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_scorer.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/analysis/scorer.py backend/tests/test_scorer.py
git commit -m "feat: composite opportunity scorer (discount, popularity, flexibility, rating)"
```

---

## Task 7: Package builder

**Files:**
- Create: `backend/app/composer/__init__.py`
- Create: `backend/app/composer/package_builder.py`
- Create: `backend/tests/test_package_builder.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_package_builder.py
from app.composer.package_builder import build_packages, match_accommodations


def test_match_accommodations_finds_compatible():
    flight = {
        "destination": "LIS",
        "departure_date": "2026-05-10",
        "return_date": "2026-05-17",
    }
    accommodations = [
        {
            "id": "acc-1",
            "city": "Lisbon",
            "check_in": "2026-05-10",
            "check_out": "2026-05-17",
            "rating": 4.3,
            "total_price": 420.0,
            "source": "booking",
            "expires_at": "2026-12-31T00:00:00+00:00",
        },
        {
            "id": "acc-2",
            "city": "Lisbon",
            "check_in": "2026-05-11",  # Wrong check_in
            "check_out": "2026-05-17",
            "rating": 4.5,
            "total_price": 500.0,
            "source": "airbnb",
            "expires_at": "2026-12-31T00:00:00+00:00",
        },
    ]
    matches = match_accommodations(flight, accommodations)
    assert len(matches) == 1
    assert matches[0]["id"] == "acc-1"


def test_match_accommodations_filters_low_rating():
    flight = {
        "destination": "LIS",
        "departure_date": "2026-05-10",
        "return_date": "2026-05-17",
    }
    accommodations = [
        {
            "id": "acc-1",
            "city": "Lisbon",
            "check_in": "2026-05-10",
            "check_out": "2026-05-17",
            "rating": 3.5,  # Below 4.0
            "total_price": 300.0,
            "source": "booking",
            "expires_at": "2026-12-31T00:00:00+00:00",
        },
    ]
    matches = match_accommodations(flight, accommodations)
    assert len(matches) == 0


def test_build_packages_creates_qualified():
    flight = {
        "id": "flight-1",
        "origin": "CDG",
        "destination": "LIS",
        "departure_date": "2026-05-10",
        "return_date": "2026-05-17",
        "price": 89.0,
    }
    accommodations = [
        {
            "id": "acc-1",
            "city": "Lisbon",
            "check_in": "2026-05-10",
            "check_out": "2026-05-17",
            "rating": 4.3,
            "total_price": 420.0,
            "source": "booking",
            "expires_at": "2026-12-31T00:00:00+00:00",
        },
    ]
    flight_baseline = {"avg_price": 198.0, "std_dev": 45.0}
    accommodation_baselines = {"lisbon-booking": {"avg_price": 780.0, "std_dev": 120.0}}

    packages = build_packages(
        flight=flight,
        accommodations=accommodations,
        flight_baseline=flight_baseline,
        accommodation_baselines=accommodation_baselines,
    )
    assert len(packages) == 1
    pkg = packages[0]
    assert pkg["flight_id"] == "flight-1"
    assert pkg["accommodation_id"] == "acc-1"
    assert pkg["total_price"] == 509.0
    assert pkg["discount_pct"] >= 40.0
    assert pkg["score"] > 0


def test_build_packages_rejects_low_discount():
    flight = {
        "id": "flight-1",
        "origin": "CDG",
        "destination": "LIS",
        "departure_date": "2026-05-10",
        "return_date": "2026-05-17",
        "price": 180.0,  # Close to baseline
    }
    accommodations = [
        {
            "id": "acc-1",
            "city": "Lisbon",
            "check_in": "2026-05-10",
            "check_out": "2026-05-17",
            "rating": 4.3,
            "total_price": 700.0,  # Close to baseline
            "source": "booking",
            "expires_at": "2026-12-31T00:00:00+00:00",
        },
    ]
    flight_baseline = {"avg_price": 198.0, "std_dev": 45.0}
    accommodation_baselines = {"lisbon-booking": {"avg_price": 780.0, "std_dev": 120.0}}

    packages = build_packages(
        flight=flight,
        accommodations=accommodations,
        flight_baseline=flight_baseline,
        accommodation_baselines=accommodation_baselines,
    )
    assert len(packages) == 0


def test_build_packages_limits_to_3():
    flight = {
        "id": "flight-1",
        "origin": "CDG",
        "destination": "LIS",
        "departure_date": "2026-05-10",
        "return_date": "2026-05-17",
        "price": 50.0,
    }
    # 5 accommodations, all qualifying
    accommodations = [
        {
            "id": f"acc-{i}",
            "city": "Lisbon",
            "check_in": "2026-05-10",
            "check_out": "2026-05-17",
            "rating": 4.0 + i * 0.1,
            "total_price": 200.0 + i * 10,
            "source": "booking",
            "expires_at": "2026-12-31T00:00:00+00:00",
        }
        for i in range(5)
    ]
    flight_baseline = {"avg_price": 198.0, "std_dev": 45.0}
    accommodation_baselines = {"lisbon-booking": {"avg_price": 780.0, "std_dev": 120.0}}

    packages = build_packages(
        flight=flight,
        accommodations=accommodations,
        flight_baseline=flight_baseline,
        accommodation_baselines=accommodation_baselines,
    )
    assert len(packages) <= 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_package_builder.py -v`
Expected: FAIL

- [ ] **Step 3: Implement package builder**

```python
# backend/app/composer/__init__.py
```

```python
# backend/app/composer/package_builder.py
from datetime import datetime, timezone
from dateutil.parser import parse as parse_date
from app.config import IATA_TO_CITY, settings
from app.analysis.scorer import compute_score

MIN_RATING = 4.0
MAX_PACKAGES_PER_FLIGHT = 3


def _get_city_for_iata(code: str) -> str | None:
    return IATA_TO_CITY.get(code)


def _baseline_key(city: str, source: str) -> str:
    return f"{city.lower()}-{source}"


def match_accommodations(flight: dict, accommodations: list[dict]) -> list[dict]:
    city = _get_city_for_iata(flight["destination"])
    if not city:
        return []

    now = datetime.now(timezone.utc)
    matched = []

    for acc in accommodations:
        if acc["city"] != city:
            continue
        if acc["check_in"] != flight["departure_date"]:
            continue
        if acc["check_out"] != flight["return_date"]:
            continue
        if acc.get("rating") is not None and acc["rating"] < MIN_RATING:
            continue
        # Freshness check
        expires = parse_date(acc["expires_at"])
        if expires < now:
            continue
        matched.append(acc)

    return matched


def build_packages(
    flight: dict,
    accommodations: list[dict],
    flight_baseline: dict,
    accommodation_baselines: dict,
) -> list[dict]:
    matched = match_accommodations(flight, accommodations)
    if not matched:
        return []

    candidates = []
    now = datetime.now(timezone.utc)

    for acc in matched:
        bl_key = _baseline_key(acc["city"], acc["source"])
        acc_baseline = accommodation_baselines.get(bl_key)
        if not acc_baseline:
            continue

        total_price = flight["price"] + acc["total_price"]
        baseline_total = flight_baseline["avg_price"] + acc_baseline["avg_price"]

        if baseline_total <= 0:
            continue

        discount_pct = (baseline_total - total_price) / baseline_total * 100

        if discount_pct < settings.MIN_DISCOUNT_PCT:
            continue

        score = compute_score(
            discount_pct=discount_pct,
            destination_code=flight["destination"],
            date_flexibility=0,  # Computed separately when full data available
            accommodation_rating=acc.get("rating"),
        )

        # expires_at = min of flight and accommodation expiry
        min_expiry = min(
            parse_date(acc["expires_at"]),
            now,  # Flight freshness managed by caller
        )

        candidates.append({
            "flight_id": flight["id"],
            "origin": flight["origin"],
            "destination": flight["destination"],
            "departure_date": flight["departure_date"],
            "return_date": flight["return_date"],
            "flight_price": flight["price"],
            "accommodation_id": acc["id"],
            "accommodation_price": acc["total_price"],
            "total_price": round(total_price, 2),
            "baseline_total": round(baseline_total, 2),
            "discount_pct": round(discount_pct, 2),
            "score": score,
            "status": "active",
            "created_at": now.isoformat(),
            "expires_at": acc["expires_at"],
        })

    # Sort by score descending, keep top 3
    candidates.sort(key=lambda p: p["score"], reverse=True)
    return candidates[:MAX_PACKAGES_PER_FLIGHT]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_package_builder.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/composer/ backend/tests/test_package_builder.py
git commit -m "feat: package builder matching flights with accommodations"
```

---

## Task 8: Telegram notifications

**Files:**
- Create: `backend/app/notifications/__init__.py`
- Create: `backend/app/notifications/telegram.py`
- Create: `backend/tests/test_telegram.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_telegram.py
from unittest.mock import AsyncMock, patch
import pytest
from app.notifications.telegram import format_deal_alert, format_admin_report, format_digest


def test_format_deal_alert():
    package = {
        "origin": "CDG",
        "destination": "LIS",
        "departure_date": "2026-05-10",
        "return_date": "2026-05-17",
        "flight_price": 89.0,
        "accommodation_price": 420.0,
        "total_price": 509.0,
        "discount_pct": 47.9,
        "score": 84,
    }
    flight = {"source_url": "https://flights.example.com", "airline": "TAP Portugal"}
    accommodation = {
        "name": "Hotel Lisboa Plaza",
        "rating": 4.3,
        "source_url": "https://hotel.example.com",
    }
    msg = format_deal_alert(package, flight, accommodation)
    assert "CDG" in msg
    assert "LIS" in msg
    assert "509" in msg
    assert "47.9%" in msg or "47.9" in msg
    assert "84" in msg
    assert "Hotel Lisboa Plaza" in msg
    assert "https://flights.example.com" in msg
    assert "https://hotel.example.com" in msg


def test_format_admin_report():
    stats = {
        "flight_scrapes": 12,
        "accommodation_scrapes": 6,
        "total_flights": 2340,
        "total_accommodations": 1890,
        "errors": 2,
        "packages_qualified": 47,
        "qualification_rate": 3.2,
        "alerts_sent": 12,
        "active_baselines": 186,
    }
    msg = format_admin_report(stats)
    assert "12" in msg  # flight scrapes
    assert "47" in msg  # packages
    assert "3.2" in msg  # rate


def test_format_digest():
    packages = [
        {
            "origin": "CDG",
            "destination": "LIS",
            "total_price": 509.0,
            "discount_pct": 47.9,
            "score": 84,
            "departure_date": "2026-05-10",
            "return_date": "2026-05-17",
        },
        {
            "origin": "LYS",
            "destination": "BCN",
            "total_price": 320.0,
            "discount_pct": 52.1,
            "score": 78,
            "departure_date": "2026-05-15",
            "return_date": "2026-05-20",
        },
    ]
    msg = format_digest(packages)
    assert "CDG" in msg
    assert "LYS" in msg
    assert "Top" in msg or "top" in msg or "DIGEST" in msg
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_telegram.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Telegram module**

```python
# backend/app/notifications/__init__.py
```

```python
# backend/app/notifications/telegram.py
import logging
from datetime import datetime
from telegram import Bot
from app.config import settings

logger = logging.getLogger(__name__)


def _get_bot() -> Bot | None:
    if not settings.TELEGRAM_BOT_TOKEN:
        return None
    return Bot(token=settings.TELEGRAM_BOT_TOKEN)


def format_deal_alert(package: dict, flight: dict, accommodation: dict) -> str:
    return (
        f"✈️ GLOBE GENIUS DEAL ALERT\n\n"
        f"🌍 {package['origin']} → {package['destination']}\n"
        f"📅 Depart : {package['departure_date']} | Retour : {package['return_date']}\n"
        f"🏨 {accommodation['name']} ⭐ {accommodation.get('rating', 'N/A')}/5\n"
        f"💰 Total : {package['total_price']}€  |  🔥 -{package['discount_pct']}% vs marche\n"
        f"🎯 Score : {package['score']}/100\n\n"
        f"👉 Vol : {flight.get('source_url', 'N/A')}\n"
        f"👉 Hotel : {accommodation.get('source_url', 'N/A')}"
    )


def format_digest(packages: list[dict]) -> str:
    today = datetime.now().strftime("%d/%m/%Y")
    lines = [f"📬 GLOBE GENIUS DIGEST — {today}\n"]
    lines.append(f"Top {len(packages)} deals du jour :\n")
    for i, pkg in enumerate(packages, 1):
        lines.append(
            f"{i}. {pkg['origin']} → {pkg['destination']} | "
            f"{pkg['total_price']}€ (-{pkg['discount_pct']}%) | "
            f"Score {pkg['score']}/100 | "
            f"{pkg['departure_date']} → {pkg['return_date']}"
        )
    return "\n".join(lines)


def format_admin_report(stats: dict) -> str:
    today = datetime.now().strftime("%d/%m/%Y")
    lines = [
        f"📊 GLOBE GENIUS — Rapport {today}\n",
        f"Scrapes : {stats['flight_scrapes']} vols ✅ | {stats['accommodation_scrapes']} hebergements ✅",
        f"Donnees : {stats['total_flights']} vols | {stats['total_accommodations']} hebergements",
        f"Erreurs : {stats['errors']}",
        f"Packages qualifies : {stats['packages_qualified']} (taux : {stats['qualification_rate']}%)",
        f"Alertes envoyees : {stats['alerts_sent']}",
        f"Baselines actives : {stats['active_baselines']} routes",
    ]

    warnings = []
    if stats["qualification_rate"] < 5:
        warnings.append("⚠️ Taux qualification < 5% — surveiller les baselines")
    if stats["errors"] > 0:
        warnings.append(f"⚠️ {stats['errors']} erreurs detectees")

    if warnings:
        lines.append("")
        lines.extend(warnings)

    return "\n".join(lines)


async def send_deal_alert(chat_id: int, package: dict, flight: dict, accommodation: dict) -> bool:
    bot = _get_bot()
    if not bot:
        logger.warning("Telegram bot not configured, skipping alert")
        return False
    msg = format_deal_alert(package, flight, accommodation)
    try:
        await bot.send_message(chat_id=chat_id, text=msg)
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram alert to {chat_id}: {e}")
        return False


async def send_digest(chat_id: int, packages: list[dict]) -> bool:
    bot = _get_bot()
    if not bot:
        return False
    msg = format_digest(packages)
    try:
        await bot.send_message(chat_id=chat_id, text=msg)
        return True
    except Exception as e:
        logger.error(f"Failed to send digest to {chat_id}: {e}")
        return False


async def send_admin_report(stats: dict) -> bool:
    bot = _get_bot()
    if not bot or not settings.TELEGRAM_ADMIN_CHAT_ID:
        return False
    msg = format_admin_report(stats)
    try:
        await bot.send_message(chat_id=int(settings.TELEGRAM_ADMIN_CHAT_ID), text=msg)
        return True
    except Exception as e:
        logger.error(f"Failed to send admin report: {e}")
        return False


async def send_admin_alert(message: str) -> bool:
    bot = _get_bot()
    if not bot or not settings.TELEGRAM_ADMIN_CHAT_ID:
        return False
    try:
        await bot.send_message(chat_id=int(settings.TELEGRAM_ADMIN_CHAT_ID), text=f"🚨 {message}")
        return True
    except Exception as e:
        logger.error(f"Failed to send admin alert: {e}")
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_telegram.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/notifications/ backend/tests/test_telegram.py
git commit -m "feat: Telegram notification formatting and sending (deal alerts, digest, admin)"
```

---

## Task 9: Apify client wrapper

**Files:**
- Create: `backend/app/scraper/apify_client.py`
- Create: `backend/app/scraper/flights.py`
- Create: `backend/app/scraper/accommodations.py`

- [ ] **Step 1: Implement Apify client wrapper**

```python
# backend/app/scraper/apify_client.py
import logging
import time
from apify_client import ApifyClient
from app.config import settings

logger = logging.getLogger(__name__)

ACTOR_TIMEOUT_S = 600  # 10 minutes
POLL_INTERVAL_S = 10


def get_apify_client() -> ApifyClient:
    return ApifyClient(settings.APIFY_API_TOKEN)


def run_actor(actor_id: str, run_input: dict) -> list[dict]:
    """Run an Apify actor and return the dataset items."""
    client = get_apify_client()
    logger.info(f"Starting actor {actor_id} with input: {run_input}")

    run = client.actor(actor_id).call(run_input=run_input, timeout_secs=ACTOR_TIMEOUT_S)

    if not run:
        logger.error(f"Actor {actor_id} returned no run object")
        return []

    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        logger.error(f"Actor {actor_id} has no dataset")
        return []

    items = list(client.dataset(dataset_id).iterate_items())
    logger.info(f"Actor {actor_id} returned {len(items)} items")
    return items
```

- [ ] **Step 2: Implement flights scraper**

```python
# backend/app/scraper/flights.py
import logging
from datetime import datetime, timedelta, timezone
from app.config import settings
from app.scraper.apify_client import run_actor
from app.scraper.normalizer import normalize_flight

logger = logging.getLogger(__name__)

# Replace with actual Apify actor IDs for flight scraping
FLIGHT_ACTOR_ID = "voyager/google-flights-scraper"

SOURCES = {
    "voyager/google-flights-scraper": "google_flights",
}


def scrape_flights_for_airport(origin: str) -> list[dict]:
    """Scrape flights for a single origin airport."""
    now = datetime.now(timezone.utc)
    date_from = (now + timedelta(days=15)).strftime("%Y-%m-%d")
    date_to = (now + timedelta(days=90)).strftime("%Y-%m-%d")

    run_input = {
        "origin": origin,
        "departureDate": date_from,
        "returnDate": date_to,
        "maxStops": 1,
        "currency": "EUR",
    }

    source = SOURCES.get(FLIGHT_ACTOR_ID, "unknown")
    raw_items = run_actor(FLIGHT_ACTOR_ID, run_input)

    normalized = []
    for item in raw_items:
        try:
            normalized.append(normalize_flight(item, source=source))
        except (KeyError, TypeError) as e:
            logger.warning(f"Failed to normalize flight item: {e}")

    return normalized


def scrape_all_flights() -> tuple[list[dict], int]:
    """Scrape flights for all MVP airports. Returns (normalized_items, error_count)."""
    all_flights = []
    errors = 0

    for airport in settings.MVP_AIRPORTS:
        try:
            flights = scrape_flights_for_airport(airport)
            all_flights.extend(flights)
            logger.info(f"Scraped {len(flights)} flights from {airport}")
        except Exception as e:
            errors += 1
            logger.error(f"Failed to scrape flights from {airport}: {e}")

    return all_flights, errors
```

- [ ] **Step 3: Implement accommodations scraper**

```python
# backend/app/scraper/accommodations.py
import logging
from app.config import IATA_TO_CITY
from app.scraper.apify_client import run_actor
from app.scraper.normalizer import normalize_accommodation

logger = logging.getLogger(__name__)

# Replace with actual Apify actor IDs
ACCOMMODATION_ACTOR_ID = "voyager/booking-scraper"

SOURCES = {
    "voyager/booking-scraper": "booking",
}


def scrape_accommodations_for_city(
    city: str, check_in: str, check_out: str
) -> list[dict]:
    """Scrape accommodations for a specific city and date range."""
    run_input = {
        "city": city,
        "checkIn": check_in,
        "checkOut": check_out,
        "currency": "EUR",
        "minRating": 4.0,
    }

    raw_items = run_actor(ACCOMMODATION_ACTOR_ID, run_input)

    normalized = []
    for item in raw_items:
        try:
            normalized.append(normalize_accommodation(item))
        except (KeyError, TypeError) as e:
            logger.warning(f"Failed to normalize accommodation item: {e}")

    return normalized


def scrape_accommodations_for_destinations(destinations: set[str]) -> tuple[list[dict], int]:
    """Scrape accommodations for a set of destination IATA codes.
    Returns (normalized_items, error_count)."""
    all_accommodations = []
    errors = 0

    for iata_code in destinations:
        city = IATA_TO_CITY.get(iata_code)
        if not city:
            logger.warning(f"No city mapping for IATA code {iata_code}, skipping")
            continue

        try:
            # For MVP, scrape a generic date range — actual dates will be refined
            # when we have flight data to match against
            items = scrape_accommodations_for_city(city, "", "")
            all_accommodations.extend(items)
            logger.info(f"Scraped {len(items)} accommodations in {city}")
        except Exception as e:
            errors += 1
            logger.error(f"Failed to scrape accommodations in {city}: {e}")

    return all_accommodations, errors
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/scraper/
git commit -m "feat: Apify client wrapper with flight and accommodation scrapers"
```

---

## Task 10: Scheduler jobs

**Files:**
- Create: `backend/app/scheduler/__init__.py`
- Create: `backend/app/scheduler/jobs.py`
- Create: `backend/tests/test_jobs.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_jobs.py
from unittest.mock import patch, MagicMock
from app.scheduler.jobs import get_scheduler_jobs


def test_get_scheduler_jobs_returns_all_jobs():
    jobs = get_scheduler_jobs()
    job_names = [j["id"] for j in jobs]
    assert "scrape_flights" in job_names
    assert "scrape_accommodations" in job_names
    assert "recalculate_baselines" in job_names
    assert "expire_stale_data" in job_names
    assert "daily_digest" in job_names
    assert "daily_admin_report" in job_names


def test_get_scheduler_jobs_has_correct_intervals():
    jobs = get_scheduler_jobs()
    jobs_by_id = {j["id"]: j for j in jobs}
    assert jobs_by_id["scrape_flights"]["hours"] == 2
    assert jobs_by_id["scrape_accommodations"]["hours"] == 4
    assert jobs_by_id["expire_stale_data"]["minutes"] == 30
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_jobs.py -v`
Expected: FAIL

- [ ] **Step 3: Implement scheduler jobs**

```python
# backend/app/scheduler/__init__.py
```

```python
# backend/app/scheduler/jobs.py
import logging
from datetime import datetime, timezone
from app.config import settings
from app.db import db
from app.scraper.flights import scrape_all_flights
from app.scraper.accommodations import scrape_accommodations_for_destinations
from app.analysis.baselines import compute_baseline
from app.analysis.anomaly_detector import detect_anomaly
from app.analysis.scorer import compute_score
from app.composer.package_builder import build_packages
from app.notifications.telegram import (
    send_deal_alert,
    send_digest,
    send_admin_report,
    send_admin_alert,
)

logger = logging.getLogger(__name__)


def get_scheduler_jobs() -> list[dict]:
    """Return job definitions for APScheduler."""
    return [
        {
            "id": "scrape_flights",
            "func": job_scrape_flights,
            "trigger": "interval",
            "hours": settings.SCRAPE_FLIGHTS_INTERVAL_HOURS,
        },
        {
            "id": "scrape_accommodations",
            "func": job_scrape_accommodations,
            "trigger": "interval",
            "hours": settings.SCRAPE_ACCOMMODATIONS_INTERVAL_HOURS,
        },
        {
            "id": "recalculate_baselines",
            "func": job_recalculate_baselines,
            "trigger": "cron",
            "hour": settings.BASELINE_RECALC_HOUR,
        },
        {
            "id": "expire_stale_data",
            "func": job_expire_stale_data,
            "trigger": "interval",
            "minutes": 30,
        },
        {
            "id": "daily_digest",
            "func": job_daily_digest,
            "trigger": "cron",
            "hour": settings.DIGEST_HOUR,
        },
        {
            "id": "daily_admin_report",
            "func": job_daily_admin_report,
            "trigger": "cron",
            "hour": 9,
        },
    ]


async def job_scrape_flights():
    """Scrape flights for all MVP airports, normalize, insert, and analyze."""
    logger.info("Starting flight scraping job")
    started_at = datetime.now(timezone.utc)

    flights, errors = scrape_all_flights()

    if not db:
        logger.warning("No database connection, skipping insert")
        return

    inserted = 0
    for flight in flights:
        try:
            db.table("raw_flights").upsert(flight, on_conflict="hash").execute()
            inserted += 1
        except Exception as e:
            logger.warning(f"Failed to insert flight: {e}")
            errors += 1

    completed_at = datetime.now(timezone.utc)
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)

    status = "success" if errors == 0 else ("partial" if inserted > 0 else "failed")
    db.table("scrape_logs").insert({
        "actor_id": "flights",
        "source": "google_flights",
        "type": "flights",
        "items_count": inserted,
        "errors_count": errors,
        "duration_ms": duration_ms,
        "status": status,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
    }).execute()

    logger.info(f"Flight scraping complete: {inserted} inserted, {errors} errors")

    # Trigger anomaly detection on new data
    await _analyze_new_flights(flights)


async def _analyze_new_flights(flights: list[dict]):
    """Run anomaly detection and package composition on newly scraped flights."""
    if not db:
        return

    for flight in flights:
        route_key = f"{flight['origin']}-{flight['destination']}"
        baseline_resp = db.table("price_baselines").select("*").eq("route_key", route_key).eq("type", "flight").execute()
        if not baseline_resp.data:
            continue

        baseline = baseline_resp.data[0]
        anomaly = detect_anomaly(price=flight["price"], baseline=baseline)

        if anomaly:
            score = compute_score(
                discount_pct=anomaly.discount_pct,
                destination_code=flight["destination"],
                date_flexibility=0,
                accommodation_rating=None,
            )

            # Insert as qualified item
            db.table("qualified_items").insert({
                "type": "flight",
                "item_id": flight.get("id", ""),
                "price": anomaly.price,
                "baseline_price": anomaly.baseline_price,
                "discount_pct": anomaly.discount_pct,
                "score": score,
                "status": "active",
            }).execute()

            # Try to compose packages
            await _compose_packages_for_flight(flight, baseline)


async def _compose_packages_for_flight(flight: dict, flight_baseline: dict):
    """Find matching accommodations and build packages for a qualified flight."""
    if not db:
        return

    from app.config import IATA_TO_CITY
    city = IATA_TO_CITY.get(flight["destination"])
    if not city:
        return

    acc_resp = (
        db.table("raw_accommodations")
        .select("*")
        .eq("city", city)
        .eq("check_in", flight["departure_date"])
        .eq("check_out", flight["return_date"])
        .gte("rating", 4.0)
        .gte("expires_at", datetime.now(timezone.utc).isoformat())
        .execute()
    )

    if not acc_resp.data:
        return

    # Fetch accommodation baselines
    acc_baselines = {}
    for acc in acc_resp.data:
        bl_key = f"{acc['city'].lower()}-{acc['source']}"
        if bl_key not in acc_baselines:
            bl_resp = db.table("price_baselines").select("*").eq("route_key", bl_key).eq("type", "accommodation").execute()
            if bl_resp.data:
                acc_baselines[bl_key] = bl_resp.data[0]

    packages = build_packages(
        flight=flight,
        accommodations=acc_resp.data,
        flight_baseline=flight_baseline,
        accommodation_baselines=acc_baselines,
    )

    for pkg in packages:
        db.table("packages").insert(pkg).execute()

        # Send Telegram alert if score >= threshold
        if pkg["score"] >= settings.MIN_SCORE_ALERT:
            subscribers = (
                db.table("telegram_subscribers")
                .select("chat_id")
                .eq("airport_code", pkg["origin"])
                .lte("min_score", pkg["score"])
                .execute()
            )
            flight_data = db.table("raw_flights").select("source_url,airline").eq("id", pkg["flight_id"]).execute()
            acc_data = db.table("raw_accommodations").select("name,rating,source_url").eq("id", pkg["accommodation_id"]).execute()

            if flight_data.data and acc_data.data and subscribers.data:
                for sub in subscribers.data:
                    await send_deal_alert(sub["chat_id"], pkg, flight_data.data[0], acc_data.data[0])


async def job_scrape_accommodations():
    """Scrape accommodations for destinations seen in recent flights."""
    logger.info("Starting accommodation scraping job")
    if not db:
        return

    # Get unique destinations from recent flights
    flights_resp = (
        db.table("raw_flights")
        .select("destination")
        .gte("expires_at", datetime.now(timezone.utc).isoformat())
        .execute()
    )
    destinations = {f["destination"] for f in (flights_resp.data or [])}

    if not destinations:
        logger.info("No active flight destinations, skipping accommodation scrape")
        return

    started_at = datetime.now(timezone.utc)
    accommodations, errors = scrape_accommodations_for_destinations(destinations)

    inserted = 0
    for acc in accommodations:
        try:
            db.table("raw_accommodations").upsert(acc, on_conflict="hash").execute()
            inserted += 1
        except Exception as e:
            logger.warning(f"Failed to insert accommodation: {e}")
            errors += 1

    completed_at = datetime.now(timezone.utc)
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)

    status = "success" if errors == 0 else ("partial" if inserted > 0 else "failed")
    db.table("scrape_logs").insert({
        "actor_id": "accommodations",
        "source": "booking",
        "type": "accommodations",
        "items_count": inserted,
        "errors_count": errors,
        "duration_ms": duration_ms,
        "status": status,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
    }).execute()

    logger.info(f"Accommodation scraping complete: {inserted} inserted, {errors} errors")


async def job_recalculate_baselines():
    """Recalculate 30-day price baselines for all routes."""
    logger.info("Starting baseline recalculation")
    if not db:
        return

    now = datetime.now(timezone.utc)
    thirty_days_ago = (now - __import__("datetime").timedelta(days=30)).isoformat()

    # Flight baselines
    flights_resp = (
        db.table("raw_flights")
        .select("origin, destination, price, scraped_at")
        .gte("scraped_at", thirty_days_ago)
        .execute()
    )

    routes: dict[str, list] = {}
    for f in (flights_resp.data or []):
        key = f"{f['origin']}-{f['destination']}"
        routes.setdefault(key, []).append({"price": f["price"], "scraped_at": f["scraped_at"]})

    for route_key, observations in routes.items():
        baseline = compute_baseline(route_key, "flight", observations)
        if baseline:
            db.table("price_baselines").upsert(baseline, on_conflict="route_key").execute()

    # Accommodation baselines
    acc_resp = (
        db.table("raw_accommodations")
        .select("city, source, total_price, scraped_at")
        .gte("scraped_at", thirty_days_ago)
        .execute()
    )

    acc_routes: dict[str, list] = {}
    for a in (acc_resp.data or []):
        key = f"{a['city'].lower()}-{a['source']}"
        acc_routes.setdefault(key, []).append({"price": a["total_price"], "scraped_at": a["scraped_at"]})

    for route_key, observations in acc_routes.items():
        baseline = compute_baseline(route_key, "accommodation", observations)
        if baseline:
            db.table("price_baselines").upsert(baseline, on_conflict="route_key").execute()

    logger.info(f"Baselines recalculated: {len(routes)} flight routes, {len(acc_routes)} accommodation routes")


async def job_expire_stale_data():
    """Mark expired packages and qualified items."""
    if not db:
        return
    now = datetime.now(timezone.utc).isoformat()

    db.table("packages").update({"status": "expired"}).eq("status", "active").lt("expires_at", now).execute()
    db.table("qualified_items").update({"status": "expired"}).eq("status", "active").execute()

    logger.info("Expired stale packages and qualified items")


async def job_daily_digest():
    """Send daily digest of top deals to subscribers."""
    if not db:
        return

    packages_resp = (
        db.table("packages")
        .select("*")
        .eq("status", "active")
        .gte("score", settings.MIN_SCORE_DIGEST)
        .order("score", desc=True)
        .limit(5)
        .execute()
    )

    if not packages_resp.data:
        return

    subscribers = db.table("telegram_subscribers").select("chat_id").execute()
    for sub in (subscribers.data or []):
        await send_digest(sub["chat_id"], packages_resp.data)


async def job_daily_admin_report():
    """Send daily admin report with pipeline stats."""
    if not db:
        return

    now = datetime.now(timezone.utc)
    yesterday = (now - __import__("datetime").timedelta(days=1)).isoformat()

    logs = db.table("scrape_logs").select("*").gte("started_at", yesterday).execute()
    log_data = logs.data or []

    flight_scrapes = sum(1 for l in log_data if l["type"] == "flights")
    acc_scrapes = sum(1 for l in log_data if l["type"] == "accommodations")
    total_flights = sum(l.get("items_count", 0) for l in log_data if l["type"] == "flights")
    total_acc = sum(l.get("items_count", 0) for l in log_data if l["type"] == "accommodations")
    errors = sum(l.get("errors_count", 0) for l in log_data)

    packages_resp = db.table("packages").select("id", count="exact").gte("created_at", yesterday).execute()
    pkg_count = packages_resp.count or 0

    total_scraped = total_flights + total_acc
    qual_rate = round(pkg_count / total_scraped * 100, 1) if total_scraped > 0 else 0

    baselines_resp = db.table("price_baselines").select("id", count="exact").execute()

    stats = {
        "flight_scrapes": flight_scrapes,
        "accommodation_scrapes": acc_scrapes,
        "total_flights": total_flights,
        "total_accommodations": total_acc,
        "errors": errors,
        "packages_qualified": pkg_count,
        "qualification_rate": qual_rate,
        "alerts_sent": 0,  # TODO: track in a counter table in phase 2
        "active_baselines": baselines_resp.count or 0,
    }

    await send_admin_report(stats)

    # Check monitoring thresholds
    if qual_rate < 5 and total_scraped > 0:
        await send_admin_alert(f"Taux qualification bas : {qual_rate}%")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_jobs.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/scheduler/ backend/tests/test_jobs.py
git commit -m "feat: APScheduler job definitions for scraping, baselines, expiry, and notifications"
```

---

## Task 11: API routes

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/routes.py`
- Create: `backend/tests/test_routes.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_routes.py
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_status():
    with patch("app.api.routes.db") as mock_db:
        # Mock scrape_logs query
        mock_db.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[], count=0)

        response = client.get("/api/status")
        assert response.status_code == 200


def test_packages_list():
    with patch("app.api.routes.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "pkg-1", "score": 80}]
        )
        response = client.get("/api/packages")
        assert response.status_code == 200


def test_packages_detail_not_found():
    with patch("app.api.routes.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        response = client.get("/api/packages/nonexistent-id")
        assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_routes.py -v`
Expected: FAIL

- [ ] **Step 3: Implement API routes**

```python
# backend/app/api/__init__.py
```

```python
# backend/app/api/routes.py
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from app.db import db

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/api/status")
def status():
    if not db:
        return {"status": "no_database"}

    # Last scrape logs
    logs = (
        db.table("scrape_logs")
        .select("*")
        .order("started_at", desc=True)
        .limit(10)
        .execute()
    )

    # Active counts
    active_packages = db.table("packages").select("id", count="exact").eq("status", "active").execute()
    active_baselines = db.table("price_baselines").select("id", count="exact").execute()

    return {
        "status": "ok",
        "recent_scrapes": logs.data or [],
        "active_packages": active_packages.count or 0,
        "active_baselines": active_baselines.count or 0,
    }


@router.get("/api/packages")
def list_packages(min_score: int = 0, limit: int = 20):
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    resp = (
        db.table("packages")
        .select("*")
        .eq("status", "active")
        .gte("score", min_score)
        .order("score", desc=True)
        .limit(limit)
        .execute()
    )
    return {"packages": resp.data or []}


@router.get("/api/packages/{package_id}")
def get_package(package_id: str):
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    resp = db.table("packages").select("*").eq("id", package_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Package not found")
    return resp.data[0]


@router.get("/api/qualified-items")
def list_qualified_items(type_filter: str = "", limit: int = 20):
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    query = db.table("qualified_items").select("*").eq("status", "active")
    if type_filter:
        query = query.eq("type", type_filter)
    resp = query.order("score", desc=True).limit(limit).execute()
    return {"items": resp.data or []}


@router.post("/api/trigger/{job_name}")
async def trigger_job(job_name: str):
    from app.scheduler.jobs import (
        job_scrape_flights,
        job_scrape_accommodations,
        job_recalculate_baselines,
        job_expire_stale_data,
    )

    jobs = {
        "scrape_flights": job_scrape_flights,
        "scrape_accommodations": job_scrape_accommodations,
        "recalculate_baselines": job_recalculate_baselines,
        "expire_stale_data": job_expire_stale_data,
    }

    if job_name not in jobs:
        raise HTTPException(status_code=404, detail=f"Unknown job: {job_name}")

    asyncio.create_task(jobs[job_name]())
    return {"status": "triggered", "job": job_name}
```

- [ ] **Step 4: Implement main.py (FastAPI app with lifespan)**

```python
# backend/app/main.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.api.routes import router
from app.scheduler.jobs import get_scheduler_jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: register and start scheduler jobs
    for job_def in get_scheduler_jobs():
        job_id = job_def["id"]
        func = job_def["func"]
        trigger = job_def["trigger"]

        if trigger == "interval":
            kwargs = {}
            if "hours" in job_def:
                kwargs["hours"] = job_def["hours"]
            if "minutes" in job_def:
                kwargs["minutes"] = job_def["minutes"]
            scheduler.add_job(func, "interval", id=job_id, **kwargs)
        elif trigger == "cron":
            scheduler.add_job(func, "cron", id=job_id, hour=job_def.get("hour", 0))

    scheduler.start()
    logger.info(f"Scheduler started with {len(scheduler.get_jobs())} jobs")

    yield

    # Shutdown
    scheduler.shutdown()
    logger.info("Scheduler shut down")


app = FastAPI(
    title="Globe Genius Pipeline",
    description="Travel deal detection pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_routes.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/ backend/app/main.py backend/tests/test_routes.py
git commit -m "feat: FastAPI app with API routes and APScheduler lifespan"
```

---

## Task 12: Dockerfile and final wiring

**Files:**
- Create: `backend/Dockerfile`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Run all tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 3: Test the app starts locally**

Run: `cd backend && timeout 5 uvicorn app.main:app --port 8000 || true`
Expected: App starts without import errors (will timeout after 5s, that's fine)

- [ ] **Step 4: Commit**

```bash
git add backend/Dockerfile
git commit -m "feat: Dockerfile for production deployment"
```

---

## Task 13: Run full migration on Supabase

- [ ] **Step 1: Run SQL migration**

Go to Supabase dashboard → SQL Editor → paste contents of `backend/supabase/migrations/001_create_tables.sql` → Run.

- [ ] **Step 2: Verify tables exist**

In Supabase dashboard, check that all 7 tables are created: `raw_flights`, `raw_accommodations`, `price_baselines`, `packages`, `qualified_items`, `scrape_logs`, `telegram_subscribers`.

- [ ] **Step 3: Configure .env**

Copy `backend/.env.example` to `backend/.env` and fill in:
- `APIFY_API_TOKEN` — from Apify dashboard
- `SUPABASE_URL` — from Supabase project settings
- `SUPABASE_SERVICE_KEY` — from Supabase project settings → API → service_role key
- `TELEGRAM_BOT_TOKEN` — create bot via @BotFather on Telegram
- `TELEGRAM_ADMIN_CHAT_ID` — your Telegram chat ID

- [ ] **Step 4: Smoke test with real services**

Run: `cd backend && uvicorn app.main:app --port 8000`
Then: `curl http://localhost:8000/health`
Expected: `{"status": "ok", "timestamp": "..."}`

Then: `curl http://localhost:8000/api/status`
Expected: `{"status": "ok", "recent_scrapes": [], "active_packages": 0, "active_baselines": 0}`

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: project ready for deployment with all pipeline components"
```
