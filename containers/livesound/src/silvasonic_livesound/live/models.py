from pydantic import BaseModel, Field


class SourceConfig(BaseModel):
    """Configuration for an audio source."""

    name: str = Field(..., description="Unique name of the source (e.g., 'front')")
    port: int = Field(..., description="UDP port to listen on")


class SourceStatus(BaseModel):
    """Real-time status of an audio source."""

    name: str
    port: int
    active: bool = Field(..., description="Whether the ingestion thread is running")
    rms_db: float = Field(default=-100.0, description="Current RMS level in dB")
    packets_received: int = Field(default=0, description="Total packets received")
