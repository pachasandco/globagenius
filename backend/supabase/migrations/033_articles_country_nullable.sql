-- 033_articles_country_nullable.sql
-- The legacy schema (migration 003) marked articles.country NOT NULL,
-- but the V9 destination guide generator does not produce a `country`
-- field — that data lives implicitly in the prompt context. Drop the
-- NOT NULL so new IATA-keyed articles can be inserted without it.
-- Existing rows already have a country value and are unaffected.

ALTER TABLE articles
    ALTER COLUMN country DROP NOT NULL;
