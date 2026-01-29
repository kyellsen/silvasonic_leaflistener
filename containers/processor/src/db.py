import logging
import os

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class Recording(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime(timezone=True), nullable=False, index=True)
    path_high = Column(String, nullable=True)  # Path to 384kHz file
    path_low = Column(String, nullable=True)  # Path to 48kHz file
    device_id = Column(String, nullable=False)

    # Metadata
    duration_sec = Column(Float, nullable=True)
    samplerate_hz = Column(Integer, nullable=True)

    # State flags
    uploaded = Column(Boolean, default=False)
    analyzed_bird = Column(Boolean, default=False)
    analyzed_bat = Column(Boolean, default=False)

    # TimescaleDB hypertable is typically created via SQL migration,
    # but the model definition here is needed for ORM.


_engine = None
_SessionLocal = None


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10))
def init_db():
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

    # Note: We do NOT call Base.metadata.create_all(_engine) here usually,
    # as the schema should be managed by the DB container's init scripts.
    # However, for development/ensure, we could check if table exists.
    # For now, we assume the DB container handles schema init as per spec.


def get_session():
    if _SessionLocal is None:
        init_db()
    return _SessionLocal()
