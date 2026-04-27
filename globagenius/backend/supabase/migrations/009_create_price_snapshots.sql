-- Migration 009: price_snapshots table
-- Stores minute-level price observations for Tier 1 routes (Ryanair + Transavia direct).
-- Used exclusively by the velocity detector to identify mistake fares:
-- prices that drop 40%+ within 2 hours — airline pricing errors.
--
-- Retention: 24 hours only (job_expire_stale_data purges older rows).
-- Volume estimate: 60 routes × 3 prices/poll × 72 polls/day ≈ 13k rows/day max.

CREATE TABLE IF NOT EXISTS price_snapshots (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    origin          CHAR(3)     NOT NULL,
    destination     CHAR(3)     NOT NULL,
    departure_date  DATE        NOT NULL,
    return_date     DATE        NOT NULL,
    price           NUMERIC     NOT NULL,
    airline         VARCHAR(10),
    source          VARCHAR(30) NOT NULL,  -- 'ryanair_direct', 'transavia_direct'
    captured_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Primary lookup: find recent snapshots for a route + date pair
CREATE INDEX IF NOT EXISTS idx_price_snapshots_route_date
    ON price_snapshots (origin, destination, departure_date, return_date, captured_at DESC);

-- Cleanup index: purge rows older than 24h
CREATE INDEX IF NOT EXISTS idx_price_snapshots_captured_at
    ON price_snapshots (captured_at DESC);

-- RLS: service_role only (internal pipeline)
ALTER TABLE price_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "price_snapshots_service_write"
    ON price_snapshots FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

COMMENT ON TABLE price_snapshots IS
    'Minute-level price history for Tier 1 routes. Retention: 24h. '
    'Used by the velocity detector to identify mistake fares (price drop ≥40% in <2h).';
