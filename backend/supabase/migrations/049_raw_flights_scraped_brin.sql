-- 049_raw_flights_scraped_brin.sql
--
-- /api/admin/routes (via the monitored_tp_routes RPC) times out
-- (statement_timeout 57014). The RPC does
--   WHERE scraped_at >= since_ts GROUP BY origin, destination
-- over raw_flights. The table is append-only and large (~41k rows per
-- 3h window, oldest row ~6 weeks back), so the planner falls back to a
-- sequential scan and the GROUP BY tips past the 8s statement timeout.
--
-- raw_flights is inserted in scraped_at order (append-only time series),
-- which is the ideal shape for a BRIN index: a few KB that lets the
-- planner skip the vast majority of blocks for a recent-window range
-- scan, instead of seq-scanning the whole table. The existing btree
-- idx_flights_scraped works too but BRIN is far smaller and cheaper to
-- maintain on a high-insert table, and the planner picks it for the
-- short recent window the RPC uses.
--
-- We keep the RPC unchanged; this is purely an access-path fix.

CREATE INDEX IF NOT EXISTS idx_raw_flights_scraped_brin
  ON raw_flights USING brin (scraped_at);

COMMENT ON INDEX idx_raw_flights_scraped_brin IS
  'BRIN on scraped_at: cheap recent-window range scans for monitored_tp_routes RPC (admin routes).';
