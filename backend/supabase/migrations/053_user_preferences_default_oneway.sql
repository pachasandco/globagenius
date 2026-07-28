-- 053_user_preferences_default_oneway.sql
--
-- Default `flight_trip_types` becomes ["round_trip", "one_way"] so
-- new signups receive both A/R and aller-simple alerts by default.
-- This is a P0 fix: 31/37 (84%) of beta users had the legacy default
-- ["round_trip"] and silently missed every one_way pépite (e.g.
-- CDG→Split 30€).
--
-- Existing users are migrated to include "one_way" UNLESS they
-- explicitly removed it (we can't tell the difference from a
-- legacy default, so we treat the entire pre-2026-06-07 cohort as
-- "never explicitly opted out" and add one_way to their array).
-- A user who genuinely doesn't want one_way alerts can still
-- remove it from their profile.

-- 1) Update the column default for future inserts.
ALTER TABLE user_preferences
  ALTER COLUMN flight_trip_types
  SET DEFAULT ARRAY['round_trip', 'one_way']::text[];

-- 2) Backfill existing users: add 'one_way' to any pref row whose
--    flight_trip_types doesn't already contain it. NULL or empty
--    arrays get reset to the new default.
UPDATE user_preferences
SET flight_trip_types = ARRAY['round_trip', 'one_way']::text[]
WHERE flight_trip_types IS NULL
   OR cardinality(flight_trip_types) = 0;

UPDATE user_preferences
SET flight_trip_types = array_append(flight_trip_types, 'one_way')
WHERE flight_trip_types IS NOT NULL
  AND NOT ('one_way' = ANY(flight_trip_types));
