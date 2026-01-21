from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from src.config import config
import os

Base = declarative_base()

class Detection(Base):
    __tablename__ = 'detections'
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Metadata from file
    recording_timestamp = Column(DateTime) # When the file was recorded
    filename = Column(String)
    
    # Detection details
    start_time = Column(Float) # Seconds from start of file
    end_time = Column(Float)   # Seconds from start of file
    
    # Species info
    scientific_name = Column(String)
    common_name = Column(String)
    label = Column(String)     # Combined "Common (Scientific)"
    confidence = Column(Float)

def init_db():
    # Ensure directory exists
    db_dir = os.path.dirname(config.DB_PATH)
    os.makedirs(db_dir, exist_ok=True)
    
    engine = create_engine(f"sqlite:///{config.DB_PATH}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

# Global session factory
SessionLocal = init_db()
