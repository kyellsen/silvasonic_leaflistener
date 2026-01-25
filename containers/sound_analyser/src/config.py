import os
from pathlib import Path

class Config:
    # Input/Monitoring
    INPUT_DIR = Path(os.getenv("INPUT_DIR", "/data/recording"))
    RECURSIVE_WATCH = os.getenv("RECURSIVE_WATCH", "true").lower() == "true"
    
    # Storage
    DB_PATH = os.getenv("DB_PATH", "/data/db/brain.sqlite")
    DB_URL = f"sqlite:///{DB_PATH}"
    
    # Processing
    ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "/data/processed/artifacts"))
    
    # JSON Metadata Export (Opt-Out)
    EXPORT_JSON_METADATA = os.getenv("EXPORT_JSON_METADATA", "true").lower() == "true"
    METADATA_DIR = Path(os.getenv("METADATA_DIR", "/data/processed/metadata"))
    
    @classmethod
    def ensure_dirs(cls):
        cls.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        if cls.EXPORT_JSON_METADATA:
            cls.METADATA_DIR.mkdir(parents=True, exist_ok=True)
        # DB Dir is handled by engine but parent must exist
        Path(cls.DB_PATH).parent.mkdir(parents=True, exist_ok=True)

config = Config()
