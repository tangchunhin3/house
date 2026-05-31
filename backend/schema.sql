CREATE TABLE IF NOT EXISTS properties (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(256) NOT NULL,
    price       INTEGER NOT NULL,
    area_sqft   DOUBLE PRECISION,
    bedrooms    INTEGER,
    floor       VARCHAR(64),
    estate_name VARCHAR(128),
    address     VARCHAR(256),
    district    VARCHAR(64) DEFAULT '屯門',
    source      VARCHAR(64) NOT NULL,
    source_url  VARCHAR(512) NOT NULL UNIQUE,
    image_url   VARCHAR(512),
    description TEXT,
    scraped_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scrape_sessions (
    id           SERIAL PRIMARY KEY,
    started_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at  TIMESTAMP,
    status       VARCHAR(32) DEFAULT 'running',
    total_found  INTEGER DEFAULT 0,
    total_new    INTEGER DEFAULT 0,
    errors       TEXT
);

CREATE INDEX IF NOT EXISTS idx_properties_source ON properties(source);
CREATE INDEX IF NOT EXISTS idx_properties_price ON properties(price);
CREATE INDEX IF NOT EXISTS idx_properties_bedrooms ON properties(bedrooms);
CREATE INDEX IF NOT EXISTS idx_properties_scraped_at ON properties(scraped_at DESC);
