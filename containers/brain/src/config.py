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
    
    @classmethod
    def ensure_dirs(cls):
        cls.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        # DB Dir is handled by engine but parent must exist
        Path(cls.DB_PATH).parent.mkdir(parents=True, exist_ok=True)

config = Config()
