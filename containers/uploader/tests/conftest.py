import os
import shutil
import sys
import tempfile
from unittest.mock import MagicMock

import pytest

# Add both project root (for src package) and src dir (for direct module imports)
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))


@pytest.fixture
def mock_env(monkeypatch):
    """Sets up clean environment variables."""
    monkeypatch.setenv("UPLOADER_NEXTCLOUD_URL", "https://example.com")
    monkeypatch.setenv("UPLOADER_NEXTCLOUD_USER", "user")
    monkeypatch.setenv("UPLOADER_NEXTCLOUD_PASSWORD", "pass")
    monkeypatch.setenv("UPLOADER_TARGET_DIR", "silvasonic")
    monkeypatch.setenv("UPLOADER_SYNC_INTERVAL", "60")
    monkeypatch.setenv("UPLOADER_CLEANUP_THRESHOLD", "70")
    monkeypatch.setenv("UPLOADER_CLEANUP_TARGET", "60")
    monkeypatch.setenv("UPLOADER_MIN_AGE", "1m")
    monkeypatch.setenv("POSTGRES_USER", "test_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test_pass")
    monkeypatch.setenv("POSTGRES_DB", "test_db")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")


@pytest.fixture
def temp_fs():
    """Creates a temporary directory for file operations."""
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)


@pytest.fixture
def mock_db():
    """Mocks the DatabaseHandler."""
    db_mock = MagicMock()
    # Setup happy path
    db_mock.connect.return_value = True
    db_mock.get_uploaded_filenames.return_value = set()
    return db_mock


@pytest.fixture
def mock_rclone():
    """Mocks the RcloneWrapper."""
    rclone = MagicMock()
    rclone.copy.return_value = True
    rclone.get_disk_usage_percent.return_value = 50.0
    rclone.list_files.return_value = {}
    return rclone
