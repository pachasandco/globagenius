-- Migration 011: destination wishlists
-- Allows users to define price targets for specific routes.
-- e.g. "Alert me when CDG→BKK drops below 500€ in July"

CREATE TABLE IF NOT EXISTS destination_wishlists (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    origin      char(3) NOT NULL,          -- IATA airport code, e.g. 'CDG'
    destination char(3) NOT NULL,          -- IATA airport code, e.g. 'BKK'
    max_price   integer,                   -- NULL = any price qualifies
    month       smallint CHECK (month BETWEEN 1 AND 12),  -- NULL = any month
    label       varchar(80),               -- optional user-facing label, e.g. "Tokyo été"
    active      boolean NOT NULL DEFAULT true,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Each user can have at most one wishlist entry per (origin, destination, month).
-- month NULL is treated as a separate wildcard entry.
CREATE UNIQUE INDEX destination_wishlists_unique_idx
    ON destination_wishlists (user_id, origin, destination, COALESCE(month, 0));

CREATE INDEX destination_wishlists_user_idx  ON destination_wishlists (user_id);
CREATE INDEX destination_wishlists_route_idx ON destination_wishlists (origin, destination);

-- auto-update updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER destination_wishlists_updated_at
    BEFORE UPDATE ON destination_wishlists
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
