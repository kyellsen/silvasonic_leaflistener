import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from silvasonic_uploader.rclone_wrapper import RcloneWrapper


class TestRcloneWrapper:
    """Tests for the RcloneWrapper class (AsyncIO)."""

    @pytest.fixture
    def rclone(self, temp_fs: str) -> RcloneWrapper:
        """Fixture providing an RcloneWrapper instance."""
        config = os.path.join(temp_fs, "rclone.conf")
        return RcloneWrapper(config_path=config)

    def test_init_creates_config_dir(self, temp_fs: str) -> None:
        """Test that initialization creates the configuration directory if missing."""
        config_path = os.path.join(temp_fs, "nested", "rclone.conf")
        RcloneWrapper(config_path=config_path)
        assert os.path.exists(os.path.dirname(config_path))

    @patch("asyncio.create_subprocess_exec", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_configure_webdav(self, mock_exec: AsyncMock, rclone: RcloneWrapper) -> None:
        """Test configuring a WebDAV remote."""
        # Setup mock process
        process_mock = MagicMock()
        process_mock.communicate = AsyncMock(return_value=(b"", b""))
        process_mock.returncode = 0
        mock_exec.return_value = process_mock

        await rclone.configure_webdav("remote", "http://url", "user", "pass")

        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        assert "rclone" in args
        assert "config" in args
        assert "create" in args
        # Check password method? Just check structure.

    @patch("asyncio.create_subprocess_exec", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_configure_webdav_failure(
        self, mock_exec: AsyncMock, rclone: RcloneWrapper
    ) -> None:
        """Test failure handling when configuring WebDAV."""
        process_mock = MagicMock()
        process_mock.communicate = AsyncMock(return_value=(b"", b"Error output"))
        process_mock.returncode = 1
        mock_exec.return_value = process_mock

        with pytest.raises(Exception, match="Rclone config failed"):
            await rclone.configure_webdav("remote", "http://url", "user", "pass")

    @patch("asyncio.create_subprocess_exec", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_sync_success_callbacks(
        self, mock_exec: AsyncMock, rclone: RcloneWrapper
    ) -> None:
        """Test sync calls callbacks on success."""
        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.wait = AsyncMock()

        # Mock stdout lines (async iterator)
        lines = [
            b"INFO : file1.txt: Copied (new)\n",
            b"INFO : file2.txt: Copied (new)\n",
            b"",  # End of stream
        ]

        # Mock readline via side_effect
        process_mock.stdout.readline = AsyncMock(side_effect=lines)

        mock_exec.return_value = process_mock

        callback = AsyncMock()

        success = await rclone.sync("/src", "remote:/dst", callback=callback)

        assert success is True
        assert callback.call_count == 2

        # Use simple assert because AsyncMock call_args_list items are tuple(args, kwargs)
        # We check specific calls.
        calls = [c.args for c in callback.call_args_list]
        assert ("file1.txt", "success", "") in calls
        assert ("file2.txt", "success", "") in calls

    @patch("asyncio.create_subprocess_exec", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_copy_failure_callbacks(
        self, mock_exec: AsyncMock, rclone: RcloneWrapper
    ) -> None:
        """Test copy calls callbacks on failure."""
        process_mock = MagicMock()
        process_mock.returncode = 1
        process_mock.wait = AsyncMock()

        lines = [b"ERROR : badfile.txt: Failed to copy: Network Error\n", b""]
        process_mock.stdout.readline = AsyncMock(side_effect=lines)

        mock_exec.return_value = process_mock

        callback = AsyncMock()

        success = await rclone.copy("/src", "remote:/dst", callback=callback)

        assert success is False
        callback.assert_called_once_with("badfile.txt", "failed", "Network Error")

    @patch("asyncio.create_subprocess_exec", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_list_files(self, mock_exec: AsyncMock, rclone: RcloneWrapper) -> None:
        """Test listing files from a remote."""
        json_output = json.dumps(
            [
                {"Path": "file1.txt", "Size": 100, "IsDir": False},
                {"Path": "subdir/file2.txt", "Size": 200, "IsDir": False},
                {"Path": "subdir", "Size": -1, "IsDir": True},
            ]
        ).encode("utf-8")

        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.communicate = AsyncMock(return_value=(json_output, b""))
        mock_exec.return_value = process_mock

        files = await rclone.list_files("remote:/path")

        assert len(files) == 2
        assert files["file1.txt"] == 100
        assert files["subdir/file2.txt"] == 200
        assert "subdir" not in files

    @patch("asyncio.create_subprocess_exec", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_list_files_failure(self, mock_exec: AsyncMock, rclone: RcloneWrapper) -> None:
        """Test failure handling when listing files."""
        process_mock = MagicMock()
        process_mock.returncode = 1
        process_mock.communicate = AsyncMock(return_value=(b"", b"Error"))
        mock_exec.return_value = process_mock

        files = await rclone.list_files("remote:/path")
        assert files is None

    @patch("os.statvfs")
    def test_get_disk_usage(self, mock_stat: MagicMock, rclone: RcloneWrapper) -> None:
        """Test disk usage calculation (sync)."""
        mock_obj = MagicMock()
        mock_obj.f_blocks = 100
        mock_obj.f_frsize = 1
        mock_obj.f_bavail = 40
        mock_stat.return_value = mock_obj

        percent = rclone.get_disk_usage_percent("/path")
        assert percent == 60.0
