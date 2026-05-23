-- 045_monitored_tp_routes_rpc.sql
--
-- /api/admin/routes used to scan raw_flights row-by-row over the
-- PostgREST REST interface to build the list of monitored Tier-2
-- (Travelpayouts) routes. With ~100k rows/day the unbounded scan
-- blew past the 8s statement timeout and returned 500 — which the
-- admin dashboard surfaced as a CORS error (Railway's edge 500 page
-- has no Access-Control-Allow-Origin header).
--
-- This RPC does the DISTINCT aggregation inside Postgres in a single
-- indexed query (idx_raw_flights_route_date already covers
-- (origin, destination) and there's an index on scraped_at), so the
-- endpoint returns in well under a second regardless of table size.
--
-- A route is "passive" only when EVERY row we have for it in the
-- window is flagged passive (bool_and). Mixed rows fall back to
-- active, matching the previous Python logic.

CREATE OR REPLACE FUNCTION monitored_tp_routes(since_ts timestamptz)
RETURNS TABLE (origin text, destination text, passive boolean)
LANGUAGE sql
STABLE
AS $$
    SELECT
        rf.origin,
        rf.destination,
        bool_and(COALESCE(rf.passive, false)) AS passive
    FROM raw_flights rf
    WHERE rf.scraped_at >= since_ts
      AND rf.origin IS NOT NULL
      AND rf.destination IS NOT NULL
    GROUP BY rf.origin, rf.destination;
$$;
