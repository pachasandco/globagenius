-- V7: password reset tokens.
-- One row per reset request. Token is the primary key (already random,
-- 32+ chars URL-safe). Single-use (used_at flips on consumption).
-- TTL is enforced at insert time via expires_at = now() + 1h; the cleanup
-- of expired-and-unused rows can run later via a scheduled job (not in V7).

CREATE TABLE IF NOT EXISTS password_reset_tokens (
  token       TEXT PRIMARY KEY,
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at  TIMESTAMPTZ NOT NULL,
  used_at     TIMESTAMPTZ,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user
  ON password_reset_tokens (user_id);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires
  ON password_reset_tokens (expires_at);
