import json
import logging
import os
import sys
import time
import typing

import schedule
import structlog
from sqlalchemy import create_engine, text
from wetterdienst.provider.dwd.observation import DwdObservationRequest

from silvasonic_weather.config import settings
from silvasonic_weather.models import WeatherMeasurement


# Setup Logging
def setup_logging() -> None:
    os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)

    # Structlog Setup
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Handlers & Formatters
    pre_chain: list[typing.Any] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
    ]
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=pre_chain,
    )

    handlers: list[logging.Handler] = []

    # Stdout
    s = logging.StreamHandler(sys.stdout)
    s.setFormatter(formatter)
    handlers.append(s)

    # File
    try:
        f = logging.FileHandler(settings.log_file)
        f.setFormatter(formatter)
        handlers.append(f)
    except Exception:
        pass

    logging.basicConfig(level=settings.log_level, handlers=handlers, force=True)


logger = structlog.get_logger("Weather")

# Database
engine = create_engine(settings.database_url)


def get_db_connection() -> typing.Any:
    """Get a new database connection."""
    return engine.connect()


def fetch_weather() -> None:
    """Fetch weather data and store it."""
    logger.info("Fetching weather data...")
    lat, lon = settings.get_location()

    try:
        # Common DWD parameters
        request = DwdObservationRequest(
            parameters=[
                "temperature_air_mean_2m",
                "humidity",
                "precipitation_height",
                "wind_speed",
                "wind_gust_max",
                "sunshine_duration",
                "cloud_cover_total",
            ],
            resolution="10_minutes",
        ).filter_by_rank(latlon=(lat, lon), rank=1)

        values = request.values.all().df

        if values.empty:
            logger.warning("No data received.")
            return

        # Get the latest timestamp
        latest_ts = values["date"].max()
        current = values[values["date"] == latest_ts]

        # Map parameters to our schema
        data_map = {}
        station_id = None

        for _, row in current.iterrows():
            param = row["parameter"]
            val = row["value"]
            station_id = str(row["station_id"])

            if param == "temperature_air_mean_2m":
                data_map["temperature_c"] = val - 273.15  # Convert Kelvin to Celsius
            elif param == "humidity":
                data_map["humidity_percent"] = val
            elif param == "precipitation_height":
                data_map["precipitation_mm"] = val
            elif param == "wind_speed":
                data_map["wind_speed_ms"] = val
            elif param == "wind_gust_max":
                data_map["wind_gust_ms"] = val
            elif param == "sunshine_duration":
                data_map["sunshine_seconds"] = val
            elif param == "cloud_cover_total":
                data_map["cloud_cover_percent"] = val

        # Ensure we have a station_id
        if not station_id:
            logger.warning("No station ID found in data.")
            return

        # Create and validate model
        measurement = WeatherMeasurement(
            timestamp=latest_ts.to_pydatetime(), station_id=station_id, **data_map
        )

        # Unit adjustment check (optional, but kept for logic parity)
        if measurement.temperature_c and measurement.temperature_c > 200:
            measurement.temperature_c -= 273.15

        # Insert into DB
        with get_db_connection() as conn:
            stmt = text(
                """
                INSERT INTO weather.measurements (
                    timestamp, station_id, temperature_c, humidity_percent,
                    precipitation_mm, wind_speed_ms, wind_gust_ms, sunshine_seconds, cloud_cover_percent
                ) VALUES (
                    :timestamp, :station_id, :temperature_c, :humidity_percent,
                    :precipitation_mm, :wind_speed_ms, :wind_gust_ms, :sunshine_seconds, :cloud_cover_percent
                ) ON CONFLICT (timestamp) DO NOTHING
            """
            )
            # Dump model to dict, excluding None/unset if needed, but here we want all fields
            conn.execute(stmt, measurement.model_dump())
            conn.commit()

        logger.info(f"Stored weather data for {latest_ts} (Station {station_id})")

    except Exception as e:
        logger.exception(f"Fetch failed: {e}")


def write_status(status_msg: str, station: str | None = None) -> None:
    """Write the current status to a JSON file."""
    try:
        import psutil

        data = {
            "service": "weather",
            "timestamp": time.time(),
            "status": status_msg,
            "cpu_percent": psutil.cpu_percent(),
            "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
            "meta": {"station_id": station},
            "pid": os.getpid(),
        }
        s_file = settings.status_file
        os.makedirs(os.path.dirname(s_file), exist_ok=True)
        tmp = f"{s_file}.tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.rename(tmp, s_file)
    except Exception as e:
        logger.error(f"Status write failed: {e}")


def init_db() -> None:
    """Initialize the database (create views)."""
    try:
        with get_db_connection() as conn:
            try:
                # Create View for Analysis
                conn.execute(
                    text(
                        """
                CREATE OR REPLACE VIEW weather.bird_stats_view AS
                WITH w_stats AS (
                    SELECT
                        date_trunc('hour', timestamp) as bucket,
                        AVG(temperature_c) as avg_temp,
                        AVG(humidity_percent) as avg_humid,
                        AVG(precipitation_mm) as total_precip
                    FROM weather.measurements
                    GROUP BY 1
                ),
                b_stats AS (
                    SELECT
                        date_trunc('hour', timestamp) as bucket,
                        COUNT(*) as detection_count,
                        COUNT(DISTINCT scientific_name) as species_count
                    FROM birdnet.detections
                    GROUP BY 1
                )
                SELECT
                    w.bucket,
                    w.avg_temp,
                    w.avg_humid,
                    w.total_precip,
                    COALESCE(b.detection_count, 0) as detection_count,
                    COALESCE(b.species_count, 0) as species_count
                FROM w_stats w
                LEFT JOIN b_stats b ON w.bucket = b.bucket;
            """
                    )
                )
                conn.commit()
                logger.info("Database initialized (Views created).")
            except Exception:
                conn.rollback()
                raise
    except Exception as e:
        logger.error(f"Failed to initialize DB: {e}")


if __name__ == "__main__":
    try:
        setup_logging()

    except Exception as e:
        logger.exception(f"Startup failed: {e}")
        time.sleep(10)
        exit(1)

    init_db()  # Initialize View

    fetch_weather()

    schedule.every(20).minutes.do(fetch_weather)

    # Analysis is now handled via SQL View, no scheduled job needed.

    logger.info("Weather service started.")
    write_status("Starting")

    while True:
        try:
            schedule.run_pending()
            write_status("Running")
            time.sleep(1)
        except KeyboardInterrupt:
            break
        except Exception:
            logger.exception("Weather Service Crashed:")
            time.sleep(60)
