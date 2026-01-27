import logging
import os
import typing

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class DatabaseHandler:
    """Handles database connections and operations for the uploader."""

    def __init__(self) -> None:
        """Initialize the DatabaseHandler."""
        self.user = os.getenv("POSTGRES_USER", "silvasonic")
        self.password = os.getenv("POSTGRES_PASSWORD", "silvasonic")
        self.db_name = os.getenv("POSTGRES_DB", "silvasonic")
        self.host = os.getenv("POSTGRES_HOST", "db")
        self.port = os.getenv("POSTGRES_PORT", "5432")

        self.db_url = (
            f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}"
        )
        self.engine: typing.Any | None = None
        self.Session: sessionmaker[typing.Any] | None = None

    def connect(self) -> bool:
        """Connect to the database and create tables."""
        try:
            self.engine = create_engine(self.db_url, pool_pre_ping=True)

            # Create schema and table
            with self.engine.begin() as conn:
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS uploader;"))
                conn.execute(
                    text(
                        """
                    CREATE TABLE IF NOT EXISTS uploader.uploads (
                        id SERIAL PRIMARY KEY,
                        filename TEXT NOT NULL,
                        remote_path TEXT NOT NULL,
                        status TEXT NOT NULL,
                        size_bytes BIGINT,
                        duration_sec FLOAT,
                        upload_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        error_message TEXT
                    );
                """
                    )
                )
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_uploads_time ON "
                        "uploader.uploads(upload_time DESC);"
                    )
                )
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_uploads_status ON uploader.uploads(status);"
                    )
                )

            # Only create session maker if connection and init was successful
            self.Session = sessionmaker(bind=self.engine)
            logger.info("Database initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to connect/init database: {e}")
            self.Session = None
            return False

    def log_upload(
        self,
        filename: str,
        remote_path: str,
        status: str,
        size_bytes: int = 0,
        error_message: str | None = None,
    ) -> None:
        """Log an upload event."""
        if not self.Session:
            if not self.connect():
                return

        if not self.Session:
            return

        session = self.Session()
        try:
            query = text(
                """
                INSERT INTO uploader.uploads
                (filename, remote_path, status, size_bytes, error_message)
                VALUES (:filename, :remote_path, :status, :size_bytes, :error_message)
            """
            )
            session.execute(
                query,
                {
                    "filename": filename,
                    "remote_path": remote_path,
                    "status": status,
                    "size_bytes": size_bytes,
                    "error_message": error_message,
                },
            )
            session.commit()
        except Exception as e:
            logger.error(f"Failed to log upload: {e}")
            session.rollback()
        finally:
            session.close()

    def get_uploaded_filenames(self, filenames: list[str]) -> set[str]:
        """Check which of the provided filenames have been successfully uploaded.

        Returns a set of filenames that are marked as 'success' in the database.
        """
        if not filenames or not self.Session:
            if not self.Session and not self.connect():
                return set()
            if not filenames:
                return set()

        assert self.Session is not None

        session = self.Session()
        uploaded = set()
        chunk_size = 1000

        try:
            # Process in chunks to avoid parameter limits
            for i in range(0, len(filenames), chunk_size):
                chunk = filenames[i : i + chunk_size]
                if not chunk:
                    continue

                query = text(
                    """
                    SELECT filename FROM uploader.uploads
                    WHERE status = 'success'
                    AND filename IN :filenames
                """
                )

                result = session.execute(query, {"filenames": tuple(chunk)})
                for row in result:
                    uploaded.add(row[0])

        except Exception as e:
            logger.error(f"Failed to check uploaded status: {e}")
        finally:
            session.close()

        return uploaded
