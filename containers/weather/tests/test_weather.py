import json
import sys
from unittest.mock import MagicMock, patch

from silvasonic_weather import main
from silvasonic_weather.config import Settings, settings


def test_fetch_weather_success(mock_db_engine) -> None:
    """Test successful weather fetch and storage via OpenMeteo."""
    mock_engine, mock_conn = mock_db_engine

    # Sample OpenMeteo Response
    api_response = {
        "latitude": 52.52,
        "longitude": 13.41,
        "generationtime_ms": 0.1,
        "utc_offset_seconds": 0,
        "timezone": "UTC",
        "timezone_abbreviation": "UTC",
        "elevation": 38.0,
        "current": {
            "time": "2023-10-27T12:00:00",
            "interval": 900,
            "temperature_2m": 20.0,
            "relative_humidity_2m": 65.0,
            "precipitation": 0.5,
            "rain": 0.5,
            "showers": 0.0,
            "snowfall": 0.0,
            "cloud_cover": 45.0,
            "wind_speed_10m": 3.5,
            "wind_gusts_10m": 8.2,
            "weather_code": 3,
            "sunshine_duration": 600.0,
        },
    }

    # Mock httpx.Client
    with patch("httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.get.return_value.json.return_value = api_response
        mock_client.get.return_value.raise_for_status = MagicMock()

        # Mock Settings.get_location (class patch)
        with patch.object(Settings, "get_location", return_value=(52.52, 13.41)):
            main.fetch_weather()

        # Verify API called correctly
        mock_client.get.assert_called_once()
        args, kwargs = mock_client.get.call_args
        assert args[0] == "https://api.open-meteo.com/v1/forecast"
        assert kwargs["params"]["latitude"] == 52.52
        assert kwargs["params"]["longitude"] == 13.41

    # Verify DB insert
    insert_call = None
    for c in mock_conn.execute.call_args_list:
        arg = c[0][0]
        sql = arg.text if hasattr(arg, "text") else str(arg)
        if "INSERT INTO weather.measurements" in sql:
            insert_call = c
            break

    assert insert_call is not None

    # Check values passed to execute (now a dict from model_dump)
    inserted_params = insert_call[0][1]

    assert inserted_params["station_id"] == "OpenMeteo-52.52-13.41"
    assert inserted_params["temperature_c"] == 20.0
    assert inserted_params["humidity_percent"] == 65.0
    assert inserted_params["precipitation_mm"] == 0.5
    assert inserted_params["wind_speed_ms"] == 3.5
    assert inserted_params["condition_code"] == "3"


def test_fetch_weather_no_data(mock_db_engine) -> None:
    """Test handling of empty/malformed API response."""
    mock_engine, mock_conn = mock_db_engine

    # Return empty current object
    api_response = {"current": {}}

    with patch("httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.get.return_value.json.return_value = api_response

        with patch.object(Settings, "get_location", return_value=(50.0, 10.0)):
            main.fetch_weather()

    # We can check that execute was NOT called with INSERT
    for c in mock_conn.execute.call_args_list:
        arg = c[0][0]
        sql = arg.text if hasattr(arg, "text") else str(arg)
        assert "INSERT INTO weather.measurements" not in sql


def test_get_location_default():
    """Test get_location returns default when config missing."""
    with patch("os.path.exists", return_value=False):
        lat, lon = settings.get_location()
        assert lat == settings.default_latitude
        assert lon == settings.default_longitude


def test_get_location_config(tmp_path):
    """Test get_location reads from config using a temporary file."""
    config_data = {"location": {"latitude": 10.5, "longitude": 20.5}}
    config_file = tmp_path / "test_settings.json"

    with open(config_file, "w") as f:
        json.dump(config_data, f)

    original = settings.config_path
    settings.config_path = str(config_file)
    try:
        lat, lon = settings.get_location()
        assert lat == 10.5
        assert lon == 20.5
    finally:
        settings.config_path = original


def test_write_status(monkeypatch) -> None:
    """Test writing status file."""
    # Mock Redis global class
    with patch("redis.Redis") as mock_redis_cls:
        mock_redis_instance = mock_redis_cls.return_value

        # Mock psutil
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 10.0
        mock_mem = MagicMock()
        mock_mem.rss = 1024 * 1024 * 10
        mock_psutil.Process.return_value.memory_info.return_value = mock_mem

        # Patch psutil in sys.modules because it is imported at top level
        with patch.dict(sys.modules, {"psutil": mock_psutil}):
            monkeypatch.setattr("os.getpid", MagicMock(return_value=123))

            main.write_status("Testing")

            # Verify Redis call
            mock_redis_instance.setex.assert_called_once()
            args = mock_redis_instance.setex.call_args[0]
            assert args[0] == "status:weather"
            assert args[1] == 1500
            assert "Testing" in args[2]
