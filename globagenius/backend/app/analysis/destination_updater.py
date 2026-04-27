"""Dynamic destination priority updater.

Runs weekly to update the `priority_destinations` table in Supabase by combining:
1. Travelpayouts cheap destinations (real deal signal from CDG)
2. Seasonal affinity for French travelers (hardcoded knowledge base)
3. Long-haul boost for priority markets

Falls back gracefully — if pytrends or Travelpayouts fails, the existing DB
rows are kept until the next successful run.
"""

import logging
from datetime import datetime, timezone

from app.analysis.route_selector import (
    LONG_HAUL_DESTINATIONS,
    LOW_COST_COMPETITION,
    HIGH_FARE_MISTAKE_ROUTES,
    SEASONAL_DESTINATIONS,
    get_current_season,
    score_route,
    is_long_haul,
)
from app.config import settings

logger = logging.getLogger(__name__)

# ─── DESTINATION UNIVERSE ────────────────────────────────────────────────────
# Full list of destinations GlobeGenius can monitor.
# Each entry: (IATA, label_fr, region)
DESTINATION_UNIVERSE = [
    # ── Europe courts courriers ──
    ("LIS", "Lisbonne", "europe"),
    ("OPO", "Porto", "europe"),
    ("FAO", "Faro (Algarve)", "europe"),
    ("BCN", "Barcelone", "europe"),
    ("MAD", "Madrid", "europe"),
    ("ALC", "Alicante", "europe"),
    ("VLC", "Valence", "europe"),
    ("PMI", "Majorque", "europe"),
    ("IBZ", "Ibiza", "europe"),
    ("AGP", "Malaga", "europe"),
    ("SVQ", "Séville", "europe"),
    ("ATH", "Athènes", "europe"),
    ("HER", "Héraklion (Crète)", "europe"),
    ("RHO", "Rhodes", "europe"),
    ("JTR", "Santorin", "europe"),
    ("JMK", "Mykonos", "europe"),
    ("CFU", "Corfou", "europe"),
    ("SKG", "Thessalonique", "europe"),
    ("NAP", "Naples", "europe"),
    ("BLQ", "Bologne", "europe"),
    ("FCO", "Rome", "europe"),
    ("VCE", "Venise", "europe"),
    ("CAG", "Cagliari (Sardaigne)", "europe"),
    ("BRI", "Bari", "europe"),
    ("CTA", "Catane (Sicile)", "europe"),
    ("PRG", "Prague", "europe"),
    ("BUD", "Budapest", "europe"),
    ("WAW", "Varsovie", "europe"),
    ("KRK", "Cracovie", "europe"),
    ("VIE", "Vienne", "europe"),
    ("BER", "Berlin", "europe"),
    ("AMS", "Amsterdam", "europe"),
    ("BRU", "Bruxelles", "europe"),
    ("DUB", "Dublin", "europe"),
    ("EDI", "Edimbourg", "europe"),
    ("CPH", "Copenhague", "europe"),
    ("OSL", "Oslo", "europe"),
    ("ARN", "Stockholm", "europe"),
    ("HEL", "Helsinki", "europe"),
    ("ZRH", "Zurich", "europe"),
    ("GVA", "Genève", "europe"),
    ("DBV", "Dubrovnik", "europe"),
    ("SPU", "Split", "europe"),
    ("ZAG", "Zagreb", "europe"),
    ("TIV", "Tivat (Monténégro)", "europe"),
    ("SAW", "Istanbul Sabiha", "europe"),
    ("IST", "Istanbul", "europe"),
    ("SOF", "Sofia", "europe"),
    ("TLL", "Tallinn", "europe"),
    ("RIX", "Riga", "europe"),
    ("VNO", "Vilnius", "europe"),
    # ── Îles Atlantique / Canaries ──
    ("TFS", "Tenerife", "iles"),
    ("PMI", "Majorque", "iles"),
    ("LPA", "Las Palmas (Grande Canarie)", "iles"),
    ("FUE", "Fuerteventura", "iles"),
    ("ACE", "Lanzarote", "iles"),
    ("FNC", "Madère", "iles"),
    ("PDL", "Açores (Ponta Delgada)", "iles"),
    # ── Maghreb / Méditerranée Sud ──
    ("RAK", "Marrakech", "maghreb"),
    ("CMN", "Casablanca", "maghreb"),
    ("TUN", "Tunis", "maghreb"),
    ("CAI", "Le Caire", "maghreb"),
    ("SSH", "Charm el-Cheikh", "maghreb"),
    ("HRG", "Hurghada", "maghreb"),
    # ── Moyen-Orient ──
    ("DXB", "Dubaï", "moyen_orient"),
    ("DOH", "Doha", "moyen_orient"),
    ("AUH", "Abu Dhabi", "moyen_orient"),
    ("AMM", "Amman", "moyen_orient"),
    # ── Amérique du Nord ──
    ("JFK", "New York", "amerique_nord"),
    ("EWR", "New York Newark", "amerique_nord"),
    ("MIA", "Miami", "amerique_nord"),
    ("LAX", "Los Angeles", "amerique_nord"),
    ("SFO", "San Francisco", "amerique_nord"),
    ("YUL", "Montréal", "amerique_nord"),
    ("YYZ", "Toronto", "amerique_nord"),
    ("YVR", "Vancouver", "amerique_nord"),
    ("MEX", "Mexico", "amerique_nord"),
    ("CUN", "Cancún", "amerique_nord"),
    # ── Caraïbes ──
    ("PUJ", "Punta Cana", "caraibes"),
    ("SXM", "Saint-Martin", "caraibes"),
    ("PTP", "Pointe-à-Pitre (Guadeloupe)", "caraibes"),
    ("FDF", "Fort-de-France (Martinique)", "caraibes"),
    ("SJU", "San Juan (Porto Rico)", "caraibes"),
    # ── Amérique du Sud ──
    ("GIG", "Rio de Janeiro", "amerique_sud"),
    ("GRU", "São Paulo", "amerique_sud"),
    ("EZE", "Buenos Aires", "amerique_sud"),
    ("SCL", "Santiago du Chili", "amerique_sud"),
    ("BOG", "Bogotá", "amerique_sud"),
    ("LIM", "Lima", "amerique_sud"),
    # ── Asie ──
    ("BKK", "Bangkok", "asie"),
    ("HKT", "Phuket", "asie"),
    ("NRT", "Tokyo Narita", "asie"),
    ("HND", "Tokyo Haneda", "asie"),
    ("KIX", "Osaka", "asie"),
    ("ICN", "Séoul", "asie"),
    ("HKG", "Hong Kong", "asie"),
    ("SIN", "Singapour", "asie"),
    ("KUL", "Kuala Lumpur", "asie"),
    ("DPS", "Bali", "asie"),
    ("DEL", "New Delhi", "asie"),
    ("BOM", "Mumbai", "asie"),
    # ── Océanie ──
    ("SYD", "Sydney", "oceanie"),
    ("MEL", "Melbourne", "oceanie"),
    ("AKL", "Auckland", "oceanie"),
    # ── Océan Indien ──
    ("MLE", "Maldives", "ocean_indien"),
    ("MRU", "Maurice", "ocean_indien"),
    ("RUN", "La Réunion", "ocean_indien"),
    ("ZNZ", "Zanzibar", "ocean_indien"),
    ("SEZ", "Seychelles", "ocean_indien"),
    # ── Afrique ──
    ("JNB", "Johannesburg", "afrique"),
    ("CPT", "Le Cap", "afrique"),
    ("NBO", "Nairobi", "afrique"),
    ("DKR", "Dakar", "afrique"),
    ("ABJ", "Abidjan", "afrique"),
]

# IATA → label mapping for quick lookups
DEST_LABELS = {iata: label for iata, label, _ in DESTINATION_UNIVERSE}
DEST_REGIONS = {iata: region for iata, label, region in DESTINATION_UNIVERSE}


def _fetch_travelpayouts_popular(origin: str = "CDG", limit: int = 50) -> dict[str, float]:
    """Fetch cheapest destinations from Travelpayouts for a given origin.

    Returns {iata: price} dict. Empty dict on failure.
    """
    try:
        from app.scraper.travelpayouts import get_cheap_destinations
        results = get_cheap_destinations(origin=origin, limit=limit)
        return {r["destination"]: r["price"] for r in results if r.get("destination")}
    except Exception as e:
        logger.warning(f"Travelpayouts popular fetch failed: {e}")
        return {}


def _score_destination(
    iata: str,
    travelpayouts_prices: dict[str, float],
    season: str,
) -> float:
    """Compute a composite priority score for a destination.

    Weights:
    - 30% seasonal affinity (French travel patterns)
    - 25% Travelpayouts signal (real cheap flights available now)
    - 20% long-haul bonus (rare deals, high value)
    - 15% low-cost competition (fare mistake probability)
    - 10% fare-mistake route history (CDG-specific)
    """
    score = 0.0
    seasonal = SEASONAL_DESTINATIONS[season]

    # 1. Seasonal affinity (30%)
    if iata in seasonal["primary"]:
        score += 100 * 0.30
    elif iata in seasonal["secondary"]:
        score += 60 * 0.30
    else:
        score += 10 * 0.30

    # 2. Travelpayouts signal (25%) — cheap flights available right now
    if iata in travelpayouts_prices:
        # Normalize: cheaper = higher signal (cap at 500€ for normalization)
        price = travelpayouts_prices[iata]
        price_score = max(0, (500 - price) / 500 * 100)
        score += price_score * 0.25
    # If not in Travelpayouts response, 0 signal for this dimension

    # 3. Long-haul bonus (20%) — these deals are rare and high-value
    if is_long_haul(iata):
        score += 100 * 0.20
    else:
        score += 20 * 0.20

    # 4. Low-cost competition (15%) — more carriers = more fare mistakes
    if iata in LOW_COST_COMPETITION:
        score += 100 * 0.15
    else:
        score += 15 * 0.15

    # 5. Fare-mistake route history for CDG (10%)
    if f"CDG-{iata}" in HIGH_FARE_MISTAKE_ROUTES:
        score += 100 * 0.10
    else:
        score += 0 * 0.10

    return round(score, 1)


def compute_priority_destinations(max_count: int = 40) -> list[dict]:
    """Compute the ranked list of priority destinations.

    Returns list of dicts ready to upsert into `priority_destinations` table:
    {iata, label_fr, region, score, is_long_haul, season, updated_at}
    """
    season = get_current_season()
    logger.info(f"Computing priority destinations for season={season}")

    # Fetch Travelpayouts signal (best-effort, non-blocking)
    tp_prices = _fetch_travelpayouts_popular(origin="CDG", limit=60)
    logger.info(f"Travelpayouts returned {len(tp_prices)} destinations")

    # Score all known destinations
    scored = []
    for iata, label, region in DESTINATION_UNIVERSE:
        s = _score_destination(iata, tp_prices, season)
        scored.append({
            "iata": iata,
            "label_fr": label,
            "region": region,
            "score": s,
            "is_long_haul": is_long_haul(iata),
            "season": season,
            "in_travelpayouts": iata in tp_prices,
            "tp_price": tp_prices.get(iata),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    # Sort by score desc, deduplicate IATA (keep highest score per IATA)
    seen = set()
    deduped = []
    for d in sorted(scored, key=lambda x: -x["score"]):
        if d["iata"] not in seen:
            seen.add(d["iata"])
            deduped.append(d)

    top = deduped[:max_count]

    long_haul_count = sum(1 for d in top if d["is_long_haul"])
    logger.info(
        f"Priority destinations computed: {len(top)} total, "
        f"{long_haul_count} long-haul, season={season}"
    )
    for d in top[:10]:
        logger.debug(f"  #{top.index(d)+1} {d['iata']} ({d['label_fr']}) score={d['score']}")

    return top


def update_priority_destinations_in_db(db, max_count: int = 40) -> int:
    """Compute and upsert priority destinations into Supabase.

    Returns number of rows upserted. 0 on failure.
    """
    if not db:
        logger.warning("No DB connection — skipping destination update")
        return 0

    rows = compute_priority_destinations(max_count=max_count)
    if not rows:
        return 0

    # Upsert all rows (on_conflict = iata column)
    try:
        db.table("priority_destinations").upsert(rows, on_conflict="iata").execute()
        logger.info(f"Upserted {len(rows)} priority destinations")
        return len(rows)
    except Exception as e:
        logger.error(f"Failed to upsert priority destinations: {e}")
        return 0


def get_priority_destinations_from_db(db, max_count: int = 40) -> list[str]:
    """Read priority destinations from DB, ordered by score desc.

    Falls back to empty list (caller should use hardcoded fallback).
    """
    if not db:
        return []
    try:
        resp = (
            db.table("priority_destinations")
            .select("iata")
            .order("score", desc=True)
            .limit(max_count)
            .execute()
        )
        return [r["iata"] for r in (resp.data or [])]
    except Exception as e:
        logger.warning(f"Failed to read priority_destinations from DB: {e}")
        return []
