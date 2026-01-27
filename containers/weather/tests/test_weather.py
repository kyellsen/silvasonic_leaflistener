
import pytest
from unittest.mock import MagicMock, call
import pandas as pd
from datetime import datetime
import main
from wetterdienst.metadata.parameter import Parameter

def test_init_db(mock_db_engine):
    """Test that init_db creates the schema and table."""
    mock_engine, mock_conn = mock_db_engine
    
    main.init_db()
    
    # Check that execute was called
    assert mock_conn.execute.called
    
    # Check for specific SQL parts
    # Check for specific SQL parts
    calls = mock_conn.execute.call_args_list
    
    # helper to get sql text from call
    def get_sql(call_obj):
        arg = call_obj[0][0] # first arg
        return str(arg) # str(TextClause) returns the SQL usually, or arg.text

    assert any("CREATE SCHEMA IF NOT EXISTS weather" in get_sql(c) for c in calls)
    assert any("CREATE TABLE IF NOT EXISTS weather.measurements" in get_sql(c) for c in calls)
    assert any("sunshine_seconds FLOAT" in get_sql(c) for c in calls)
    assert any("wind_gust_ms FLOAT" in get_sql(c) for c in calls)

def test_fetch_weather_success(mock_wetterdienst, mock_db_engine, sample_weather_df):
    """Test successful weather fetch and storage."""
    mock_cls, mock_req = mock_wetterdienst
    mock_engine, mock_conn = mock_db_engine
    
    # Setup mock return chain: request.filter_by_rank(...).values.all().df -> sample_df
    mock_values = MagicMock()
    mock_values.all.return_value.df = sample_weather_df
    
    mock_filtered = MagicMock()
    mock_filtered.values = mock_values
    
    mock_req.filter_by_rank.return_value = mock_filtered
    
    # Run
    main.fetch_weather()
    
    # Verify request param setup
    mock_cls.assert_called_once()
    args, kwargs = mock_cls.call_args
    params = kwargs['parameters']
    
    assert Parameter.SUNSHINE_DURATION in params
    assert Parameter.WIND_GUST_MAX in params
    
    # Verify DB insert
    # We look for the INSERT statement call
    insert_call = None
    for c in mock_conn.execute.call_args_list:
        if "INSERT INTO weather.measurements" in str(c[0][0]):  # str(text object)
            insert_call = c
            break
            
    assert insert_call is not None
    
    # Check values passed to execute
    # args[0] is the statement, args[1] is the params dict
    inserted_params = insert_call[0][1]
    
    assert inserted_params['sid'] == "00433"
    assert inserted_params['temp'] == 20.0  # 293.15K - 273.15 = 20.0C
    assert inserted_params['hum'] == 65.0
    assert inserted_params['precip'] == 0.5
    assert inserted_params['wind'] == 3.5
    assert inserted_params['gust'] == 8.2
    assert inserted_params['sun'] == 600.0
    assert inserted_params['cloud'] == 45.0
    
def test_fetch_weather_no_data(mock_wetterdienst, mock_db_engine):
    """Test handling of empty API response."""
    mock_cls, mock_req = mock_wetterdienst
    mock_engine, mock_conn = mock_db_engine
    
    # Return empty DF
    mock_values = MagicMock()
    mock_values.all.return_value.df = pd.DataFrame() # Empty
    
    mock_filtered = MagicMock()
    mock_filtered.values = mock_values
    mock_req.filter_by_rank.return_value = mock_filtered
    
    main.fetch_weather()
    
    # Should not call db execute with INSERT
    # mock_conn.execute might be called for other things? No, we use a new connection in fetch_weather context.
    # Actually fetch_weather calls get_db_connection() inside.
    # So if it returns early, it might not even open the connection if the 'with' block is later.
    # Looking at code:
    # 1. request...
    # 2. if values.empty: return
    # 3. with get_db_connection()...
    
    # So get_db_connection should NOT be called if we strictly mock engine.connect
    # BUT main.py calls get_db_connection() inside fetch_weather ONLY after the check.
    # So mock_engine.connect() should NOT be called.
    
    # Wait, get_db_connection call `engine.connect()`.
    # If we return early, `engine.connect()` is not called.
    
    assert not mock_engine.connect.called
