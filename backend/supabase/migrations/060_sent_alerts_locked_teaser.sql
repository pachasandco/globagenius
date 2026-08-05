-- 060_sent_alerts_locked_teaser.sql
--
-- The free-tier locked-teaser feature (2026-07-06) writes sent_alerts
-- rows with alert_type='locked_teaser' for dedup. But the CHECK
-- constraint (last set by migration 054) only allowed
--   flight, package, one_way, split_ticket, teaser_premium, stopover
-- so EVERY teaser insert was rejected (23514 check_violation). The
-- dispatcher had already sent the Telegram teaser, so with no dedup row
-- the next cycle re-sent it — a duplicate storm that forced the worker
-- to be shut down (2026-07-13).
--
-- Add 'locked_teaser'. ('teaser_premium' is kept for backward
-- compatibility even though the code uses 'locked_teaser'.)

ALTER TABLE sent_alerts
    DROP CONSTRAINT IF EXISTS sent_alerts_alert_type_check;

ALTER TABLE sent_alerts
    ADD CONSTRAINT sent_alerts_alert_type_check
    CHECK (alert_type IN (
        'flight',
        'package',
        'one_way',
        'split_ticket',
        'teaser_premium',
        'stopover',
        'locked_teaser'
    ));
