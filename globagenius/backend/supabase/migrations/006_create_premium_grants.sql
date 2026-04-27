-- Manual premium grants by admin (not tied to Stripe).
-- _get_user_tier checks this table first, then falls back to stripe_customer_id.
-- Execute manually in Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS premium_grants (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    granted_by varchar NOT NULL,
    granted_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz,
    reason varchar,
    revoked boolean NOT NULL DEFAULT false,
    revoked_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_premium_grants_user ON premium_grants(user_id);
CREATE INDEX IF NOT EXISTS idx_premium_grants_active
  ON premium_grants(user_id)
  WHERE revoked = false;
