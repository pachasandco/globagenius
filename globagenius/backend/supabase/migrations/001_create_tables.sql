-- backend/supabase/migrations/001_create_tables.sql
-- Run this in Supabase SQL Editor

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE raw_flights (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    hash varchar UNIQUE NOT NULL,
    origin varchar(3) NOT NULL,
    destination varchar(3) NOT NULL,
    departure_date date NOT NULL,
    return_date date NOT NULL,
    price decimal NOT NULL,
    airline varchar,
    stops int DEFAULT 0,
    source_url text,
    source varchar NOT NULL,
    scraped_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL
);

CREATE INDEX idx_flights_origin ON raw_flights(origin);
CREATE INDEX idx_flights_destination ON raw_flights(destination);
CREATE INDEX idx_flights_dates ON raw_flights(departure_date, return_date);
CREATE INDEX idx_flights_expires ON raw_flights(expires_at);
CREATE INDEX idx_flights_scraped ON raw_flights(scraped_at);

CREATE TABLE raw_accommodations (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    hash varchar UNIQUE NOT NULL,
    city varchar NOT NULL,
    name varchar NOT NULL,
    price_per_night decimal NOT NULL,
    total_price decimal NOT NULL,
    rating decimal,
    check_in date NOT NULL,
    check_out date NOT NULL,
    source_url text,
    source varchar NOT NULL,
    scraped_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL
);

CREATE INDEX idx_accommodations_city ON raw_accommodations(city);
CREATE INDEX idx_accommodations_dates ON raw_accommodations(check_in, check_out);
CREATE INDEX idx_accommodations_expires ON raw_accommodations(expires_at);
CREATE INDEX idx_accommodations_rating ON raw_accommodations(rating);

CREATE TABLE price_baselines (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    route_key varchar UNIQUE NOT NULL,
    type varchar NOT NULL CHECK (type IN ('flight', 'accommodation')),
    avg_price decimal NOT NULL,
    std_dev decimal NOT NULL,
    sample_count int NOT NULL,
    calculated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE packages (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    flight_id uuid REFERENCES raw_flights(id),
    origin varchar(3) NOT NULL,
    destination varchar(3) NOT NULL,
    departure_date date NOT NULL,
    return_date date NOT NULL,
    flight_price decimal NOT NULL,
    accommodation_id uuid REFERENCES raw_accommodations(id),
    accommodation_price decimal NOT NULL,
    total_price decimal NOT NULL,
    baseline_total decimal NOT NULL,
    discount_pct decimal NOT NULL,
    score int NOT NULL,
    status varchar NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired')),
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL
);

CREATE INDEX idx_packages_status ON packages(status);
CREATE INDEX idx_packages_score ON packages(score DESC);
CREATE INDEX idx_packages_expires ON packages(expires_at);

CREATE TABLE qualified_items (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    type varchar NOT NULL CHECK (type IN ('flight', 'accommodation')),
    item_id uuid NOT NULL,
    price decimal NOT NULL,
    baseline_price decimal NOT NULL,
    discount_pct decimal NOT NULL,
    score int NOT NULL,
    status varchar NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_qualified_status ON qualified_items(status);
CREATE INDEX idx_qualified_type ON qualified_items(type);

CREATE TABLE scrape_logs (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_id varchar,
    source varchar NOT NULL,
    type varchar NOT NULL CHECK (type IN ('flights', 'accommodations')),
    items_count int DEFAULT 0,
    errors_count int DEFAULT 0,
    duration_ms int,
    status varchar NOT NULL CHECK (status IN ('success', 'partial', 'failed')),
    started_at timestamptz NOT NULL,
    completed_at timestamptz
);

CREATE INDEX idx_scrape_logs_type ON scrape_logs(type);
CREATE INDEX idx_scrape_logs_started ON scrape_logs(started_at DESC);

CREATE TABLE telegram_subscribers (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    chat_id bigint UNIQUE NOT NULL,
    airport_code varchar(3) NOT NULL,
    min_score int NOT NULL DEFAULT 50,
    created_at timestamptz NOT NULL DEFAULT now()
);
