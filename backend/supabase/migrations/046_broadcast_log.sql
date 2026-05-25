-- 046_broadcast_log.sql
--
-- Traceability for admin Telegram broadcasts (the "message to all beta
-- users" feature). Every send — test or real — records who/what/when
-- and the delivery counts, so an accidental or abusive broadcast is
-- auditable after the fact.

CREATE TABLE IF NOT EXISTS broadcast_log (
    id          uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    message     text NOT NULL,
    kind        varchar NOT NULL DEFAULT 'broadcast',  -- 'test' | 'broadcast'
    recipients  int NOT NULL DEFAULT 0,                -- targeted count
    delivered   int NOT NULL DEFAULT 0,                -- succeeded
    failed      int NOT NULL DEFAULT 0,                -- failed sends
    sent_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_broadcast_log_sent_at
    ON broadcast_log (sent_at DESC);
