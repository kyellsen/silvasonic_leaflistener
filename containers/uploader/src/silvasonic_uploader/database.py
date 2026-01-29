import logging
import os
import typing
from contextlib import contextmanager

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
        """Connect to the database."""
        try:
            self.engine = create_engine(self.db_url, pool_pre_ping=True)

            # Verify connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            self.Session = sessionmaker(bind=self.engine)
            logger.info("Database connection established.")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            self.Session = None
            return False

    @contextmanager
    def get_session(self) -> typing.Iterator[typing.Any]:
        """Provide a transactional scope around a series of operations."""
        if not self.Session:
            if not self.connect():
                raise ConnectionError("Database not connected")

        assert self.Session is not None
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_pending_recordings(self, limit: int = 10) -> list[dict[str, typing.Any]]:
        """Fetch recordings that have not been uploaded."""
        if not self.Session and not self.connect():
            return []

        assert self.Session is not None
        session = self.Session()
        try:
            # Query recordings where uploaded IS FALSE
            query = text(
                "SELECT id, path_high, path_low FROM recordings WHERE uploaded = false AND path_high IS NOT NULL ORDER BY time ASC LIMIT :limit"
            )
            result = session.execute(query, {"limit": limit})
            return [{"id": row[0], "path_high": row[1], "path_low": row[2]} for row in result]
        except Exception as e:
            logger.error(f"Failed to fetch pending recordings: {e}")
            return []
        finally:
            session.close()

    def mark_recording_uploaded(self, rec_id: int) -> None:
        """Mark a recording as uploaded in the DB."""
        if not self.Session:
            return

        session = self.Session()
        try:
            query = text(
                "UPDATE recordings SET uploaded = true, uploaded_at = NOW() WHERE id = :id"
            )
            session.execute(query, {"id": rec_id})
            session.commit()
        except Exception as e:
            logger.error(f"Failed to mark recording {rec_id} as uploaded: {e}")
            session.rollback()
        finally:
            session.close()

    def count_pending_recordings(self) -> int:
        """Count number of pending uploads."""
        if not self.Session:
            return 0
        session = self.Session()
        try:
            query = text(
                "SELECT COUNT(*) FROM recordings WHERE uploaded = false AND path_high IS NOT NULL"
            )
            return session.execute(query).scalar() or 0
        except Exception:
            return 0
        finally:
            session.close()
