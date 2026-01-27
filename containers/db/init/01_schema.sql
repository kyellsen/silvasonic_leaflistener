-- Initialize schema for Silvasonic Carrier (Uploader)
CREATE SCHEMA IF NOT EXISTS carrier;

CREATE TABLE IF NOT EXISTS carrier.uploads (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    remote_path TEXT NOT NULL,
    status TEXT NOT NULL,
    size_bytes BIGINT,
    duration_sec FLOAT,
    upload_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_uploads_time ON carrier.uploads(upload_time DESC);
CREATE INDEX IF NOT EXISTS idx_uploads_status ON carrier.uploads(status);
