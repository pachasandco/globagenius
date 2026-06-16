-- 057_purge_raw_flights_faster.sql
--
-- 056's purge_raw_flights_batch worked at batch_size=100 but TIMED OUT
-- at 5000 (the size the nightly job actually calls) — found 2026-06-16
-- when the purge alert fired again. Root cause: the inner
-- `SELECT id ... WHERE scraped_at < cutoff ORDER BY scraped_at LIMIT N`
-- forces Postgres to sort a large slice of the table before deleting,
-- and that sort blows the 8s statement_timeout once the table is back
-- near ~1M rows. The ORDER BY served no purpose — for a purge, the
-- delete ORDER is irrelevant; we only need "any N rows older than the
-- cutoff". Dropping it lets the planner use the scraped_at index for a
-- cheap bounded scan with no sort.

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
        LIMIT batch_size           -- no ORDER BY: purge order is irrelevant
    );
    GET DIAGNOSTICS n = ROW_COUNT;
    RETURN n;
END
$$;
