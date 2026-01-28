import socket
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Silvasonic Livesound Configuration.
    Reads from environment variables and optional .env file.
    """

    # Service Configuration
    HOST: str = Field(default="0.0.0.0", description="Host to bind the service to")
    PORT: int = Field(default=8000, description="Port to bind the service to")

    # Audio Processing Configuration
    SAMPLE_RATE: int = Field(default=48000, description="Audio sample rate in Hz")
    CHANNELS: int = Field(default=1, description="Number of audio channels")
    CHUNK_SIZE: int = Field(default=4096, description="Processing chunk size (samples)")
    FFT_WINDOW: int = Field(default=2048, description="FFT Window size")
    HOP_LENGTH: int = Field(default=512, description="FFT Hop length")

    # Port Configuration
    LISTEN_PORTS: dict[str, int] = Field(
        default_factory=lambda: {"default": 8010},
        description="Mapping of source names to UDP ports",
    )

    # Instance Identity
    INSTANCE_ID: str = Field(default_factory=socket.gethostname, description="Unique Instance ID")

    # Paths
    LOG_DIR: str = Field(default="/var/log/silvasonic", description="Directory for log files")
    STATUS_FILE: str = Field(
        default="",  # Calculated in validator if empty
        description="Path to status file",
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    @field_validator("LISTEN_PORTS", mode="before")
    def parse_listen_ports(cls, v: Any) -> dict[str, int]:
        if isinstance(v, dict):
            return v

        if not v or not isinstance(v, str):
            return {"default": 8010}

        ports = {}
        try:
            # Format: "front:1234,back:1235"
            for part in v.split(","):
                if ":" in part:
                    name, port = part.split(":")
                    ports[name.strip()] = int(port.strip())
        except ValueError:
            # Fallback to default if parsing fails, similar to original logic
            return {"default": 8010}

        if not ports:
            return {"default": 8010}

        return ports

    @field_validator("STATUS_FILE", mode="after")
    def set_status_file(cls, v: str, info: Any) -> str:
        if v:
            return v
        # Construct default using INSTANCE_ID
        # Note: In Pydantic V2 'info.data' holds previously validated fields
        instance_id = info.data.get("INSTANCE_ID", "default")
        return f"/mnt/data/services/silvasonic/status/livesound_{instance_id}.json"


settings = Settings()
