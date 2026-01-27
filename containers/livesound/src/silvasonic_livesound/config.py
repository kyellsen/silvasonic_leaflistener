import os
from pathlib import Path


class Config:
    """Configuration for Livesound service."""

    # Input/Monitoring
    INPUT_DIR = Path(os.getenv("INPUT_DIR", "/data/recording"))
    RECURSIVE_WATCH = os.getenv("RECURSIVE_WATCH", "true").lower() == "true"

    # Storage
    # (Database configuration removed as it is unused in Livesound)

    # Processing
    ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "/data/processed/artifacts"))

    # JSON Metadata Export (Opt-Out)
    EXPORT_JSON_METADATA = os.getenv("EXPORT_JSON_METADATA", "true").lower() == "true"
    METADATA_DIR = Path(os.getenv("METADATA_DIR", "/data/processed/metadata"))

    @classmethod
    def ensure_dirs(cls) -> None:
        """Ensure necessary directories exist."""
        cls.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        if cls.EXPORT_JSON_METADATA:
            cls.METADATA_DIR.mkdir(parents=True, exist_ok=True)


config = Config()
