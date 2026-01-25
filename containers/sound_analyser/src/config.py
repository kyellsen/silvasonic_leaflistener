import os
from pathlib import Path

class Config:
    # Input/Monitoring
    INPUT_DIR = Path(os.getenv("INPUT_DIR", "/data/recording"))
    RECURSIVE_WATCH = os.getenv("RECURSIVE_WATCH", "true").lower() == "true"
    
    # Storage
    _pg_user = os.getenv("POSTGRES_USER", "silvasonic")
    _pg_pass = os.getenv("POSTGRES_PASSWORD", "silvasonic")
    _pg_host = os.getenv("POSTGRES_HOST", "db")
    _pg_db = os.getenv("POSTGRES_DB", "silvasonic")
    
    # Default to Postgres if host is 'db' (from compose)
    if _pg_host:
        DB_PATH = None
        DB_URL = f"postgresql://{_pg_user}:{_pg_pass}@{_pg_host}:5432/{_pg_db}"
    else:
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
        if cls.DB_PATH:
            Path(cls.DB_PATH).parent.mkdir(parents=True, exist_ok=True)

config = Config()
