-- Drop the unused click-tracking columns on sent_alerts.
--
-- Migration 013 originally added `clicked_at` + `click_count` to
-- sent_alerts, intending each alert row to be its own click counter.
-- That design got superseded by the alert_redirect_tokens table (also
-- introduced in migration 013), where each Telegram CTA is a unique
-- token, and click counts live on the token row.
--
-- Result: sent_alerts.click_count has been a hardcoded 0 since launch
-- and sent_alerts.clicked_at has always been NULL. They were a trap —
-- I read them when computing CTR earlier today and concluded "0 click
-- on 3,005 alerts", panicking unnecessarily about engagement. Real CTR
-- (read from alert_redirect_tokens) is 0.95% (17 / 1,794).
--
-- No application code writes either column; no application code reads
-- either column for sent_alerts (verified via grep on 2026-05-04).
-- Safe to drop.

alter table sent_alerts
  drop column if exists click_count,
  drop column if exists clicked_at;
