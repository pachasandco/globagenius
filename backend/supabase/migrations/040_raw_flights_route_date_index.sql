-- Migration 040: compound index on raw_flights for the 7-day
-- per-route rate query used by baseline clustering (chantier 2).
--
-- Without this index, the query
--   SELECT origin, destination, COUNT(*) FROM raw_flights
--     WHERE scraped_at > NOW() - INTERVAL '7 days'
--     GROUP BY origin, destination
-- scans ~98k rows (14k/day × 7d). Empirical baseline measured
-- 2026-05-17: pulling 200k rows over 7 days took 88s without
-- this index. Target after deploy: < 1s for the GROUP BY.
--
-- IF NOT EXISTS so re-running is safe even if the index was
-- created out-of-band.

CREATE INDEX IF NOT EXISTS idx_raw_flights_route_date
  ON raw_flights(origin, destination, scraped_at DESC);
