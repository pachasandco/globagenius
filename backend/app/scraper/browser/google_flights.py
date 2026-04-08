"""Scrape Google Flights using Playwright + LLM extraction.
Inspired by Fairtrail approach: browser → visible text → LLM → structured data.
Includes content hash cache to avoid redundant LLM calls."""

import json
import hashlib
import logging
from datetime import datetime, timezone
from app.config import settings
from app.agents.llm_client import get_client
from app.scraper.browser.stealth import create_browser, create_stealth_context, navigate_and_extract

# Cache: hash of page text → extracted result. Avoids re-calling LLM if page content unchanged.
_extraction_cache: dict[str, dict] = {}
_CACHE_MAX_SIZE = 200

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Tu recois le texte visible d'une page Google Flights. Extrais TOUS les vols affiches.

Pour chaque vol, retourne :
- price: prix en euros (nombre)
- airline: compagnie aerienne
- departure_time: heure de depart
- arrival_time: heure d'arrivee
- duration: duree du vol
- stops: nombre d'escales (0 = direct)
- origin: code IATA depart
- destination: code IATA arrivee

Extrais aussi les "price insights" si presents :
- typical_low: prix bas habituel
- typical_high: prix haut habituel
- price_level: "low", "typical", ou "high"

Reponds UNIQUEMENT en JSON :
{
  "flights": [...],
  "price_insights": {"typical_low": X, "typical_high": Y, "price_level": "..."}
}

Si tu ne trouves pas de vols, retourne {"flights": [], "price_insights": null}"""


def _build_flights_url(origin: str, destination: str, dep_date: str, ret_date: str, currency: str = "EUR") -> str:
    """Build Google Flights search URL (same format as Fairtrail)."""
    return (
        f"https://www.google.com/travel/flights?"
        f"q=flights+from+{origin}+to+{destination}"
        f"+on+{dep_date}+to+{ret_date}"
        f"&curr={currency}&hl=en"
    )


async def scrape_flights_page(origin: str, destination: str, dep_date: str, ret_date: str) -> dict | None:
    """Scrape a single Google Flights search page.
    Returns {"flights": [...], "price_insights": {...}} or None."""

    url = _build_flights_url(origin, destination, dep_date, ret_date)
    logger.info(f"Scraping Google Flights: {origin}→{destination} {dep_date}")

    browser = None
    pw = None
    try:
        browser, pw = await create_browser()
        context = await create_stealth_context(browser)
        page = await context.new_page()

        # [data-gs] is the flight result container on Google Flights (from Fairtrail)
        text = await navigate_and_extract(page, url, "[data-gs]", timeout=20000)

        if not text or len(text) < 50:
            logger.warning(f"No content extracted for {origin}→{destination}")
            return None

        logger.info(f"Extracted {len(text)} chars for {origin}→{destination}")

        # Truncate to ~4KB for LLM (like Fairtrail)
        if len(text) > 4000:
            text = text[:4000]

        # Check cache — skip LLM if same page content
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in _extraction_cache:
            logger.info(f"Cache hit for {origin}→{destination}, skipping LLM call")
            return _extraction_cache[text_hash]

        # Extract with Claude Haiku (fast + cheap)
        result = _extract_with_llm(text, origin, destination, dep_date, ret_date)

        # Cache the result
        if result and len(_extraction_cache) < _CACHE_MAX_SIZE:
            _extraction_cache[text_hash] = result
        return result

    except Exception as e:
        logger.error(f"Scrape failed for {origin}→{destination}: {e}")
        return None
    finally:
        if browser:
            await browser.close()
        if pw:
            await pw.stop()


def _extract_with_llm(text: str, origin: str, destination: str, dep_date: str, ret_date: str) -> dict | None:
    """Use Claude Haiku to extract flight data from visible text."""
    client = get_client()
    if not client:
        logger.warning("No ANTHROPIC_API_KEY, skipping LLM extraction")
        return None

    user_msg = f"Route: {origin} → {destination}\nDates: {dep_date} → {ret_date}\n\nTexte de la page:\n{text}"

    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1500,
            system=EXTRACTION_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )

        result_text = response.content[0].text.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()

        data = json.loads(result_text)

        # Add metadata
        for flight in data.get("flights", []):
            flight.setdefault("origin", origin)
            flight.setdefault("destination", destination)
            flight.setdefault("departureDate", dep_date)
            flight.setdefault("returnDate", ret_date)
            flight.setdefault("currency", "EUR")
            flight.setdefault("url", _build_flights_url(origin, destination, dep_date, ret_date))
            flight.setdefault("stops", 0)

        return data

    except json.JSONDecodeError as e:
        logger.error(f"LLM returned invalid JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}")
        return None
