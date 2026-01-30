from datetime import UTC, datetime
from typing import Any

from pydantic import field_validator
from sqlalchemy import Text
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


class BirdDetection(SQLModel, table=True):
    """
    Data model representing a single bird detection event.
    Acts as both Pydantic model for validation and SQLAlchemy model for DB.
    """

    __tablename__ = "detections"
    __table_args__ = {"schema": "public"}

    # Enforce validation
    model_config = {"validate_assignment": True}

    # ID (Auto-increment)
    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # File Info
    filename: str = Field(max_length=255)
    filepath: str = Field(max_length=1024)
    source_device: str | None = Field(default=None, max_length=50)

    # Temporal Info
    start_time: float = Field(ge=0.0)
    end_time: float = Field(ge=0.0)

    # Classification Info
    confidence: float = Field(ge=0.0, le=1.0)
    species_code: str | None = Field(default=None, max_length=50)
    common_name: str | None = Field(default=None, max_length=255)
    scientific_name: str | None = Field(default=None, max_length=255)

    # Metadata
    latitude: float | None = Field(
        default=None, alias="lat"
    )  # Alias for Pydantic compat (lat -> latitude in DB)
    longitude: float | None = Field(default=None, alias="lon")  # Alias for Pydantic compat
    model_version: str | None = Field(default=None, max_length=50)
    clip_path: str | None = Field(default=None, max_length=1024)

    # Algorithm Flexibility
    # Algorithm Flexibility
    details: dict[str, Any] | None = Field(default=None, sa_type=JSON)

    # Additional Pydantic Validation logic if needed (e.g. for API inputs)
    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: float, info: Any) -> float:
        """Ensure end_time is positive."""
        if v < 0:
            raise ValueError("End time must be positive")
        return v

    # To support existing logic that might access .lat/.lon properties if alias doesn't auto-create them as attributes on the instance:
    @property
    def lat(self) -> float | None:
        return self.latitude

    @lat.setter
    def lat(self, value: float | None) -> None:
        self.latitude = value

    @property
    def lon(self) -> float | None:
        return self.longitude

    @lon.setter
    def lon(self, value: float | None) -> None:
        self.longitude = value


class SpeciesInfo(SQLModel, table=True):
    __tablename__ = "species_info"
    __table_args__ = {"schema": "public"}

    scientific_name: str = Field(primary_key=True, max_length=255)
    common_name: str | None = Field(default=None, max_length=255)
    german_name: str | None = Field(default=None, max_length=255)
    family: str | None = Field(default=None, max_length=255)

    image_url: str | None = Field(default=None, max_length=1024)
    image_author: str | None = Field(default=None, max_length=255)
    image_license: str | None = Field(default=None, max_length=255)

    description: str | None = Field(default=None, sa_type=Text)  # Explicit Text type
    wikipedia_url: str | None = Field(default=None, max_length=1024)

    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Watchlist(SQLModel, table=True):
    __tablename__ = "watchlist"
    __table_args__ = {"schema": "public"}

    id: int | None = Field(default=None, primary_key=True)
    scientific_name: str = Field(max_length=255, unique=True)
    common_name: str | None = Field(default=None, max_length=255)

    enabled: int = Field(default=1)  # 1=Enabled, 0=Disabled
    last_notification: datetime | None = Field(default=None)

    min_confidence: float = Field(default=0.0)


class ProcessedFile(SQLModel, table=True):
    __tablename__ = "processed_files"
    __table_args__ = {"schema": "public"}

    id: int | None = Field(default=None, primary_key=True)
    filename: str = Field(max_length=255)
    processed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    processing_time_sec: float | None = Field(default=None)
    audio_duration_sec: float | None = Field(default=None)
    file_size_bytes: int | None = Field(default=None)
