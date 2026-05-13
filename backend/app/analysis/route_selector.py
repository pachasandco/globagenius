"""Dynamic route selection based on seasonality and deal potential."""

from datetime import datetime, timezone

SEASONAL_DESTINATIONS = {
    "winter": {  # Dec-Feb — vacances scolaires Noël + février
        "primary": [
            # Long-courrier soleil — saison sèche idéale
            "BKK", "HKT", "DPS", "SGN", "HAN",
            "CUN", "PUJ", "HAV", "VRA", "SDQ", "POP",
            "DXB", "DOH", "AUH",
            "MLE", "MRU", "RUN", "SEZ",
            "RAK", "AGA", "TUN",
            # DOM-TOM Caraïbes + Pacifique (haute saison touristique FR)
            "PTP", "FDF", "PPT", "NOU", "CAY",
            # Canaries + Madère + Andalousie (soleil court-courrier)
            "TFS", "FUE", "LPA", "ACE", "FNC", "SSH", "HRG", "SVQ",
            # USA / Australie (été là-bas)
            "JFK", "MIA", "LAX", "SYD", "MEL",
        ],
        "secondary": [
            "LIS", "FCO", "ATH", "IST", "CAI", "GVA", "PDL",
            "PMI", "HER",
            "BOM", "DEL", "CMB",
        ],
    },
    "spring": {  # Mar-May — Pâques, ponts mai
        "primary": [
            # Europe basse saison
            "LIS", "ATH", "PRG", "BCN", "BUD", "OPO", "NAP", "DBV",
            # Maghreb
            "RAK", "CMN", "TUN",
            # Long-courrier
            "IST", "NRT", "JFK", "YUL",
            # Asie en pleine saison sèche
            "BKK", "DPS", "SGN", "HAN", "HKT",
            # Caraïbes / DOM-TOM (encore en saison sèche)
            "PUJ", "HAV", "PTP", "FDF",
            # Europe du Sud + Balkans mi-saison
            "FAO", "ALC", "BLQ", "SAW", "TIV", "SKG",
        ],
        "secondary": [
            "AMS", "FCO", "BER", "MAD", "VCE", "SPU", "EDI",
            "DXB", "MIA", "SYD", "PPT",
            "HND", "ICN", "SIN", "HKG", "KIX", "BOM", "DEL",
            "TNR", "ZNZ",
        ],
    },
    "summer": {  # Jun-Aug — grandes vacances
        "primary": [
            # Europe off-peak Nord
            "PRG", "BUD", "DUB", "BER", "WAW", "ZAG", "SPU", "DBV",
            "EDI", "CPH", "HEL", "OSL", "ARN",
            # Long-courrier été — USA, Canada, Pacifique
            "JFK", "EWR", "YUL", "YVR", "LAX", "MIA", "SFO",
            "NRT", "HND", "KIX", "SYD", "MEL", "AKL", "PPT", "NOU",
            # Mediterranee estivale (iles grecques, Italie du sud, Espagne)
            "VLC", "CAG", "BRI", "CTA", "RHO", "JTR", "JMK", "CFU", "IBZ",
            "PMI", "ALC",
        ],
        "secondary": [
            "IST", "RAK", "ATH", "LIS", "OPO", "VCE",
            "BKK", "KUL", "BOM", "DEL", "ICN", "HKG", "SIN", "CGK", "MNL",
            "GIG", "EZE", "SCL", "BOG", "LIM",  # printemps austral, prix bas
        ],
    },
    "autumn": {  # Sep-Nov — Toussaint, arrière-saison
        "primary": [
            # Americas + Oceanie
            "JFK", "EWR", "YUL", "YVR", "MIA", "LAX", "SFO", "GIG", "EZE", "SCL",
            "SYD", "MEL", "AKL",
            # Caraïbes (saison sèche reprend en novembre)
            "PUJ", "HAV", "VRA", "PTP", "FDF",
            # Asie début saison sèche
            "BKK", "HKT", "DPS", "SGN", "HAN", "CMB",
            # Europe arriere-saison
            "BCN", "LIS", "FCO", "IST", "BUD", "PRG", "ATH",
            # Maghreb
            "RAK", "TUN", "AGA",
            # Afrique long-courrier
            "JNB", "CPT", "NBO", "TNR", "ZNZ",
            # City-breaks Europe centrale + Baltes + Alpes
            "KRK", "WAW", "VIE", "SOF", "TLL", "RIX", "VNO", "HEL", "BRU", "ZRH", "GVA",
        ],
        "secondary": [
            "AMS", "BER", "DUB", "NAP", "MAD", "DXB", "DOH", "CMN",
            "BOG", "LIM", "MLE", "MRU", "RUN", "SEZ",
            "BOM", "DEL", "ICN", "HKG", "SIN", "KUL",
            "PPT", "NOU", "CAY",
        ],
    },
}

HIGH_FARE_MISTAKE_ROUTES = {
    # Transatlantic
    "CDG-JFK", "CDG-EWR", "ORY-JFK", "LYS-JFK",
    "CDG-YUL", "CDG-YVR", "CDG-YYZ",
    # Asia via hub
    "CDG-BKK", "CDG-NRT", "CDG-HKG", "CDG-DXB",
    "CDG-HND", "CDG-ICN", "CDG-SIN", "CDG-KUL", "CDG-DEL", "CDG-BOM",
    "CDG-DPS", "CDG-HKT", "CDG-SGN", "CDG-HAN", "CDG-CGK", "CDG-MNL", "CDG-CMB",
    # Caribbean (incl. Cuba/DR very price-volatile via charters)
    "CDG-CUN", "CDG-PUJ", "ORY-PUJ", "CDG-HAV", "CDG-VRA", "CDG-SDQ", "CDG-POP",
    # US
    "CDG-MIA", "CDG-LAX", "CDG-SFO",
    # Iles + Oceanie
    "CDG-MLE", "CDG-MRU", "ORY-RUN", "CDG-SYD", "CDG-MEL", "CDG-AKL",
    "CDG-PPT", "ORY-PPT", "CDG-NOU", "CDG-SEZ",
    # DOM-TOM (Air Caraïbes / French Bee promotional fares from Orly)
    "ORY-PTP", "ORY-FDF", "ORY-CAY", "CDG-PTP", "CDG-FDF",
    # South America
    "CDG-EZE", "CDG-BOG", "CDG-LIM", "CDG-SCL", "CDG-GIG", "CDG-GRU",
    # Africa
    "CDG-JNB", "CDG-CPT", "CDG-ZNZ", "CDG-NBO", "CDG-TNR",
    # Middle East
    "CDG-DOH", "CDG-AUH",
}

LOW_COST_COMPETITION = {
    "BCN", "LIS", "FCO", "ATH", "PRG", "BUD", "RAK",
    "AMS", "BER", "DUB", "NAP", "OPO", "PMI", "TFS",
    "AGP", "HER", "SPU", "DBV", "MAD", "VCE", "EDI",
    "CPH", "WAW", "ZAG", "CMN", "TUN",
}

LONG_HAUL_DESTINATIONS = {
    # North America
    "JFK", "EWR", "MIA", "LAX", "SFO", "YUL", "YYZ", "YVR", "MEX", "CUN",
    # Caribbean (incl. French DOM-TOM and Cuba/DR popular winter spots)
    "PUJ", "PTP", "FDF", "HAV", "VRA", "SDQ", "POP", "SXM", "SJU",
    # South America
    "GIG", "GRU", "EZE", "SCL", "BOG", "LIM",
    # Asia
    "BKK", "HKT", "NRT", "HND", "KIX", "ICN", "HKG", "SIN", "KUL",
    "DEL", "BOM", "DPS", "SGN", "HAN", "CGK", "MNL", "CMB",
    # Oceania + Pacific
    "SYD", "MEL", "AKL", "PPT", "NOU",
    # Indian Ocean
    "MLE", "MRU", "RUN", "ZNZ", "SEZ",
    # Africa (sub-Saharan + west Africa)
    "JNB", "CPT", "NBO", "TNR", "DKR", "ABJ",
    # Middle East (long-haul-ish from CDG)
    "DXB", "DOH", "AUH", "AMM",
    # French Guiana (DOM)
    "CAY",
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


def get_priority_destinations(max_count: int = 40, db=None) -> list[str]:
    """Return ranked list of priority destinations.

    Order of precedence:
    1. DB table `priority_destinations` (updated weekly by job_update_destinations)
    2. Hardcoded seasonal fallback (used on first boot or if DB is unavailable)

    Pass `db` (Supabase client) to enable DB lookup. When called from the
    scheduler, db is always available. When called from tests or scripts, the
    fallback list is used.
    """
    if db is not None:
        try:
            from app.analysis.destination_updater import get_priority_destinations_from_db
            db_results = get_priority_destinations_from_db(db, max_count=max_count)
            if db_results:
                return db_results
        except Exception:
            pass  # Fall through to hardcoded list

    # Hardcoded seasonal fallback
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
