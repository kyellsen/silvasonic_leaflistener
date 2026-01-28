from unittest.mock import MagicMock

import pytest
import silvasonic_weather.main as weather_main


def test_init_db_creates_view_v2(mock_db_engine) -> None:
    """Test that the complex analysis view is created."""
    print(f"DEBUG: weather_main file: {weather_main.__file__}")

    mock_engine, mock_conn = mock_db_engine
    weather_main.init_db()

    # Capture all SQL statements
    statements = []
    for call in mock_conn.execute.call_args_list:
        arg = call[0][0]
        sql = arg.text if hasattr(arg, "text") else str(arg)
        statements.append(sql)

    # Verify View Logic
    assert any("CREATE OR REPLACE VIEW weather.bird_stats_view" in s for s in statements)
    assert any("WITH w_stats AS" in s for s in statements)
    assert any("LEFT JOIN b_stats" in s for s in statements)


def test_init_db_view_failure_graceful_v2(mock_db_engine) -> None:
    """Test that init_db does not crash if view creation fails (e.g. missing birdnet schema)."""
    mock_engine, mock_conn = mock_db_engine

    # Fail only on VIEW creation
    def side_effect(statement, *args, **kwargs):
        sql = statement.text if hasattr(statement, "text") else str(statement)
        if "CREATE OR REPLACE VIEW" in sql:
            raise Exception("BirdNET schema missing")
        return MagicMock()

    mock_conn.execute.side_effect = side_effect

    # Should not raise exception
    try:
        weather_main.init_db()
    except Exception:
        pytest.fail("init_db crashed on view creation failure")
