-- Add chunk_hash column for deduplication via upsert (PostgREST can't use md5() in on_conflict)
ALTER TABLE rag_chunks ADD COLUMN IF NOT EXISTS chunk_hash TEXT;

-- Populate existing rows
UPDATE rag_chunks SET chunk_hash = md5(chunk_text) WHERE chunk_hash IS NULL;

-- Make non-nullable going forward
ALTER TABLE rag_chunks ALTER COLUMN chunk_hash SET NOT NULL;

-- Drop old functional index and unique constraint, replace with column-based
DROP INDEX IF EXISTS idx_rag_chunks_dedup;
CREATE UNIQUE INDEX IF NOT EXISTS idx_rag_chunks_dedup ON rag_chunks (video_id, chunk_hash);
