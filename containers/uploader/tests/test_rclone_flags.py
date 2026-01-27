from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from silvasonic_uploader.rclone_wrapper import RcloneWrapper


@pytest.mark.asyncio
class TestRcloneFlags:
    """Tests for specific Rclone flags like disable-http2."""

    @pytest.fixture
    def rclone(self, temp_fs: str) -> RcloneWrapper:
        return RcloneWrapper(config_path=f"{temp_fs}/rclone.conf")

    @patch("asyncio.create_subprocess_exec", new_callable=AsyncMock)
    async def test_sync_includes_http2_disable(
        self, mock_exec: AsyncMock, rclone: RcloneWrapper
    ) -> None:
        """Verify that sync command includes --disable-http2 and retries."""
        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout.readline = AsyncMock(side_effect=[b""])
        process_mock.wait = AsyncMock()
        mock_exec.return_value = process_mock

        await rclone.sync("/src", "remote:/dst")

        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        # args is tuple of (program, *args)
        # silvasonic_uploader.rclone_wrapper.RcloneWrapper._run_transfer uses:
        # cmd = ["rclone", "sync"|"copy", ...]
        # process = await asyncio.create_subprocess_exec(*cmd, ...)
        # So call_args[0] will be ("rclone", "sync", ..., "--disable-http2", ...)

        # Flatten args if needed, or check presence
        flat_args = [str(arg) for arg in args]
        assert "--disable-http2" in flat_args
        assert "--retries" in flat_args
        assert "5" in flat_args

    @patch("asyncio.create_subprocess_exec", new_callable=AsyncMock)
    async def test_copy_includes_http2_disable(
        self, mock_exec: AsyncMock, rclone: RcloneWrapper
    ) -> None:
        """Verify that copy command includes --disable-http2 and retries."""
        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout.readline = AsyncMock(side_effect=[b""])
        process_mock.wait = AsyncMock()
        mock_exec.return_value = process_mock

        await rclone.copy("/src", "remote:/dst")

        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        flat_args = [str(arg) for arg in args]
        assert "--disable-http2" in flat_args
        assert "--retries" in flat_args
        assert "5" in flat_args
