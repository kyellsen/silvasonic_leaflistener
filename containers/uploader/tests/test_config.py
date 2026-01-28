import json
import os
from unittest.mock import patch

from silvasonic_uploader.config import UploaderSettings


class TestConfig:
    def test_defaults(self):
        """Test default values."""
        settings = UploaderSettings()
        assert settings.sync_interval == 10
        assert settings.cleanup_threshold == 70
        assert settings.nextcloud_url == ""

    def test_env_override(self):
        """Test partial override from environment."""
        with patch.dict(os.environ, {"UPLOADER_SYNC_INTERVAL": "999"}):
            settings = UploaderSettings()
            assert settings.sync_interval == 999
            # Others remain default
            assert settings.cleanup_threshold == 70

    def test_save_and_load(self, tmp_path):
        """Test saving to file and reloading."""
        # Mock CONFIG_PATH to use tmp_path
        mock_path = tmp_path / "uploader_config.json"

        with patch("silvasonic_uploader.config.CONFIG_PATH", mock_path):
            # 1. Save
            settings = UploaderSettings(sync_interval=50, nextcloud_user="testuser")
            settings.save()

            assert mock_path.exists()

            with open(mock_path) as f:
                data = json.load(f)
            assert data["sync_interval"] == 50
            assert data["nextcloud_user"] == "testuser"

            # 2. Load
            loaded = UploaderSettings.load()
            assert loaded.sync_interval == 50
            assert loaded.nextcloud_user == "testuser"
            # Default
            assert loaded.cleanup_target == 60

    def test_load_priority(self, tmp_path):
        """Test that file overrides env/default."""
        mock_path = tmp_path / "uploader_config.json"

        # File has sync_interval=50
        with open(mock_path, "w") as f:
            json.dump({"sync_interval": 50}, f)

        with patch("silvasonic_uploader.config.CONFIG_PATH", mock_path):
            # Env has sync_interval=100
            with patch.dict(os.environ, {"UPLOADER_SYNC_INTERVAL": "100"}):
                settings = UploaderSettings.load()
                # File wins implies persistent config overrides env?
                # The logic in config.py is:
                # 1. base = cls() (which reads env)
                # 2. update with file
                # So File > Env
                assert settings.sync_interval == 50
