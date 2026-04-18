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

        # Retrieve RAG context
        rag_context = ""
        if self.retriever and destination:
            chunks = self.retriever.retrieve_by_destination(destination, top_k=5)
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
        base_prompt = """Tu es un expert voyage passionné qui planifie des séjours incroyables.

Tu réponds toujours en FRANÇAIS. Tu dois répondre avec un JSON strict dans l'un de ces formats:

1. Pour poser une question:
{"type": "question", "message": "Ta question en français", "options": ["Option 1", "Option 2", "Option 3"]}

2. Pour proposer un plan de voyage:
{"type": "planning", "destination": "Destination", "duration": "7 jours", "estimated_budget": "1500€", "days": [{"day": 1, "title": "Titre", "morning": {"activity": "Activité"}, "afternoon": {"activity": "Activité"}, "evening": {"activity": "Activité"}}, ...]}

3. Pour un message simple:
{"type": "message", "message": "Ton message en français"}

RÈGLES:
- Réponds TOUJOURS en JSON valide.
- Si tu trouves des informations pertinentes dans les sources YouTube, cite le créateur et la vidéo.
- Si aucune source YouTube ne couvre la destination, dis-le et propose quand même un plan basé sur tes connaissances.
- Les plans de voyage doivent inclure 1 jour par jour du séjour.
- Sois engageant et enthousiaste.
"""

        if rag_context:
            base_prompt += f"\n\nSOURCES DISPONIBLES:\n{rag_context}"

        if destination:
            base_prompt += f"\n\nDestination mentionnée: {destination}"

        return base_prompt

    def _format_rag_chunks(self, chunks: list[dict]) -> str:
        """Format RAG chunks for LLM context."""
        lines = ["Sources YouTube:"]
        seen_videos = set()

        for chunk in chunks:
            video_id = chunk.get("video_id")
            channel = chunk.get("channel")
            title = chunk.get("video_title")
            text = chunk.get("text", "")[:300]  # Truncate to 300 chars

            # Avoid duplicate video references
            key = (video_id, channel)
            if key not in seen_videos:
                lines.append(f"- {channel} - {title}")
                seen_videos.add(key)

            lines.append(f"  {text}...")

        return "\n".join(lines)

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
