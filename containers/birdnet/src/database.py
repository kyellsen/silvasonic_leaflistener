import logging
import os
import time
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.schema import CreateSchema
from sqlalchemy.exc import ProgrammingError, OperationalError
from datetime import datetime, timezone

# Setup logging
logger = logging.getLogger("Database")

Base = declarative_base()

class BirdNETDetection(Base):
    __tablename__ = 'detections'
    __table_args__ = {'schema': 'birdnet'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # File Info
    filename = Column(String(255), nullable=False)
    filepath = Column(String(1024), nullable=False)
    
    # Detection Info (Raw)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    species_code = Column(String(50), nullable=True) # e.g. "Turdus merula"
    common_name = Column(String(255), nullable=True)
    scientific_name = Column(String(255), nullable=True)
    
    # Metadata
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    model_version = Column(String(50), nullable=True)
    clip_path = Column(String(1024), nullable=True)

class SpeciesInfo(Base):
    __tablename__ = 'species_info'
    __table_args__ = {'schema': 'birdnet'}

    scientific_name = Column(String(255), primary_key=True)
    common_name = Column(String(255), nullable=True)
    german_name = Column(String(255), nullable=True)
    family = Column(String(255), nullable=True)
    image_url = Column(String(1024), nullable=True)
    image_author = Column(String(255), nullable=True)
    image_license = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    wikipedia_url = Column(String(1024), nullable=True)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Watchlist(Base):
    __tablename__ = 'watchlist'
    __table_args__ = {'schema': 'birdnet'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    scientific_name = Column(String(255), unique=True, nullable=False)
    common_name = Column(String(255), nullable=True) # Cache for display if needed
    enabled = Column(Integer, default=1) # 1=Enabled, 0=Disabled. Using Integer for SQLite/PG compat just in case, though Boolean is fine in PG.
    last_notification = Column(DateTime, nullable=True)
    
    # Notification Settings (Future Proofing)
    min_confidence = Column(Float, default=0.0) # 0.0 = Use global default

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
        """Establish database connection and ensure schema exists."""
        retries = 10
        while retries > 0:
            try:
                logger.info(f"Connecting to Database {self.host}...")
                self.engine = create_engine(self.db_url, pool_pre_ping=True)
                
                # Check connection
                with self.engine.connect() as conn:
                    # Create Schema 'birdnet' if not exists
                    try:
                        conn.execute(CreateSchema('birdnet', if_not_exists=True))
                        conn.commit()
                    except ProgrammingError as e:
                        # Sometimes race condition or perm issue, but CreateSchema if_not_exists handles most
                        # This catch is generic for DB errors
                        logger.warning(f"Schema creation warning: {e}")
                        conn.rollback()

                # Create Tables
                Base.metadata.create_all(self.engine)
                
                self.Session = sessionmaker(bind=self.engine)
                logger.info("Database connected and initialized.")
                return True
                
            except OperationalError as e:
                logger.warning(f"Database not ready ({e}). Retrying in 5s... ({retries} left)")
                time.sleep(5)
                retries -= 1
            except Exception as e:
                logger.error(f"Critical DB connection error: {e}")
                return False
        
        return False

    def save_detection(self, detection_dict: dict):
        """
        Save a single detection to the database.
        
        Args:
            detection_dict: {
                'filename': str,
                'start_time': float,
                'end_time': float,
                'confidence': float,
                'common_name': str,
                'scientific_name': str,
                ...
            }
        """
        if not self.Session:
            logger.error("DB Session not initialized.")
            return

        session = self.Session()
        try:
            det = BirdNETDetection(
                filename=detection_dict.get('filename'),
                filepath=detection_dict.get('filepath', ''),
                start_time=detection_dict.get('start_time'),
                end_time=detection_dict.get('end_time'),
                confidence=detection_dict.get('confidence'),
                common_name=detection_dict.get('common_name'),
                scientific_name=detection_dict.get('scientific_name'),
                latitude=detection_dict.get('lat'),
                longitude=detection_dict.get('lon'),
                clip_path=detection_dict.get('clip_path'),
                timestamp=datetime.now(timezone.utc)
            )
            session.add(det)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to save detection: {e}")
            session.rollback()
        finally:
            session.close()

    def get_watchlist(self):
        """Returns all enabled watchlist items."""
        if not self.Session: return []
        session = self.Session()
        try:
            return session.query(Watchlist).filter_by(enabled=1).all()
        finally:
            session.close()

    def update_watchlist(self, scientific_name, common_name, enabled=True):
        """Add/Update a species in the watchlist."""
        if not self.Session: return False
        session = self.Session()
        try:
            item = session.query(Watchlist).filter_by(scientific_name=scientific_name).first()
            if item:
                item.enabled = 1 if enabled else 0
                item.common_name = common_name # Update common name just in case
            else:
                item = Watchlist(
                    scientific_name=scientific_name,
                    common_name=common_name,
                    enabled=1 if enabled else 0
                )
                session.add(item)
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update watchlist: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def is_watched(self, scientific_name):
        """Check if a species is in the watchlist and enabled."""
        if not self.Session: return False
        session = self.Session()
        try:
            # We trust scientific name to be stable
            return session.query(Watchlist).filter_by(scientific_name=scientific_name, enabled=1).count() > 0
        finally:
            session.close()

# Singleton
db = DatabaseHandler()
