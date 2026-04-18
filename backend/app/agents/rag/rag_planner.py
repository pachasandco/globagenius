"""RAG-augmented travel planner — replaces travel_planner.py."""

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
            JSON dict with type "message" and message text (Markdown formatted)
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
                max_tokens=3000,
                system=system_prompt,
                messages=self.messages,
            )

            assistant_message = response.content[0].text

            # Store assistant message
            self.messages.append({"role": "assistant", "content": assistant_message})

            # Add Telegram reminder at the end
            telegram_reminder = self._get_telegram_reminder()
            final_message = f"{assistant_message}\n\n{telegram_reminder}"

            # Return as plain message (Markdown will render naturally)
            return {
                "type": "message",
                "message": final_message,
            }

        except Exception as e:
            logger.error(f"Chat error: {e}")
            return {
                "type": "message",
                "message": f"Erreur: {str(e)}",
            }

    def _build_system_prompt(self, rag_context: str, destination: Optional[str] = None) -> str:
        """Build system prompt with RAG context."""
        base_prompt = """Tu es un expert voyage passionné qui planifie des séjours extraordinaires basé sur l'expérience réelle de voyageurs du monde entier.

Tu réponds TOUJOURS en FRANÇAIS en langage naturel, conversationnel et enthousiaaste.

FORMAT DE RÉPONSE:
- Utilise Markdown pour structurer ta réponse (# titres, ## sous-titres, • bullet points)
- Réponds comme un ami enthousiaste qui partage ses meilleures découvertes
- Pas de JSON, pas de parenthèses inutiles
- Chaque activité, adresse, tarif sur sa propre ligne en bullet point
- Groupes par jour (Jour 1, Jour 2, etc.) avec sections Matin, Après-midi, Soir

CONTENU:
- Sois très détaillé: noms de restaurants, adresses, tarifs, horaires
- Inclus les meilleures expériences authentiques, street food, marchés, monuments
- Propose des itinéraires réalistes avec transports et timing
- Budget détaillé: hébergement, nourriture, activités, transport
- Recommandations basées sur l'expérience réelle, pas génériques
- Ne cite jamais les créateurs YouTube, intègre juste leurs insights

STYLE:
- Enthousiaste et inspirant
- Conversationnel, comme entre amis
- Très détaillé et pratique
- Honnête sur les prix et difficultés
- Inclus astuces locales et plans secrets"""

        if rag_context:
            base_prompt += f"\n\nINFORMATIONS DE TERRAIN (expériences réelles de voyageurs):\n{rag_context}"

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
