"""Tier 1 route definitions — hot routes polled every 15-30 min via direct LCC endpoints.

Criteria for Tier 1:
- High search volume from CDG/ORY
- Served by Ryanair or Transavia (direct endpoint available)
- Historical mistake fare activity (CDG→NYC, CDG→BKK excluded: not LCC)

Tier 1 uses direct airline endpoints for near-real-time prices.
Tier 2 (all other routes) uses Travelpayouts cache.

Each entry: (origin, destination, airlines)
  airlines: list of scrapers to use — "ryanair", "transavia"
"""

TIER1_ROUTES: list[tuple[str, str, list[str]]] = [
    # Maroc
    ("CDG", "RAK", ["ryanair", "transavia"]),  # Marrakech
    ("CDG", "CMN", ["ryanair", "transavia"]),  # Casablanca
    ("CDG", "AGA", ["ryanair", "transavia"]),  # Agadir
    ("CDG", "FEZ", ["ryanair"]),               # Fès
    ("CDG", "TNG", ["ryanair"]),               # Tanger
    ("ORY", "RAK", ["transavia"]),
    ("ORY", "CMN", ["transavia"]),
    ("ORY", "AGA", ["transavia"]),

    # Portugal
    ("CDG", "LIS", ["ryanair", "transavia"]),  # Lisbonne
    ("CDG", "OPO", ["ryanair"]),               # Porto
    ("CDG", "FAO", ["ryanair"]),               # Faro
    ("ORY", "LIS", ["transavia"]),
    ("ORY", "OPO", ["transavia"]),

    # Espagne
    ("CDG", "BCN", ["ryanair", "transavia"]),  # Barcelone
    ("CDG", "MAD", ["ryanair"]),               # Madrid
    ("CDG", "SVQ", ["ryanair"]),               # Séville
    ("CDG", "VLC", ["ryanair"]),               # Valence
    ("CDG", "AGP", ["ryanair"]),               # Malaga
    ("ORY", "BCN", ["transavia"]),
    ("ORY", "AGP", ["transavia"]),

    # Italie
    ("CDG", "FCO", ["ryanair"]),               # Rome
    ("CDG", "CIA", ["ryanair"]),               # Rome Ciampino
    ("CDG", "BGY", ["ryanair"]),               # Milan Bergame
    ("CDG", "NAP", ["ryanair"]),               # Naples
    ("CDG", "BRI", ["ryanair"]),               # Bari
    ("CDG", "PMO", ["ryanair"]),               # Palerme
    ("ORY", "FCO", ["transavia"]),
    ("ORY", "NAP", ["transavia"]),

    # Grèce
    ("CDG", "ATH", ["ryanair", "transavia"]),  # Athènes
    ("CDG", "HER", ["ryanair", "transavia"]),  # Héraklion (Crète)
    ("CDG", "RHO", ["ryanair"]),               # Rhodes
    ("CDG", "SKG", ["ryanair"]),               # Thessalonique
    ("ORY", "ATH", ["transavia"]),
    ("ORY", "HER", ["transavia"]),

    # Canaries
    ("CDG", "TFS", ["ryanair", "transavia"]),  # Ténérife Sud
    ("CDG", "LPA", ["ryanair", "transavia"]),  # Gran Canaria
    ("CDG", "ACE", ["ryanair"]),               # Lanzarote
    ("CDG", "FUE", ["ryanair"]),               # Fuerteventura
    ("ORY", "TFS", ["transavia"]),
    ("ORY", "LPA", ["transavia"]),

    # Tunisie / Algérie
    ("CDG", "TUN", ["transavia"]),             # Tunis
    ("CDG", "MIR", ["transavia"]),             # Monastir
    ("ORY", "TUN", ["transavia"]),
    ("ORY", "ALG", ["transavia"]),             # Alger

    # Irlande / UK
    ("CDG", "DUB", ["ryanair"]),               # Dublin
    ("CDG", "STN", ["ryanair"]),               # Londres Stansted

    # Europe centrale / Balkans
    ("CDG", "KRK", ["ryanair"]),               # Cracovie
    ("CDG", "WRO", ["ryanair"]),               # Wrocław
    ("CDG", "BUD", ["ryanair"]),               # Budapest
]


def get_tier1_routes() -> list[tuple[str, str, list[str]]]:
    """Return all Tier 1 routes."""
    return TIER1_ROUTES


def get_tier1_routes_for_airport(origin: str) -> list[tuple[str, str, list[str]]]:
    """Return Tier 1 routes departing from a specific airport."""
    return [(o, d, airlines) for o, d, airlines in TIER1_ROUTES if o == origin]
