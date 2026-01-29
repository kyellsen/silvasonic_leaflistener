import logging
import os
import typing
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):  # type: ignore[misc]
    pass


class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    path_high: Mapped[str | None] = mapped_column(String, nullable=True)  # Path to 384kHz file
    path_low: Mapped[str | None] = mapped_column(String, nullable=True)  # Path to 48kHz file
    device_id: Mapped[str] = mapped_column(String, nullable=False)

    # Metadata
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    samplerate_hz: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # State flags
    uploaded: Mapped[bool] = mapped_column(Boolean, default=False)
    analyzed_bird: Mapped[bool] = mapped_column(Boolean, default=False)
    analyzed_bat: Mapped[bool] = mapped_column(Boolean, default=False)


_engine: typing.Any = None
_SessionLocal: sessionmaker | None = None


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10))
def init_db() -> None:
    global _engine, _SessionLocal

    db_url = os.getenv(
        "DB_URL", "postgresql://silvasonic:silvasonic@silvasonic_database:5432/silvasonic"
    )

    logger.info("Connecting to database...")
    _engine = create_engine(db_url, echo=False)

    # Verify connection
    try:
        with _engine.connect():
            logger.info("Database connection successful.")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise e

    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)


def get_session() -> Session:
    if _SessionLocal is None:
        init_db()
    assert _SessionLocal is not None
    return _SessionLocal()
