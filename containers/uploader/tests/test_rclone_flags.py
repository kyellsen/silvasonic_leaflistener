import subprocess
from unittest.mock import MagicMock, patch

import pytest
from rclone_wrapper import RcloneWrapper


class TestRcloneFlags:
    """Tests for specific Rclone flags like disable-http2."""

    @pytest.fixture
    def rclone(self, temp_fs: str) -> RcloneWrapper:
        return RcloneWrapper(config_path=f"{temp_fs}/rclone.conf")

    @patch("subprocess.Popen")
    def test_sync_includes_http2_disable(self, mock_popen: MagicMock, rclone: RcloneWrapper) -> None:
        """Verify that sync command includes --disable-http2 and retries."""
        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = []
        process_mock.wait.return_value = None
        mock_popen.return_value = process_mock

        rclone.sync("/src", "remote:/dst")

        args = mock_popen.call_args[0][0]
        assert "--disable-http2" in args
        assert "--retries" in args
        assert "5" in args

    @patch("subprocess.Popen")
    def test_copy_includes_http2_disable(self, mock_popen: MagicMock, rclone: RcloneWrapper) -> None:
        """Verify that copy command includes --disable-http2 and retries."""
        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = []
        process_mock.wait.return_value = None
        mock_popen.return_value = process_mock

        rclone.copy("/src", "remote:/dst")

        args = mock_popen.call_args[0][0]
        assert "--disable-http2" in args
        assert "--retries" in args
        assert "5" in args
