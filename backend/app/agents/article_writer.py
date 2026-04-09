import json
import logging
from datetime import datetime, timezone
from app.config import settings
from app.agents.llm_client import get_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un redacteur voyage expert pour Globe Genius. Tu rediges des GUIDES DE VOYAGE COMPLETS et detailles en francais.

Chaque guide doit etre un vrai outil pratique pour un voyageur, pas une simple introduction touristique.

Produis un JSON avec :

1. title : Titre accrocheur (max 60 caracteres)
2. subtitle : Sous-titre (max 100 caracteres)
3. intro : Introduction immersive (4-5 phrases qui transportent le lecteur)
4. sections : EXACTEMENT 4 sections, chacune avec :
   - title : titre
   - content : 3-4 paragraphes detailles (300-500 mots par section). Inclus des noms REELS de lieux, restaurants, quartiers. Prix indicatifs et astuces.
   - photo_query : mot-cle anglais pour Unsplash

Les 4 sections :
- "Quartiers et ambiances" : 3-4 quartiers avec ambiance, ou manger, ou se balader
- "Gastronomie et bonnes adresses" : plats locaux, 5-6 restaurants avec noms reels et prix, street food, marches
- "Top experiences" : 8 choses a faire avec prix, horaires, duree
- "Pratique : transport, budget, astuces" : aeroport→centre, transports, budget quotidien par gamme, pourboires, securite, mots utiles

5. best_time : Meilleure periode (3-4 phrases avec mois, temperatures, evenements)
6. budget_tip : Budget detaille (budget quotidien par gamme : backpacker, moyen, confort)
7. tags : 5-6 tags
8. photo_query : mot-cle photo couverture

Style : concret, pratique, avec des vrais noms et prix. Le lecteur doit pouvoir planifier son voyage uniquement avec ce guide.

Reponds UNIQUEMENT en JSON valide."""


def generate_article(destination: str, country: str) -> dict | None:
    """Generate a destination article using Claude."""
    client = get_client()
    if not client:
        logger.warning("ANTHROPIC_API_KEY not set")
        return None

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Redige un article complet sur {destination}, {country} comme destination voyage."
            }],
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        raw = json.loads(text)

        # Normalize keys to lowercase (LLM sometimes returns TITLE, SUBTITLE, etc.)
        article = {k.lower(): v for k, v in raw.items()}

        # Add Unsplash photo URLs
        photo_query = article.get("photo_query", destination)
        article["cover_photo"] = f"https://images.unsplash.com/photo-{_get_unsplash_query(photo_query)}?w=1200&q=80"
        for section in article.get("sections", []):
            query = section.get("photo_query", destination)
            section["photo_url"] = f"https://source.unsplash.com/800x500/?{query.replace(' ', '+')}"

        article["destination"] = destination
        article["country"] = country
        article["generated_at"] = datetime.now(timezone.utc).isoformat()

        return article

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse article JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Article generation failed: {e}")
        return None


def _get_unsplash_query(query: str) -> str:
    """Return a stable Unsplash photo ID-like string for common destinations."""
    # Map popular destinations to known good Unsplash photo IDs
    PHOTO_IDS = {
        "lisbon": "1585208798174-6cedd86e019a",
        "lisbonne": "1585208798174-6cedd86e019a",
        "barcelona": "1583422409516-2895a77efded",
        "barcelone": "1583422409516-2895a77efded",
        "athens": "1555993539-1732b0258235",
        "athenes": "1555993539-1732b0258235",
        "prague": "1519677100203-a0e668c92439",
        "marrakech": "1597212618440-806262de4f6b",
        "amsterdam": "1534351590666-13e3e96b5017",
        "rome": "1552832230-c0197dd311b5",
        "istanbul": "1524231757912-21f4fe3a7200",
        "budapest": "1551867633-194f125bddfa",
        "dubai": "1512453913616-1bf17ba41e32",
        "new york": "1496442226666-8d4d0e62e6e9",
        "tokyo": "1540959733332-eab4deabeeaf",
        "bangkok": "1508009603885-50cf7c579365",
    }
    for key, photo_id in PHOTO_IDS.items():
        if key in query.lower():
            return photo_id
    return "1507525428034-b723cf961d3e"  # Default beach photo


# Pre-defined destination list for batch generation
DESTINATIONS_TO_WRITE = [
    ("Lisbonne", "Portugal"),
    ("Barcelone", "Espagne"),
    ("Rome", "Italie"),
    ("Athenes", "Grece"),
    ("Marrakech", "Maroc"),
    ("Prague", "Republique tcheque"),
    ("Amsterdam", "Pays-Bas"),
    ("Istanbul", "Turquie"),
    ("Budapest", "Hongrie"),
    ("Dubai", "Emirats arabes unis"),
    ("New York", "Etats-Unis"),
    ("Bangkok", "Thailande"),
]
