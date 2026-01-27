
import pytest
from unittest.mock import MagicMock, call
from datetime import datetime, timedelta
from silvasonic_weather import analysis
from sqlalchemy import text

def test_init_analysis_db(mock_db_engine):
    """Test that init_analysis_db creates the schema."""
    mock_engine, mock_conn = mock_db_engine
    
    analysis.init_analysis_db()
    
    assert mock_conn.execute.called
    calls = mock_conn.execute.call_args_list
    assert any("CREATE TABLE IF NOT EXISTS weather.bird_stats" in str(c[0][0]) for c in calls)

def test_run_analysis_nothing_new_to_analyze(mock_db_engine, monkeypatch):
    """Test scenario where start_time >= end_time."""
    mock_engine, mock_conn = mock_db_engine
    
    # Mock current time
    mock_now = datetime(2023, 10, 27, 12, 0, 0)
    monkeypatch.setattr("silvasonic_weather.analysis.datetime", MagicMock())
    analysis.datetime.utcnow.return_value = mock_now
    
    # Mock last entry to be recently (1 hour ago, so next start is 13:00, which is > now?? No.)
    # now = 12:00. end_time = 12:00.
    # last_entry = 10:00. start_time = 11:00. start < end.
    
    # We want start >= end. start is based on last_entry + 1h.
    # If last_entry is 11:00. start = 12:00. end = 12:00. start >= end.
    
    mock_conn.execute.return_value.scalar.return_value = datetime(2023, 10, 27, 11, 0, 0)
    
    analysis.run_analysis()
    
    # Should check for max timestamp
    assert "SELECT MAX(timestamp)" in str(mock_conn.execute.call_args_list[0][0][0])
    
    # Should NOT execute the massive insert
    INSERT_SQL_SNIPPET = "INSERT INTO weather.bird_stats"
    calls = [str(c[0][0]) for c in mock_conn.execute.call_args_list]
    assert not any(INSERT_SQL_SNIPPET in c for c in calls if "SELECT" not in c)

def test_run_analysis_bootstrap(mock_db_engine, monkeypatch):
    """Test analysis run when table is empty (bootstrap mode)."""
    mock_engine, mock_conn = mock_db_engine
    
    # Mock time
    mock_now = datetime(2023, 10, 27, 12, 0, 0)
    monkeypatch.setattr("silvasonic_weather.analysis.datetime", MagicMock())
    analysis.datetime.utcnow.return_value = mock_now
    
    # Mock empty last entry
    mock_conn.execute.return_value.scalar.return_value = None
    
    analysis.run_analysis()
    
    # Verify it ran the logic
    # It should have executed the complex query
    
    # Find the call with the insert
    insert_call = None
    for c in mock_conn.execute.call_args_list:
        if "INSERT INTO weather.bird_stats" in str(c[0][0]):
            insert_call = c
            break
            
    assert insert_call is not None
    
    # Check params
    args, kwargs = insert_call
    params = args[1] # the dict passed as second arg
    
    # Start time should be 30 days ago
    expected_start = mock_now - timedelta(days=30)
    expected_start = expected_start.replace(minute=0, second=0, microsecond=0)
    
    assert params['start'] == expected_start
    assert params['end'] == mock_now

def test_run_analysis_incremental(mock_db_engine, monkeypatch):
    """Test normal incremental analysis."""
    mock_engine, mock_conn = mock_db_engine
    
    # Mock time: 14:00
    mock_now = datetime(2023, 10, 27, 14, 0, 0)
    monkeypatch.setattr("silvasonic_weather.analysis.datetime", MagicMock())
    analysis.datetime.utcnow.return_value = mock_now
    
    # Mock last entry: 12:00
    # So start should be 13:00
    mock_conn.execute.return_value.scalar.return_value = datetime(2023, 10, 27, 12, 0, 0)
    
    analysis.run_analysis()
    
    # Find insert call
    insert_call = None
    for c in mock_conn.execute.call_args_list:
        if "INSERT INTO weather.bird_stats" in str(c[0][0]):
            insert_call = c
            break
            
    assert insert_call is not None
    params = insert_call[0][1]
    
    current_call_start = params['start']
    expected_start = datetime(2023, 10, 27, 13, 0, 0)
    
    assert current_call_start == expected_start

def test_run_analysis_failure(mock_db_engine):
    """Test exception handling."""
    mock_engine, mock_conn = mock_db_engine
    mock_conn.execute.side_effect = Exception("DB Error")
    
    # Should not raise
    analysis.run_analysis()
