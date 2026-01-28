import json
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
from silvasonic_weather import main
from silvasonic_weather.config import Settings, settings


def test_init_db(mock_db_engine) -> None:
    """Test that init_db creates the schema and table."""
    mock_engine, mock_conn = mock_db_engine

    main.init_db()

    # Check that execute was called
    assert mock_conn.execute.called

    # Check for specific SQL parts
    calls = mock_conn.execute.call_args_list

    # helper to get sql text from call
    def get_sql(call_obj):
        arg = call_obj[0][0]  # first arg
        if hasattr(arg, "text"):
            return arg.text
        return str(arg)

    assert any("CREATE SCHEMA IF NOT EXISTS weather" in get_sql(c) for c in calls)
    assert any("CREATE TABLE IF NOT EXISTS weather.measurements" in get_sql(c) for c in calls)
    assert any("sunshine_seconds FLOAT" in get_sql(c) for c in calls)
    assert any("wind_gust_ms FLOAT" in get_sql(c) for c in calls)


def test_fetch_weather_success(mock_wetterdienst, mock_db_engine, sample_weather_df) -> None:
    """Test successful weather fetch and storage."""
    mock_cls, mock_req = mock_wetterdienst
    mock_engine, mock_conn = mock_db_engine

    # Setup mock return chain
    mock_values = MagicMock()
    mock_values.all.return_value.df = sample_weather_df

    mock_filtered = MagicMock()
    mock_filtered.values = mock_values

    mock_req.filter_by_rank.return_value = mock_filtered

    # Mock Settings.get_location (class patch)
    with patch.object(Settings, "get_location", return_value=(50.0, 10.0)):
        main.fetch_weather()

    # Verify connection usage
    assert mock_cls.call_count >= 1
    # Verify that we used the correct argument name 'parameters'
    call_kwargs = mock_cls.call_args[1]
    assert "parameters" in call_kwargs

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

    assert inserted_params["station_id"] == "00433"
    assert abs(inserted_params["temperature_c"] - 20.0) < 0.001
    assert inserted_params["humidity_percent"] == 65.0
    assert inserted_params["precipitation_mm"] == 0.5


def test_fetch_weather_no_data(mock_wetterdienst, mock_db_engine) -> None:
    """Test handling of empty API response."""
    mock_cls, mock_req = mock_wetterdienst
    mock_engine, mock_conn = mock_db_engine

    # Return empty DF
    mock_values = MagicMock()
    mock_values.all.return_value.df = pd.DataFrame()

    mock_filtered = MagicMock()
    mock_filtered.values = mock_values
    mock_req.filter_by_rank.return_value = mock_filtered

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

    # Patch field on instance is allowed if it's a field... but config_path IS a field.
    # settings.config_path = str(config_file) should work?
    # But Settings is frozen by default? No, BaseSettings default config.
    # Let's try direct assignment in test, or patch.
    # Since config_path is a field, we can just set it if model is not frozen.
    # BaseSettings is not frozen by default.

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
    mock_open = MagicMock()
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file

    monkeypatch.setattr("builtins.open", mock_open)
    monkeypatch.setattr("os.makedirs", MagicMock())
    monkeypatch.setattr("os.rename", MagicMock())
    monkeypatch.setattr("os.getpid", MagicMock(return_value=123))

    # Mock psutil
    mock_psutil = MagicMock()
    mock_psutil.cpu_percent.return_value = 10.0
    mock_mem = MagicMock()
    mock_mem.rss = 1024 * 1024 * 10
    mock_psutil.Process.return_value.memory_info.return_value = mock_mem
    sys.modules["psutil"] = mock_psutil

    main.write_status("Testing")

    assert mock_open.called
    assert mock_psutil.cpu_percent.called
