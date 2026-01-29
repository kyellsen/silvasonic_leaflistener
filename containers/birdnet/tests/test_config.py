import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from silvasonic_birdnet.config import Settings


# Helper to clear env
@pytest.fixture
def clean_env():
    old_env = os.environ.copy()
    keys = ["MIN_CONFIDENCE", "LATITUDE", "LONGITUDE", "WEEK", "OVERLAP", "SENSITIVITY", "THREADS"]
    for k in keys:
        if k in os.environ:
            del os.environ[k]
    yield
    os.environ.clear()
    os.environ.update(old_env)


def test_defaults(clean_env):
    """Test default values."""
    # We patch Path.exists to return False to avoid reading real files
    with patch.object(Path, "exists", return_value=False):
        s = Settings()
        assert s.birdnet.min_conf == 0.7
        assert s.birdnet.threads == 3
        # Derived
        assert s.CLIPS_DIR == s.RESULTS_DIR / "clips"


def test_env_override(clean_env):
    """Test environment variable overrides."""
    os.environ["MIN_CONFIDENCE"] = "0.85"
    os.environ["THREADS"] = "5"

    with patch.object(Path, "exists", return_value=False):
        s = Settings()
        assert s.birdnet.min_conf == 0.85
        assert s.birdnet.threads == 5


def test_yaml_override(clean_env, tmp_path):
    """Test YAML config override."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("birdnet:\n  min_confidence: 0.9\n  sensitivity: 1.25")

    # test basic loading (no patch.multiple)
    s = Settings(CONFIG_FILE=config_file, SETTINGS_JSON=Path("/non/existent"))

    assert s.birdnet.min_conf == 0.9
    # Intentionally ignoring the 'pass' and comment block which was confusing

    config_file_fixed = tmp_path / "config_fixed.yml"
    config_file_fixed.write_text("birdnet:\n  min_conf: 0.9\n  sensitivity: 1.25")

    s = Settings(CONFIG_FILE=config_file_fixed, SETTINGS_JSON=Path("/non/existent"))
    assert s.birdnet.min_conf == 0.9
    assert s.birdnet.sensitivity == 1.25


def test_json_override(clean_env, tmp_path):
    """Test JSON config override (Highest Priority)."""
    # JSON logic maps "min_confidence" -> "min_conf" (Line 171 config.py)

    json_file = tmp_path / "settings.json"
    content = {
        "birdnet": {"min_confidence": 0.55, "latitude": 52.0},
        "location": {"longitude": 13.0},
    }
    json_file.write_text(json.dumps(content))

    s = Settings(SETTINGS_JSON=json_file, CONFIG_FILE=Path("/non/existent"))

    assert s.birdnet.min_conf == 0.55
    assert s.birdnet.lat == 52.0
    assert s.birdnet.lon == 13.0  # From location fallback


def test_validation_error(clean_env):
    """Test validation (e.g. invalid confidence)."""
    # Set invalid env
    os.environ["MIN_CONFIDENCE"] = "1.5"  # > 1.0

    # Validation error is caught and logged, defaults preserved (Line 183 config.py)
    # Actually `self.birdnet` is initialized safe defaults in `default_factory`.
    # If reload fails, it stays default.

    with patch.object(Path, "exists", return_value=False):
        s = Settings()
        assert s.birdnet.min_conf == 0.7  # Default
