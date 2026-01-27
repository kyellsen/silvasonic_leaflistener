
import pytest
from unittest.mock import MagicMock
import sys
import os
import pandas as pd
from datetime import datetime

# Add src to pythonpath
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

@pytest.fixture
def mock_wetterdienst(monkeypatch):
    """Mock the wetterdienst DwdObservationRequest."""
    mock_request = MagicMock()
    
    # Mock class to return our mock instance
    mock_cls = MagicMock(return_value=mock_request)
    
    monkeypatch.setattr("main.DwdObservationRequest", mock_cls)
    
    return mock_cls, mock_request

@pytest.fixture
def mock_db_engine(monkeypatch):
    """Mock the SQLAlchemy engine."""
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    
    monkeypatch.setattr("main.engine", mock_engine)
    
    return mock_engine, mock_conn

@pytest.fixture
def sample_weather_df():
    """Create a sample DataFrame mimicking Wetterdienst structure."""
    data = {
        "station_id": ["00433"] * 7,
        "dataset": ["climate_summary"] * 7,
        "parameter": [
            "temperature_air_mean_2m",
            "humidity",
            "precipitation_height",
            "wind_speed",
            "wind_gust_max",
            "sunshine_duration",
            "cloud_cover_total"
        ],
        "date": [datetime(2023, 10, 27, 12, 0, 0)] * 7,
        "value": [
            293.15, # Temp in Kelvin (20C)
            65.0,   # Humidity
            0.5,    # Precip
            3.5,    # Wind
            8.2,    # Gust
            600.0,  # Sunshine (seconds)
            45.0    # Cloud cover
        ],
        "quality": [1] * 7
    }
    return pd.DataFrame(data)
