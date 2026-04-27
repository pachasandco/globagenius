-- RAG vector store: YouTube travel transcript chunks.
-- Uses PostgreSQL full-text search (no ML dependency on Railway).
-- pgvector column reserved for future embedding upgrade.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS rag_chunks (
  id          BIGSERIAL PRIMARY KEY,
  channel     TEXT NOT NULL,
  video_id    TEXT NOT NULL,
  video_title TEXT,
  destination TEXT,
  chunk_text  TEXT NOT NULL,
  tsv         TSVECTOR GENERATED ALWAYS AS (to_tsvector('french', chunk_text)) STORED,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_destination
  ON rag_chunks (destination);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_tsv
  ON rag_chunks USING GIN (tsv);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_video_id
  ON rag_chunks (video_id);

-- Prevent re-ingesting the same video chunk twice
CREATE UNIQUE INDEX IF NOT EXISTS idx_rag_chunks_dedup
  ON rag_chunks (video_id, md5(chunk_text));
