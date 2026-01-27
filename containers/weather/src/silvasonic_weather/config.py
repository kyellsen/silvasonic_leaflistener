import os

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration using Pydantic Settings.
    Reads from environment variables and optional JSON config file.
    """

    # Application Config
    log_level: str = "INFO"
    log_file: str = "/var/log/silvasonic/weather.log"
    status_file: str = "/mnt/data/services/silvasonic/status/weather.json"

    # Location defaults (Berlin)
    default_latitude: float = Field(default=52.52, ge=-90, le=90)
    default_longitude: float = Field(default=13.40, ge=-180, le=180)
    config_path: str = "/config/settings.json"

    # Database Config
    postgres_user: str = "silvasonic"
    postgres_password: str = "silvasonic"
    postgres_db: str = "silvasonic"
    postgres_host: str = "db"
    postgres_port: int = 5432

    @computed_field
    def database_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def get_location(self) -> tuple[float, float]:
        """
        Get location from JSON file if available, otherwise return defaults.
        Simple logic kept here to avoid over-engineering with multiple sources for now.
        """
        try:
            import json

            if os.path.exists(self.config_path):
                with open(self.config_path) as f:
                    data = json.load(f)
                    loc = data.get("location", {})
                    # Basic type check through float conversion, Pydantic model for JSON could be added if stricter validation needed
                    lat = float(loc.get("latitude", self.default_latitude))
                    lon = float(loc.get("longitude", self.default_longitude))
                    return lat, lon
        except Exception:
            pass  # Fallback to defaults on any error

        return self.default_latitude, self.default_longitude


# Global settings instance
settings = Settings()
