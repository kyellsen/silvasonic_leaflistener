import os
import time
from unittest.mock import MagicMock, patch

import pytest
from janitor import StorageJanitor


class TestStorageJanitor:
    @pytest.fixture
    def janitor(self, temp_fs):
        return StorageJanitor(temp_fs, threshold_percent=70, target_percent=60)

    def create_file(self, base_dir, name, size=1024, age_offset=0):
        path = os.path.join(base_dir, name)
        with open(path, 'wb') as f:
            f.write(b'\0' * size)
        # Set mtime
        new_time = time.time() - age_offset
        os.utime(path, (new_time, new_time))
        return path

    def test_no_cleanup_needed(self, janitor):
        # Mock usage 10%
        mock_usage = MagicMock(return_value=10.0)
        janitor.check_and_clean({}, mock_usage)
        # Usage was called
        mock_usage.assert_called_once()

    def test_cleanup_trigger(self, janitor, temp_fs):
        # Create 3 files: older, old, new
        f1 = self.create_file(temp_fs, "old.flac", age_offset=300)
        f2 = self.create_file(temp_fs, "mid.flac", age_offset=200)
        f3 = self.create_file(temp_fs, "new.flac", age_offset=100)

        # Remote knows all of them
        remote_files = {
            "old.flac": 1024,
            "mid.flac": 1024,
            "new.flac": 1024
        }

        # Mock usage to trigger cleanup: 80% -> 75% -> 65% -> 50%
        mock_usage = MagicMock(side_effect=[80.0, 75.0, 65.0, 50.0])

        janitor.check_and_clean(remote_files, mock_usage)

        # Oldest should be gone
        assert not os.path.exists(f1), "Oldest file should be deleted"
        # Middle should be gone (first iteration reduced to 75, still > 60 target)
        assert not os.path.exists(f2), "Middle file should be deleted"
        # Newest should remain (second iteration reduced to 50, < 60 target)
        assert os.path.exists(f3), "Newest file should remain"

    def test_safety_check_missing_on_remote(self, janitor, temp_fs):
        f1 = self.create_file(temp_fs, "local_only.flac", age_offset=300)

        # Remote empty
        remote_files = {}

        mock_usage = MagicMock(return_value=90.0)

        janitor.check_and_clean(remote_files, mock_usage)

        assert os.path.exists(f1), "File NOT on remote should NOT be deleted"

    def test_safety_check_remote_failure(self, janitor, temp_fs):
        f1 = self.create_file(temp_fs, "safe.flac", age_offset=300)

        # Remote status unknown (None)
        remote_files = None

        mock_usage = MagicMock(return_value=90.0)

        janitor.check_and_clean(remote_files, mock_usage)

        assert os.path.exists(f1), "File should not be deleted if remote status is unknown"

    def test_remote_size_zero_check(self, janitor, temp_fs):
        f1 = self.create_file(temp_fs, "bad_upload.flac", size=1024, age_offset=300)

        # Remote says size is 0
        remote_files = {
            "bad_upload.flac": 0
        }

        mock_usage = MagicMock(return_value=90.0)

        janitor.check_and_clean(remote_files, mock_usage)

        assert os.path.exists(f1), "File should not be deleted if remote size is 0"

    def test_list_local_files_handles_file_not_found(self, janitor, temp_fs):
        # This is hard to trigger with real FS as it happens between os.walk and os.stat
        # So we mock os.walk and os.stat

        with patch('os.walk') as mock_walk, \
             patch('os.stat') as mock_stat:

            mock_walk.return_value = [('/root', [], ['ghost.file'])]
            mock_stat.side_effect = FileNotFoundError

            files = janitor._list_local_files()
            assert len(files) == 0

    def test_exception_during_deletion(self, janitor, temp_fs, caplog):
        # Create a file
        f1 = self.create_file(temp_fs, "readonly.flac", age_offset=300)

        remote_files = {"readonly.flac": 1024}
        mock_usage = MagicMock(return_value=90.0)

        # Mock os.remove to fail
        with patch('os.remove') as mock_remove:
            mock_remove.side_effect = PermissionError("Access denied")

            # Using logs to verify error logging
            with caplog.at_level('ERROR'):
                janitor.check_and_clean(remote_files, mock_usage)

            assert "Failed to delete" in caplog.text
            # File 'exists' (mocked remove didn't happen)
            assert os.path.exists(f1)
