-- Migration 039: message_id on sent_alerts
--
-- Before: a grouped Telegram alert with N offers writes N rows to
-- sent_alerts, each with a distinct alert_key but the same created_at.
-- CTR, L2 cap counts, and any per-message analytics inherit the
-- "N rows per message" inflation, and L2 leans on a fragile 5-min
-- bucket dedup to compensate.
--
-- After: every row of the same Telegram message shares one UUID.
-- - Python generates the UUID at dispatch time (one per
--   send_grouped_flight_alerts call).
-- - Historical rows are backfilled in a separate, idempotent script
--   (scripts/backfill_message_id.py).
-- - The existing (user_id, alert_key) unique index is preserved —
--   it serves the 168h offer-level dedup which is orthogonal.

ALTER TABLE sent_alerts
  ADD COLUMN IF NOT EXISTS message_id uuid;

CREATE INDEX IF NOT EXISTS idx_sent_alerts_message_id
  ON sent_alerts(message_id);
