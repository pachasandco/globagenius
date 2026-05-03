-- 031_stripe_columns.sql
-- Reconcile schema with prod: stripe_customer_id, stripe_subscription_id
-- and is_premium were added directly through the Supabase UI when the
-- Stripe integration was wired up. This migration records that schema
-- in repo so a fresh environment (staging, local, dev) matches prod.
-- Idempotent: every column is `IF NOT EXISTS` so applying on prod is a no-op.

ALTER TABLE user_preferences
    ADD COLUMN IF NOT EXISTS stripe_customer_id text,
    ADD COLUMN IF NOT EXISTS stripe_subscription_id text,
    ADD COLUMN IF NOT EXISTS is_premium boolean NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_user_prefs_stripe_customer
    ON user_preferences(stripe_customer_id)
    WHERE stripe_customer_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_prefs_stripe_subscription
    ON user_preferences(stripe_subscription_id)
    WHERE stripe_subscription_id IS NOT NULL;
