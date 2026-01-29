-- Retention Policies (Janitor for Data)

-- 1. Measurements: Keep 1 year
SELECT add_retention_policy('measurements', INTERVAL '1 year', if_not_exists => TRUE);

-- 2. Detections: Keep 1 year (or match recordings strategy)
-- Concept says: "For measurements and detections (pure data), we use TimescaleDB native policies"
-- Concept example only explicitly listed measurements, but detections usually follow similar logic or stay as long as the recording exists.
-- However, detections are derived data. If we keep recordings, we might want to keep detections.
-- Concept: "For recordings, we rely on the Janitor (due to file dependency)."
-- I will add a 1 year policy for detections too, to prevent infinite growth of metadata if recordings are deleted by janitor but not cascaded (though FK ON DELETE CASCADE handles that).
-- Actually, since detections has a FK to recordings with ON DELETE CASCADE, when the Processor/Janitor deletes a recording row, the detections are deleted.
-- But if we want to enforce a hard limit for "orphaned" or just old data regardless:
SELECT add_retention_policy('detections', INTERVAL '1 year', if_not_exists => TRUE);
