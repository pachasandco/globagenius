-- 051_raw_flights_samples_by_route_rpc.sql
--
-- The baseline maturity report (app/analysis/baseline_maturity.py)
-- needs the per-(origin, destination) row count over the last N days
-- of raw_flights to distinguish hot routes from dormant ones.
--
-- The previous Python implementation paginated ALL rows via PostgREST
-- and aggregated in memory. With raw_flights now in the 250k+ range
-- for a 7-day window the request times out (statement_timeout 8s) on
-- anything above ~3h. This RPC pushes the GROUP BY to Postgres so the
-- caller reads a few hundred aggregated rows instead of hundreds of
-- thousands of raw rows. The BRIN index from migration 049 keeps the
-- range scan cheap.

CREATE OR REPLACE FUNCTION raw_flights_samples_by_route(since_ts timestamptz)
RETURNS TABLE (origin text, destination text, n integer)
LANGUAGE sql
STABLE
AS $$
    SELECT
        rf.origin,
        rf.destination,
        COUNT(*)::int AS n
    FROM raw_flights rf
    WHERE rf.scraped_at >= since_ts
      AND rf.origin IS NOT NULL
      AND rf.destination IS NOT NULL
    GROUP BY rf.origin, rf.destination;
$$;
