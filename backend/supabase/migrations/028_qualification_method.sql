-- V5+: track HOW each qualified_item was qualified, so we can measure
-- baseline maturity and the share of fallback (discount-only) qualifications.
--
-- Values:
--   'zscore_fare_mistake' — z >= 3.5 AND discount >= 60%
--   'zscore_flash_promo'  — z >= 2.5 AND discount >= 40%
--   'zscore_good_deal'    — z >= 2.0 AND discount >= 20%
--   'fallback_discount'   — z-score path failed but raw discount >= 40% (legacy)
--   'oneway_discount'     — V5+ one-way qualified on raw median lookback (P1)
--   'velocity_drop'       — Tier 1 detected a -40%+ drop in <2h (bypass)
--   'unknown'             — pre-migration rows, before we tracked this

ALTER TABLE qualified_items
  ADD COLUMN IF NOT EXISTS qualification_method TEXT NOT NULL DEFAULT 'unknown';

CREATE INDEX IF NOT EXISTS idx_qualified_items_method
  ON qualified_items (qualification_method, created_at DESC);
