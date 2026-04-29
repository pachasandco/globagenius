-- V5+ P1: extend alert_redirect_tokens so we can break down click-through
-- rate by trip_type (round_trip | one_way | split_ticket) and by the
-- qualification_method that produced the alert (zscore_*, fallback_discount,
-- oneway_discount, velocity_drop, ...).
--
-- Without these we cannot tell whether one-way alerts engage the same way
-- round-trips do — exactly the question we shipped V5 to be able to answer.

ALTER TABLE alert_redirect_tokens
  ADD COLUMN IF NOT EXISTS trip_type TEXT,
  ADD COLUMN IF NOT EXISTS qualification_method TEXT;

CREATE INDEX IF NOT EXISTS idx_redirect_tokens_trip_type
  ON alert_redirect_tokens (trip_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_redirect_tokens_qualification_method
  ON alert_redirect_tokens (qualification_method, created_at DESC);
