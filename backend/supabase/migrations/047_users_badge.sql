-- 047_users_badge.sql
-- Contributor badge: highlight founding Active Beta contributors.
-- display_name = first name the founder collected manually (shown on the badge);
-- badge        = whether this user has been granted the "Membre fondateur" badge.

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS display_name text,
  ADD COLUMN IF NOT EXISTS badge boolean NOT NULL DEFAULT false;
