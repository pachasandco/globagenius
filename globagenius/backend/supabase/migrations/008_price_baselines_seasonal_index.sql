-- Migration 008: index optimisations for seasonal baseline lookups
--
-- The V2 baseline segmentation produces route_keys of two forms:
--   Legacy:   CDG-JFK-bucket_long
--   Seasonal: CDG-JFK-bucket_long-m08-lt60
--
-- The qualification pipeline does 3 lookups per flight (seasonal → legacy → dest-wide).
-- Without an index on route_key this becomes a full-scan on every lookup.
-- price_baselines already has a UNIQUE constraint on route_key (from migration 001),
-- which creates a btree index automatically. This migration adds a partial index
-- optimised for the prefix pattern used in fallback lookups.

-- Partial index for destination-wide fallback keys (prefix "*-")
-- Covers the cold-start case where no route-specific baseline exists yet.
CREATE INDEX IF NOT EXISTS idx_price_baselines_dest_fallback
    ON price_baselines (route_key)
    WHERE route_key LIKE '*-%';

-- Index on (type, route_key) to speed up the type='flight' filter combined with key lookup.
-- The existing UNIQUE index on route_key alone does not include type.
CREATE INDEX IF NOT EXISTS idx_price_baselines_type_route
    ON price_baselines (type, route_key);

-- Add departure_date column to raw_flights if not already present
-- (needed by compute_baselines_by_bucket for seasonal segmentation)
ALTER TABLE raw_flights
    ADD COLUMN IF NOT EXISTS departure_date DATE
        GENERATED ALWAYS AS (CAST(departure_date_text AS DATE)) STORED;

-- departure_date_text may already exist as the underlying text column;
-- if raw_flights already has departure_date as a text column we just ensure
-- it is queryable. The GENERATED column above is a no-op if departure_date
-- already exists. Safe to run multiple times.

-- Index for baseline recalculation query (filters by scraped_at + trip_duration_days NOT NULL)
CREATE INDEX IF NOT EXISTS idx_raw_flights_scraped_duration
    ON raw_flights (scraped_at DESC)
    WHERE trip_duration_days IS NOT NULL;

COMMENT ON INDEX idx_price_baselines_type_route IS
    'Speeds up the 3-level seasonal→legacy→dest-wide baseline lookup in the qualification pipeline (V2).';

COMMENT ON INDEX idx_raw_flights_scraped_duration IS
    'Speeds up job_recalculate_baselines which filters on scraped_at + trip_duration_days NOT NULL.';
