-- Migration 017: add created_at alias on sent_alerts
-- The scheduler queries sent_alerts.created_at but the column is named sent_at.
-- Add created_at with the same default so both names work.

ALTER TABLE sent_alerts
    ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();

-- Backfill existing rows from sent_at
UPDATE sent_alerts SET created_at = sent_at WHERE created_at IS DISTINCT FROM sent_at;

CREATE INDEX IF NOT EXISTS idx_sent_alerts_created_at ON sent_alerts(created_at DESC);
