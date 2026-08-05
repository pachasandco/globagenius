-- 064_end_premium_trials.sql
-- Premium Découverte is closed. Existing trial accounts become Freemium.
-- OG badges and active Stripe subscriptions are intentionally preserved.

-- Revoke every active automatic trial grant owned by a non-OG account.
UPDATE premium_grants AS pg
SET
  revoked = true,
  revoked_at = now()
FROM users AS u
WHERE pg.user_id = u.id
  AND COALESCE(u.badge, false) = false
  AND pg.granted_by = 'auto_premium_trial'
  AND pg.revoked = false;

-- Keep the legacy users.tier column aligned when it contains a trial-only value.
UPDATE users
SET tier = 'free'
WHERE COALESCE(badge, false) = false
  AND tier = 'premium_trial';

-- Apply the effective Freemium preferences to former trial users that do not
-- currently hold an active Stripe subscription.
UPDATE user_preferences AS up
SET
  airport_codes = ARRAY[COALESCE((up.airport_codes)[1], 'CDG')]::text[],
  flight_trip_types = ARRAY['round_trip']::text[],
  include_split_tickets = false,
  updated_at = now()
WHERE (up.premium_expires_at IS NULL OR up.premium_expires_at <= now())
  AND EXISTS (
    SELECT 1
    FROM premium_grants AS pg
    JOIN users AS u ON u.id = pg.user_id
    WHERE pg.user_id = up.user_id
      AND pg.granted_by = 'auto_premium_trial'
      AND COALESCE(u.badge, false) = false
  );

-- Remove obsolete secondary Telegram origins for those Freemium accounts.
DELETE FROM telegram_subscribers AS ts
USING user_preferences AS up, premium_grants AS pg, users AS u
WHERE ts.user_id = up.user_id
  AND pg.user_id = up.user_id
  AND u.id = up.user_id
  AND pg.granted_by = 'auto_premium_trial'
  AND COALESCE(u.badge, false) = false
  AND (up.premium_expires_at IS NULL OR up.premium_expires_at <= now())
  AND ts.airport_code <> COALESCE((up.airport_codes)[1], 'CDG');
