from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Recorder Service Configuration."""

    # Audio Output
    AUDIO_OUTPUT_DIR: str = Field(
        default="/data/recording", description="Base directory for recordings"
    )

    # Live Stream
    LIVE_STREAM_TARGET: str = Field(
        default="silvasonic_livesound", description="Hostname for live stream target"
    )
    LIVE_STREAM_PORT: int = Field(default=1234, description="Port for live stream target")

    # Hardware Selection
    RECORDER_ID: str | None = Field(
        default=None, description="Unique ID for this recorder instance"
    )
    MOCK_HARDWARE: bool = Field(
        default=False, description="Enable mock hardware mode (no physical mic)"
    )
    AUDIO_PROFILE: str | None = Field(
        default=None, description="Force a specific microphone profile by name/slug"
    )
    STRICT_HARDWARE_MATCH: bool = Field(
        default=False, description="If True, disable generic fallback"
    )

    # Internal paths (not usually configurable via env, but good to have here)
    STATUS_DIR: str = Field(default="/mnt/data/services/silvasonic/status")
    LOG_DIR: str = Field(default="/var/log/silvasonic")


# Global settings instance
settings = Settings()
