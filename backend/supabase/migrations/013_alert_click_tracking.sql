-- Migration 013: click tracking on alert links
-- Adds clicked_at to sent_alerts + a redirect_tokens table for UTM tracking.
-- A redirect token is a short opaque key embedded in every Telegram booking link.
-- When the user clicks, /r/{token} records the click and redirects to the real URL.

ALTER TABLE sent_alerts
    ADD COLUMN IF NOT EXISTS clicked_at timestamptz,
    ADD COLUMN IF NOT EXISTS click_count smallint NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS alert_redirect_tokens (
    token       varchar(20)  PRIMARY KEY,
    user_id     uuid         REFERENCES users(id) ON DELETE CASCADE,
    alert_key   varchar      NOT NULL,
    destination varchar(3),
    origin      varchar(3),
    url         text         NOT NULL,
    created_at  timestamptz  NOT NULL DEFAULT now(),
    clicked_at  timestamptz,
    click_count smallint     NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_redirect_tokens_alert_key ON alert_redirect_tokens(alert_key);
CREATE INDEX IF NOT EXISTS idx_redirect_tokens_user    ON alert_redirect_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_redirect_tokens_created ON alert_redirect_tokens(created_at DESC);
