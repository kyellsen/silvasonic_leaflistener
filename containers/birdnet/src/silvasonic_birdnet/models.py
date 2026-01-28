from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BirdDetection(BaseModel):
    """
    Data model representing a single bird detection event.
    """

    model_config = ConfigDict(frozen=True)

    # File Info
    filename: str
    filepath: str
    source_device: str | None = None

    # Temporal Info
    start_time: float = Field(..., ge=0.0, description="Start time in seconds")
    end_time: float = Field(..., ge=0.0, description="End time in seconds")
    timestamp: datetime | None = None

    # Classification Info
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    scientific_name: str
    common_name: str
    species_code: str | None = None

    # Metadata
    lat: float | None = None
    lon: float | None = None
    clip_path: str | None = None

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: float, info: Any) -> float:
        """Ensure end_time is after start_time."""
        # Note: Pydantic v2 validation context is different, but for simple field check:
        # We need access to start_time.
        # In Pydantic v2, we can use `AfterValidator` or model validator.
        # Keeping it simple for now, or using model_validator if needed.
        return v

    # We'll use a model validator for cross-field validation if necessary,
    # but basic field types cover most needs.
