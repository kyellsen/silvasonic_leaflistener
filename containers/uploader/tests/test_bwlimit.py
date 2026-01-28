from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from silvasonic_uploader.rclone_wrapper import RcloneWrapper


@pytest.mark.asyncio
class TestRcloneBwLimit:
    """Tests for the RcloneWrapper bwlimit functionality."""

    @pytest.fixture
    def rclone(self, temp_fs: str) -> RcloneWrapper:
        return RcloneWrapper(config_path=f"{temp_fs}/rclone.conf")

    @patch("asyncio.create_subprocess_exec", new_callable=AsyncMock)
    async def test_copy_with_bwlimit(self, mock_exec: AsyncMock, rclone: RcloneWrapper) -> None:
        """Verify that copy accepts and passes bwlimit."""
        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout.readline = AsyncMock(side_effect=[b""])
        process_mock.wait = AsyncMock()
        mock_exec.return_value = process_mock

        await rclone.copy("/src", "remote:/dst", bwlimit="500k")

        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        # args is flat arguments to create_subprocess_exec?
        # No, they are passed as *cmd.
        # So args will be the command parts.

        flat_args = [str(arg) for arg in args]
        assert "--bwlimit" in flat_args
        assert "500k" in flat_args

        # Verify order/proximity if important (rclone doesn't strictly care about order of flags usually)

    @patch("asyncio.create_subprocess_exec", new_callable=AsyncMock)
    async def test_sync_with_bwlimit(self, mock_exec: AsyncMock, rclone: RcloneWrapper) -> None:
        """Verify that sync accepts and passes bwlimit."""
        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout.readline = AsyncMock(side_effect=[b""])
        process_mock.wait = AsyncMock()
        mock_exec.return_value = process_mock

        await rclone.sync("/src", "remote:/dst", bwlimit="2M")

        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        flat_args = [str(arg) for arg in args]
        assert "--bwlimit" in flat_args
        assert "2M" in flat_args

    @patch("asyncio.create_subprocess_exec", new_callable=AsyncMock)
    async def test_copy_without_bwlimit(self, mock_exec: AsyncMock, rclone: RcloneWrapper) -> None:
        """Verify that copy works without bwlimit."""
        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout.readline = AsyncMock(side_effect=[b""])
        process_mock.wait = AsyncMock()
        mock_exec.return_value = process_mock

        await rclone.copy("/src", "remote:/dst")

        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        flat_args = [str(arg) for arg in args]
        assert "--bwlimit" not in flat_args
