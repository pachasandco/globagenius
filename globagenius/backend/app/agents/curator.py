import json
import logging
from app.config import settings
from app.agents.llm_client import get_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es l'expert qualite de Globe Genius. On te donne un deal voyage detecte par notre pipeline. Ton role est de VALIDER ou REJETER ce deal.

VALIDE le deal si :
- Le prix est coherent (pas une erreur de scraping, pas un vol avec 3 escales deguise en direct)
- La remise est reelle par rapport au prix habituel de cette route
- La destination est accessible depuis l'aeroport de depart
- Les dates sont logiques (pas de vol le jour meme, duree raisonnable)

REJETTE le deal si :
- Le prix semble trop beau pour etre vrai (vol long-courrier a 20€)
- La remise est artificielle (baseline mal calculee)
- C'est un trajet illogique (CDG→CDG, escales excessives pour un court-courrier)
- Les dates sont incoherentes

Reponds UNIQUEMENT en JSON :
{
  "valid": true/false,
  "confidence": 0.0-1.0,
  "reason": "explication courte",
  "is_error_fare": true/false,
  "urgency": "low/medium/high"
}

- is_error_fare: true si ca ressemble a une erreur de prix d'une compagnie (tres rare, tres bon deal)
- urgency: high si le prix risque de disparaitre vite"""


def curate_deal(package: dict, flight_data: dict | None = None, accommodation_data: dict | None = None) -> dict | None:
    """Validate a deal using AI curation. Returns validation result or None on failure."""
    if not settings.ANTHROPIC_API_KEY:
        return {"valid": True, "confidence": 0.5, "reason": "No API key, auto-approved", "is_error_fare": False, "urgency": "medium"}

    client = get_client()

    from app.config import IATA_TO_CITY
    origin_city = IATA_TO_CITY.get(package.get("origin", ""), package.get("origin", ""))
    dest_city = IATA_TO_CITY.get(package.get("destination", ""), package.get("destination", ""))

    deal_info = {
        "origin": package.get("origin"),
        "origin_city": origin_city,
        "destination": package.get("destination"),
        "destination_city": dest_city,
        "departure_date": package.get("departure_date"),
        "return_date": package.get("return_date"),
        "flight_price": package.get("flight_price"),
        "accommodation_price": package.get("accommodation_price"),
        "total_price": package.get("total_price"),
        "baseline_total": package.get("baseline_total"),
        "discount_pct": package.get("discount_pct"),
        "score": package.get("score"),
    }

    if flight_data:
        deal_info["airline"] = flight_data.get("airline")
        deal_info["stops"] = flight_data.get("stops")

    if accommodation_data:
        deal_info["hotel_name"] = accommodation_data.get("name")
        deal_info["hotel_rating"] = accommodation_data.get("rating")

    try:
        response = client.messages.create(
            model="claude-haiku-4-5",  # Fast + cheap for validation
            max_tokens=200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(deal_info, ensure_ascii=False)}],
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        return json.loads(text)

    except Exception as e:
        logger.warning(f"Curation failed, auto-approving: {e}")
        return {"valid": True, "confidence": 0.5, "reason": "Curation unavailable", "is_error_fare": False, "urgency": "medium"}
