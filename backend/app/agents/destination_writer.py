"""Generate a 2000-word destination guide following the
travel-journalist-writer skill (format: guide destination).

Architecture decision: this module is intentionally separate from the
legacy article_writer.py (which produces a different 4-section shape
and is kept for the existing /api/articles/generate admin endpoint).
We don't extend article_writer to avoid breaking those 4 existing
articles' contract.

The output dict matches what we'll insert into the `articles` table:
title, h1, slug, meta_description, lead, nut_graf, top_picks,
itinerary, infos_pratiques, faq, sources, tags, photo_query, plus
the technical fields iata, generated_at, word_count.

References (from /tmp/travel-skill/travel-journalist-writer/):
- references/format-guide.md (structure)
- references/seo-blog.md (slug, meta, FAQ)
- references/voix-journaliste.md (style rules)
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from app.agents.llm_client import get_client
from app.config import IATA_TO_CITY

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
FALLBACK_MODEL = "claude-haiku-4-5"
MAX_TOKENS = 16000  # 2000-3000 words of JSON-wrapped guide; 8k truncated ~half the runs

SYSTEM_PROMPT = """Tu es un journaliste voyage français professionnel. Style: Le Monde Voyage, Géo, National Geographic Traveler. Tu écris pour Globe Genius (alertes vols pas chers depuis la France) un GUIDE DESTINATION de 2000 mots minimum.

PRINCIPES NON-NÉGOCIABLES:
1. ANGLE avant la destination. Pas de "X est une ville magnifique".
2. Montrer, pas affirmer. Pas de "magnifique", "incroyable", "à couper le souffle". Remplace par scènes, chiffres, citations, détails sensoriels.
3. Premier paragraphe = scène ou tension, jamais de définition Wikipedia.
4. Sources fact-checkables (office du tourisme, INSEE, étude). Pas d'invention.
5. Pas de clichés ("perle de…", "pays des sourires", "Venise du Nord").
6. Le lecteur n'est pas un client. L'article informe et raconte, il ne vend pas.

FORMAT GUIDE DESTINATION mixé Top X + Itinéraire J1-J3 + Infos pratiques. Toujours en français, toujours rigoureux.

Réponds UNIQUEMENT avec un JSON valide qui suit EXACTEMENT cette structure:

{
  "title": "Title tag SEO ≤60 caractères, mot-clé en début, promesse claire",
  "h1": "H1 article (peut différer du title, plus accrocheur)",
  "slug": "slug-court-kebab-mots-cles (3-6 mots, pas de mots vides)",
  "meta_description": "140-155 caractères, verbe action, mot-clé, promesse",
  "lead": "Paragraphe d'ouverture (80-150 mots): scène concrète qui pose l'angle. Pas de définition.",
  "nut_graf": "Paragraphe-clé (150-200 mots): de quoi parle vraiment l'article et pourquoi le lecteur doit lire.",
  "top_picks": [
    {
      "name": "Nom du lieu/expérience",
      "angle": "phrase d'angle 6-12 mots qui dit pourquoi celui-ci",
      "description": "2-4 phrases journalistiques sur le lieu, son histoire, son intérêt",
      "practical": "Adresse · Horaires · Prix · Comment y aller depuis le centre"
    }
    // EXACTEMENT 8 entrées
  ],
  "itinerary": [
    {
      "day": 1,
      "title": "Titre thématique de la journée",
      "morning": "9h-12h: description avec adresses + temps + prix",
      "lunch": "Restau précis avec adresse et budget",
      "afternoon": "14h-18h: description + transports",
      "evening": "Bar/dîner/spectacle",
      "lodging": "Suggestion gamme + quartier",
      "rain_plan": "Plan B 1-2 phrases si pluie",
      "budget_option": "Variante éco",
      "premium_option": "Variante haut de gamme"
    }
    // EXACTEMENT 3 jours
  ],
  "infos_pratiques": {
    "best_season": "Mois précis et pourquoi (3-4 phrases)",
    "how_to_get_there": "Depuis Paris (vol/train/voiture) + ordres de prix",
    "visa": "Formalités pour ressortissants UE",
    "daily_budget_eco": "Montant € pour 1 jour éco",
    "daily_budget_comfort": "Montant € confort",
    "daily_budget_premium": "Montant € premium",
    "where_to_sleep": "3 quartiers avec angle (charme/calme/local)",
    "to_avoid": "Pièges à touristes, arnaques, périodes",
    "local_tips": "Pratiques locales utiles, pourboire, tabous"
  },
  "faq": [
    {"q": "Question issue de Google People Also Ask", "a": "Réponse 40-80 mots autonome"}
    // 3 à 6 questions
  ],
  "sources": [
    "https://lien.officiel.fr/source-1",
    "https://lien.officiel.fr/source-2"
    // 2 à 4 sources d'autorité
  ],
  "tags": ["mot-cle-1", "mot-cle-2", "mot-cle-3", "mot-cle-4", "mot-cle-5"],
  "photo_query": "search query in English for Unsplash, e.g. 'Barcelona Spain travel'"
}

Densité totale visée: 2000 mots minimum (lead + nut_graf + 8x top_picks + 3x itinerary + infos_pratiques + faq). Sans bourrage. Si l'angle ne porte pas 2000 mots de qualité, descends à 1500 mais ne brode pas.

Aucun texte en dehors du JSON. Aucun ```. JSON brut."""


def _strip_code_fence(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers Claude often adds
    even when explicitly told not to."""
    text = text.strip()
    if text.startswith("```"):
        # remove first line (```json or ```)
        first_newline = text.find("\n")
        if first_newline > 0:
            text = text[first_newline + 1 :]
        # remove trailing ```
        if text.endswith("```"):
            text = text[: -3]
    return text.strip()


def _count_words(article: dict) -> int:
    """Rough word count over the user-visible text fields. Used for
    audit (are articles really hitting 2000 words?)."""
    parts: list[str] = []
    parts.append(article.get("lead", ""))
    parts.append(article.get("nut_graf", ""))
    for pick in article.get("top_picks", []) or []:
        parts.append(pick.get("description", ""))
        parts.append(pick.get("practical", ""))
    for day in article.get("itinerary", []) or []:
        for k in ("morning", "lunch", "afternoon", "evening", "lodging", "rain_plan", "budget_option", "premium_option"):
            parts.append(day.get(k, ""))
    infos = article.get("infos_pratiques") or {}
    for v in infos.values():
        if isinstance(v, str):
            parts.append(v)
    for q in article.get("faq", []) or []:
        parts.append(q.get("a", ""))
    return sum(len(p.split()) for p in parts if p)


def generate_destination_guide(iata: str) -> Optional[dict]:
    """Generate a 2000-word guide for a destination identified by its
    IATA code (BCN, BKK, MLE...). Synchronous, blocks ~30-60s.

    Returns a dict ready to insert into the `articles` table, or None
    on any failure (no API key, JSON parse error, network error).
    """
    client = get_client()
    if client is None:
        logger.warning("Anthropic client unavailable, cannot generate guide for %s", iata)
        return None

    # Build a friendly user message: city name + country if we know it
    city_label = IATA_TO_CITY.get(iata, iata)
    user_message = (
        f"Rédige le guide destination pour {city_label} (code aéroport: {iata}). "
        f"Public: voyageurs français qui partent en court ou moyen séjour. "
        f"Mot-clé SEO principal: \"{city_label.lower()} guide voyage\". "
        f"Mots-clés secondaires: \"que faire à {city_label.lower()}\", \"itinéraire {city_label.lower()}\", "
        f"\"voyage {city_label.lower()} pas cher\". Format de réponse: JSON brut conforme au schéma."
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except Exception as e:
        logger.warning("Sonnet call failed for %s, retrying with Haiku: %s", iata, e)
        try:
            response = client.messages.create(
                model=FALLBACK_MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
        except Exception as e2:
            logger.error("Haiku fallback also failed for %s: %s", iata, e2)
            return None

    if not response.content:
        logger.error("Empty Anthropic response for %s", iata)
        return None
    raw_text = response.content[0].text or ""
    if response.stop_reason == "max_tokens":
        logger.warning("Guide generation hit max_tokens for %s — JSON may be truncated", iata)

    cleaned = _strip_code_fence(raw_text)
    try:
        article = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("Guide JSON parse failed for %s: %s. Last 200 chars: %s",
                     iata, e.msg, cleaned[-200:])
        return None

    article["iata"] = iata
    article["destination"] = city_label  # keep human-readable name in DB too
    article["generated_at"] = datetime.now(timezone.utc).isoformat()
    article["word_count"] = _count_words(article)

    return article
