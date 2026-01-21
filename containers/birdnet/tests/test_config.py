import os
import pytest
import importlib
from unittest.mock import patch
import src.config

def test_config_defaults():
    """Test that config loads with expected defaults when no env vars are set."""
    # We need to ensure we are testing a clean state. 
    # Since config is a module-level instance, we must reload it with a clean environment.
    with patch.dict(os.environ, {}, clear=True):
        importlib.reload(src.config)
        assert str(src.config.config.DB_PATH) == "/data/db/birdnet.sqlite"
        assert str(src.config.config.INPUT_DIR) == "/data/recording"
        assert src.config.config.LATITUDE is None
        assert src.config.config.LONGITUDE is None
        assert src.config.config.MIN_CONFIDENCE == 0.7
        assert src.config.config.SIG_OVERLAP == 0.0
        assert src.config.config.SIG_LENGTH == 3.0
        assert src.config.config.THREADS == 1
        assert src.config.config.RECURSIVE_WATCH is True 

def test_config_overrides():
    """Test that environment variables correctly override defaults."""
    env_vars = {
        "DB_PATH": "/tmp/custom.sqlite",
        "INPUT_DIR": "/tmp/custom_input",
        "LATITUDE": "10.0",
        "LONGITUDE": "20.0",
        "MIN_CONFIDENCE": "0.5",
        "SIG_OVERLAP": "1.5",
        "SIG_LENGTH": "5.0",
        "THREADS": "4",
        "RECURSIVE_WATCH": "true"
    }
    
    with patch.dict(os.environ, env_vars, clear=True):
        importlib.reload(src.config)
        assert str(src.config.config.DB_PATH) == "/tmp/custom.sqlite"
        assert str(src.config.config.INPUT_DIR) == "/tmp/custom_input"
        assert src.config.config.LATITUDE == 10.0
        assert src.config.config.LONGITUDE == 20.0
        assert src.config.config.MIN_CONFIDENCE == 0.5
        # SIG_OVERLAP and SIG_LENGTH are hardcoded in Config
        assert src.config.config.SIG_OVERLAP == 0.0
        assert src.config.config.SIG_LENGTH == 3.0
        assert src.config.config.THREADS == 4
        assert src.config.config.RECURSIVE_WATCH is True

