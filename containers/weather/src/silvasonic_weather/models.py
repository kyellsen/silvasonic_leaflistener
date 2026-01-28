from datetime import datetime

from pydantic import BaseModel, Field


class WeatherMeasurement(BaseModel):
    """
    Strict model for weather measurements to be stored in DB.
    Ensures data consistency before insertion.
    """

    timestamp: datetime
    station_id: str
    temperature_c: float | None = None
    humidity_percent: float | None = Field(None, ge=0, le=100)
    precipitation_mm: float | None = Field(None, ge=0)
    wind_speed_ms: float | None = Field(None, ge=0)
    wind_gust_ms: float | None = Field(None, ge=0)
    sunshine_seconds: float | None = Field(None, ge=0)
    cloud_cover_percent: float | None = Field(None, ge=0, le=100)
    condition_code: str | None = None
