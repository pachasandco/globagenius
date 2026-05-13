-- Migration 023: deal sub-types (oneway_exceptional + split_ticket)
--
-- 1. Add `deal_subtype` and `metadata` columns to qualified_items
--    so the dispatcher can route per-type templates and the frontend can
--    style cards accordingly.
-- 2. Add `trip_type` to raw_flights and relax `return_date NOT NULL`
--    so one-way fares can be stored.
-- Existing rows are backfilled to 'roundtrip' via DEFAULT.

ALTER TABLE qualified_items
  ADD COLUMN IF NOT EXISTS deal_subtype varchar(20) NOT NULL DEFAULT 'roundtrip',
  ADD COLUMN IF NOT EXISTS metadata jsonb DEFAULT '{}'::jsonb;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'qualified_items_deal_subtype_check'
  ) THEN
    ALTER TABLE qualified_items
      ADD CONSTRAINT qualified_items_deal_subtype_check
      CHECK (deal_subtype IN ('roundtrip', 'oneway_exceptional', 'split_ticket'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_qualified_items_deal_subtype
  ON qualified_items(deal_subtype);

-- raw_flights: one-way support
ALTER TABLE raw_flights
  ADD COLUMN IF NOT EXISTS trip_type varchar(20) NOT NULL DEFAULT 'roundtrip';

ALTER TABLE raw_flights
  ALTER COLUMN return_date DROP NOT NULL;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'raw_flights_trip_type_check'
  ) THEN
    ALTER TABLE raw_flights
      ADD CONSTRAINT raw_flights_trip_type_check
      CHECK (trip_type IN ('roundtrip', 'oneway'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_raw_flights_trip_type
  ON raw_flights(trip_type);
