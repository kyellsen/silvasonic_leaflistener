import pytest
import os
import sys
from pathlib import Path

# Add src to pythonpath
sys.path.append(str(Path(__file__).parent.parent))

from src.database import Base, Detection
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
