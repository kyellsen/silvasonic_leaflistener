import json
import unittest
from unittest.mock import MagicMock, patch

from silvasonic_recorder.main import Recorder
from silvasonic_recorder.mic_profiles import DetectedDevice, MicrophoneProfile


class TestRecorderStatusError(unittest.TestCase):
    def setUp(self):
        # Mock settings
        self.settings_patcher = patch("silvasonic_recorder.main.settings")
        self.mock_settings = self.settings_patcher.start()
        self.mock_settings.AUDIO_OUTPUT_DIR = "/tmp/audio"
        self.mock_settings.AUDIO_PROFILE = None
        self.mock_settings.RECORDER_ID = "test_rec"

        with patch("silvasonic_recorder.main.os.makedirs"):
            self.recorder = Recorder()

        # Mock Redis
        self.recorder._redis = MagicMock()

        # Reset internal state
        self.recorder._last_status_write = 0
        self.recorder._last_status_hash = 0

    def tearDown(self):
        self.settings_patcher.stop()

    def test_json_content(self):
        # Arrange
        mock_profile = MicrophoneProfile(name="Test", slug="test")
        mock_device = DetectedDevice(
            card_id="0", hw_address="test", description="desc", usb_id="123"
        )

        # Act 1: Initial Recording Status
        self.recorder._write_status("Recording", profile=mock_profile, device=mock_device)

        # Assert 1
        ensure_called = self.recorder._redis.setex.call_args
        self.assertIsNotNone(ensure_called)
        # setex(key, ttl, value)
        data_str = ensure_called[0][2]
        data = json.loads(data_str)

        self.assertEqual(data["status"], "Recording")
        self.assertEqual(data["service"], "recorder")
        self.assertEqual(data["meta"]["profile"]["name"], "Test")
        self.assertEqual(data["meta"]["device"]["description"], "desc")

    def test_error_status(self):
        # Act: Write Error Status
        self.recorder._write_status("Error: Failed")

        # Assert
        ensure_called = self.recorder._redis.setex.call_args
        data_str = ensure_called[0][2]
        data = json.loads(data_str)

        self.assertEqual(data["status"], "Error: Failed")


if __name__ == "__main__":
    unittest.main()
