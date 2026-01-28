from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Silvasonic Livesound Configuration.
    Reads from environment variables and optional .env file.
    """

    # Service Configuration
    HOST: str = Field("0.0.0.0", description="Host to bind the service to")
    PORT: int = Field(8000, description="Port to bind the service to")

    # Audio Processing Configuration
    SAMPLE_RATE: int = Field(48000, description="Audio sample rate in Hz")
    CHANNELS: int = Field(1, description="Number of audio channels")
    CHUNK_SIZE: int = Field(4096, description="Processing chunk size (samples)")
    FFT_WINDOW: int = Field(2048, description="FFT Window size")
    HOP_LENGTH: int = Field(512, description="FFT Hop length")

    # Port Configuration
    LISTEN_PORTS: dict[str, int] = Field(
        default_factory=lambda: {"default": 1234},
        description="Mapping of source names to UDP ports",
    )

    # Paths
    LOG_DIR: str = Field("/var/log/silvasonic", description="Directory for log files")
    STATUS_FILE: str = Field(
        "/mnt/data/services/silvasonic/status/livesound.json", description="Path to status file"
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    @field_validator("LISTEN_PORTS", mode="before")
    def parse_listen_ports(cls, v: Any) -> dict[str, int]:
        if isinstance(v, dict):
            return v

        if not v or not isinstance(v, str):
            return {"default": 1234}

        ports = {}
        try:
            # Format: "front:1234,back:1235"
            for part in v.split(","):
                if ":" in part:
                    name, port = part.split(":")
                    ports[name.strip()] = int(port.strip())
        except ValueError:
            # Fallback to default if parsing fails, similar to original logic
            return {"default": 1234}

        if not ports:
            return {"default": 1234}

        return ports


settings = Settings()
