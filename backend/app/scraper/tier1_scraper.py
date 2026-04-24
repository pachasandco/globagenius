"""Tier 1 orchestrator — scrapes hot routes via direct LCC endpoints.

Called by job_scrape_tier1() every 15-30 min (configurable).
Falls back to Travelpayouts automatically when an airline endpoint is demoted.
"""

import logging
from app.scraper.tier1_routes import get_tier1_routes_for_airport
from app.scraper.tier1_ryanair import scrape_route as scrape_ryanair, is_demoted as ryanair_demoted
from app.scraper.tier1_transavia import scrape_route as scrape_transavia, is_demoted as transavia_demoted
from app.scraper.travelpayouts_flights import scrape_flights_for_route

logger = logging.getLogger(__name__)


def scrape_tier1_airport(origin: str) -> list[dict]:
    """Scrape all Tier 1 routes from one airport via direct LCC endpoints.

    For each route, tries each configured airline scraper in order.
    If an airline endpoint is demoted (too many failures), falls back to
    Travelpayouts for that specific (origin, destination) pair.

    Returns list of normalized flight dicts ready for DB upsert."""
    routes = get_tier1_routes_for_airport(origin)
    all_flights: list[dict] = []

    for orig, dest, airlines in routes:
        route_flights: list[dict] = []

        for airline in airlines:
            if airline == "ryanair":
                if not ryanair_demoted(orig, dest):
                    flights = scrape_ryanair(orig, dest)
                    route_flights.extend(flights)
            elif airline == "transavia":
                if not transavia_demoted(orig, dest):
                    flights = scrape_transavia(orig, dest)
                    route_flights.extend(flights)

        # If all direct scrapers failed / demoted → Travelpayouts fallback
        if not route_flights:
            logger.info(f"Tier1 {orig}->{dest}: all direct scrapers demoted, falling back to Travelpayouts")
            route_flights = scrape_flights_for_route(orig, dest)

        all_flights.extend(route_flights)

    logger.info(f"Tier1 scrape {origin}: {len(all_flights)} flights from {len(routes)} routes")
    return all_flights


async def scrape_all_tier1() -> tuple[list[dict], int]:
    """Scrape all Tier 1 airports. Returns (flights, error_count)."""
    from app.config import settings

    # Tier 1 is CDG + ORY only (main hubs with LCC coverage)
    tier1_airports = [a for a in settings.MVP_AIRPORTS if a in ("CDG", "ORY")]

    all_flights: list[dict] = []
    errors = 0

    for airport in tier1_airports:
        try:
            flights = scrape_tier1_airport(airport)
            all_flights.extend(flights)
        except Exception as e:
            errors += 1
            logger.error(f"Tier1 scrape failed for {airport}: {e}")

    return all_flights, errors
