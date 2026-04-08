"""Scrape Google Hotels using Playwright + LLM extraction."""

import json
import logging
from datetime import datetime, timezone
from anthropic import Anthropic
from app.config import settings
from app.scraper.browser.stealth import create_browser, create_stealth_context, navigate_and_extract

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Tu recois le texte visible d'une page Google Hotels. Extrais TOUS les hotels affiches.

Pour chaque hotel, retourne :
- name: nom de l'hotel
- price_per_night: prix par nuit en euros (nombre)
- total_price: prix total du sejour en euros (si affiche, sinon calcule price_per_night * nuits)
- rating: note (sur 5)
- stars: nombre d'etoiles (1-5, si affiche)
- reviews_count: nombre d'avis (si affiche)
- amenities: equipements cles (wifi, piscine, etc.)

Reponds UNIQUEMENT en JSON :
{
  "hotels": [...]
}

Si tu ne trouves pas d'hotels, retourne {"hotels": []}"""


def _build_hotels_url(city: str, check_in: str, check_out: str, currency: str = "EUR") -> str:
    """Build Google Hotels search URL."""
    return (
        f"https://www.google.com/travel/hotels?"
        f"q=hotels+in+{city.replace(' ', '+')}"
        f"&dates={check_in},{check_out}"
        f"&curr={currency}&hl=en"
    )


async def scrape_hotels_page(city: str, check_in: str, check_out: str) -> dict | None:
    """Scrape a single Google Hotels search page.
    Returns {"hotels": [...]} or None."""

    url = _build_hotels_url(city, check_in, check_out)
    logger.info(f"Scraping Google Hotels: {city} {check_in}→{check_out}")

    browser = None
    pw = None
    try:
        browser, pw = await create_browser()
        context = await create_stealth_context(browser)
        page = await context.new_page()

        text = await navigate_and_extract(page, url, "div[class*='price'], span[class*='price']", timeout=20000)

        if not text or len(text) < 100:
            logger.warning(f"No content extracted for hotels in {city}")
            return None

        if len(text) > 4000:
            text = text[:4000]

        result = _extract_with_llm(text, city, check_in, check_out)
        return result

    except Exception as e:
        logger.error(f"Hotel scrape failed for {city}: {e}")
        return None
    finally:
        if browser:
            await browser.close()
        if pw:
            await pw.stop()


def _extract_with_llm(text: str, city: str, check_in: str, check_out: str) -> dict | None:
    """Use Claude Haiku to extract hotel data from visible text."""
    if not settings.ANTHROPIC_API_KEY:
        return None

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Calculate nights
    try:
        ci = datetime.strptime(check_in, "%Y-%m-%d")
        co = datetime.strptime(check_out, "%Y-%m-%d")
        nights = max((co - ci).days, 1)
    except (ValueError, TypeError):
        nights = 7

    user_msg = f"Ville: {city}\nDates: {check_in} → {check_out} ({nights} nuits)\n\nTexte de la page:\n{text}"

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

        # Add metadata and calculate missing fields
        for hotel in data.get("hotels", []):
            hotel.setdefault("city", city)
            hotel.setdefault("checkIn", check_in)
            hotel.setdefault("checkOut", check_out)
            hotel.setdefault("currency", "EUR")
            hotel.setdefault("source", "google_hotels")

            ppn = hotel.get("price_per_night", 0)
            total = hotel.get("total_price", 0)
            if ppn and not total:
                hotel["total_price"] = ppn * nights
            elif total and not ppn:
                hotel["price_per_night"] = round(total / nights, 2)

            hotel["url"] = _build_hotels_url(city, check_in, check_out)

        return data

    except json.JSONDecodeError as e:
        logger.error(f"LLM returned invalid JSON for hotels: {e}")
        return None
    except Exception as e:
        logger.error(f"LLM hotel extraction failed: {e}")
        return None
