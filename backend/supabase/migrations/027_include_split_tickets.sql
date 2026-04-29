-- V5+: opt-in for split-ticket (2x one-way) combo alerts.
-- Sub-option of 'round_trip' — combos are A/R-equivalent but require 2 separate
-- bookings, so we ask explicit user consent before sending.
-- Default false: existing users keep round-trip-only behaviour, no surprise alert.

ALTER TABLE user_preferences
  ADD COLUMN IF NOT EXISTS include_split_tickets boolean NOT NULL DEFAULT false;
