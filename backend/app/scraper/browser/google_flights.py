"""Scrape Google Flights using Playwright + LLM extraction.
Inspired by Fairtrail approach: browser → visible text → LLM → structured data."""

import json
import logging
from datetime import datetime, timezone
from anthropic import Anthropic
from app.config import settings
from app.scraper.browser.stealth import create_browser, create_stealth_context, navigate_and_extract

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
    """Build Google Flights search URL."""
    return (
        f"https://www.google.com/travel/flights?"
        f"q=flights+from+{origin}+to+{destination}"
        f"+on+{dep_date}+to+{ret_date}"
        f"&curr={currency}&gl=FR&hl=fr"
    )


async def scrape_flights_page(origin: str, destination: str, dep_date: str, ret_date: str) -> dict | None:
    """Scrape a single Google Flights search page.
    Returns {"flights": [...], "price_insights": {...}} or None."""

    url = _build_flights_url(origin, destination, dep_date, ret_date)
    logger.info(f"Scraping Google Flights: {origin}→{destination} {dep_date}")

    browser = None
    try:
        browser = await create_browser()
        context = await create_stealth_context(browser)
        page = await context.new_page()

        # Google Flights uses [data-gs] for flight results, but we use a broader selector
        text = await navigate_and_extract(page, url, "div[class*='result'], li[class*='flight']", timeout=25000)

        if not text or len(text) < 100:
            logger.warning(f"No content extracted for {origin}→{destination}")
            return None

        # Truncate to ~4KB for LLM (like Fairtrail)
        if len(text) > 4000:
            text = text[:4000]

        # Extract with Claude Haiku (fast + cheap)
        result = _extract_with_llm(text, origin, destination, dep_date, ret_date)
        return result

    except Exception as e:
        logger.error(f"Scrape failed for {origin}→{destination}: {e}")
        return None
    finally:
        if browser:
            await browser.close()


def _extract_with_llm(text: str, origin: str, destination: str, dep_date: str, ret_date: str) -> dict | None:
    """Use Claude Haiku to extract flight data from visible text."""
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("No ANTHROPIC_API_KEY, skipping LLM extraction")
        return None

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

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
