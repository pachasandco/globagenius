"""Dynamic route selection based on seasonality and deal potential.

Prioritizes destinations where deals are most likely to appear,
based on season, competition, and historical fare mistake patterns.
"""

from datetime import datetime, timezone

# Seasonal destination priorities
SEASONAL_DESTINATIONS = {
    "winter": {  # Dec-Feb: sun + ski
        "primary": ["RAK", "BKK", "CUN", "TFS", "PMI", "DXB", "MLE", "MRU"],
        "secondary": ["LIS", "FCO", "ATH", "IST"],
    },
    "spring": {  # Mar-May: Europe low season + Japan
        "primary": ["LIS", "ATH", "PRG", "BCN", "RAK", "BUD", "OPO", "NAP"],
        "secondary": ["NRT", "IST", "AMS", "FCO"],
    },
    "summer": {  # Jun-Aug: off-peak + low-cost routes
        "primary": ["PRG", "BUD", "DUB", "BER", "WAW", "ZAG", "SPU", "DBV"],
        "secondary": ["IST", "RAK", "ATH", "LIS"],
    },
    "autumn": {  # Sep-Nov: Americas + Eastern Europe
        "primary": ["JFK", "YUL", "BCN", "LIS", "FCO", "IST", "BUD", "PRG"],
        "secondary": ["RAK", "ATH", "AMS", "BER"],
    },
}

# Routes with historically high fare mistake occurrence
HIGH_FARE_MISTAKE_ROUTES = {
    # Transatlantic business class pricing errors
    "CDG-JFK", "CDG-EWR", "ORY-JFK",
    # Asia via hub (pricing errors frequent)
    "CDG-BKK", "CDG-NRT", "CDG-HKG",
    # Caribbean in off-season
    "CDG-CUN", "CDG-PUJ",
    # Internal routes booked from Europe
    "CDG-MIA", "CDG-LAX",
}

# Destinations known for low-cost competition (more flash sales)
LOW_COST_COMPETITION = {
    "BCN", "LIS", "FCO", "ATH", "PRG", "BUD", "RAK",
    "AMS", "BER", "DUB", "NAP", "OPO", "PMI", "TFS",
}


def get_current_season() -> str:
    month = datetime.now(timezone.utc).month
    if month in (12, 1, 2):
        return "winter"
    elif month in (3, 4, 5):
        return "spring"
    elif month in (6, 7, 8):
        return "summer"
    else:
        return "autumn"


def get_priority_destinations(max_count: int = 12) -> list[str]:
    """Get prioritized destination list based on current season."""
    season = get_current_season()
    seasonal = SEASONAL_DESTINATIONS[season]

    destinations = []
    # Primary seasonal destinations first
    destinations.extend(seasonal["primary"])
    # Then secondary
    destinations.extend(seasonal["secondary"])

    # Deduplicate and limit
    seen = set()
    result = []
    for d in destinations:
        if d not in seen:
            seen.add(d)
            result.append(d)
        if len(result) >= max_count:
            break

    return result


def score_route(origin: str, destination: str, volatility_30d: float = 0, num_carriers: int = 1) -> float:
    """Score a route for deal potential (0-100).

    Higher score = more likely to produce deals.
    Used to prioritize scraping order.
    """
    score = 0.0
    route_key = f"{origin}-{destination}"
    season = get_current_season()
    seasonal = SEASONAL_DESTINATIONS[season]

    # Volatility (30% weight) — routes with price swings have more deals
    score += min(volatility_30d / 50 * 100, 100) * 0.30

    # Competition (20% weight) — more carriers = more price wars
    score += min(num_carriers / 5 * 100, 100) * 0.20

    # Low-cost presence (20% weight) — flash sales
    if destination in LOW_COST_COMPETITION:
        score += 100 * 0.20
    else:
        score += 30 * 0.20

    # Seasonal relevance (15% weight)
    if destination in seasonal["primary"]:
        score += 100 * 0.15
    elif destination in seasonal["secondary"]:
        score += 60 * 0.15
    else:
        score += 20 * 0.15

    # Fare mistake history (15% weight)
    if route_key in HIGH_FARE_MISTAKE_ROUTES:
        score += 100 * 0.15
    else:
        score += 10 * 0.15

    return round(score, 1)
