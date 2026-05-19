-- 044_raw_flights_passive.sql
--
-- Passive collection flag for raw_flights.
--
-- Some origin airports (BRU, GVA, ZRH initially — francophone expansion
-- markets) are scraped to build their price baselines silently. No user
-- currently has any of these as a preferred origin, so they must never
-- generate alerts. The flag lets the dispatcher and qualifier filter
-- those rows out without us having to maintain a parallel list at every
-- read site (the list of passive origins still lives in app.config
-- so the scrapers can decide where to set the flag).
--
-- Default false so every existing row stays in the active pipeline.

ALTER TABLE raw_flights
  ADD COLUMN IF NOT EXISTS passive boolean NOT NULL DEFAULT false;

-- Most reads hit (origin, destination, passive=false). A partial index
-- on passive=false (which is 99 %+ of the table) keeps the hot path the
-- same speed as before; the passive rows are slower to scan but they
-- are never read by the alert dispatcher anyway.
CREATE INDEX IF NOT EXISTS idx_raw_flights_active
  ON raw_flights (origin, destination)
  WHERE passive = false;
