"""Tier 1 route definitions — hot routes polled every 20 min via direct
LCC endpoints.

Criteria for Tier 1:
- High search volume from BVA / CDG / ORY
- Served by Ryanair (BVA hub) or Vueling (CDG/ORY)
- Mistake fares historically appear here, and the 2h Travelpayouts
  cycle is too slow to catch them

Tier 1 uses direct airline endpoints for near-real-time prices.
Tier 2 (all other routes) uses Travelpayouts every 2h.

Each entry: (origin, destination, airlines)
  airlines: list of scrapers to use, in priority order.
  Currently active scrapers: "ryanair", "vueling".
  "transavia" is globally disabled (API v1 dead) and excluded here.

Audit 2026-05-01:
- Ryanair scraper expects an airport that Ryanair actually serves.
  Their main French hub is BVA (Beauvais). Most CDG/ORY entries
  previously listed here returned HTTP 400 because Ryanair does not
  fly the route from CDG/ORY. Routes are now keyed to the airport
  that actually has Ryanair service.
- Vueling now reaches apiwww.vueling.com (the old booking.vueling.com
  domain went dead). It serves a wide network from CDG/ORY/BCN.
"""

TIER1_ROUTES: list[tuple[str, str, list[str]]] = [
    # ── Ryanair from BVA (Paris-Beauvais — Ryanair's Paris hub) ──
    ("BVA", "BCN", ["ryanair"]),  # Barcelone
    ("BVA", "MAD", ["ryanair"]),  # Madrid
    ("BVA", "AGP", ["ryanair"]),  # Malaga
    ("BVA", "VLC", ["ryanair"]),  # Valence
    ("BVA", "SVQ", ["ryanair"]),  # Séville
    ("BVA", "ALC", ["ryanair"]),  # Alicante
    ("BVA", "OPO", ["ryanair"]),  # Porto
    ("BVA", "LIS", ["ryanair"]),  # Lisbonne
    ("BVA", "FAO", ["ryanair"]),  # Faro
    ("BVA", "RAK", ["ryanair"]),  # Marrakech
    ("BVA", "FEZ", ["ryanair"]),  # Fès
    ("BVA", "TNG", ["ryanair"]),  # Tanger
    ("BVA", "DUB", ["ryanair"]),  # Dublin
    ("BVA", "STN", ["ryanair"]),  # Londres Stansted
    ("BVA", "KRK", ["ryanair"]),  # Cracovie
    ("BVA", "BUD", ["ryanair"]),  # Budapest
    ("BVA", "WAW", ["ryanair"]),  # Varsovie
    ("BVA", "FCO", ["ryanair"]),  # Rome
    ("BVA", "BGY", ["ryanair"]),  # Milan Bergame
    ("BVA", "NAP", ["ryanair"]),  # Naples
    ("BVA", "ATH", ["ryanair"]),  # Athènes
    ("BVA", "TFS", ["ryanair"]),  # Ténérife
    ("BVA", "LPA", ["ryanair"]),  # Gran Canaria
    ("BVA", "ACE", ["ryanair"]),  # Lanzarote
    ("BVA", "FUE", ["ryanair"]),  # Fuerteventura

    # ── Vueling from CDG ──
    ("CDG", "BCN", ["vueling"]),
    ("CDG", "MAD", ["vueling"]),
    ("CDG", "SVQ", ["vueling"]),
    ("CDG", "VLC", ["vueling"]),
    ("CDG", "AGP", ["vueling"]),
    ("CDG", "IBZ", ["vueling"]),
    ("CDG", "PMI", ["vueling"]),
    ("CDG", "ALC", ["vueling"]),
    ("CDG", "BIO", ["vueling"]),  # Bilbao

    # ── Vueling from ORY ──
    ("ORY", "BCN", ["vueling"]),
    ("ORY", "MAD", ["vueling"]),
    ("ORY", "AGP", ["vueling"]),
    ("ORY", "PMI", ["vueling"]),
    ("ORY", "IBZ", ["vueling"]),
    ("ORY", "ALC", ["vueling"]),
    ("ORY", "VLC", ["vueling"]),
    ("ORY", "SVQ", ["vueling"]),
]


def get_tier1_routes() -> list[tuple[str, str, list[str]]]:
    """Return all Tier 1 routes."""
    return TIER1_ROUTES


def get_tier1_routes_for_airport(origin: str) -> list[tuple[str, str, list[str]]]:
    """Return Tier 1 routes departing from a specific airport."""
    return [(o, d, airlines) for o, d, airlines in TIER1_ROUTES if o == origin]
