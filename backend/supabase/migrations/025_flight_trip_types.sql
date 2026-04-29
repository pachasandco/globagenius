-- V5: user preference for flight trip types (round-trip vs one-way).
-- Existing users keep round-trip-only behaviour; one-way is opt-in via profile.

ALTER TABLE user_preferences
  ADD COLUMN IF NOT EXISTS flight_trip_types text[] NOT NULL
    DEFAULT ARRAY['round_trip']::text[];
