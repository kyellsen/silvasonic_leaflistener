import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from silvasonic_uploader.config import UploaderSettings


class TestMain:
    """Tests for the main application logic."""

    def test_calculate_queue_size(self, temp_fs: str, mock_db: MagicMock):
        """Test queue size calculation."""
        from silvasonic_uploader.main import calculate_queue_size

        os.makedirs(os.path.join(temp_fs, "subdir"))
        with open(os.path.join(temp_fs, "file1.txt"), "w") as f:
            f.write("a")

        mock_db.get_all_uploaded_set.return_value = set()

        queue_size = calculate_queue_size(temp_fs, mock_db)
        assert queue_size == 1

    @patch("silvasonic_uploader.main.DatabaseHandler")
    @patch("silvasonic_uploader.main.RcloneWrapper")
    @patch("silvasonic_uploader.main.StorageJanitor")
    @patch("asyncio.sleep")
    @patch("os.path.exists")
    @pytest.mark.asyncio
    async def test_service_loop_flow(
        self,
        mock_exists,
        mock_sleep: AsyncMock,
        mock_janitor: MagicMock,
        mock_rclone_cls: MagicMock,
        mock_db_cls: MagicMock,
        temp_fs: str,
    ):
        """Test the proper execution of the service loop."""
        # Setup mocks
        mock_sleep.side_effect = [None, asyncio.CancelledError("Break")]
        mock_db = mock_db_cls.return_value
        mock_db.connect = MagicMock(return_value=True)
        # Mock session
        mock_db.get_session.return_value.__enter__.return_value = MagicMock()

        mock_wrapper = mock_rclone_cls.return_value
        mock_wrapper.configure_webdav = AsyncMock()
        mock_wrapper.copy = AsyncMock(return_value=True)
        mock_wrapper.get_disk_usage_percent = MagicMock(return_value=20.0)
        mock_wrapper.list_files = AsyncMock(return_value={})

        # Setup path mocking
        original_exists = os.path.exists

        def side_effect(path):
            if path == "/data/recording" or str(path).startswith("/data/recording"):
                return True
            return original_exists(path)

        mock_exists.side_effect = side_effect

        # Also need os.path.getsize to work if it's called on /data/recording files?
        # service_loop calls os.path.getsize(full_path) IF status=="success".
        # But our copy mock returns True, so loop thinks it succeeded.
        # But callback is NOT CALLED by mock copy unless we make it call it.
        # RcloneWrapper.copy logic:
        # calls _run_transfer -> process -> callback.
        # Our mock is on RcloneWrapper.copy.
        # It just returns True. It does NOT call the callback.
        # Wait, if callback is not called, then DB update and progress update don't happen.
        # But `service_loop` calls `copy`.
        # The test asserts `copy` is awaited.
        # The failure was `Expected copy to have been awaited`.
        # This failure happened because `if os.path.exists(source_dir)` was False.
        # With `mock_exists`, it should enter the block.

        # Setup Settings
        settings = UploaderSettings(
            sync_interval=1,
            nextcloud_url="http://test",
            nextcloud_user="user",
            nextcloud_password="pass",
            target_dir="silvasonic",
        )

        from silvasonic_uploader.main import service_loop

        with patch("silvasonic_uploader.main.calculate_queue_size", return_value=5):
            # run loop
            try:
                await service_loop(settings)
            except asyncio.CancelledError:
                pass

            mock_wrapper.configure_webdav.assert_awaited()
            mock_wrapper.copy.assert_awaited()

    @patch("silvasonic_uploader.main.UploaderSettings.load")
    @patch("silvasonic_uploader.main.service_loop")
    @pytest.mark.asyncio
    async def test_reload_service(self, mock_loop, mock_load):
        from silvasonic_uploader.main import reload_service

        # Mock global _service_task using Future (awaitable and cancellable)
        mock_task = asyncio.Future()
        # We don't want to actually wait forever if await is called, so set result?
        # But `await _service_task` in `reload_service` happens AFTER `cancel()`.
        # `_service_task` (if it was a real task) would raise CancelledError when awaited?
        # Or if it's just a Future that is not done.
        # If we cancel it, we should ensure it behaves like a cancelled task.
        # mock_task.cancel() returns True.
        # Awaiting a cancelled future raises CancelledError.

        # But we need to patch the global variable.
        with patch("silvasonic_uploader.main._service_task", mock_task):
            # We must schedule the future to be done or cancelled to avoid hanging?
            # reload_service calls cancel(), then await.
            # If we use a real Future, cancel() makes it done (cancelled).
            # So awaiting it raises CancelledError.
            # reload_service catches CancelledError.

            await reload_service()

            assert mock_task.cancelled()
            mock_load.assert_called()
            mock_loop.assert_called()
