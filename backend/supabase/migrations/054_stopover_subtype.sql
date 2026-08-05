-- Migration 054: stopover phase 1 (2026-06-09, hardened 2026-06-10)
--
-- A stopover chain is 3 one-way tickets (origin → hub → final
-- destination → origin) qualified against the direct round-trip
-- baseline.
--
-- HARDENED 2026-06-10: production reported `column "deal_subtype" does
-- not exist` — migration 023_deal_subtype.sql was never applied there
-- (duplicate "023_" numbering collides with 023_rag_chunks_hash_column;
-- one of the two silently never ran). This script is therefore
-- self-contained: it (re)creates the 023 columns/index when missing,
-- then installs the widened CHECK constraints. Safe to re-run.

-- 1. qualified_items: ensure the 023 columns exist.
ALTER TABLE qualified_items
    ADD COLUMN IF NOT EXISTS deal_subtype varchar(20) NOT NULL DEFAULT 'roundtrip',
    ADD COLUMN IF NOT EXISTS metadata jsonb DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_qualified_items_deal_subtype
    ON qualified_items(deal_subtype);

-- 2. qualified_items.deal_subtype gains 'stopover'.
ALTER TABLE qualified_items
    DROP CONSTRAINT IF EXISTS qualified_items_deal_subtype_check;

ALTER TABLE qualified_items
    ADD CONSTRAINT qualified_items_deal_subtype_check
    CHECK (deal_subtype IN ('roundtrip', 'oneway_exceptional', 'split_ticket', 'stopover'));

-- 3. sent_alerts.alert_type gains 'stopover' (column exists since 005;
--    the constraint list was last widened in 034).
ALTER TABLE sent_alerts
    DROP CONSTRAINT IF EXISTS sent_alerts_alert_type_check;

ALTER TABLE sent_alerts
    ADD CONSTRAINT sent_alerts_alert_type_check
    CHECK (alert_type IN ('flight', 'package', 'one_way', 'split_ticket', 'teaser_premium', 'stopover'));
