import json
import logging
import os
import time
import typing
from datetime import datetime

import schedule
from sqlalchemy import create_engine, text
from wetterdienst.metadata.parameter import Parameter
from wetterdienst.provider.dwd.observation import DwdObservationRequest

# Setup Logging
def setup_logging():
    os.makedirs("/var/log/silvasonic", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("/var/log/silvasonic/weather.log")],
    )

logger = logging.getLogger("Weather")

# Configuration
CONFIG_PATH = "/config/settings.json"
DEFAULT_LAT = 52.52  # Berlin
DEFAULT_LON = 13.40

# Database
DB_USER = os.getenv("POSTGRES_USER", "silvasonic")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "silvasonic")
DB_NAME = os.getenv("POSTGRES_DB", "silvasonic")
DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DB_URL)


def get_db_connection() -> typing.Any:
    """Get a new database connection."""
    return engine.connect()


def init_db() -> None:
    """Initialize the database schema."""
    logger.info("Initializing Database...")
    with get_db_connection() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS weather;"))
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS weather.measurements (
                timestamp TIMESTAMPTZ PRIMARY KEY,
                station_id TEXT,
                temperature_c FLOAT,
                humidity_percent FLOAT,
                precipitation_mm FLOAT,
                wind_speed_ms FLOAT,
                wind_gust_ms FLOAT,
                sunshine_seconds FLOAT,
                cloud_cover_percent FLOAT,
                condition_code TEXT
            );
        """)
        )
        conn.commit()
    logger.info("Database initialized.")


def get_location() -> tuple[float, float]:
    """Read location from settings or default."""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH) as f:
                data = json.load(f)
                loc = data.get("location", {})
                lat = loc.get("latitude", DEFAULT_LAT)
                lon = loc.get("longitude", DEFAULT_LON)
                # Ensure they are floats
                return float(lat), float(lon)
    except Exception as e:
        logger.error(f"Error reading location: {e}")
    return DEFAULT_LAT, DEFAULT_LON


def find_station(lat: float, lon: float) -> str | None:
    """Find the nearest DWD station."""
    try:
        request = DwdObservationRequest(
            parameters=[Parameter.TEMPERATURE_AIR_MEAN_2M],
            resolution="reaction",  # or "hourly"
            start_date=datetime.now(),
            end_date=datetime.now(),
        )
        # Using built-in filter
        result = request.filter_by_rank(latlon=(lat, lon), rank=1)

        # Wetterdienst filter_by_rank returns a values result actually?
        # Check docs or inspect.
        # Actually filter_by_rank returns a filtered request/stations df.

        # Let's use filter_by_distance if Rank is not returning exactly what we expect immediately.
        # But filter_by_rank is good.

        df = result.df
        if not df.empty:
            station_id = df.iloc[0]["station_id"]
            logger.info(f"Found nearest station: {station_id} for {lat}, {lon}")
            return str(station_id)
    except Exception as e:
        logger.error(f"Error finding station: {e}")
    return None


def fetch_weather() -> None:
    """Fetch weather data and store it."""
    logger.info("Fetching weather data...")
    lat, lon = get_location()

    # We ideally want a 'current' reading.
    # DWD 'observation' '10_minutes' resolution is best for 'current'.
    try:
        # We need to find the station first or let Wetterdienst handle it via rank?
        # Ideally we cache the station ID, but for simplicity let's resolve it.
        # Actually, query_by_rank is nicer.

        request = DwdObservationRequest(
            parameters=[
                Parameter.TEMPERATURE_AIR_MEAN_2M,
                Parameter.HUMIDITY,
                Parameter.PRECIPITATION_HEIGHT,
                Parameter.WIND_SPEED,
                Parameter.WIND_GUST_MAX,
                Parameter.SUNSHINE_DURATION,
                Parameter.CLOUD_COVER_TOTAL,
            ],
            resolution="10_minutes",
        ).filter_by_rank(latlon=(lat, lon), rank=1)

        # Value extraction
        # values() fetches the data
        values = request.values.all().df

        # We want the LATEST value for each parameter
        # Pivot or just iterate?
        # The DF has columns: station_id, dataset, parameter, date, value, quality

        if values.empty:
            logger.warning("No data received.")
            return

        # Get the latest timestamp
        latest_ts = values["date"].max()
        current = values[values["date"] == latest_ts]

        # Map parameters to our schema
        # Parameter names in wetterdienst can be specific string keys.
        # We need to check what they are.
        # Usually: 'temperature_air_mean_200', 'humidity', etc.

        data_map = {}
        station_id = None

        for _, row in current.iterrows():
            param = row["parameter"]
            val = row["value"]
            station_id = row["station_id"]

            if param == "temperature_air_mean_2m":
                data_map["temperature_c"] = val - 273.15  # It's Kelvin usually?
                # DWD 10 min usually Celsius?
                # Checking docs: DWD observation is usually K for creating consistent units?
                # Wetterdienst tries to be SI compliant.
                # Kelvin = True is default.
                pass

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

        # Adjust units if necessary (Checking standard behavior of Wetterdienst)
        # Assuming Kelvin for Temp.
        if "temperature_c" in data_map:
            # If value is around 290, it's K. If around 20, it's C.
            # Safe check or assume K as per library default.
            if data_map["temperature_c"] > 200:
                data_map["temperature_c"] -= 273.15

        if not station_id:
            logger.warning("No station ID found in data.")
            return

        # Insert into DB
        with get_db_connection() as conn:
            stmt = text("""
                INSERT INTO weather.measurements (
                    timestamp, station_id, temperature_c, humidity_percent,
                    precipitation_mm, wind_speed_ms, wind_gust_ms, sunshine_seconds, cloud_cover_percent
                ) VALUES (
                    :ts, :sid, :temp, :hum, :precip, :wind, :gust, :sun, :cloud
                ) ON CONFLICT (timestamp) DO NOTHING
            """)
            conn.execute(
                stmt,
                {
                    "ts": latest_ts.to_pydatetime(),
                    "sid": station_id,
                    "temp": data_map.get("temperature_c"),
                    "hum": data_map.get("humidity_percent"),
                    "precip": data_map.get("precipitation_mm"),
                    "wind": data_map.get("wind_speed_ms"),
                    "gust": data_map.get("wind_gust_ms"),
                    "sun": data_map.get("sunshine_seconds"),
                    "cloud": data_map.get("cloud_cover_percent"),
                },
            )
            conn.commit()

        logger.info(f"Stored weather data for {latest_ts} (Station {station_id})")

    except Exception as e:
        logger.error(f"Fetch failed: {e}")



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
        s_file = "/mnt/data/services/silvasonic/status/weather.json"
        os.makedirs(os.path.dirname(s_file), exist_ok=True)
        tmp = f"{s_file}.tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.rename(tmp, s_file)
    except Exception as e:
        logger.error(f"Status write failed: {e}")


if __name__ == "__main__":
    try:
        setup_logging()
        init_db()
    except Exception as e:
        logger.exception(f"Startup failed: {e}")
        time.sleep(10) # Wait a bit to ensure log is written and avoid rapid restart loop
        exit(1)

    # Run once on startup
    fetch_weather()

    # Schedule every 20 minutes (DWD updates are around that)
    schedule.every(20).minutes.do(fetch_weather)

    # Analysis aggregation (every hour)
    from silvasonic_weather.analysis import init_analysis_db, run_analysis

    init_analysis_db()
    run_analysis()  # Run once on startup
    schedule.every(1).hours.do(run_analysis)

    logger.info("Weather service started.")

    # Initial Status
    write_status("Starting")

    while True:
        try:
            schedule.run_pending()
            # Update status heartbeat
            # We don't have the station ID accessible here without refactoring
            # fetch_weather to return it, but for heartbeat "Running" is enough.
            # but for heartbeat "Running" is enough.
            write_status("Running")
            time.sleep(1)
        except KeyboardInterrupt:
            break
        except Exception:
            logger.exception("Weather Service Crashed:")
            time.sleep(60)  # Prevent tight loop
