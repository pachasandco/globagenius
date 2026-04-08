import json
import logging
from datetime import datetime, timezone
from app.config import settings
from app.agents.llm_client import get_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un redacteur voyage expert pour Globe Genius. Tu rediges des articles de destination captivants en francais.

Pour chaque destination, tu produis un article structure en JSON avec :

1. TITLE : Titre accrocheur (max 60 caracteres)
2. SUBTITLE : Sous-titre descriptif (max 100 caracteres)
3. INTRO : Paragraphe d'introduction (3-4 phrases, donne envie)
4. SECTIONS : 3-4 sections thematiques, chacune avec :
   - title : titre de section
   - content : 2-3 paragraphes riches
   - photo_query : mot-cle en anglais pour chercher une photo Unsplash (ex: "lisbon alfama streets")
5. BEST_TIME : Meilleure periode pour visiter (1-2 phrases)
6. BUDGET_TIP : Conseil budget (1-2 phrases)
7. TAGS : 4-6 tags (#destination #theme #saison)
8. PHOTO_QUERY : mot-cle principal pour la photo de couverture

Ton style : vivant, immersif, informatif. Tu donnes des details concrets (noms de quartiers, plats, experiences). Pas de cliches generiques.

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
            max_tokens=3000,
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
