import os
import subprocess
from unittest.mock import MagicMock, call, patch

import pytest
from rclone_wrapper import RcloneWrapper


class TestRcloneWrapper:
    """Tests for the RcloneWrapper class."""
    @pytest.fixture
    def rclone(self, temp_fs):
        """Fixture providing an RcloneWrapper instance."""
        config = os.path.join(temp_fs, "rclone.conf")
        return RcloneWrapper(config_path=config)

    def test_init_creates_config_dir(self, temp_fs):
        """Test that initialization creates the configuration directory if missing."""
        config_path = os.path.join(temp_fs, "nested", "rclone.conf")
        RcloneWrapper(config_path=config_path)
        assert os.path.exists(os.path.dirname(config_path))

    @patch("subprocess.run")
    def test_configure_webdav(self, mock_run, rclone):
        """Test configuring a WebDAV remote."""
        mock_run.return_value.returncode = 0

        rclone.configure_webdav("remote", "http://url", "user", "pass")

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "rclone" in args
        assert "config" in args
        assert "create" in args
        assert "remote" in args
        assert "webdav" in args

    @patch("subprocess.run")
    def test_configure_webdav_failure(self, mock_run, rclone):
        """Test failure handling when configuring WebDAV."""
        mock_run.side_effect = subprocess.CalledProcessError(1, ["cmd"], stderr="Error output")

        with pytest.raises(subprocess.CalledProcessError):
            rclone.configure_webdav("remote", "http://url", "user", "pass")

    @patch("subprocess.Popen")
    def test_sync_success_callbacks(self, mock_popen, rclone):
        """Test sync calls callbacks on success."""
        # Mock process output
        process_mock = MagicMock()
        process_mock.stdout = [
            "INFO : file1.txt: Copied (new)",
            "INFO : file2.txt: Copied (new)"
        ]
        process_mock.returncode = 0
        process_mock.wait.return_value = None
        mock_popen.return_value = process_mock

        callback = MagicMock()

        success = rclone.sync("/src", "remote:/dst", callback=callback)

        assert success is True
        assert callback.call_count == 2
        callback.assert_has_calls([
            call("file1.txt", "success"),
            call("file2.txt", "success")
        ], any_order=True)

    @patch("subprocess.Popen")
    def test_copy_failure_callbacks(self, mock_popen, rclone):
        """Test copy calls callbacks on failure."""
        # Mock process output with error
        process_mock = MagicMock()
        process_mock.stdout = [
            "ERROR : badfile.txt: Failed to copy: Network Error"
        ]
        process_mock.returncode = 1
        process_mock.wait.return_value = None
        mock_popen.return_value = process_mock

        callback = MagicMock()

        success = rclone.copy("/src", "remote:/dst", callback=callback)

        assert success is False
        callback.assert_called_once_with("badfile.txt", "failed", error="Network Error")

    @patch("subprocess.Popen")
    def test_transfer_execution_exception(self, mock_popen, rclone):
        """Test handling of exceptions during transfer execution."""
        mock_popen.side_effect = Exception("Popopen failed")

        success = rclone.copy("/src", "remote:/dst")
        assert success is False

    @patch("subprocess.run")
    def test_list_files(self, mock_run, rclone):
        """Test listing files from a remote."""
        # Mock lsjson output
        json_output = """
        [
            {"Path": "file1.txt", "Size": 100, "IsDir": false},
            {"Path": "subdir/file2.txt", "Size": 200, "IsDir": false},
            {"Path": "subdir", "Size": -1, "IsDir": true}
        ]
        """
        mock_run.return_value.stdout = json_output
        mock_run.return_value.returncode = 0

        files = rclone.list_files("remote:/path")

        assert len(files) == 2
        assert files["file1.txt"] == 100
        assert files["subdir/file2.txt"] == 200
        assert "subdir" not in files

    @patch("subprocess.run")
    def test_list_files_failure(self, mock_run, rclone):
        """Test failure handling when listing files."""
        mock_run.side_effect = subprocess.CalledProcessError(1, ["cmd"], stderr="Error")

        files = rclone.list_files("remote:/path")
        assert files is None

    @patch("os.statvfs")
    def test_get_disk_usage(self, mock_stat, rclone):
        """Test disk usage calculation."""
        # Mock statvfs
        # percent = (used / total) * 100
        # total = blocks * frsize
        # free = bavail * frsize

        # Total = 100 * 1 = 100
        # Free = 40 * 1 = 40
        # Used = 60
        # Percent = 60%

        mock_obj = MagicMock()
        mock_obj.f_blocks = 100
        mock_obj.f_frsize = 1
        mock_obj.f_bavail = 40
        mock_stat.return_value = mock_obj

        percent = rclone.get_disk_usage_percent("/path")
        assert percent == 60.0

    @patch("os.statvfs")
    def test_get_disk_usage_error(self, mock_stat, rclone):
        """Test disk usage returns 0 on error."""
        mock_stat.side_effect = OSError("Disk error")
        percent = rclone.get_disk_usage_percent("/path")
        assert percent == 0.0
