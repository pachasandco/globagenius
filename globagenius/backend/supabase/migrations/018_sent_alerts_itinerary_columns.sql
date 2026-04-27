-- Migration 018: add departure_date and return_date to sent_alerts
-- Allows dedup by itinerary (destination + dates) instead of hashed key,
-- making it origin-agnostic: CDG→FCO and ORY→FCO on the same dates
-- share the same dedup row regardless of which key format was used.

ALTER TABLE sent_alerts
    ADD COLUMN IF NOT EXISTS departure_date date,
    ADD COLUMN IF NOT EXISTS return_date date;

CREATE INDEX IF NOT EXISTS idx_sent_alerts_itinerary
    ON sent_alerts(user_id, destination, departure_date, return_date);
