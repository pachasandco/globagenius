"""Wrapper around ChromaDB for RAG vector storage."""

import logging
from typing import Optional, List
import os

logger = logging.getLogger(__name__)

# Try to import ChromaDB, but don't fail if not installed yet
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("chromadb not installed — RAG will use stub mode (retriever returns empty)")

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("sentence-transformers not installed — RAG will use stub mode")


class ChromaDBClient:
    """Vector database client for RAG."""

    def __init__(self, db_path: str = "./data/travel_rag.db"):
        """Initialize ChromaDB client."""
        self.db_path = db_path
        self.client = None
        self.collection = None
        self.embedder = None

        if CHROMADB_AVAILABLE and EMBEDDINGS_AVAILABLE:
            try:
                # Initialize ChromaDB
                os.makedirs(db_path, exist_ok=True)
                self.client = chromadb.Client(
                    Settings(
                        chroma_db_impl="duckdb",
                        persist_directory=db_path,
                        anonymized_telemetry=False,
                    )
                )
                self.collection = self.client.get_or_create_collection(
                    name="travel_guides",
                    metadata={"hnsw:space": "cosine"},
                )

                # Load embedding model
                self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("✅ ChromaDB initialized successfully")
            except Exception as e:
                logger.error(f"ChromaDB initialization failed: {e}")
                self.client = None
                self.collection = None

    def add_document(
        self,
        text: str,
        metadata: Optional[dict] = None,
        doc_id: Optional[str] = None,
    ) -> bool:
        """Add a document to the vector store."""
        if not self.collection or not self.embedder:
            return False

        try:
            embedding = self.embedder.encode(text).tolist()
            self.collection.add(
                ids=[doc_id or f"doc_{len(self.collection.get()['ids'])}"],
                embeddings=[embedding],
                metadatas=[metadata or {}],
                documents=[text],
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            return False

    def query(
        self,
        query_text: str,
        destination: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.3,
    ) -> List[dict]:
        """Query the vector database."""
        if not self.collection or not self.embedder:
            return []

        try:
            query_embedding = self.embedder.encode(query_text).tolist()
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
            )

            # Format results
            documents = []
            if results and results.get("documents"):
                for i, doc_text in enumerate(results["documents"][0]):
                    if doc_text:
                        doc = {
                            "text": doc_text,
                            "similarity": results.get("distances", [[]])[0][i] if results.get("distances") else 0,
                        }
                        # Add metadata
                        if results.get("metadatas") and i < len(results["metadatas"][0]):
                            doc.update(results["metadatas"][0][i])
                        documents.append(doc)

            return documents
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []

    def health_check(self) -> bool:
        """Check if ChromaDB is operational."""
        return self.client is not None and self.collection is not None


# Global ChromaDB instance
_chromadb_client: Optional[ChromaDBClient] = None


def get_chromadb_client() -> ChromaDBClient:
    """Get or create the global ChromaDB client."""
    global _chromadb_client
    if _chromadb_client is None:
        _chromadb_client = ChromaDBClient()
    return _chromadb_client
