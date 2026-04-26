-- Add reverified_at to qualified_items to track when a deal was last
-- confirmed live. Used by the homepage to filter out stale deals.
ALTER TABLE qualified_items
  ADD COLUMN IF NOT EXISTS reverified_at TIMESTAMPTZ;

-- Backfill: treat existing active items as reverified at creation time
-- so they don't all disappear immediately after deploy.
UPDATE qualified_items
  SET reverified_at = created_at
  WHERE status = 'active' AND reverified_at IS NULL;

-- Index for the homepage query: active deals with fresh reverification
CREATE INDEX IF NOT EXISTS idx_qualified_items_reverified_at
  ON qualified_items (reverified_at)
  WHERE status = 'active';
