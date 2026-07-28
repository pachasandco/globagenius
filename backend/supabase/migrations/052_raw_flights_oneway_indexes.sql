-- 052_raw_flights_oneway_indexes.sql
--
-- The one-way alert pipeline silently died for 7+ days because two
-- queries inside _detect_and_dispatch_oneway_alerts() hit the 8s
-- statement timeout on raw_flights as the table grew:
--
--   1. Candidate fetch: ORDER BY price LIMIT 200 with filters on
--      (trip_type='one_way', passive=false, scraped_at >= 24h ago).
--      With ~230k one_way rows/day the planner did a seq scan + sort
--      that tipped past 8s.
--
--   2. Per-route history fetch: 30-day range on
--      (origin, destination, direction, trip_type, passive). Called
--      hundreds of times per job run; safe today (3M rows/30d) but
--      will timeout when the table reaches ~500k one_way rows/day.
--
-- These two partial indexes are scoped to the one-way alert path so
-- they stay small (<50MB combined) and don't slow down inserts.

CREATE INDEX IF NOT EXISTS idx_raw_flights_oneway_price
  ON raw_flights (trip_type, passive, price)
  WHERE trip_type = 'one_way' AND passive = false;

CREATE INDEX IF NOT EXISTS idx_raw_flights_oneway_history
  ON raw_flights (origin, destination, direction, trip_type, passive, scraped_at DESC)
  WHERE trip_type = 'one_way' AND passive = false;

COMMENT ON INDEX idx_raw_flights_oneway_price IS
  'Partial index: price-ordered one_way candidates for _detect_and_dispatch_oneway_alerts.';

COMMENT ON INDEX idx_raw_flights_oneway_history IS
  'Partial index: per-(o,d,direction) 30-day history scan for one_way qualifier.';
