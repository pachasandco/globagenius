-- 056_purge_raw_flights_batch_rpc.sql
--
-- The nightly raw_flights purge (job_expire_stale_data) has been
-- silently dead for ~8 days: it deleted one full DAY per DELETE
-- statement, and at ~240k rows/day a single PostgREST DELETE blows the
-- 8s statement timeout. The exception was caught and logged as
-- "non-fatal", so the table silently grew to 40 days of history
-- (found by the 2026-06-12 full-app audit) — the exact growth pattern
-- that caused the one-way pipeline timeouts of early June.
--
-- This RPC deletes a bounded batch server-side and returns the count,
-- so the Python loop can call it repeatedly with minimal payload and
-- each call stays far below the timeout (5k-row indexed delete).

CREATE OR REPLACE FUNCTION purge_raw_flights_batch(
    cutoff timestamptz,
    batch_size int DEFAULT 5000
)
RETURNS int
LANGUAGE plpgsql
AS $$
DECLARE
    n int;
BEGIN
    DELETE FROM raw_flights
    WHERE id IN (
        SELECT id FROM raw_flights
        WHERE scraped_at < cutoff
        ORDER BY scraped_at
        LIMIT batch_size
    );
    GET DIAGNOSTICS n = ROW_COUNT;
    RETURN n;
END
$$;
