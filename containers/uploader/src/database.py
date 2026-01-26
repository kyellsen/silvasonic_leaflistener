import logging
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

class DatabaseHandler:
    def __init__(self):
        self.user = os.getenv("POSTGRES_USER", "silvasonic")
        self.password = os.getenv("POSTGRES_PASSWORD", "silvasonic")
        self.db_name = os.getenv("POSTGRES_DB", "silvasonic")
        self.host = os.getenv("POSTGRES_HOST", "db")
        self.port = os.getenv("POSTGRES_PORT", "5432")

        self.db_url = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}"
        self.engine = None
        self.Session = None

    def connect(self):
        """Connect to the database and create tables."""
        try:
            self.engine = create_engine(self.db_url, pool_pre_ping=True)

            # Create schema and table
            with self.engine.begin() as conn:
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS carrier;"))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS carrier.uploads (
                        id SERIAL PRIMARY KEY,
                        filename TEXT NOT NULL,
                        remote_path TEXT NOT NULL,
                        status TEXT NOT NULL,
                        size_bytes BIGINT,
                        duration_sec FLOAT,
                        upload_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        error_message TEXT
                    );
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_uploads_time ON carrier.uploads(upload_time DESC);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_uploads_status ON carrier.uploads(status);"))

            # Only create session maker if connection and init was successful
            self.Session = sessionmaker(bind=self.engine)
            logger.info("Database initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to connect/init database: {e}")
            self.Session = None
            return False

    def log_upload(self, filename: str, remote_path: str, status: str, size_bytes: int = 0, error_message: str = None):
        """Log an upload event."""
        if not self.Session:
            if not self.connect():
                return

        session = self.Session()
        try:
            query = text("""
                INSERT INTO carrier.uploads (filename, remote_path, status, size_bytes, error_message)
                VALUES (:filename, :remote_path, :status, :size_bytes, :error_message)
            """)
            session.execute(query, {
                "filename": filename,
                "remote_path": remote_path,
                "status": status,
                "size_bytes": size_bytes,
                "error_message": error_message
            })
            session.commit()
        except Exception as e:
            logger.error(f"Failed to log upload: {e}")
            session.rollback()
        finally:
            session.close()
