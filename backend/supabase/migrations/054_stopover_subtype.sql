-- Migration 054: stopover phase 1 (2026-06-09)
--
-- A stopover chain is 3 one-way tickets (origin → hub → final
-- destination → origin) qualified against the direct round-trip
-- baseline. Two CHECK constraints need the new value:
--   1. qualified_items.deal_subtype gains 'stopover' (migration 023
--      defined the original list).
--   2. sent_alerts.alert_type gains 'stopover' (migration 034 defined
--      the current list).

ALTER TABLE qualified_items
    DROP CONSTRAINT IF EXISTS qualified_items_deal_subtype_check;

ALTER TABLE qualified_items
    ADD CONSTRAINT qualified_items_deal_subtype_check
    CHECK (deal_subtype IN ('roundtrip', 'oneway_exceptional', 'split_ticket', 'stopover'));

ALTER TABLE sent_alerts
    DROP CONSTRAINT IF EXISTS sent_alerts_alert_type_check;

ALTER TABLE sent_alerts
    ADD CONSTRAINT sent_alerts_alert_type_check
    CHECK (alert_type IN ('flight', 'package', 'one_way', 'split_ticket', 'teaser_premium', 'stopover'));
