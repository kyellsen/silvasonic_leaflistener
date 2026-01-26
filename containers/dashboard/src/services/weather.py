import datetime
import json
import os
import time

from sqlalchemy import text

from .common import STATUS_DIR, logger
from .database import db


class WeatherService:
    @staticmethod
    async def get_current_weather():
        """Get the latest weather measurement."""
        try:
            async with db.get_connection() as conn:
                query = text("""
                    SELECT * FROM weather.measurements 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """)
                row = (await conn.execute(query)).fetchone()
                if row:
                    d = dict(row._mapping)
                    if d.get("timestamp") and d["timestamp"].tzinfo is None:
                        d["timestamp"] = d["timestamp"].replace(tzinfo=datetime.UTC)
                    return d
        except Exception as e:
            logger.error(f"Weather DB Error: {e}", exc_info=True)
        return None

    @staticmethod
    async def get_history(hours=24):
        """Get weather history for charts."""
        try:
            async with db.get_connection() as conn:
                # Bind param properly or safe f-string for int
                query = text(
                    f"SELECT * FROM weather.measurements WHERE timestamp >= NOW() - INTERVAL '{int(hours)} HOURS' ORDER BY timestamp ASC"
                )

                result = await conn.execute(query)
                data = {"labels": [], "temp": [], "humidity": [], "rain": [], "wind": []}

                for row in result:
                    d = dict(row._mapping)
                    ts = d["timestamp"]
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=datetime.UTC)

                    data["labels"].append(ts.strftime("%H:%M"))
                    data["temp"].append(d.get("temperature_c"))
                    data["humidity"].append(d.get("humidity_percent"))
                    data["rain"].append(d.get("precipitation_mm"))
                    data["wind"].append(d.get("wind_speed_ms"))

                return data
        except Exception as e:
            logger.error(f"Weather History Error: {e}", exc_info=True)
            return {"labels": [], "temp": [], "humidity": [], "rain": [], "wind": []}

    @staticmethod
    async def get_correlations(days=30):
        """Get correlation stats for charts (Hourly buckets)."""
        try:
            async with db.get_connection() as conn:
                # Fetch aggregated stats from weather.bird_stats
                # We order by timestamp ASC for the time series
                query = text(f"""
                    SELECT * 
                    FROM weather.bird_stats 
                    WHERE timestamp >= NOW() - INTERVAL '{int(days)} DAYS'
                    ORDER BY timestamp ASC
                """)

                result = await conn.execute(query)

                data = {
                    "labels": [],
                    "scatter_temp": [],  # {x: temp, y: count}
                    "scatter_rain": [],
                    "scatter_wind": [],
                    "series_temp": [],
                    "series_count": [],
                    "series_rain": [],
                }

                for row in result:
                    d = dict(row._mapping)
                    ts = d["timestamp"]
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=datetime.UTC)

                    label = ts.strftime("%d.%m %H:00")
                    count = d.get("detection_count", 0)
                    temp = d.get("temperature_c", 0)
                    rain = d.get("precipitation_mm", 0)
                    wind = d.get("wind_speed_ms", 0)

                    data["labels"].append(label)

                    # Series (for Overlay Chart)
                    data["series_temp"].append(temp)
                    data["series_count"].append(count)
                    data["series_rain"].append(rain)

                    # Scatter (Correlation)
                    # ChartJS scatter format: {x: val, y: val}
                    data["scatter_temp"].append({"x": temp, "y": count})
                    data["scatter_wind"].append({"x": wind, "y": count})
                    if rain > 0:
                        data["scatter_rain"].append({"x": rain, "y": count})

                return data
        except Exception as e:
            logger.error(f"Weather Correlation Error: {e}", exc_info=True)
            return {
                "labels": [],
                "scatter_temp": [],
                "scatter_rain": [],
                "series_temp": [],
                "series_count": [],
                "series_rain": [],
            }

    @staticmethod
    def get_status():
        """Get service status from JSON file."""
        try:
            status_file = os.path.join(STATUS_DIR, "weather.json")
            if os.path.exists(status_file):
                with open(status_file) as f:
                    data = json.load(f)
                    # Check staleness (20 mins schedule, so maybe 25 min stale check)
                    if time.time() - data.get("timestamp", 0) > 1500:
                        data["status"] = "Stalen"
                    return data
        except Exception as e:
            logger.error(f"Weather Status Error: {e}", exc_info=True)
        return {"status": "Unknown"}
