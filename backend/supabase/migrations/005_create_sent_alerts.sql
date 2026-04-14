-- Track sent Telegram alerts for deal-level deduplication.
-- alert_key = sha256(user_id|origin|destination|departure|return|round(price))[:32]
-- One row per (user_id, alert_key), unique constraint enforced.
-- Execute manually in Supabase SQL Editor before deploying.

CREATE TABLE IF NOT EXISTS sent_alerts (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid REFERENCES users(id) ON DELETE CASCADE,
    chat_id bigint NOT NULL,
    alert_key varchar NOT NULL,
    destination varchar(3),
    alert_type varchar(20) NOT NULL CHECK (alert_type IN ('flight', 'package')),
    sent_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_sent_alerts_user_key ON sent_alerts(user_id, alert_key);
CREATE INDEX IF NOT EXISTS idx_sent_alerts_chat ON sent_alerts(chat_id);
CREATE INDEX IF NOT EXISTS idx_sent_alerts_sent_at ON sent_alerts(sent_at DESC);
