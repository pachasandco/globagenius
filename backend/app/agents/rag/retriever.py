"""Retrieve relevant chunks from RAG vector database."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RagRetriever:
    """Query vector database for travel-relevant context."""

    def __init__(self, db_client):
        """Initialize retriever with ChromaDB client."""
        self.db_client = db_client

    def retrieve(
        self,
        query: str,
        destination: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.3,
    ) -> list[dict]:
        """
        Retrieve top-K relevant chunks for a travel query.

        Args:
            query: User query or destination name
            destination: Optional explicit destination for filtering
            top_k: Number of chunks to retrieve
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            List of dicts: {text, similarity, channel, video_id, video_title}
        """
        try:
            results = self.db_client.query(
                query_text=query,
                destination=destination,
                top_k=top_k,
                min_similarity=min_similarity,
            )
            return results or []
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return []

    def retrieve_by_destination(
        self,
        destination: str,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Retrieve chunks specifically about a destination.

        Args:
            destination: Destination name (e.g., "Tokyo", "Paris")
            top_k: Number of chunks to retrieve

        Returns:
            List of relevant chunks with metadata
        """
        return self.retrieve(
            query=destination,
            destination=destination,
            top_k=top_k,
            min_similarity=0.2,  # Stricter for destination-specific queries
        )
