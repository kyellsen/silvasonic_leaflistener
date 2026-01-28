import logging
import os
import time
from datetime import UTC, datetime

from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, SQLModel, create_engine, select

from silvasonic_birdnet.models import BirdDetection, ProcessedFile, Watchlist

# Setup logging
logger = logging.getLogger("Database")


class DatabaseHandler:
    def __init__(self) -> None:
        self.user = os.getenv("POSTGRES_USER", "silvasonic")
        self.password = os.getenv("POSTGRES_PASSWORD", "silvasonic")
        self.db_name = os.getenv("POSTGRES_DB", "silvasonic")
        self.host = os.getenv("POSTGRES_HOST", "db")
        self.port = os.getenv("POSTGRES_PORT", "5432")

        self.db_url = (
            f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}"
        )
        self.engine: Engine | None = None

    def connect(self) -> bool:
        """Establish database connection."""
        retries = 10
        while retries > 0:
            try:
                logger.info(f"Connecting to Database {self.host}...")
                self.engine = create_engine(self.db_url, pool_pre_ping=True)

                # Check connection and initialize
                with self.engine.connect() as connection:
                    from sqlalchemy import text

                    connection.execute(text("CREATE SCHEMA IF NOT EXISTS birdnet"))
                    connection.commit()

                # Create Tables
                SQLModel.metadata.create_all(self.engine)

                logger.info("Database connected and initialized.")
                return True

            except OperationalError as e:
                retries -= 1
                logger.warning(f"Database not ready ({e}). Retrying in 5s... ({retries} left)")
                time.sleep(5)
            except Exception as e:
                logger.error(f"Critical DB connection error: {e}")
                return False

        return False

    def save_detection(self, detection: BirdDetection) -> None:
        """Save a single detection to the database."""
        if not self.engine:
            logger.error("DB Engine not initialized.")
            return

        with Session(self.engine) as session:
            try:
                # detection is already a SQLModel instance
                # Ensure timestamp is set if missing (though default factory handles it)
                if not detection.timestamp:
                    detection.timestamp = datetime.now(UTC)

                session.add(detection)
                session.commit()
            except Exception as e:
                logger.error(f"Failed to save detection: {e}")

    def get_watchlist(self) -> list[Watchlist]:
        """Returns all enabled watchlist items."""
        if not self.engine:
            return []

        with Session(self.engine) as session:
            try:
                statement = select(Watchlist).where(Watchlist.enabled == 1)
                results = session.exec(statement).all()
                return list(results)
            except Exception as e:
                logger.error(f"Failed to get watchlist: {e}")
                return []

    def update_watchlist(
        self, scientific_name: str, common_name: str, enabled: bool = True
    ) -> bool:
        """Add/Update a species in the watchlist."""
        if not self.engine:
            return False

        with Session(self.engine) as session:
            try:
                statement = select(Watchlist).where(Watchlist.scientific_name == scientific_name)
                item = session.exec(statement).first()

                if item:
                    item.enabled = 1 if enabled else 0
                    item.common_name = common_name
                    session.add(item)
                else:
                    item = Watchlist(
                        scientific_name=scientific_name,
                        common_name=common_name,
                        enabled=1 if enabled else 0,
                    )
                    session.add(item)

                session.commit()
                return True
            except Exception as e:
                logger.error(f"Failed to update watchlist: {e}")
                return False

    def is_watched(self, scientific_name: str) -> bool:
        """Check if a species is in the watchlist and enabled."""
        if not self.engine:
            return False

        with Session(self.engine) as session:
            try:
                statement = select(Watchlist).where(
                    Watchlist.scientific_name == scientific_name, Watchlist.enabled == 1
                )
                result = session.exec(statement).first()
                return result is not None
            except Exception as e:
                logger.error(f"Failed to check watchlist: {e}")
                return False

    def log_processed_file(
        self, filename: str, duration: float, processing_time: float, file_size: int = 0
    ) -> None:
        """Log that a file was processed (regardless of detections)."""
        if not self.engine:
            return

        with Session(self.engine) as session:
            try:
                entry = ProcessedFile(
                    filename=filename,
                    audio_duration_sec=duration,
                    processing_time_sec=processing_time,
                    file_size_bytes=file_size,
                    processed_at=datetime.now(UTC),
                )
                session.add(entry)
                session.commit()
            except Exception as e:
                logger.error(f"Failed to log processed file: {e}")


# Singleton
db = DatabaseHandler()
