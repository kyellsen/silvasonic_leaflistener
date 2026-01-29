-- 1. Recordings (Central Index)
CREATE TABLE IF NOT EXISTS recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    time TIMESTAMPTZ NOT NULL,
    path_high TEXT NOT NULL,
    path_low TEXT,
    device_id TEXT NOT NULL,
    uploaded BOOLEAN DEFAULT FALSE,
    analyzed_bird BOOLEAN DEFAULT FALSE,
    analyzed_bat BOOLEAN DEFAULT FALSE
);

-- Convert to Hypertable (Partition by time)
SELECT create_hypertable('recordings', 'time', if_not_exists => TRUE);


-- 2. Detections (Analysis Results)
CREATE TABLE IF NOT EXISTS detections (
    time TIMESTAMPTZ NOT NULL,
    recording_id UUID NOT NULL,
    species TEXT NOT NULL,
    confidence FLOAT NOT NULL,
    algorithm TEXT NOT NULL, -- e.g. 'birdnet'
    CONSTRAINT fk_recording FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE
);

-- Convert to Hypertable
SELECT create_hypertable('detections', 'time', if_not_exists => TRUE);
-- Create index for faster querying by species/confidence
CREATE INDEX IF NOT EXISTS idx_detections_species ON detections (species, time DESC);


-- 3. Weather Measurements
CREATE SCHEMA IF NOT EXISTS weather;

CREATE TABLE IF NOT EXISTS weather.measurements (
    timestamp TIMESTAMPTZ NOT NULL,
    station_id TEXT NOT NULL,
    temperature_c FLOAT,
    humidity_percent FLOAT,
    precipitation_mm FLOAT,
    wind_speed_ms FLOAT,
    wind_gust_ms FLOAT,
    sunshine_seconds FLOAT,
    cloud_cover_percent FLOAT,
    condition_code TEXT,
    CONSTRAINT pk_weather_measurements PRIMARY KEY (timestamp, station_id)
);

-- Convert to Hypertable
SELECT create_hypertable('weather.measurements', 'timestamp', if_not_exists => TRUE);


-- 4. Service State (Configuration)
-- Not a hypertable, standard relational table for preferences
CREATE TABLE IF NOT EXISTS service_state (
    service_name TEXT PRIMARY KEY,
    enabled BOOLEAN DEFAULT TRUE,
    params JSONB DEFAULT '{}'::jsonb
);


-- 5. Devices (Inventory)
-- Not a hypertable
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    name TEXT,
    hardware_profile TEXT,
    last_seen TIMESTAMPTZ DEFAULT NOW()
);
