-- Add discount_pct and price columns to sent_alerts so we can implement
-- two new dispatch-time guards without an additional join:
--
--   1. Levier 1 — same-destination dedup with significant-drop override:
--      we re-alert a destination already pushed within 7 days only when
--      the new price is < 70% of the previously alerted price. To check
--      that, we need to know the previous price.
--
--   2. Levier 2 — daily 3-alert cap with "+10 points" exception:
--      a 4th alert in the last 24h is allowed only if its discount is at
--      least 10 percentage points above the *minimum* discount of the
--      previously sent alerts in that window. To compute that minimum, we
--      need discount_pct on each row.
--
-- Both columns are nullable so existing rows (no historical data) don't
-- break — the dispatch-time guards treat NULL as "unknown, skip the
-- guard" and fall back to the legacy behaviour for those rows.

alter table sent_alerts
  add column if not exists discount_pct numeric,
  add column if not exists price numeric;

create index if not exists idx_sent_alerts_user_dest_created
  on sent_alerts (user_id, destination, created_at desc);

create index if not exists idx_sent_alerts_user_created
  on sent_alerts (user_id, created_at desc);
