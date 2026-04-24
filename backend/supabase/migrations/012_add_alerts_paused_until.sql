-- Migration 012: per-user alert pause
-- Allows users to temporarily silence alerts via the Telegram inline button.
-- NULL means alerts are active; a future timestamp means alerts are muted until that time.

ALTER TABLE user_preferences
    ADD COLUMN IF NOT EXISTS alerts_paused_until timestamptz;
