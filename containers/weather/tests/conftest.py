import os
import sys
from unittest.mock import MagicMock

import pytest

# Add src to pythonpath
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))


@pytest.fixture
def mock_db_engine(monkeypatch):
    """Mock the SQLAlchemy engine."""
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    monkeypatch.setattr("silvasonic_weather.main.engine", mock_engine)

    return mock_engine, mock_conn
