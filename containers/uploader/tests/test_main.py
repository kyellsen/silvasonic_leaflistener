# Ensure local src is used directly to avoid namespace collision with 'src' from other containers
import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure local src is used directly to avoid namespace collision with 'src' from other containers


class TestMain:
    """Tests for the main application logic."""

    def test_calculate_queue_size(self, temp_fs: str, mock_db: MagicMock) -> None:
        """Test queue size calculation with some uploaded and some pending files."""
        from silvasonic_uploader.main import calculate_queue_size

        # Create some files
        os.makedirs(os.path.join(temp_fs, "subdir"))
        with open(os.path.join(temp_fs, "file1.txt"), "w") as f:
            f.write("a")
        with open(os.path.join(temp_fs, "subdir", "file2.txt"), "w") as f:
            f.write("b")

        # Mock DB to say file1 is uploaded
        mock_db.get_all_uploaded_set.return_value = {"file1.txt"}

        queue_size = calculate_queue_size(temp_fs, mock_db)
        # Total 2, 1 uploaded -> 1 pending
        assert queue_size == 1

        mock_db.get_all_uploaded_set.assert_called_once()

    def test_calculate_queue_size_empty(self, temp_fs: str, mock_db: MagicMock) -> None:
        """Test queue size is 0 when directory is empty."""
        from silvasonic_uploader.main import calculate_queue_size

        queue_size = calculate_queue_size(temp_fs, mock_db)
        assert queue_size == 0

        # Depending on implementation order, it might call DB or not.
        # Current implementation: ALWAYS calls DB first.
        mock_db.get_all_uploaded_set.assert_called_once()

    @patch("silvasonic_uploader.main.STATUS_FILE", new_callable=lambda: "status.json")
    def test_write_status(self, mock_status_file: MagicMock, temp_fs: str) -> None:
        """Test writing status to the status file."""
        # Redirect STATUS_FILE to temp dir
        status_path = os.path.join(temp_fs, "status.json")

        with (
            patch("silvasonic_uploader.main.STATUS_FILE", status_path),
            patch("silvasonic_uploader.main.psutil") as mock_psutil,
        ):
            mock_psutil.cpu_percent.return_value = 10.0
            mock_psutil.Process.return_value.memory_info.return_value.rss = 1024 * 1024 * 50
            from silvasonic_uploader.main import write_status

            write_status("Testing", last_upload=123.0, queue_size=5, disk_usage=45.0)

            assert os.path.exists(status_path)
            with open(status_path) as f:
                data = json.load(f)

            assert data["status"] == "Testing"
            assert data["last_upload"] == 123.0
            assert data["meta"]["queue_size"] == 5
            assert data["meta"]["disk_usage_percent"] == 45.0
            assert "timestamp" in data
            assert data["last_error"] is None

    @patch("silvasonic_uploader.main.STATUS_FILE", new_callable=lambda: "status.json")
    def test_write_status_with_error(self, mock_status_file: MagicMock, temp_fs: str) -> None:
        """Test writing status containing error info."""
        status_path = os.path.join(temp_fs, "status.json")

        with (
            patch("silvasonic_uploader.main.STATUS_FILE", status_path),
            patch("silvasonic_uploader.main.psutil") as mock_psutil,
        ):
            mock_psutil.cpu_percent.return_value = 5.0
            mock_psutil.Process.return_value.memory_info.return_value.rss = 100

            # Reset global error state for test safety
            import silvasonic_uploader.main as main_mod
            from silvasonic_uploader.main import write_status

            main_mod._last_error = None

            # Act: Write with error
            err_obj = ConnectionError("Nextcloud Down")
            write_status("Error", last_upload=0, queue_size=1, disk_usage=10.0, error=err_obj)

            # Assert
            with open(status_path) as f:
                data = json.load(f)

            assert data["status"] == "Error"
            assert data["last_error"] == "Nextcloud Down"
            assert data["last_error_time"] > 0

            # Act: Succeed later
            write_status("Idle", last_upload=1, queue_size=0, disk_usage=10.0)

            # Assert: Error persisted
            with open(status_path) as f:
                data2 = json.load(f)
            assert data2["status"] == "Idle"
            assert data2["last_error"] == "Nextcloud Down"

    @patch("silvasonic_uploader.main.setup_environment")
    @patch("silvasonic_uploader.main.DatabaseHandler")
    @patch("silvasonic_uploader.main.RcloneWrapper")
    @patch("silvasonic_uploader.main.StorageJanitor")
    @patch("asyncio.sleep")
    @pytest.mark.asyncio
    async def test_main_loop_flow(
        self,
        mock_sleep: AsyncMock,
        mock_janitor: MagicMock,
        mock_rclone_cls: MagicMock,
        mock_db_cls: MagicMock,
        mock_setup: MagicMock,
        temp_fs: str,
    ) -> None:
        """Test the main loop flow including upload and cleanup."""
        # Break loop via asyncio.sleep
        mock_sleep.side_effect = [None, asyncio.CancelledError("Break Loop")]

        # Mock instances
        mock_db = mock_db_cls.return_value
        mock_wrapper = mock_rclone_cls.return_value
        mock_janitor_inst = mock_janitor.return_value

        # Mock connect
        mock_db.connect = MagicMock(return_value=True)

        # Mock wrapper methods (async)
        mock_wrapper.configure_webdav = AsyncMock()
        mock_wrapper.copy = AsyncMock(return_value=True)
        mock_wrapper.list_files = AsyncMock(return_value={})
        mock_wrapper.get_disk_usage_percent = MagicMock(return_value=50.0)  # Blocking mock

        # Mock DB session context manager
        session_mock = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = session_mock

        # Run main_loop
        import silvasonic_uploader.main as main

        with (
            patch("silvasonic_uploader.main.SOURCE_DIR", temp_fs),
            patch("silvasonic_uploader.main.NEXTCLOUD_URL", "http://url"),
            patch("silvasonic_uploader.main.NEXTCLOUD_USER", "user"),
            patch("silvasonic_uploader.main.NEXTCLOUD_PASSWORD", "pass"),
        ):
            try:
                await main.main_loop()
            except asyncio.CancelledError:
                pass

        # Verification
        mock_wrapper.configure_webdav.assert_awaited_once()
        mock_wrapper.copy.assert_awaited()
        mock_janitor_inst.check_and_clean.assert_called()

    @patch("silvasonic_uploader.main.setup_environment")
    @patch("silvasonic_uploader.main.DatabaseHandler")
    @patch("silvasonic_uploader.main.RcloneWrapper")
    @patch("silvasonic_uploader.main.StorageJanitor")
    @patch("asyncio.sleep")
    @pytest.mark.asyncio
    async def test_main_loop_failure(
        self,
        mock_sleep: AsyncMock,
        mock_janitor: MagicMock,
        mock_rclone_cls: MagicMock,
        mock_db_cls: MagicMock,
        mock_setup: MagicMock,
        temp_fs: str,
    ) -> None:
        """Test the main loop handling of upload failures."""
        mock_sleep.side_effect = [None, asyncio.CancelledError("Break Loop")]

        mock_wrapper = mock_rclone_cls.return_value
        mock_db = mock_db_cls.return_value
        mock_db.connect = MagicMock(return_value=True)

        mock_wrapper.configure_webdav = AsyncMock()
        mock_wrapper.copy = AsyncMock(return_value=False)  # Failure
        mock_wrapper.get_disk_usage_percent = MagicMock(return_value=50.0)

        mock_db.get_session.return_value.__enter__.return_value = MagicMock()

        import silvasonic_uploader.main as main

        with (
            patch("silvasonic_uploader.main.SOURCE_DIR", temp_fs),
            patch("silvasonic_uploader.main.NEXTCLOUD_URL", "http://url"),
            patch("silvasonic_uploader.main.NEXTCLOUD_USER", "user"),
            patch("silvasonic_uploader.main.NEXTCLOUD_PASSWORD", "pass"),
        ):
            try:
                await main.main_loop()
            except asyncio.CancelledError:
                pass

        # Cleanup NOT called
        mock_janitor.return_value.check_and_clean.assert_not_called()
