-- Enable TimescaleDB (Required for Hypertables)
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Enable PostGIS (Optional but recommended for future geo-features)
-- CREATE EXTENSION IF NOT EXISTS postgis; 
-- Commented out PostGIS for now to keep image size/complexity lower unless strictly needed by concept.
-- Concept mentions "PostGIS (optional for maps)", so I will leave it commented or skip it to avoid bloat if not strictly required yet.
-- Re-reading concept: "Extensions: PostGIS (optional for maps), TimescaleDB."
-- I'll stick to just timescaledb for now to be lean, can uncomment later.
