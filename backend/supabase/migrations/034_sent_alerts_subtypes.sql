-- 034_sent_alerts_subtypes.sql
-- The original CHECK constraint (migration 005) only allowed alert_type
-- IN ('flight', 'package'). Since V5+ we send 'one_way' and
-- 'split_ticket' alerts via Telegram, but the upsert into sent_alerts
-- silently failed (Postgres 23514) so those alerts had NO inhibition
-- record, and the same combo / one-way deal was re-fired at every
-- dispatch run.
--
-- This widens the constraint to include the two missing subtypes plus
-- 'teaser_premium' (already used in some code paths).

ALTER TABLE sent_alerts
    DROP CONSTRAINT IF EXISTS sent_alerts_alert_type_check;

ALTER TABLE sent_alerts
    ADD CONSTRAINT sent_alerts_alert_type_check
    CHECK (alert_type IN ('flight', 'package', 'one_way', 'split_ticket', 'teaser_premium'));
