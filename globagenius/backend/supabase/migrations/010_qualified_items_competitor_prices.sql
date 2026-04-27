-- Migration 010: Add competitor_prices column to qualified_items
--
-- Stores cross-airline price comparison context for Tier 1 flights.
-- Populated by the cross_airline_comparator when a flight is qualified.
--
-- Schema:
-- {
--   "competitor_medians": {"HV": 145.0, "U2": 132.0},  -- median price per airline (IATA)
--   "max_competitor_median": 145.0,
--   "divergence_pct": 38.6,   -- how much cheaper vs most expensive competitor
--   "signal": "notable"       -- "none" | "notable" | "strong"
-- }
--
-- Null when:
--  - No Tier 1 competitor data available for this itinerary
--  - The flight is from a Tier 2 (Travelpayouts) source
--  - Signal is "none" (current price not lower than competitors)

ALTER TABLE qualified_items
    ADD COLUMN IF NOT EXISTS competitor_prices JSONB DEFAULT NULL;

-- Index for querying items with cross-airline signals (analytics / admin dashboard)
CREATE INDEX IF NOT EXISTS idx_qualified_items_competitor_signal
    ON qualified_items ((competitor_prices->>'signal'))
    WHERE competitor_prices IS NOT NULL;

COMMENT ON COLUMN qualified_items.competitor_prices IS
    'Cross-airline comparison context from the velocity comparator. '
    'Contains competitor_medians (per airline), max_competitor_median, '
    'divergence_pct, and signal (none/notable/strong). '
    'Null for Tier 2 flights or when no competitor data is available.';
