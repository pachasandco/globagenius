-- Add blocked_destinations to user_preferences.
-- Users can mute specific destinations to stop receiving alerts for them.
ALTER TABLE user_preferences
  ADD COLUMN IF NOT EXISTS blocked_destinations TEXT[] NOT NULL DEFAULT '{}';
