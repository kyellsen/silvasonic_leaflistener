import unittest
from unittest.mock import MagicMock, patch

from silvasonic_recorder.main import Recorder
from silvasonic_recorder.mic_profiles import DetectedDevice, MicrophoneProfile


class TestRecorderStatusError(unittest.TestCase):
    def setUp(self):
        # Mock settings
        self.settings_patcher = patch("silvasonic_recorder.main.settings")
        self.mock_settings = self.settings_patcher.start()
        self.mock_settings.STATUS_DIR = "/tmp/status"
        self.mock_settings.AUDIO_OUTPUT_DIR = "/tmp/audio"
        self.mock_settings.AUDIO_PROFILE = None
        self.mock_settings.RECORDER_ID = None

        with patch("silvasonic_recorder.main.os.makedirs"):
            self.recorder = Recorder()

        # Reset internal state
        self.recorder._last_status_write = 0
        self.recorder._last_status_hash = 0

    def tearDown(self):
        self.settings_patcher.stop()

    @patch("silvasonic_recorder.main.json.dump")
    @patch("silvasonic_recorder.main.os.rename")
    @patch("silvasonic_recorder.main.open")
    def test_json_content(self, mock_open, mock_rename, mock_json_dump):
        # Arrange
        mock_profile = MicrophoneProfile(name="Test", slug="test")
        mock_device = DetectedDevice(
            card_id="0", hw_address="test", description="desc", usb_id="123"
        )

        # Mock open context manager
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Act 1: Initial Recording Status
        self.recorder._write_status("Recording", profile=mock_profile, device=mock_device)

        # Assert 1
        ensure_called = mock_json_dump.call_args
        self.assertIsNotNone(ensure_called)
        data = ensure_called[0][0]  # First arg of call

        self.assertEqual(data["status"], "Recording")
        self.assertEqual(data["service"], "recorder")
        self.assertEqual(data["meta"]["profile"]["name"], "Test")
        self.assertEqual(data["meta"]["device"]["description"], "desc")

    @patch("silvasonic_recorder.main.json.dump")
    @patch("silvasonic_recorder.main.os.rename")
    @patch("silvasonic_recorder.main.open")
    def test_error_status(self, mock_open, mock_rename, mock_json_dump):
        # Act: Write Error Status
        self.recorder._write_status("Error: Failed")

        # Assert
        ensure_called = mock_json_dump.call_args
        data = ensure_called[0][0]

        self.assertEqual(data["status"], "Error: Failed")
        # Note: Recorder._write_status currently does not accept an 'error' object param
        # based on my reading of the source code in main.py lines 263-313.
        # It only takes status string, profile, and device.
        # If we need to pass error details, main.py needs update.
        # For now, we test what exists.


if __name__ == "__main__":
    unittest.main()
