-- Migration 015: per-user flight range filter
-- 'all'          = court-courrier + long-courrier (défaut)
-- 'short_medium' = court et moyen-courrier uniquement
-- 'long_haul'    = long-courrier uniquement

ALTER TABLE user_preferences
    ADD COLUMN IF NOT EXISTS flight_range varchar(20) NOT NULL DEFAULT 'all'
    CHECK (flight_range IN ('all', 'short_medium', 'long_haul'));
