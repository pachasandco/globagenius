-- Migration 007: priority_destinations table
-- Stores the weekly-updated list of destinations to monitor, scored by
-- seasonal affinity (French travelers) + Travelpayouts cheap routes signal.
-- Updated by job_update_destinations() every Monday at 3am.

CREATE TABLE IF NOT EXISTS priority_destinations (
    iata          TEXT        PRIMARY KEY,
    label_fr      TEXT        NOT NULL,
    region        TEXT        NOT NULL,
    score         NUMERIC     NOT NULL DEFAULT 0,
    is_long_haul  BOOLEAN     NOT NULL DEFAULT FALSE,
    season        TEXT,                              -- season when last scored
    in_travelpayouts BOOLEAN  DEFAULT FALSE,         -- found in TP cheap routes this week
    tp_price      NUMERIC,                           -- cheapest price found on TP (€)
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for score-ordered reads (used by get_priority_destinations_from_db)
CREATE INDEX IF NOT EXISTS idx_priority_destinations_score
    ON priority_destinations (score DESC);

-- Index for region filtering (future use)
CREATE INDEX IF NOT EXISTS idx_priority_destinations_region
    ON priority_destinations (region);

COMMENT ON TABLE priority_destinations IS
    'Weekly-scored destination list. Updated by job_update_destinations every Monday at 3am. '
    'Combines seasonal French travel patterns with Travelpayouts live cheap-route signal.';

-- RLS: table is public read, service_role only for writes
ALTER TABLE priority_destinations ENABLE ROW LEVEL SECURITY;

-- Anyone can read (used by scraping jobs and frontend)
CREATE POLICY "priority_destinations_select"
    ON priority_destinations FOR SELECT
    USING (true);

-- Only service_role can insert/update/delete (backend jobs)
CREATE POLICY "priority_destinations_service_write"
    ON priority_destinations FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
