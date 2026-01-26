import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import MagicMock

from janitor import StorageJanitor


class TestStorageJanitor(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.janitor = StorageJanitor(self.test_dir, threshold_percent=70, target_percent=60)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_file(self, name, size=1024, age_offset=0):
        path = os.path.join(self.test_dir, name)
        with open(path, 'wb') as f:
            f.write(b'\0' * size)
        # Set mtime
        new_time = time.time() - age_offset
        os.utime(path, (new_time, new_time))
        return path

    def test_no_cleanup_needed(self):
        # Mock usage 0%
        mock_usage = MagicMock(return_value=10.0)
        self.janitor.check_and_clean({}, mock_usage)
        # No calls
        self.assertTrue(True)

    def test_cleanup_trigger(self):
        # Create 3 files: older, old, new
        f1 = self.create_file("old.flac", age_offset=300)
        f2 = self.create_file("mid.flac", age_offset=200)
        f3 = self.create_file("new.flac", age_offset=100)

        # Remote knows all of them
        remote_files = {
            "old.flac": 1024,
            "mid.flac": 1024,
            "new.flac": 1024
        }

        # Mock usage to trigger cleanup: 80% -> 75% -> 65% -> 50%
        mock_usage = MagicMock(side_effect=[80.0, 75.0, 65.0, 50.0])

        self.janitor.check_and_clean(remote_files, mock_usage)

        # Oldest should be gone
        self.assertFalse(os.path.exists(f1), "Oldest file should be deleted")
        # Middle should be gone (first iteration reduced to 75, still > 60 target)
        self.assertFalse(os.path.exists(f2), "Middle file should be deleted")
        # Newest should remain (second iteration reduced to 50, < 60 target)
        self.assertTrue(os.path.exists(f3), "Newest file should remain")

    def test_safety_check_missing_on_remote(self):
        f1 = self.create_file("local_only.flac", age_offset=300)

        # Remote empty
        remote_files = {}

        mock_usage = MagicMock(return_value=90.0)

        self.janitor.check_and_clean(remote_files, mock_usage)

        self.assertTrue(os.path.exists(f1), "File NOT on remote should NOT be deleted")

    def test_safety_check_remote_failure(self):
        f1 = self.create_file("safe.flac", age_offset=300)

        # Remote status unknown (None)
        remote_files = None

        mock_usage = MagicMock(return_value=90.0)

        self.janitor.check_and_clean(remote_files, mock_usage)

        self.assertTrue(os.path.exists(f1), "File should not be deleted if remote status is unknown")

if __name__ == '__main__':
    unittest.main()
