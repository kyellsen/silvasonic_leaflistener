-- Retention Policies (Janitor for Data)

-- 1. Measurements: Keep 10 year
SELECT add_retention_policy('measurements', INTERVAL '10 year', if_not_exists => TRUE);