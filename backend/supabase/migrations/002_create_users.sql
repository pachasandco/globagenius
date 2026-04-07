-- Run this in Supabase SQL Editor

CREATE TABLE users (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    email varchar UNIQUE NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE user_preferences (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    airport_codes text[] NOT NULL DEFAULT ARRAY['CDG'],
    offer_types text[] NOT NULL DEFAULT ARRAY['package', 'flight', 'accommodation'],
    min_discount int NOT NULL DEFAULT 40,
    max_budget int,
    preferred_destinations text[],
    telegram_chat_id bigint,
    telegram_connected boolean NOT NULL DEFAULT false,
    notifications_enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_user_prefs_user ON user_preferences(user_id);
CREATE INDEX idx_user_prefs_airports ON user_preferences USING GIN(airport_codes);
CREATE INDEX idx_user_prefs_telegram ON user_preferences(telegram_chat_id);

ALTER TABLE telegram_subscribers ADD COLUMN user_id uuid REFERENCES users(id);
