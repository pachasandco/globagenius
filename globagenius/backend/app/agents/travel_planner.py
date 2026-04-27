import json
import logging
from anthropic import Anthropic
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es le planificateur de voyage de Globe Genius. Tu aides les utilisateurs a construire un programme d'activites personnalise pour leur sejour.

PROCESSUS :
1. L'utilisateur donne sa destination et ses dates
2. Tu poses 3-4 questions courtes pour cerner ses preferences :
   - Type de voyage (culture, detente, aventure, gastronomie, fete, famille)
   - Budget quotidien (economique, moyen, confort, luxe)
   - Centres d'interet specifiques
   - Contraintes (mobilite, enfants, etc.)
3. Tu proposes un programme jour par jour

FORMAT DU PROGRAMME (quand tu as assez d'infos) :
Reponds en JSON :
{
  "type": "planning",
  "destination": "...",
  "duration": "X jours",
  "style": "...",
  "days": [
    {
      "day": 1,
      "title": "Titre du jour",
      "morning": {"activity": "...", "description": "...", "duration": "2h", "cost": "Gratuit"},
      "lunch": {"restaurant": "...", "cuisine": "...", "budget": "15-25€"},
      "afternoon": {"activity": "...", "description": "...", "duration": "3h", "cost": "12€"},
      "evening": {"activity": "...", "description": "...", "budget": "20-40€"}
    }
  ],
  "tips": ["conseil 1", "conseil 2", "conseil 3"],
  "estimated_budget": "XXX€ / personne"
}

QUAND TU POSES DES QUESTIONS :
Reponds en JSON :
{
  "type": "question",
  "message": "Ta question en francais",
  "options": ["Option A", "Option B", "Option C"]  // optionnel, si choix multiples
}

REGLES :
- Sois concret : noms de lieux reels, prix estimes, horaires
- Maximum 4 questions avant de proposer le planning
- Adapte le niveau de detail a la duree du sejour
- Inclus des adresses/quartiers specifiques
- Mentionne les astuces locales (transport, pourboires, etc.)
- Reponds TOUJOURS en JSON"""


class TravelPlannerSession:
    """Manages a multi-turn conversation for travel planning."""

    def __init__(self):
        self.messages: list[dict] = []
        self.destination: str = ""
        self.dates: str = ""

    def chat(self, user_message: str) -> dict | None:
        """Send a message and get the planner's response."""
        if not settings.ANTHROPIC_API_KEY:
            return {"type": "error", "message": "API non configuree"}

        from app.agents.llm_client import get_client
        client = get_client()

        self.messages.append({"role": "user", "content": user_message})

        try:
            response = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=2000,
                system=SYSTEM_PROMPT,
                messages=self.messages,
            )

            assistant_text = response.content[0].text.strip()
            self.messages.append({"role": "assistant", "content": assistant_text})

            # Parse JSON response
            text = assistant_text
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            return json.loads(text)

        except json.JSONDecodeError:
            # If not valid JSON, wrap the text response
            return {"type": "message", "message": assistant_text}
        except Exception as e:
            logger.error(f"Travel planner error: {e}")
            return {"type": "error", "message": "Erreur de l'assistant. Reessayez."}


# Store active sessions (in-memory, keyed by user_id)
_sessions: dict[str, TravelPlannerSession] = {}


def get_or_create_session(user_id: str) -> TravelPlannerSession:
    if user_id not in _sessions:
        _sessions[user_id] = TravelPlannerSession()
    return _sessions[user_id]


def reset_session(user_id: str):
    _sessions.pop(user_id, None)
