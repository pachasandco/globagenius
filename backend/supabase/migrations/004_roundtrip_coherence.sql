-- Roundtrip coherence — add duration metadata and tier classification.
-- Purely additive: existing rows get NULL/default values, no breaking changes.

ALTER TABLE raw_flights
  ADD COLUMN IF NOT EXISTS trip_duration_days INTEGER,
  ADD COLUMN IF NOT EXISTS duration_minutes INTEGER;

CREATE INDEX IF NOT EXISTS idx_raw_flights_route_duration
  ON raw_flights (origin, destination, trip_duration_days);

ALTER TABLE qualified_items
  ADD COLUMN IF NOT EXISTS tier TEXT DEFAULT 'free';
