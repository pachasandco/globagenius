-- 032_articles_iata_destination.sql
-- V9 destination pages: index articles by IATA code (BCN, BKK, ...)
-- to match sent_alerts.destination, raw_flights.destination, etc.
-- The legacy `destination` column (FR name like "Marrakech") stays for
-- the 4 pre-existing articles. New articles MUST set both `iata` and
-- `destination`.
--
-- Also extends the schema with the journalist-style guide fields
-- (h1, meta_description, lead, nut_graf, top_picks, itinerary,
-- infos_pratiques, faq, sources, word_count) and Unsplash attribution
-- columns (photographer_name, photographer_url, photo_id). The legacy
-- columns (intro, sections, subtitle, best_time, budget_tip) are kept
-- so the 4 existing articles still render via /api/articles.

ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS iata text,
    ADD COLUMN IF NOT EXISTS word_count int,
    ADD COLUMN IF NOT EXISTS h1 text,
    ADD COLUMN IF NOT EXISTS meta_description text,
    ADD COLUMN IF NOT EXISTS lead text,
    ADD COLUMN IF NOT EXISTS nut_graf text,
    ADD COLUMN IF NOT EXISTS top_picks jsonb,
    ADD COLUMN IF NOT EXISTS itinerary jsonb,
    ADD COLUMN IF NOT EXISTS infos_pratiques jsonb,
    ADD COLUMN IF NOT EXISTS faq jsonb,
    ADD COLUMN IF NOT EXISTS sources jsonb,
    ADD COLUMN IF NOT EXISTS photographer_name text,
    ADD COLUMN IF NOT EXISTS photographer_url text,
    ADD COLUMN IF NOT EXISTS photo_id text;

CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_iata_unique
    ON articles(iata)
    WHERE iata IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_articles_iata
    ON articles(iata)
    WHERE iata IS NOT NULL;
