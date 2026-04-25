-- Migration 016: replace flight_range + min_discount slider with deal_tier filter
-- 'regular'     = bons deals -30% à -50% (default)
-- 'exceptional' = promos flash & erreurs de prix -50% et plus

ALTER TABLE user_preferences
    ADD COLUMN IF NOT EXISTS deal_tier varchar(20) NOT NULL DEFAULT 'regular'
    CHECK (deal_tier IN ('regular', 'exceptional'));
