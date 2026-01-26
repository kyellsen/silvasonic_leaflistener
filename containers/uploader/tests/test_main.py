import os
import json
import time
import pytest
from unittest.mock import MagicMock, patch, call, ANY
from src.main import calculate_queue_size, write_status, report_error
import src.main as main

class TestMain:

    def test_calculate_queue_size(self, temp_fs, mock_db):
        # Create some files
        os.makedirs(os.path.join(temp_fs, "subdir"))
        with open(os.path.join(temp_fs, "file1.txt"), "w") as f: f.write("a")
        with open(os.path.join(temp_fs, "subdir", "file2.txt"), "w") as f: f.write("b")
        
        # Mock DB to say file1 is uploaded
        mock_db.get_uploaded_filenames.return_value = {"file1.txt"}
        
        queue_size = calculate_queue_size(temp_fs, mock_db)
        # Total 2, 1 uploaded -> 1 pending
        assert queue_size == 1
        
        mock_db.get_uploaded_filenames.assert_called_once()
        args = mock_db.get_uploaded_filenames.call_args[0][0]
        assert "file1.txt" in args
        assert "subdir/file2.txt" in args

    def test_calculate_queue_size_empty(self, temp_fs, mock_db):
        queue_size = calculate_queue_size(temp_fs, mock_db)
        assert queue_size == 0
        mock_db.get_uploaded_filenames.assert_not_called()

    def test_calculate_queue_size_exception(self, temp_fs, mock_db):
        # Pass invalid directory to trigger exception in os.walk (e.g. file as dir)
        # Or mock os.walk
        with patch("os.walk") as mock_walk:
            mock_walk.side_effect = Exception("Walk Error")
            queue_size = calculate_queue_size(temp_fs, mock_db)
            assert queue_size == 0

    @patch("src.main.STATUS_FILE", new_callable=lambda: "status.json")
    def test_write_status(self, mock_status_file, temp_fs):
        # Redirect STATUS_FILE to temp dir
        status_path = os.path.join(temp_fs, "status.json")
        
        with patch("src.main.STATUS_FILE", status_path):
            write_status("Testing", last_upload=123.0, queue_size=5, disk_usage=45.0)
            
            assert os.path.exists(status_path)
            with open(status_path) as f:
                data = json.load(f)
                
            assert data["status"] == "Testing"
            assert data["last_upload"] == 123.0
            assert data["meta"]["queue_size"] == 5
            assert data["meta"]["disk_usage_percent"] == 45.0
            assert "timestamp" in data

    @patch("src.main.ERROR_DIR", new_callable=lambda: "errors")
    def test_report_error(self, mock_error_dir, temp_fs):
        error_dir = os.path.join(temp_fs, "errors")
        
        with patch("src.main.ERROR_DIR", error_dir):
            os.makedirs(error_dir, exist_ok=True)
            try:
                raise ValueError("Test Error")
            except ValueError as e:
                report_error("test_context", e)
                
            files = os.listdir(error_dir)
            assert len(files) == 1
            with open(os.path.join(error_dir, files[0])) as f:
                data = json.load(f)
                
            assert data["context"] == "test_context"
            assert "Test Error" in data["error"]

    @patch("src.main.setup_environment")
    @patch("src.database.DatabaseHandler")
    @patch("src.main.RcloneWrapper")
    @patch("src.main.StorageJanitor")
    @patch("time.sleep")
    def test_main_loop_flow(self, mock_sleep, mock_janitor, mock_rclone, mock_db_cls, mock_setup, temp_fs):
        # We need to break the infinite loop
        # We'll use a side effect on time.sleep to raise an exception after 1 call
        mock_sleep.side_effect = [None, SystemExit("Break Loop")]
        
        # Setup mocks
        mock_db = mock_db_cls.return_value
        mock_wrapper = mock_rclone.return_value
        mock_janitor_inst = mock_janitor.return_value
        
        mock_wrapper.copy.return_value = True # Success
        
        # Run main
        # We need to patch SOURCE_DIR and constants locally
        with patch("src.main.SOURCE_DIR", temp_fs), \
             patch("src.main.NEXTCLOUD_URL", "http://url"), \
             patch("src.main.NEXTCLOUD_USER", "user"), \
             patch("src.main.NEXTCLOUD_PASSWORD", "pass"):
             
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

    @patch("src.main.setup_environment")
    @patch("src.database.DatabaseHandler")
    @patch("src.main.RcloneWrapper")
    @patch("src.main.StorageJanitor")
    @patch("time.sleep")
    def test_main_loop_failure(self, mock_sleep, mock_janitor, mock_rclone, mock_db_cls, mock_setup, temp_fs):
        mock_sleep.side_effect = [None, SystemExit("Break Loop")]
        
        mock_wrapper = mock_rclone.return_value
        mock_wrapper.copy.return_value = False # Failure
        
        with patch("src.main.SOURCE_DIR", temp_fs), \
             patch("src.main.NEXTCLOUD_URL", "http://url"), \
             patch("src.main.NEXTCLOUD_USER", "user"), \
             patch("src.main.NEXTCLOUD_PASSWORD", "pass"):
             
             try:
                 main.main()
             except SystemExit:
                 pass

        # Cleanup should NOT be called
        mock_janitor.return_value.check_and_clean.assert_not_called()

    def test_upload_callback(self, mock_db):
        
        with patch("src.database.DatabaseHandler") as mock_db_cls, \
             patch("src.main.RcloneWrapper") as mock_rclone, \
             patch("src.main.StorageJanitor"), \
             patch("time.sleep", side_effect=SystemExit), \
             patch("src.main.SOURCE_DIR", "/tmp"), \
             patch("src.main.setup_environment"):
            
            try:
                main.main()
            except SystemExit:
                pass
                
            # wrapper.copy was called with callback=upload_callback
            copy_call = mock_rclone.return_value.copy.call_args
            callback = copy_call.kwargs['callback']
            
            # Now test the callback
            # Case 1: Success with file
            with patch("os.path.exists", return_value=True), \
                 patch("os.path.getsize", return_value=1234):
                 
                callback("test.mp3", "success")
                
                mock_db_cls.return_value.log_upload.assert_called_with(
                    filename="test.mp3",
                    remote_path=ANY,
                    status="success",
                    size_bytes=1234,
                    error_message=None
                )
                
            # Case 2: Failure
            callback("fail.mp3", "failed", "Network Error")
            mock_db_cls.return_value.log_upload.assert_called_with(
                filename="fail.mp3",
                remote_path=ANY,
                status="failed",
                size_bytes=0,
                error_message="Network Error"
            )

    @patch("src.main.logging")
    @patch("src.main.os.makedirs")
    def test_setup_environment(self, mock_makedirs, mock_logging):
        from src.main import setup_environment
        setup_environment()
        
        # Verify makedirs called twice (log dir, status dir, error dir) -> 3 times actually
        assert mock_makedirs.call_count >= 2
        mock_logging.basicConfig.assert_called_once()

    @patch("src.main.setup_environment")
    @patch("src.database.DatabaseHandler")
    @patch("src.main.RcloneWrapper")
    @patch("src.main.StorageJanitor")
    @patch("time.sleep")
    def test_main_loop_crash(self, mock_sleep, mock_janitor, mock_rclone, mock_db, mock_setup, temp_fs):
        # Create a file so calculate_queue_size proceeds to call db
        with open(os.path.join(temp_fs, "test.wav"), "w") as f: f.write("data")

        # Raise exception inside loop
        # We can make calculate_queue_size raise exception via db
        mock_db.return_value.get_uploaded_filenames.side_effect = Exception("Major Crash")
        
        # sleep triggers SystemExit to break loop eventually, but verify we hit report_error
        mock_sleep.side_effect = [SystemExit("Stop")] 
        
        with patch("src.main.SOURCE_DIR", temp_fs), \
             patch("src.main.report_error") as mock_report:
             
             try:
                 main.main()
             except SystemExit:
                 pass
                 
             mock_report.assert_called_with("main_loop_crash", ANY)

    def test_signal_handler(self):
        import signal
        from src.main import signal_handler
        
        with pytest.raises(SystemExit) as e:
            signal_handler(signal.SIGTERM, None)
        assert e.value.code == 0

