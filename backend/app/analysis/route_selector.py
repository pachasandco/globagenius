"""Dynamic route selection based on seasonality and deal potential."""

from datetime import datetime, timezone

SEASONAL_DESTINATIONS = {
    "winter": {  # Dec-Feb
        "primary": [
            # Soleil long-courrier
            "RAK", "BKK", "CUN", "PUJ", "DXB", "MLE", "MRU", "RUN",
            # Canaries + Mediterranee
            "TFS", "PMI", "AGP", "HER",
            # US + Australie (ete la-bas)
            "JFK", "MIA", "SYD",
        ],
        "secondary": ["LIS", "FCO", "ATH", "IST", "CAI", "TUN", "GVA"],
    },
    "spring": {  # Mar-May
        "primary": [
            # Europe basse saison
            "LIS", "ATH", "PRG", "BCN", "BUD", "OPO", "NAP", "DBV",
            # Maghreb
            "RAK", "CMN", "TUN",
            # Long-courrier
            "IST", "NRT", "JFK",
        ],
        "secondary": ["AMS", "FCO", "BER", "MAD", "VCE", "SPU", "EDI", "BKK", "YUL", "DXB", "MIA", "SYD"],
    },
    "summer": {  # Jun-Aug
        "primary": [
            # Europe off-peak
            "PRG", "BUD", "DUB", "BER", "WAW", "ZAG", "SPU", "DBV",
            "EDI", "CPH", "HEL", "OSL", "ARN",
            # Long-courrier
            "YUL", "NRT", "SYD",
        ],
        "secondary": ["IST", "RAK", "ATH", "LIS", "OPO", "VCE", "JFK"],
    },
    "autumn": {  # Sep-Nov
        "primary": [
            # Americas + Oceanie
            "JFK", "YUL", "GIG", "MIA", "LAX", "SYD",
            # Europe arriere-saison
            "BCN", "LIS", "FCO", "IST", "BUD", "PRG", "ATH",
            # Maghreb
            "RAK",
        ],
        "secondary": ["AMS", "BER", "DUB", "NAP", "MAD", "BKK", "DXB", "CMN"],
    },
}

HIGH_FARE_MISTAKE_ROUTES = {
    # Transatlantic
    "CDG-JFK", "CDG-EWR", "ORY-JFK", "LYS-JFK",
    # Asia via hub
    "CDG-BKK", "CDG-NRT", "CDG-HKG", "CDG-DXB",
    # Caribbean
    "CDG-CUN", "CDG-PUJ", "ORY-PUJ",
    # US
    "CDG-MIA", "CDG-LAX", "CDG-SFO",
    # Iles + Oceanie
    "CDG-MLE", "CDG-MRU", "ORY-RUN", "CDG-SYD",
}

LOW_COST_COMPETITION = {
    "BCN", "LIS", "FCO", "ATH", "PRG", "BUD", "RAK",
    "AMS", "BER", "DUB", "NAP", "OPO", "PMI", "TFS",
    "AGP", "HER", "SPU", "DBV", "MAD", "VCE", "EDI",
    "CPH", "WAW", "ZAG", "CMN", "TUN",
}

LONG_HAUL_DESTINATIONS = {
    "NRT", "JFK", "BKK", "YUL", "DXB", "MIA", "SYD",
    "CUN", "PUJ", "MLE", "MRU", "RUN", "GIG", "LAX",
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


def get_priority_destinations(max_count: int = 25) -> list[str]:
    season = get_current_season()
    seasonal = SEASONAL_DESTINATIONS[season]

    seen = set()
    result = []
    for d in seasonal["primary"] + seasonal["secondary"]:
        if d not in seen:
            seen.add(d)
            result.append(d)
        if len(result) >= max_count:
            break

    return result


def score_route(origin: str, destination: str, volatility_30d: float = 0, num_carriers: int = 1) -> float:
    score = 0.0
    route_key = f"{origin}-{destination}"
    season = get_current_season()
    seasonal = SEASONAL_DESTINATIONS[season]

    score += min(volatility_30d / 50 * 100, 100) * 0.30
    score += min(num_carriers / 5 * 100, 100) * 0.20

    if destination in LOW_COST_COMPETITION:
        score += 100 * 0.20
    else:
        score += 30 * 0.20

    if destination in seasonal["primary"]:
        score += 100 * 0.15
    elif destination in seasonal["secondary"]:
        score += 60 * 0.15
    else:
        score += 20 * 0.15

    if route_key in HIGH_FARE_MISTAKE_ROUTES:
        score += 100 * 0.15
    else:
        score += 10 * 0.15

    return round(score, 1)


def is_long_haul(destination: str) -> bool:
    return destination in LONG_HAUL_DESTINATIONS
