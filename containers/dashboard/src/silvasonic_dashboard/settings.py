import json
import logging
import os
import re
import typing

from pydantic import BaseModel, Field, ValidationError, validator

logger = logging.getLogger("Dashboard.Settings")

CONFIG_PATH = "/config/settings.json"


# ... imports ...


class LocaleSettings(BaseModel):  # type: ignore[misc]
    use_german_names: bool = False


class BirdNETSettings(BaseModel):  # type: ignore[misc]
    min_confidence: float = Field(
        default=0.7, ge=0.01, le=0.99, description="Minimum confidence score (0.01-0.99)"
    )
    sensitivity: float = Field(
        default=1.0, ge=0.5, le=1.5, description="Detection sensitivity (0.5-1.5)"
    )
    overlap: float = Field(default=0.0, ge=0.0, le=2.5, description="Overlap in seconds (0.0-2.5)")


class HealthCheckerSettings(BaseModel):  # type: ignore[misc]
    recipient_email: str | None = Field(default="")  # Empty allowed, falls back to env
    apprise_urls: list[str] = Field(default_factory=list)
    service_timeouts: dict[str, int] = Field(
        default_factory=lambda: {
            "uploader": 3600,
            "recorder": 120,
            "birdnet": 300,
            "sound_analyser": 300,
            "weather": 300,
        }
    )

    @validator("recipient_email")  # type: ignore[untyped-decorator]
    def validate_email(cls, v: str | None) -> str:  # noqa: N805
        if not v:
            return ""
        # Simple regex for email validation to avoid external dependencies
        if not re.match(r"[^@]+@[^@]+\.[^@]+", v):
            raise ValueError("Invalid email address format")
        return v


class LocationSettings(BaseModel):  # type: ignore[misc]
    latitude: float = Field(default=54.17301, ge=-90, le=90)
    longitude: float = Field(default=10.49468, ge=-180, le=180)


class Settings(BaseModel):  # type: ignore[misc]
    locale: LocaleSettings = Field(default_factory=LocaleSettings)
    healthchecker: HealthCheckerSettings = Field(default_factory=HealthCheckerSettings)
    location: LocationSettings = Field(default_factory=LocationSettings)
    birdnet: BirdNETSettings = Field(default_factory=BirdNETSettings)


DEFAULT_SETTINGS = Settings().dict()


class SettingsService:
    @staticmethod
    def get_settings() -> dict[str, typing.Any]:
        """Load settings from JSON, returning dict for compatibility."""
        return SettingsService.load_model().dict()  # type: ignore[no-any-return]

    @staticmethod
    def load_model() -> Settings:
        """Load settings as Pydantic model."""
        if not os.path.exists(CONFIG_PATH):
            return Settings()

        try:
            with open(CONFIG_PATH) as f:
                data = json.load(f)
            # Use parse_obj to validate and merge with defaults
            # However, partial updates need care.
            # Pydantic replaces whole sub-models usually.
            # Best strategy: Load default, update dict, then parse.

            # Deep merge helper
            current = Settings().dict()

            def deep_update(target: dict[str, typing.Any], source: dict[str, typing.Any]) -> None:
                for k, v in source.items():
                    if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                        deep_update(target[k], v)
                    else:
                        target[k] = v

            deep_update(current, data)

            return Settings(**current)

        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            return Settings()

    @staticmethod
    def save_settings(new_settings: dict[str, typing.Any]) -> bool:
        """Save settings (dict) to JSON, with validation."""
        try:
            # Validate via model
            model = Settings(**new_settings)

            # Ensure directory exists
            if not os.path.exists(os.path.dirname(CONFIG_PATH)):
                try:
                    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
                except OSError:
                    pass

            with open(CONFIG_PATH, "w") as f:
                json.dump(model.dict(), f, indent=4)
            return True
        except ValidationError as e:
            logger.error(f"Validation Error saving settings: {e}")
            raise e  # Propagate to controller for UI feedback
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False

    @staticmethod
    def is_german_names_enabled() -> bool:
        return SettingsService.load_model().locale.use_german_names
