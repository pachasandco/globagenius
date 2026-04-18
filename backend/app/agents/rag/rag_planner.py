"""RAG-augmented travel planner — replaces travel_planner.py."""

import json
import logging
import re
from typing import Optional

from app.agents.llm_client import get_client
from .retriever import RagRetriever
from .web_fallback import search_destination, format_search_results

logger = logging.getLogger(__name__)

# Global retriever and RAG DB client (initialized on first use)
_retriever: Optional[RagRetriever] = None


def set_rag_retriever(retriever: RagRetriever):
    """Set the RAG retriever instance."""
    global _retriever
    _retriever = retriever


def get_rag_retriever() -> Optional[RagRetriever]:
    """Get the current RAG retriever instance."""
    return _retriever


def extract_destination(text: str) -> Optional[str]:
    """
    Try to extract destination from user message.

    Examples:
        "Je pars à Tokyo 7 jours" -> "Tokyo"
        "Paris pour un weekend" -> "Paris"
    """
    # Simple pattern matching for French "à {destination}"
    match = re.search(r"(?:à|vers|pour|aller à)\s+([A-Z][a-zA-Zéè\s]+?)(?:\s+\d|$|\.)", text)
    if match:
        return match.group(1).strip()
    return None


class RagTravelPlannerSession:
    """Travel planner session with RAG retrieval."""

    def __init__(self, user_id: str, retriever: Optional[RagRetriever] = None):
        """Initialize session."""
        self.user_id = user_id
        self.messages = []
        self.retriever = retriever or get_rag_retriever()

    def chat(self, user_message: str) -> dict:
        """
        Process user message and return travel planning response.

        Args:
            user_message: User input (French)

        Returns:
            JSON dict with keys: type, message, options, destination, days, estimated_budget
        """
        # Store user message
        self.messages.append({"role": "user", "content": user_message})

        # Try to extract destination
        destination = extract_destination(user_message)

        # Retrieve RAG context with multiple queries for comprehensive coverage
        rag_context = ""
        if self.retriever and destination:
            # Query for main destination
            chunks = self.retriever.retrieve_by_destination(destination, top_k=5)

            # If weak results, also query for food, activities, culture
            if chunks and len(chunks) < 3:
                food_chunks = self.retriever.retrieve(f"restaurants food cuisine {destination}", top_k=3)
                activity_chunks = self.retriever.retrieve(f"activities things to do {destination}", top_k=3)
                culture_chunks = self.retriever.retrieve(f"culture local tips {destination}", top_k=2)
                chunks.extend(food_chunks)
                chunks.extend(activity_chunks)
                chunks.extend(culture_chunks)

            if chunks:
                rag_context = self._format_rag_chunks(chunks)
            else:
                # Fall back to web search
                web_results = search_destination(destination, limit=5)
                rag_context = format_search_results(web_results)

        # Build augmented system prompt
        system_prompt = self._build_system_prompt(rag_context, destination)

        # Call Claude
        try:
            client = get_client()
            response = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=2000,
                system=system_prompt,
                messages=self.messages,
            )

            assistant_message = response.content[0].text

            # Try to parse JSON response
            data = self._parse_response(assistant_message)

            # Store assistant message
            self.messages.append({"role": "assistant", "content": assistant_message})

            return data

        except Exception as e:
            logger.error(f"Chat error: {e}")
            return {
                "type": "error",
                "message": f"Erreur: {str(e)}",
            }

    def _build_system_prompt(self, rag_context: str, destination: Optional[str] = None) -> str:
        """Build system prompt with RAG context."""
        base_prompt = """Tu es un expert voyage passionné qui planifie des séjours incroyables, basé sur l'expérience réelle de voyageurs du monde entier.

Tu réponds toujours en FRANÇAIS. Tu dois répondre avec un JSON strict dans l'un de ces formats:

1. Pour poser une question:
{"type": "question", "message": "Ta question en français", "options": ["Option 1", "Option 2", "Option 3"]}

2. Pour proposer un plan de voyage détaillé:
{"type": "planning", "destination": "Destination", "duration": "7 jours", "estimated_budget": "1500€", "days": [{"day": 1, "title": "Jour 1 - Arrivée et exploration du quartier XYZ", "morning": {"activity": "08h: Arrivée à l'aéroport. Transfert à l'hôtel. Petit-déjeuner au café local recommandé (El Café, rue XX). Pause et repos jusqu'à 11h."}, "afternoon": {"activity": "12h-15h: Déjeuner dans le quartier historique (Restaurant NOM, spécialité: PLAT). 15h-17h: Visite du marché central, exploration des ruelles, photos. Magasinage d'artisanat local."}, "evening": {"activity": "19h: Apéritif au rooftop bar vue sur la ville (NOM du bar). 20h: Dîner street food au quartier XXXX (tacos, kebabs, fruits tropicaux). Repos à l'hôtel."}}, ...]}

3. Pour un message simple:
{"type": "message", "message": "Ton message en français"}

INSTRUCTIONS CRITIQUES:
- Réponds TOUJOURS en JSON valide et complet.
- N'UTILISE PAS les noms de créateurs ou chaînes YouTube — intègre leurs insights directement dans tes conseils.
- Les plans doivent être très détaillés: noms de lieux, restaurants, activités précises, horaires, conseils pratiques.
- Inclus les meilleurs restaurants, street food, marchés, monuments, quartiers à explorer.
- Propose des itinéraires réalistes avec les transports et temps de trajet.
- Les budgets doivent être réalistes par catégorie: hébergement, nourriture, activités, transport.
- Les plans de voyage doivent inclure 1 jour par jour complet du séjour avec timing.
- Sois très engageant, enthousiaste et inspirant dans tes descriptions.
- Fais des recommandations authentiques basées sur l'expérience réelle (pas générique).
"""

        if rag_context:
            base_prompt += f"\n\nINFORMATIONS DE TERRAIN (d'expériences réelles de voyageurs):\n{rag_context}"

        if destination:
            base_prompt += f"\n\nDestination demandée: {destination}"

        return base_prompt

    def _format_rag_chunks(self, chunks: list[dict]) -> str:
        """Format RAG chunks for LLM context (without citing sources)."""
        lines = []

        for chunk in chunks:
            text = chunk.get("text", "")
            if text.strip():
                lines.append(f"• {text}")

        return "\n".join(lines) if lines else ""

    def _parse_response(self, text: str) -> dict:
        """Extract JSON from Claude response."""
        # Try to extract JSON block
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Fallback: wrap raw text
        return {
            "type": "message",
            "message": text,
        }


# Global session storage
_sessions = {}


def get_or_create_session(user_id: str, retriever: Optional[RagRetriever] = None) -> RagTravelPlannerSession:
    """Get or create a travel planner session for a user."""
    if user_id not in _sessions:
        _sessions[user_id] = RagTravelPlannerSession(user_id, retriever)
    return _sessions[user_id]


def reset_session(user_id: str):
    """Reset a user's planner session."""
    if user_id in _sessions:
        del _sessions[user_id]
