from pydantic import BaseModel, ConfigDict, Field


class ServiceConfig(BaseModel):
    """Configuration for a monitored service."""

    name: str
    timeout: int = Field(..., description="Timeout in seconds before considering the service down")


class HealthCheckerConfig(BaseModel):
    """Configuration overrides loaded from settings.json."""

    service_timeouts: dict[str, int] = Field(default_factory=dict)
    recipient_email: str | None = None
    apprise_urls: list[str] = Field(default_factory=list)


class GlobalSettings(BaseModel):
    """Global settings structure."""

    healthchecker: HealthCheckerConfig = Field(default_factory=HealthCheckerConfig)


class BaseStatus(BaseModel):
    """Base class for status files."""

    model_config = ConfigDict(extra="ignore")  # Ignore unknown fields for forward compatibility
    timestamp: float = Field(0.0, description="Unix timestamp of the last heartbeat")


class RecorderMetaProfile(BaseModel):
    """Nested profile information in recorder status."""

    name: str | None = None


class RecorderMeta(BaseModel):
    """Metadata field in recorder status."""

    profile: RecorderMetaProfile = Field(default_factory=RecorderMetaProfile)


class RecorderStatus(BaseStatus):
    """Structure of recorder_*.json files."""

    meta: RecorderMeta = Field(default_factory=RecorderMeta)

    # We might add other fields if we need them, but for now we just need the timestamp and name
    # The 'ignore' config handles the rest of the file content.


class ServiceStatus(BaseStatus):
    """Generic status file structure for most services."""

    # Some services might have specific fields (e.g., uploader's last_upload)
    last_upload: float | None = None

    # 'postgres' logic is internal probe, not file-based status.


class ErrorDrop(BaseModel):
    """Structure of an error report in the errors/ directory."""

    service: str = "Unknown Service"
    context: str | None = None
    error: str
    timestamp: str  # Usually a string formatted date

    # Allow extra fields for full dumps
    model_config = ConfigDict(extra="allow")


class NotificationData(BaseModel):
    """Data payload for notifications."""

    common_name: str = "Unknown Bird"
    scientific_name: str = ""
    confidence: float = 0.0
    start_time: float = 0.0


class NotificationEvent(BaseModel):
    """Structure of a notification file."""

    type: str
    data: NotificationData = Field(default_factory=NotificationData)
