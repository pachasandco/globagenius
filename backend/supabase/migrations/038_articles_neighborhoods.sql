-- Migration 038: replace itinerary (3-day program) with neighborhoods.
--
-- The product moved from "guide with prescribed 3-day stay" to a city
-- presentation (assets, character, neighborhoods) — GG users don't
-- reliably stay 3 days, so the itinerary block was misleading.
--
-- Strategy:
--   1. Add `neighborhoods` jsonb. Default '[]' so old code paths that
--      read .neighborhoods don't break.
--   2. Leave `itinerary` in place for now — the on-demand regeneration
--      hook in destination_articles.py will null it out on the next
--      visit to articles that still carry the legacy 3-day block.
--      We don't drop the column to keep older API consumers (admin,
--      analytics) reading the legacy field until regen catches up.

ALTER TABLE articles
  ADD COLUMN IF NOT EXISTS neighborhoods jsonb DEFAULT '[]'::jsonb;
