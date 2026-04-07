-- Run this in Supabase SQL Editor

CREATE TABLE articles (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug varchar UNIQUE NOT NULL,
    destination varchar NOT NULL,
    country varchar NOT NULL,
    title varchar,
    subtitle varchar,
    intro text,
    sections jsonb,
    best_time varchar,
    budget_tip varchar,
    tags text[],
    cover_photo text,
    photo_query varchar,
    generated_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_articles_slug ON articles(slug);
CREATE INDEX idx_articles_destination ON articles(destination);
