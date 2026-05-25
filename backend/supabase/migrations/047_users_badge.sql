-- 047_users_badge.sql
-- Contributor badge: highlight founding Active Beta contributors ("OG").
-- display_name = first name the founder collected manually (shown on the badge);
-- badge        = whether this user has been granted the OG badge;
-- badge_number = sequential OG number (OG #1, #2, ...), assigned in grant order.

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS display_name text,
  ADD COLUMN IF NOT EXISTS badge boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS badge_number integer;

-- One OG number per badge; null until a badge is granted.
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_badge_number
  ON users(badge_number) WHERE badge_number IS NOT NULL;
