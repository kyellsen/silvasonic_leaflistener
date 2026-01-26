import logging
import os
import typing
from datetime import datetime, timedelta

from sqlalchemy import create_engine, text

logger = logging.getLogger("WeatherAnalysis")

# Reuse DB connection settings from main or env
DB_USER = os.getenv("POSTGRES_USER", "silvasonic")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "silvasonic")
DB_NAME = os.getenv("POSTGRES_DB", "silvasonic")
DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DB_URL)


def get_connection() -> typing.Any:
    """Get a new database connection."""
    return engine.connect()


def init_analysis_db() -> None:
    """Create the analysis table if it doesn't exist."""
    try:
        with get_connection() as conn:
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS weather.bird_stats (
                    timestamp TIMESTAMPTZ PRIMARY KEY,
                    temperature_c FLOAT,
                    precipitation_mm FLOAT,
                    wind_speed_ms FLOAT,
                    detection_count INTEGER,
                    species_count INTEGER
                );
            """)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to init analysis DB: {e}")


def run_analysis() -> None:
    """Run the aggregation logic."""
    logger.info("Running statistical analysis...")
    try:
        with get_connection() as conn:
            # 1. Determine Window to Analyze
            # We look for the last analyzed entry in bird_stats
            # Only go back max 7 days to avoid massive churn on startup if empty
            # Or just "last 24 hours" if running frequently?
            # Better: "Since last entry" or "Last 30 days" if empty.

            last_entry = conn.execute(
                text("SELECT MAX(timestamp) FROM weather.bird_stats")
            ).scalar()

            now = datetime.utcnow()
            # truncate to previous hour to be safe?
            # Actually, we want to analyze completed hours.
            # So from (last_entry + 1h) up to (now - 1h).

            if last_entry is None:
                # Start from 30 days ago
                start_time = now - timedelta(days=30)
            else:
                # Start from next hour
                start_time = last_entry + timedelta(hours=1)

            # Align to top of hour
            start_time = start_time.replace(minute=0, second=0, microsecond=0)
            end_time = now.replace(minute=0, second=0, microsecond=0)

            if start_time >= end_time:
                logger.info("Nothing new to analyze.")
                return

            logger.info(f"Analyzing from {start_time} to {end_time}")

            # 2. Iterate hours (or do a massive group by query?)
            # Group by query is more efficient.

            # Aggregate Weather (Hourly Avg/Sum)
            # Weather measurements are irregular (every 10-20 mins).
            # We group by date_trunc('hour', timestamp)

            # Query definition removed as it was unused and replaced by complex_query below
            # to handle efficient aggregation without cross-join explosion.

            # Wait, the JOIN in the original approach was a Cross Join on the hour?
            # If there are multiple weather measurements per hour (e.g. 3) and
            # multiple detections (e.g. 10), a simple join will explode rows (3 * 10 = 30 rows).
            # We need to aggregate separately and then join.

            # Correct approach: CTEs or separate subqueries.

            complex_query = text("""
                WITH w_stats AS (
                    SELECT
                        date_trunc('hour', timestamp) as ts,
                        AVG(temperature_c) as temp,
                        SUM(precipitation_mm) as rain,
                        AVG(wind_speed_ms) as wind
                    FROM weather.measurements
                    WHERE timestamp >= :start AND timestamp < :end
                    GROUP BY 1
                ),
                b_stats AS (
                    SELECT
                        date_trunc('hour', timestamp) as ts,
                        COUNT(*) as det_count,
                        COUNT(DISTINCT common_name) as sp_count
                    FROM birdnet.detections
                    WHERE timestamp >= :start AND timestamp < :end
                    GROUP BY 1
                )
                INSERT INTO weather.bird_stats (
                    timestamp, temperature_c, precipitation_mm,
                    wind_speed_ms, detection_count, species_count
                )
                SELECT
                    w_stats.ts,
                    w_stats.temp,
                    w_stats.rain,
                    w_stats.wind,
                    COALESCE(b_stats.det_count, 0),
                    COALESCE(b_stats.sp_count, 0)
                FROM w_stats
                LEFT JOIN b_stats ON w_stats.ts = b_stats.ts
                ON CONFLICT (timestamp) DO NOTHING;
            """)

            conn.execute(complex_query, {"start": start_time, "end": end_time})
            conn.commit()

            logger.info("Analysis complete.")

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
