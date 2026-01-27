import json
import os
from unittest.mock import ANY, MagicMock, patch

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
        mock_db.get_uploaded_filenames.return_value = {"file1.txt"}

        queue_size = calculate_queue_size(temp_fs, mock_db)
        # Total 2, 1 uploaded -> 1 pending
        assert queue_size == 1

        mock_db.get_uploaded_filenames.assert_called_once()
        args = mock_db.get_uploaded_filenames.call_args[0][0]
        assert "file1.txt" in args
        assert "subdir/file2.txt" in args

    def test_calculate_queue_size_empty(self, temp_fs: str, mock_db: MagicMock) -> None:
        """Test queue size is 0 when directory is empty."""
        from silvasonic_uploader.main import calculate_queue_size

        queue_size = calculate_queue_size(temp_fs, mock_db)
        assert queue_size == 0
        mock_db.get_uploaded_filenames.assert_not_called()

    def test_calculate_queue_size_exception(self, temp_fs: str, mock_db: MagicMock) -> None:
        """Test graceful handling of exceptions during queue size calculation."""
        # Pass invalid directory to trigger exception in os.walk (e.g. file as dir)
        # Or mock os.walk
        with patch("os.walk") as mock_walk:
            mock_walk.side_effect = Exception("Walk Error")
            from silvasonic_uploader.main import calculate_queue_size

            queue_size = calculate_queue_size(temp_fs, mock_db)
            assert queue_size == 0

    @patch("main.STATUS_FILE", new_callable=lambda: "status.json")
    def test_write_status(self, mock_status_file: MagicMock, temp_fs: str) -> None:
        """Test writing status to the status file."""
        # Redirect STATUS_FILE to temp dir
        status_path = os.path.join(temp_fs, "status.json")

        with patch("main.STATUS_FILE", status_path):
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

    @patch("main.ERROR_DIR", new_callable=lambda: "errors")
    def test_report_error(self, mock_error_dir: MagicMock, temp_fs: str) -> None:
        """Test reporting errors to the error directory."""
        error_dir = os.path.join(temp_fs, "errors")

        with patch("main.ERROR_DIR", error_dir):
            os.makedirs(error_dir, exist_ok=True)
            try:
                raise ValueError("Test Error")
            except ValueError as e:
                from silvasonic_uploader.main import report_error

                report_error("test_context", e)

            files = os.listdir(error_dir)
            assert len(files) == 1
            with open(os.path.join(error_dir, files[0])) as f:
                data = json.load(f)

            assert data["context"] == "test_context"
            assert "Test Error" in data["error"]

    @patch("main.setup_environment")
    @patch("silvasonic_uploader.database.DatabaseHandler")
    @patch("main.RcloneWrapper")
    @patch("main.StorageJanitor")
    @patch("time.sleep")
    def test_main_loop_flow(
        self,
        mock_sleep: MagicMock,
        mock_janitor: MagicMock,
        mock_rclone: MagicMock,
        mock_db_cls: MagicMock,
        mock_setup: MagicMock,
        temp_fs: str,
    ) -> None:
        """Test the main loop flow including upload and cleanup."""
        # We need to break the infinite loop
        # We'll use a side effect on time.sleep to raise an exception after 1 call
        mock_sleep.side_effect = [None, SystemExit("Break Loop")]

        # Setup mocks
        mock_db = mock_db_cls.return_value
        mock_wrapper = mock_rclone.return_value
        mock_janitor_inst = mock_janitor.return_value

        mock_wrapper.copy.return_value = True  # Success

        mock_wrapper.copy.return_value = True  # Success

        # Run main
        # We need to patch SOURCE_DIR and constants locally
        import main

        with (
            patch("main.SOURCE_DIR", temp_fs),
            patch("main.NEXTCLOUD_URL", "http://url"),
            patch("main.NEXTCLOUD_USER", "user"),
            patch("main.NEXTCLOUD_PASSWORD", "pass"),
        ):
            try:
                main.main()
            except SystemExit:
                pass

        # Verify Interactions
        mock_db.connect.assert_called_once()
        mock_wrapper.configure_webdav.assert_called_once()

        # Check upload called
        mock_wrapper.copy.assert_called()

        # Check cleanup called (since upload success)
        mock_janitor_inst.check_and_clean.assert_called()

    @patch("main.setup_environment")
    @patch("silvasonic_uploader.database.DatabaseHandler")
    @patch("main.RcloneWrapper")
    @patch("main.StorageJanitor")
    @patch("time.sleep")
    def test_main_loop_failure(
        self,
        mock_sleep: MagicMock,
        mock_janitor: MagicMock,
        mock_rclone: MagicMock,
        mock_db_cls: MagicMock,
        mock_setup: MagicMock,
        temp_fs: str,
    ) -> None:
        """Test the main loop handling of upload failures."""
        mock_sleep.side_effect = [None, SystemExit("Break Loop")]

        mock_wrapper = mock_rclone.return_value
        mock_wrapper.copy.return_value = False  # Failure

        with (
            patch("main.SOURCE_DIR", temp_fs),
            patch("main.NEXTCLOUD_URL", "http://url"),
            patch("main.NEXTCLOUD_USER", "user"),
            patch("main.NEXTCLOUD_PASSWORD", "pass"),
        ):
            try:
                import main

                main.main()
            except SystemExit:
                pass

        # Cleanup should NOT be called
        mock_janitor.return_value.check_and_clean.assert_not_called()

    def test_upload_callback(self, mock_db: MagicMock) -> None:
        """Test the upload callback function logging to the database."""
        with (
            patch("silvasonic_uploader.database.DatabaseHandler") as mock_db_cls,
            patch("main.RcloneWrapper") as mock_rclone,
            patch("main.StorageJanitor"),
            patch("time.sleep", side_effect=SystemExit),
            patch("main.SOURCE_DIR", "/tmp"),
            patch("main.setup_environment"),
        ):
            try:
                import main

                main.main()
            except SystemExit:
                pass

            # wrapper.copy was called with callback=upload_callback
            copy_call = mock_rclone.return_value.copy.call_args
            callback = copy_call.kwargs["callback"]

            # Now test the callback
            # Case 1: Success with file
            with (
                patch("os.path.exists", return_value=True),
                patch("os.path.getsize", return_value=1234),
            ):
                callback("test.mp3", "success")

                mock_db_cls.return_value.log_upload.assert_called_with(
                    filename="test.mp3",
                    remote_path=ANY,
                    status="success",
                    size_bytes=1234,
                    error_message=None,
                )

            # Case 2: Failure
            callback("fail.mp3", "failed", "Network Error")
            mock_db_cls.return_value.log_upload.assert_called_with(
                filename="fail.mp3",
                remote_path=ANY,
                status="failed",
                size_bytes=0,
                error_message="Network Error",
            )

    @patch("main.logging")
    @patch("main.os.makedirs")
    def test_setup_environment(self, mock_makedirs: MagicMock, mock_logging: MagicMock) -> None:
        """Test that environment setup creates necessary directories and configures logging."""
        from silvasonic_uploader.main import setup_environment

        setup_environment()

        # Verify makedirs called twice (log dir, status dir, error dir) -> 3 times actually
        assert mock_makedirs.call_count >= 2
        mock_logging.basicConfig.assert_called_once()

    @patch("main.setup_environment")
    @patch("silvasonic_uploader.database.DatabaseHandler")
    @patch("main.RcloneWrapper")
    @patch("main.StorageJanitor")
    @patch("time.sleep")
    def test_main_loop_crash(
        self,
        mock_sleep: MagicMock,
        mock_janitor: MagicMock,
        mock_rclone: MagicMock,
        mock_db: MagicMock,
        mock_setup: MagicMock,
        temp_fs: str,
    ) -> None:
        """Test that unhandled exceptions in the main loop are caught and reported."""
        # Create a file so calculate_queue_size proceeds to call db
        with open(os.path.join(temp_fs, "test.wav"), "w") as f:
            f.write("data")

        # Raise exception inside loop
        # We can make calculate_queue_size raise exception via db
        mock_db.return_value.get_uploaded_filenames.side_effect = Exception("Major Crash")

        # sleep triggers SystemExit to break loop eventually, but verify we hit report_error
        mock_sleep.side_effect = [SystemExit("Stop")]

        with patch("main.SOURCE_DIR", temp_fs), patch("main.report_error") as mock_report:
            try:
                import main

                main.main()
            except SystemExit:
                pass

            mock_report.assert_called_with("main_loop_crash", ANY)

    def test_signal_handler(self) -> None:
        """Test the signal handler raises SystemExit."""
        import signal

        from silvasonic_uploader.main import signal_handler

        with pytest.raises(SystemExit) as e:
            signal_handler(signal.SIGTERM, None)
        assert e.value.code == 0
