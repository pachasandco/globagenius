"""RAG-augmented travel planner backed by Supabase full-text search."""

import logging
import re
from typing import Optional

from app.agents.llm_client import get_client
from .retriever import RagRetriever

logger = logging.getLogger(__name__)

_retriever: Optional[RagRetriever] = None


def set_rag_retriever(retriever: RagRetriever):
    global _retriever
    _retriever = retriever


def get_rag_retriever() -> Optional[RagRetriever]:
    return _retriever


def extract_destination(text: str) -> Optional[str]:
    """Extract destination name from French travel request."""
    patterns = [
        r"destination\s*[:\-]\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-]+?)(?:\s*[,\n]|$)",
        r"(?:à|vers|pour|aller à|planifie.*?)\s+([A-Z][A-Za-zÀ-ÿ\s\-]+?)(?:\s+\d|\s*[,\n]|$)",
        r"(?:voyage|séjour|trip|week-end|weekend)\s+(?:à|en|au|aux)\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-]+?)(?:\s+\d|\s*[,\n]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            dest = match.group(1).strip().rstrip(",")
            if len(dest) > 2:
                return dest
    return None


SYSTEM_PROMPT = """Tu es un expert voyage passionné qui planifie des séjours extraordinaires basé sur l'expérience réelle de voyageurs.

Tu réponds TOUJOURS en FRANÇAIS en langage naturel, conversationnel et enthousiaste.

FORMAT DE RÉPONSE:
- Utilise Markdown: ## titres, • bullet points
- Réponds comme un ami qui partage ses meilleures découvertes
- Chaque activité, adresse, tarif sur sa propre ligne en bullet point
- Groupes par jour (## Jour 1, ## Jour 2, etc.) avec sections Matin / Après-midi / Soir

CONTENU:
- Sois concret: noms de lieux réels, adresses, tarifs estimés, horaires
- Inclus les meilleures expériences authentiques, street food, marchés, monuments
- Propose des itinéraires réalistes avec transports et timing
- Budget détaillé: hébergement, nourriture, activités, transport
- Astuces locales pratiques (transports, pourboires, saison, etc.)

STYLE:
- Enthousiaste et inspirant
- Conversationnel, comme entre amis
- Très détaillé et pratique
- Honnête sur les prix et difficultés"""


class RagTravelPlannerSession:
    """Travel planner session with Supabase RAG retrieval."""

    def __init__(self, user_id: str, retriever: Optional[RagRetriever] = None):
        self.user_id = user_id
        self.messages: list[dict] = []
        self.retriever = retriever or get_rag_retriever()

    def chat(self, user_message: str) -> dict:
        self.messages.append({"role": "user", "content": user_message})

        destination = extract_destination(user_message)
        rag_context = self._fetch_context(user_message, destination)
        system = self._build_system(rag_context, destination)

        try:
            client = get_client()
            if client is None:
                return {"type": "error", "message": "Clé API non configurée."}

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=system,
                messages=self.messages,
            )

            reply = response.content[0].text
            self.messages.append({"role": "assistant", "content": reply})
            return {"type": "message", "message": reply}

        except Exception as e:
            logger.error(f"Planner chat error: {e}")
            return {"type": "error", "message": "Une erreur est survenue. Réessayez."}

    def _fetch_context(self, query: str, destination: Optional[str]) -> str:
        if not self.retriever:
            return ""
        try:
            if destination:
                chunks = self.retriever.retrieve_by_destination(destination, top_k=6)
            else:
                chunks = self.retriever.retrieve(query, top_k=4)
            return "\n".join(f"• {c['chunk_text']}" for c in chunks if c.get("chunk_text"))
        except Exception as e:
            logger.warning(f"RAG context fetch failed: {e}")
            return ""

    def _build_system(self, rag_context: str, destination: Optional[str]) -> str:
        prompt = SYSTEM_PROMPT
        if destination:
            prompt += f"\n\nDestination demandée : **{destination}**"
        if rag_context:
            prompt += f"\n\nINFORMATIONS DE TERRAIN (expériences réelles de voyageurs) :\n{rag_context}"
        return prompt


_sessions: dict[str, RagTravelPlannerSession] = {}


def get_or_create_session(user_id: str, retriever: Optional[RagRetriever] = None) -> RagTravelPlannerSession:
    if user_id not in _sessions:
        _sessions[user_id] = RagTravelPlannerSession(user_id, retriever)
    return _sessions[user_id]


def reset_session(user_id: str):
    _sessions.pop(user_id, None)
