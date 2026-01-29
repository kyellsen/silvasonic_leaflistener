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
        """Connect to the database and create tables."""
        try:
            self.engine = create_engine(self.db_url, pool_pre_ping=True)

            # Create schema and table
            with self.engine.begin():
                pass

            # Only create session maker if connection and init was successful
            self.Session = sessionmaker(bind=self.engine)
            logger.info("Database initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to connect/init database: {e}")
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

    def log_upload(
        self,
        filename: str,
        remote_path: str,
        status: str,
        size_bytes: int = 0,
        error_message: str | None = None,
        session: typing.Any | None = None,
    ) -> None:
        """Log an upload event.

        Args:
            filename: Name of the file.
            remote_path: Path on remote.
            status: Upload status.
            size_bytes: Size in bytes.
            error_message: Optional error message.
            session: Optional existing session to reuse. If None, a new one is created.
        """
        if session:
            # reuse existing session, do not commit/close here
            self._execute_log_upload(
                session, filename, remote_path, status, size_bytes, error_message
            )
        else:
            # ephemeral session
            if not self.Session:
                if not self.connect():
                    return

            if not self.Session:
                return

            local_sess = self.Session()
            try:
                self._execute_log_upload(
                    local_sess, filename, remote_path, status, size_bytes, error_message
                )
                local_sess.commit()
            except Exception as e:
                logger.error(f"Failed to log upload: {e}")
                local_sess.rollback()
            finally:
                local_sess.close()

    def _execute_log_upload(
        self,
        session: typing.Any,
        filename: str,
        remote_path: str,
        status: str,
        size_bytes: int,
        error_message: str | None,
    ) -> None:
        """Internal helper to execute the insert statement."""
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

    def get_uploaded_filenames(self, filenames: list[str]) -> set[str]:
        """Check which of the provided filenames have been successfully uploaded.

        Returns a set of filenames that are marked as 'success' in the database.
        DEPRECATED: Use get_all_uploaded_set() for bulk operations to avoid large IN clauses.
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

    def get_all_uploaded_set(self) -> set[str]:
        """Retrieve ALL filenames that have been successfully uploaded.

        Returns a set of filenames (strings).
        This is used for Inverted-Set-Pattern (Client-Side Diff) to avoid sending
        massive file lists to the DB.
        """
        if not self.Session:
            if not self.connect():
                return set()

        assert self.Session is not None
        session = self.Session()
        uploaded_set = set()

        try:
            # Fetch only filename column, where status is success
            # Use stream_results=True or yield_per if supported/needed,
            # but for <1M rows, standard fetchall is usually faster than overhead.
            # We select ONLY the filename to minimize bandwidth.
            query = text("SELECT filename FROM uploader.uploads WHERE status = 'success'")
            result = session.execute(query)

            # Consume result directly into set
            # result.scalars() yields the first column
            uploaded_set = set(result.scalars().all())
            return uploaded_set

        except Exception as e:
            logger.error(f"Failed to fetch all uploaded filenames: {e}")
        finally:
            session.close()

    def get_pending_recordings(self, limit: int = 10) -> list[dict]:
        """Fetch recordings that have not been uploaded."""
        if not self.Session and not self.connect():
            return []

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
