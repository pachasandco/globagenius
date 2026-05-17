-- Migration 041: tier column on users — chantier 5 (2026-05-17)
--
-- Three tiers planned:
--   'free'                  — default. Cap 3 short / 0 long / day. No
--                             burst exception. Designed for the future
--                             public open after summer 2026.
--   'premium'               — paying customer (Stripe). Cap 3 short +
--                             2 long / 5 total. Burst exception 70/60%.
--                             No paid customer exists yet.
--   'premium_grandfathered' — beta founders (the first ~100 who linked
--                             Telegram). Same caps as premium, forever
--                             free. Cap on the count is 100 (operational
--                             rule, not DB-enforced).
--
-- The dispatcher reads users.tier via get_user_caps() in
-- dispatch_guards.py and applies the right caps to L2 + L3. Existing
-- behaviour (before this migration) maps onto 'premium_grandfathered'
-- for the 8 users who have linked Telegram, 'free' for everyone else.

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS tier varchar(32) NOT NULL DEFAULT 'free';

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'users_tier_check'
  ) THEN
    ALTER TABLE users
      ADD CONSTRAINT users_tier_check
      CHECK (tier IN ('free', 'premium', 'premium_grandfathered'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_users_tier ON users(tier);
