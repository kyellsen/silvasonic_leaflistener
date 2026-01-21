import pytest
import os
import sys
from pathlib import Path

# Set test environment defaults BEFORE importing app modules
os.environ["DB_PATH"] = "/tmp/test_birdnet.sqlite"
os.environ["INPUT_DIR"] = "/tmp/test_input"
os.environ["LATITUDE"] = "52.0"
os.environ["LONGITUDE"] = "13.0"
os.environ["MIN_CONFIDENCE"] = "0.8"

# Add src to pythonpath
sys.path.append(str(Path(__file__).parent.parent))

from src.database import Base, Detection
from src.config import config # ensure config is loaded with these envs
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv("INPUT_DIR", "/tmp/input")
    monkeypatch.setenv("DB_PATH", "/tmp/test.sqlite")
    monkeypatch.setenv("LATITUDE", "52.0")
    monkeypatch.setenv("LONGITUDE", "13.0")
    monkeypatch.setenv("MIN_CONFIDENCE", "0.8")
    monkeypatch.setenv("THREADS", "2")
    monkeypatch.setenv("RECURSIVE_WATCH", "false")

@pytest.fixture(scope="function")
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
