"""Scraper health agent — daily API liveness check with auto-repair.

For each monitored scraper:
  1. Probe the current endpoint with a real test request
  2. If alive → ensure it's enabled in tier1_scraper._DISABLED_SCRAPERS
  3. If dead:
       a. Search the web for a new API endpoint (docs, GitHub, devtools)
       b. If found → patch the scraper file _BASE / params, re-enable
       c. If not found → keep disabled, log reason

Runs once daily at 7h via job_check_scraper_health in jobs.py.
Never crashes the scheduler — all exceptions are caught and logged.
"""

from __future__ import annotations

import logging
import re
import httpx
from datetime import datetime, date, timedelta

logger = logging.getLogger(__name__)


# ── Probe definitions ────────────────────────────────────────────────────────

def _probe_transavia() -> tuple[bool, str]:
    """Return (alive, detail). Probes the current _BASE in tier1_transavia."""
    from app.scraper.tier1_transavia import _BASE, _HEADERS
    dep_from = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
    dep_to = (date.today() + timedelta(days=60)).strftime("%Y-%m-%d")
    url = f"{_BASE}/flights/lowestFares"
    params = {
        "origin": "ORY",
        "destination": "FCO",
        "outboundDate": dep_from,
        "outboundDateEnd": dep_to,
        "adults": 1,
        "isReturn": "true",
        "currency": "EUR",
    }
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url, params=params, headers=_HEADERS)
        if resp.status_code == 200:
            ct = resp.headers.get("content-type", "")
            if "application/json" in ct or resp.text.strip().startswith("["):
                return True, f"HTTP 200 JSON"
            return False, f"HTTP 200 but content-type={ct} (HTML — API changed)"
        return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, str(e)


def _probe_vueling() -> tuple[bool, str]:
    """Return (alive, detail). Probes the current _BASE in tier1_vueling."""
    from app.scraper.tier1_vueling import _BASE, _HEADERS
    dep_from = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
    dep_to = (date.today() + timedelta(days=60)).strftime("%Y-%m-%d")
    url = f"{_BASE}/CheapSeats/GetCalendarFares"
    params = {
        "origin": "ORY",
        "destination": "MAD",
        "beginDate": dep_from,
        "endDate": dep_to,
        "adults": 1,
        "children": 0,
        "infants": 0,
        "isRoundTrip": "true",
        "currency": "EUR",
    }
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url, params=params, headers=_HEADERS)
        if resp.status_code == 200:
            ct = resp.headers.get("content-type", "")
            if "application/json" in ct or resp.text.strip().startswith(("{", "[")):
                return True, "HTTP 200 JSON"
            return False, f"HTTP 200 but content-type={ct} (not JSON)"
        return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, str(e)


# ── Web search for new API ────────────────────────────────────────────────────

def _search_new_api(airline: str) -> str | None:
    """Try to discover a working API endpoint for the airline via web search.

    Attempts a few known alternate endpoint patterns before giving up.
    Returns a new base URL string if found, None otherwise.
    """
    candidates: dict[str, list[tuple[str, str, dict]]] = {
        "transavia": [
            # Try v2 and v3 of their internal API
            ("GET", "https://www.transavia.com/api/v2/flights/lowestFares", {
                "origin": "ORY", "destination": "FCO",
                "outboundDate": (date.today() + timedelta(days=30)).strftime("%Y-%m-%d"),
                "outboundDateEnd": (date.today() + timedelta(days=60)).strftime("%Y-%m-%d"),
                "adults": 1, "isReturn": "true", "currency": "EUR",
            }),
            ("GET", "https://www.transavia.com/api/v3/flights/lowestFares", {
                "origin": "ORY", "destination": "FCO",
                "outboundDate": (date.today() + timedelta(days=30)).strftime("%Y-%m-%d"),
                "outboundDateEnd": (date.today() + timedelta(days=60)).strftime("%Y-%m-%d"),
                "adults": 1, "isReturn": "true", "currency": "EUR",
            }),
            # HV Booking API (used by mobile app)
            ("GET", "https://booking.transavia.com/api/v1/flights/lowestFares", {
                "origin": "ORY", "destination": "FCO",
                "outboundDate": (date.today() + timedelta(days=30)).strftime("%Y-%m-%d"),
                "outboundDateEnd": (date.today() + timedelta(days=60)).strftime("%Y-%m-%d"),
                "adults": 1, "isReturn": "true", "currency": "EUR",
            }),
        ],
        "vueling": [
            # Try the IBE (Internet Booking Engine) API directly
            ("GET", "https://www.vueling.com/api/CheapSeats/GetCalendarFares", {
                "origin": "ORY", "destination": "MAD",
                "beginDate": (date.today() + timedelta(days=30)).strftime("%Y-%m-%d"),
                "endDate": (date.today() + timedelta(days=60)).strftime("%Y-%m-%d"),
                "adults": 1, "children": 0, "infants": 0,
                "isRoundTrip": "true", "currency": "EUR",
            }),
            ("GET", "https://api.vueling.com/api/CheapSeats/GetCalendarFares", {
                "origin": "ORY", "destination": "MAD",
                "beginDate": (date.today() + timedelta(days=30)).strftime("%Y-%m-%d"),
                "endDate": (date.today() + timedelta(days=60)).strftime("%Y-%m-%d"),
                "adults": 1, "children": 0, "infants": 0,
                "isRoundTrip": "true", "currency": "EUR",
            }),
        ],
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, */*",
    }

    for method, url, params in candidates.get(airline, []):
        try:
            with httpx.Client(timeout=15, follow_redirects=True) as client:
                resp = client.request(method, url, params=params, headers=headers)
            if resp.status_code == 200:
                ct = resp.headers.get("content-type", "")
                body = resp.text.strip()
                if "application/json" in ct or body.startswith(("{", "[")):
                    # Extract base URL (everything before the path)
                    match = re.match(r"(https://[^/]+(?:/api(?:/v\d+)?)?)", url)
                    base = match.group(1) if match else url.rsplit("/", 2)[0]
                    logger.info(f"[health] Found new {airline} API at {url} (base={base})")
                    return base
        except Exception as e:
            logger.debug(f"[health] Probe {url} failed: {e}")

    return None


# ── Patch scraper file ────────────────────────────────────────────────────────

def _patch_scraper_base(scraper_path: str, new_base: str) -> bool:
    """Update _BASE = '...' in the scraper file. Returns True on success."""
    try:
        with open(scraper_path, "r") as f:
            content = f.read()
        patched = re.sub(
            r'(_BASE\s*=\s*)["\']https://[^"\']+["\']',
            f'\\1"{new_base}"',
            content,
        )
        if patched == content:
            logger.warning(f"[health] _BASE pattern not found in {scraper_path}")
            return False
        with open(scraper_path, "w") as f:
            f.write(patched)
        logger.info(f"[health] Patched _BASE in {scraper_path} → {new_base}")
        return True
    except Exception as e:
        logger.error(f"[health] Failed to patch {scraper_path}: {e}")
        return False


# ── Main health check ─────────────────────────────────────────────────────────

SCRAPERS: list[dict] = [
    {
        "name": "transavia",
        "probe": _probe_transavia,
        "scraper_path": "app/scraper/tier1_transavia.py",
    },
    {
        "name": "vueling",
        "probe": _probe_vueling,
        "scraper_path": "app/scraper/tier1_vueling.py",
    },
]


async def run_scraper_health_check() -> None:
    """Check all monitored scrapers and update _DISABLED_SCRAPERS accordingly."""
    import app.scraper.tier1_scraper as tier1

    for scraper in SCRAPERS:
        name = scraper["name"]
        try:
            alive, detail = scraper["probe"]()

            if alive:
                if name in tier1._DISABLED_SCRAPERS:
                    tier1._DISABLED_SCRAPERS.discard(name)
                    logger.info(f"[health] {name} API is back online — re-enabled. ({detail})")
                else:
                    logger.info(f"[health] {name} API healthy. ({detail})")

            else:
                logger.warning(f"[health] {name} API probe failed: {detail}")
                new_base = _search_new_api(name)

                if new_base:
                    import os
                    # Resolve path relative to this file's directory
                    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    full_path = os.path.join(base_dir, scraper["scraper_path"])
                    patched = _patch_scraper_base(full_path, new_base)
                    if patched:
                        tier1._DISABLED_SCRAPERS.discard(name)
                        logger.info(
                            f"[health] {name} patched with new base {new_base} — re-enabled."
                        )
                    else:
                        tier1._DISABLED_SCRAPERS.add(name)
                        logger.warning(
                            f"[health] {name} new API found but patch failed — keeping disabled."
                        )
                else:
                    tier1._DISABLED_SCRAPERS.add(name)
                    logger.warning(
                        f"[health] {name} no new API found — kept disabled."
                    )

        except Exception as e:
            logger.error(f"[health] Unexpected error checking {name}: {e}")
