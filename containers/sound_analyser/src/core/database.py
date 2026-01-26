import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.schema import CreateSchema
from src.config import config

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class AudioFile(Base):
    __tablename__ = 'audio_files'
    __table_args__ = {'schema': 'brain'}

    id = Column(String, primary_key=True, default=generate_uuid)
    filepath = Column(String, unique=True, nullable=False)
    filename = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    # Meta
    duration_sec = Column(Float, nullable=True)
    sample_rate = Column(Integer, nullable=True)
    channels = Column(Integer, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)

    # Relationships
    metrics = relationship("AnalysisMetrics", back_populates="audio_file", uselist=False, cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="audio_file", cascade="all, delete-orphan")

class AnalysisMetrics(Base):
    __tablename__ = 'analysis_metrics'
    __table_args__ = {'schema': 'brain'}

    id = Column(String, primary_key=True, default=generate_uuid)
    audio_file_id = Column(String, ForeignKey('brain.audio_files.id'), nullable=False)

    # Metrics
    rms_loudness = Column(Float, nullable=True)
    peak_frequency_hz = Column(Float, nullable=True)
    is_active = Column(Boolean, default=False)

    audio_file = relationship("AudioFile", back_populates="metrics")

class Artifact(Base):
    __tablename__ = 'artifacts'
    __table_args__ = {'schema': 'brain'}

    id = Column(String, primary_key=True, default=generate_uuid)
    audio_file_id = Column(String, ForeignKey('brain.audio_files.id'), nullable=False)

    artifact_type = Column(String, nullable=False) # e.g. 'spectrogram'
    filepath = Column(String, nullable=False)

    audio_file = relationship("AudioFile", back_populates="artifacts")

# Engine Setup
engine = create_engine(config.DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Enable WAL mode for SQLite ONLY
if config.DB_URL.startswith("sqlite"):
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

def init_db():
    config.ensure_dirs()

    # Create Schema 'brain' if using Postgres
    if not config.DB_URL.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                conn.execute(CreateSchema('brain', if_not_exists=True))
                conn.commit()
        except Exception:
            pass # Usually exists or retry logic needed, but let's assume it works or fails hard

    Base.metadata.create_all(bind=engine)
