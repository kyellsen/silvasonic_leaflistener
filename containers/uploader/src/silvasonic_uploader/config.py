import json
import logging
import os
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

CONFIG_PATH = Path("/config/uploader_config.json")


class UploaderSettings(BaseSettings):
    """Runtime configuration for the Uploader service."""

    # Nextcloud / WebDAV
    nextcloud_url: str = Field(default="", description="URL of the Nextcloud instance (WebDAV)")
    nextcloud_user: str = Field(default="", description="Username for Nextcloud")
    nextcloud_password: SecretStr = Field(
        default=SecretStr(""), description="App Password for Nextcloud"
    )

    # Sync Settings
    sync_interval: int = Field(default=10, description="Interval in seconds between sync attempts")
    cleanup_threshold: int = Field(default=70, description="Disk usage percent to trigger cleanup")
    cleanup_target: int = Field(default=60, description="Target disk usage percent after cleanup")
    min_age: str = Field(default="1m", description="Minimum age of files to upload (e.g. 1m, 1h)")
    bwlimit: str | None = Field(default=None, description="Bandwidth limit (e.g. 500k, 1M)")

    # Internal / Immutable (handled via env usually, but allow override)
    sensor_id: str = Field(
        default_factory=lambda: os.getenv("SENSOR_ID", __import__("socket").gethostname())
    )
    target_dir: str = Field(default="silvasonic")

    model_config = SettingsConfigDict(
        env_prefix="UPLOADER_",
        env_file=".env",
        extra="ignore",
        json_file_encoding="utf-8",
    )

    def save(self) -> None:
        """Persist settings to the JSON config file."""
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            # Dump to JSON, handling SecretStr
            data = self.model_dump(mode="json", exclude_none=True)

            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Configuration saved to {CONFIG_PATH}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise

    @classmethod
    def load(cls) -> "UploaderSettings":
        """Load settings from JSON file, falling back to ENV/Defaults."""
        # 1. Start with defaults/env via standard Pydantic instantiation
        base_settings = cls()

        # 2. If JSON file exists, update fields
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, encoding="utf-8") as f:
                    file_data = json.load(f)

                # Update base settings with file data
                # using model_validate to ensure types
                # We interpret file data as overrides for env vars
                updated_data = base_settings.model_dump()
                updated_data.update(file_data)

                return cls.model_validate(updated_data)
            except Exception as e:
                logger.warning(f"Failed to load config file {CONFIG_PATH}, using defaults/env: {e}")

        return base_settings
