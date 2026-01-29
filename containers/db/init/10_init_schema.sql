-- 1. Recordings (Central Index)
CREATE TABLE IF NOT EXISTS recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    time TIMESTAMPTZ NOT NULL,
    path_high TEXT NOT NULL,
    path_low TEXT,
    device_id TEXT NOT NULL,
    uploaded BOOLEAN DEFAULT FALSE,
    analyzed_bird BOOLEAN DEFAULT FALSE,
    analyzed_bat BOOLEAN DEFAULT FALSE,
    -- Add explicit updated_at for sync logic if needed, but not strictly required by v2 concept yet
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to Hypertable (Partition by time)
SELECT create_hypertable('recordings', 'time', if_not_exists => TRUE);


-- 2. Detections (Analysis Results)
-- Consolidated table for BirdNET, BatDetect, etc.
CREATE TABLE IF NOT EXISTS detections (
    id SERIAL PRIMARY KEY, -- Integer ID for simpler Python model compatibility (optional, but good for admin)
    time TIMESTAMPTZ NOT NULL,
    
    -- Link to recording (Nullable to support file-based workflows where DB ID isn't known yet)
    recording_id UUID REFERENCES recordings(id) ON DELETE CASCADE,
    
    -- File Identify (Alternative to FK)
    filename TEXT,
    filepath TEXT,
    
    -- Classification Attributes
    scientific_name TEXT,
    common_name TEXT,
    species TEXT, -- Simplified/Legacy code support
    confidence FLOAT NOT NULL,
    
    -- Temporal within file
    start_time FLOAT,
    end_time FLOAT,
    
    -- Metadata
    algorithm TEXT NOT NULL, -- 'birdnet', 'batdetect'
    model_version TEXT,
    
    -- Media
    clip_path TEXT,
    
    -- Flex-Field for Algorithm specifics (e.g. Bat frequency, calls count)
    details JSONB
);

-- Convert to Hypertable
SELECT create_hypertable('detections', 'time', if_not_exists => TRUE);

-- Indexes for Dashboard Performance
CREATE INDEX IF NOT EXISTS idx_detections_species ON detections (scientific_name, time DESC);
CREATE INDEX IF NOT EXISTS idx_detections_confidence ON detections (confidence);
CREATE INDEX IF NOT EXISTS idx_detections_filename ON detections (filename);


-- 3. Measurements (Weather)
-- Moved to PUBLIC schema (was weather.measurements)
CREATE TABLE IF NOT EXISTS measurements (
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
    CONSTRAINT pk_measurements PRIMARY KEY (timestamp, station_id)
);

-- Convert to Hypertable
SELECT create_hypertable('measurements', 'timestamp', if_not_exists => TRUE);


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

-- 6. BirdNET specific tables (moved to Public for simplicity)
-- These are relational lookups, not time-series
CREATE TABLE IF NOT EXISTS species_info (
    scientific_name TEXT PRIMARY KEY,
    common_name TEXT,
    german_name TEXT,
    family TEXT,
    image_url TEXT,
    image_author TEXT,
    image_license TEXT,
    description TEXT,
    wikipedia_url TEXT,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS watchlist (
    id SERIAL PRIMARY KEY,
    scientific_name TEXT UNIQUE NOT NULL,
    common_name TEXT,
    enabled INTEGER DEFAULT 1,
    min_confidence FLOAT DEFAULT 0.0,
    last_notification TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS processed_files (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    processing_time_sec FLOAT,
    audio_duration_sec FLOAT,
    file_size_bytes BIGINT
);

-- 7. Uploads (History)
CREATE TABLE IF NOT EXISTS uploads (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    remote_path TEXT,
    size_bytes BIGINT,
    status TEXT NOT NULL, -- 'success', 'failed'
    error_message TEXT,
    upload_time TIMESTAMPTZ DEFAULT NOW()
);
SELECT create_hypertable('uploads', 'upload_time', if_not_exists => TRUE);

-- Add uploaded_at to recordings if not exists (alter table is idempotent-ish if checked)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='recordings' AND column_name='uploaded_at') THEN
        ALTER TABLE recordings ADD COLUMN uploaded_at TIMESTAMPTZ;
    END IF;
END $$;
