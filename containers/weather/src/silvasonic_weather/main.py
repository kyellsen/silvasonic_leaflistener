import json
import logging
import os
import sys
import time
import typing
from datetime import UTC, datetime

import httpx
import schedule
import structlog
from sqlalchemy import create_engine, text

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

# Global Error State
_last_error: str | None = None
_last_error_time: float | None = None


# Database
engine = create_engine(settings.database_url)


def get_db_connection() -> typing.Any:
    """Get a new database connection."""
    return engine.connect()


def fetch_weather() -> None:
    """Fetch weather data from OpenMeteo and store it."""
    logger.info("Fetching weather data from OpenMeteo...")
    lat, lon = settings.get_location()

    try:
        # OpenMeteo API
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ",".join(
                [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "precipitation",
                    "rain",
                    "showers",
                    "snowfall",
                    "cloud_cover",
                    "wind_speed_10m",
                    "wind_gusts_10m",
                    "weather_code",
                    "sunshine_duration",
                ]
            ),
            "wind_speed_unit": "ms",
            "timeformat": "iso8601",
            "timezone": "UTC",
        }

        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        current = data.get("current", {})

        if not current:
            logger.warning("No current weather data received.")
            return

        # Map OpenMeteo data to our model
        # OpenMeteo provides ISO timestamp in "time" field
        ts_str = current.get("time")
        # Ensure UTC timezone awareness if not present
        timestamp = datetime.fromisoformat(ts_str)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)

        # Create station ID from location to track source
        station_id = f"OpenMeteo-{lat:.2f}-{lon:.2f}"

        measurement = WeatherMeasurement(
            timestamp=timestamp,
            station_id=station_id,
            temperature_c=current.get("temperature_2m"),
            humidity_percent=current.get("relative_humidity_2m"),
            precipitation_mm=current.get("precipitation"),
            wind_speed_ms=current.get("wind_speed_10m"),
            wind_gust_ms=current.get("wind_gusts_10m"),
            sunshine_seconds=current.get("sunshine_duration"),
            cloud_cover_percent=current.get("cloud_cover"),
            condition_code=str(current.get("weather_code", "")),
        )

        # Insert into DB
        with get_db_connection() as conn:
            stmt = text(
                """
                INSERT INTO measurements (
                    timestamp, station_id, temperature_c, humidity_percent,
                    precipitation_mm, wind_speed_ms, wind_gust_ms, sunshine_seconds, cloud_cover_percent
                ) VALUES (
                    :timestamp, :station_id, :temperature_c, :humidity_percent,
                    :precipitation_mm, :wind_speed_ms, :wind_gust_ms, :sunshine_seconds, :cloud_cover_percent
                ) ON CONFLICT (timestamp, station_id) DO NOTHING
            """
            )
            conn.execute(stmt, measurement.model_dump())
            conn.commit()

        logger.info(f"Stored weather data for {timestamp} (Station {station_id})")
        write_status("Idle (Waiting for next schedule)")

    except Exception as e:
        logger.exception(f"Fetch failed: {e}")
        write_status("Error: Fetch Failed", error=e)


def write_status(
    status_msg: str, station: str | None = None, error: Exception | str | None = None
) -> None:
    """Write the current status to Redis."""
    try:
        import psutil
        import redis

        global _last_error, _last_error_time

        if error:
            _last_error = str(error)
            _last_error_time = time.time()

        # Connect to Redis (creates new connection each time, which is fine for infrequent updates,
        # or we could use a global if frequency is high. For weather (every 20m), this is fine)
        # Actually, let's use a simple direct connection with timeout
        r = redis.Redis(host="silvasonic_redis", port=6379, db=0, socket_connect_timeout=1)

        data = {
            "service": "weather",
            "timestamp": time.time(),
            "status": status_msg,
            "last_error": _last_error,
            "last_error_time": _last_error_time,
            "cpu_percent": psutil.cpu_percent(),
            "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
            "meta": {"station_id": station, "provider": "OpenMeteo"},
            "pid": os.getpid(),
        }

        # 10 minute TTL because weather updates are slow?
        # No, the loop calls this potentially on error or startup.
        # Ideally we want it to persist "Idle" for the 20min sleep.
        # But if the container dies, we want it gone.
        # Let's set TTL to 25 minutes (1500s) since update interval is 20m.
        r.setex("status:weather", 1500, json.dumps(data))

    except Exception as e:
        logger.error(f"Status write to Redis failed: {e}")


if __name__ == "__main__":
    try:
        setup_logging()
    except Exception as e:
        logger.exception(f"Startup failed: {e}")
        time.sleep(10)
        exit(1)

    # Initial fetch
    fetch_weather()

    schedule.every(20).minutes.do(fetch_weather)

    logger.info("Weather service started.")
    write_status("Starting")

    while True:
        try:
            schedule.run_pending()
            # Don't overwrite specific statuses like "Fetching..." with "Running" constantly
            # Only update heartbeat if needed, or let fetch_weather handle status
            if _last_error:
                # If we are in error state, keep it visible or clear it after some time?
                # ideally we just update timestamp
                pass
            time.sleep(1)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.exception("Weather Service Crashed:")
            write_status("Error: Crashed", error=e)
            time.sleep(60)
