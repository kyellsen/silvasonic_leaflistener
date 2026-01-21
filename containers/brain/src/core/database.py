from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import uuid
from src.config import config

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class AudioFile(Base):
    __tablename__ = 'audio_files'
    
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
    
    id = Column(String, primary_key=True, default=generate_uuid)
    audio_file_id = Column(String, ForeignKey('audio_files.id'), nullable=False)
    
    # Metrics
    rms_loudness = Column(Float, nullable=True)
    peak_frequency_hz = Column(Float, nullable=True)
    is_active = Column(Boolean, default=False)
    
    audio_file = relationship("AudioFile", back_populates="metrics")

class Artifact(Base):
    __tablename__ = 'artifacts'
    
    id = Column(String, primary_key=True, default=generate_uuid)
    audio_file_id = Column(String, ForeignKey('audio_files.id'), nullable=False)
    
    artifact_type = Column(String, nullable=False) # e.g. 'spectrogram'
    filepath = Column(String, nullable=False)
    
    audio_file = relationship("AudioFile", back_populates="artifacts")

# Engine Setup
# Engine Setup
engine = create_engine(config.DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Enable WAL mode for SQLite
from sqlalchemy import event

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

def init_db():
    config.ensure_dirs()
    Base.metadata.create_all(bind=engine)
