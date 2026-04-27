"""Retrieve relevant RAG chunks from Supabase using PostgreSQL full-text search."""

import logging
import re

logger = logging.getLogger(__name__)


def _normalize_query(query: str) -> str:
    """Convert free text to a tsquery-compatible OR string."""
    words = re.findall(r"[a-zA-ZÀ-ÿ]{3,}", query)
    return " | ".join(words) if words else query


class RagRetriever:
    """Query rag_chunks via Supabase full-text search (no ML deps)."""

    def __init__(self, db):
        self.db = db

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        """Full-text search across all chunks."""
        if not self.db:
            return []
        try:
            tsquery = _normalize_query(query)
            resp = (
                self.db.table("rag_chunks")
                .select("chunk_text, channel, video_title, destination")
                .text_search("tsv", tsquery, config="french")
                .limit(top_k)
                .execute()
            )
            return resp.data or []
        except Exception as e:
            logger.warning(f"RAG retrieve error: {e}")
            return []

    def retrieve_by_destination(self, destination: str, top_k: int = 8) -> list[dict]:
        """Retrieve chunks tagged to a specific destination, with FTS fallback."""
        if not self.db:
            return []
        try:
            resp = (
                self.db.table("rag_chunks")
                .select("chunk_text, channel, video_title, destination")
                .ilike("destination", f"%{destination}%")
                .limit(top_k)
                .execute()
            )
            rows = resp.data or []

            if len(rows) < 3:
                fts = self.retrieve(destination, top_k=top_k - len(rows))
                seen = {r["chunk_text"] for r in rows}
                rows += [r for r in fts if r["chunk_text"] not in seen]

            return rows[:top_k]
        except Exception as e:
            logger.warning(f"RAG retrieve_by_destination error: {e}")
            return []
