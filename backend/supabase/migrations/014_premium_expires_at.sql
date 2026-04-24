-- Migration 014: explicit premium expiry date on user_preferences
-- Replaces the implicit "has stripe_subscription_id = premium" logic.
-- Populated by the Stripe webhook on checkout.session.completed and
-- kept fresh by the daily job_sync_stripe_subscriptions scheduler job.
-- NULL = never set (free). A past timestamp = expired (free).

ALTER TABLE user_preferences
    ADD COLUMN IF NOT EXISTS premium_expires_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_user_prefs_premium_expires
    ON user_preferences(premium_expires_at)
    WHERE premium_expires_at IS NOT NULL;
