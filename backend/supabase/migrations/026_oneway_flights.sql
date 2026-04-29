-- V5: extend raw_flights and qualified_items to store one-way deals
-- alongside the existing round-trip rows.
--
-- Design:
--   trip_type: 'round_trip' | 'one_way'
--   direction: 'outbound' (home → dest) | 'inbound' (dest → home) | NULL for round-trip
--   return_date: NOT NULL for round-trip, NULL for one-way
-- Constraint enforces consistency.

ALTER TABLE raw_flights
  ADD COLUMN IF NOT EXISTS trip_type text NOT NULL DEFAULT 'round_trip',
  ADD COLUMN IF NOT EXISTS direction text;

ALTER TABLE raw_flights ALTER COLUMN return_date DROP NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'raw_flights_trip_type_chk'
  ) THEN
    ALTER TABLE raw_flights
      ADD CONSTRAINT raw_flights_trip_type_chk
        CHECK (trip_type IN ('round_trip', 'one_way'));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'raw_flights_oneway_dates_chk'
  ) THEN
    ALTER TABLE raw_flights
      ADD CONSTRAINT raw_flights_oneway_dates_chk
        CHECK (
          (trip_type = 'round_trip' AND return_date IS NOT NULL AND direction IS NULL)
          OR
          (trip_type = 'one_way' AND return_date IS NULL AND direction IN ('outbound','inbound'))
        );
  END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_raw_flights_trip_type
  ON raw_flights (origin, destination, trip_type, departure_date);

ALTER TABLE qualified_items
  ADD COLUMN IF NOT EXISTS trip_type text NOT NULL DEFAULT 'round_trip',
  ADD COLUMN IF NOT EXISTS direction text;

CREATE INDEX IF NOT EXISTS idx_qualified_items_trip_type
  ON qualified_items (type, trip_type, direction);
