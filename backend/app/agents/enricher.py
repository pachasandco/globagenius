import json
import logging
from datetime import datetime, timezone
from app.config import settings
from app.agents.llm_client import get_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es l'expert voyage de Globe Genius. On te donne un package voyage (vol + hotel) detecte a prix casse. Ton role :

1. DESCRIPTION : Redige 2-3 phrases attractives en francais qui donnent envie de reserver. Mentionne la destination, l'ambiance, la saison. Ton: enthousiaste mais pas racoleur.

2. RAISON : Explique en 1-2 phrases pourquoi ce prix est exceptionnel (comparaison au prix moyen, saisonnalite, popularite de la destination).

3. CONSEIL : Donne un conseil de reservation concret (urgence, meilleur moment, astuce). 1 phrase max.

4. TAGS : 3-5 tags pertinents en francais avec # (#destination #type #saison #etoiles).

Reponds UNIQUEMENT en JSON valide :
{"description": "...", "reason": "...", "tip": "...", "tags": ["#...", "#..."]}"""


def _get_client():
    client = get_client()
    if not client:
        logger.warning("ANTHROPIC_API_KEY not set, skipping enrichment")
    return client


def enrich_package(package: dict, flight: dict | None = None, accommodation: dict | None = None) -> dict | None:
    """Call Claude to enrich a package with description, reason, tip, and tags.
    Returns dict with keys: description, reason, tip, tags. Or None on failure."""
    client = _get_client()
    if not client:
        return None

    # Build user message with package data
    from app.config import IATA_TO_CITY
    dest_city = IATA_TO_CITY.get(package.get("destination", ""), package.get("destination", ""))
    origin_city = IATA_TO_CITY.get(package.get("origin", ""), package.get("origin", ""))

    acc_name = "Hotel"
    acc_rating = None
    if accommodation:
        acc_name = accommodation.get("name", "Hotel")
        acc_rating = accommodation.get("rating")

    dep_date = package.get("departure_date", "")
    ret_date = package.get("return_date", "")

    user_msg = json.dumps({
        "origin": package.get("origin", ""),
        "origin_city": origin_city,
        "destination": package.get("destination", ""),
        "destination_city": dest_city,
        "departure_date": dep_date,
        "return_date": ret_date,
        "flight_price": package.get("flight_price", 0),
        "accommodation_name": acc_name,
        "accommodation_rating": acc_rating,
        "accommodation_price": package.get("accommodation_price", 0),
        "total_price": package.get("total_price", 0),
        "baseline_total": package.get("baseline_total", 0),
        "discount_pct": package.get("discount_pct", 0),
        "score": package.get("score", 0),
    }, ensure_ascii=False)

    try:
        # Use Sonnet for top deals (score >= 80), Haiku for the rest
        score = package.get("score", 0)
        model = "claude-sonnet-4-6" if score >= 80 else "claude-haiku-4-5"

        response = client.messages.create(
            model=model,
            max_tokens=350,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )

        text = response.content[0].text.strip()

        # Parse JSON — handle potential markdown wrapping
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        result = json.loads(text)

        # Validate expected keys
        if not all(k in result for k in ("description", "reason", "tip", "tags")):
            logger.warning(f"Enrichment response missing keys: {result.keys()}")
            return None

        return {
            "ai_description": result["description"],
            "ai_reason": result["reason"],
            "ai_tip": result["tip"],
            "ai_tags": result["tags"] if isinstance(result["tags"], list) else [],
            "ai_enriched_at": datetime.now(timezone.utc).isoformat(),
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse enrichment JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Enrichment API call failed: {e}")
        return None
