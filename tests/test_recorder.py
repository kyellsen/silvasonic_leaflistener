import importlib.util
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Load recorder/src/main.py directly by path logic
recorder_src = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../containers/recorder/src/main.py")
)
spec = importlib.util.spec_from_file_location("recorder_main", recorder_src)
main = importlib.util.module_from_spec(spec)
sys.modules["recorder_main"] = main
spec.loader.exec_module(main)


class TestRecorder(unittest.TestCase):
    """Test the Recorder module."""

    def setUp(self):
        """Set up test fixtures."""
        # We don't really need to call setup_logging/ensure_status_dir for unit tests of functions
        # mocking them is better if needed, or relying on the import-safe refactor we did.

        # Mock profile and device
        self.profile = MagicMock()
        self.profile.audio.channels = 1
        self.profile.audio.sample_rate = 48000
        self.profile.recording.chunk_duration_seconds = 30
        self.profile.recording.compression_level = 5
        self.profile.is_mock = False
        self.profile.slug = "test_profile"

        self.device = MagicMock()
        self.device.hw_address = "hw:0,0"

        self.output_dir = "/tmp/test_rec"

    @patch("recorder_main.subprocess.Popen")
    @patch("recorder_main.os.makedirs")
    def test_start_recording(self, mock_makedirs, mock_popen):
        """Test that start_recording calls FFmpeg with correct arguments."""
        process_mock = MagicMock()
        mock_popen.return_value = process_mock

        # Call the function
        main.start_recording(self.profile, self.device, self.output_dir)

        # Verify directory creation
        mock_makedirs.assert_called_with(self.output_dir, exist_ok=True)

        # Verify FFmpeg call
        args, kwargs = mock_popen.call_args
        cmd = args[0]

        # Check essential flags
        self.assertIn("ffmpeg", cmd)
        self.assertIn("alsa", cmd)
        self.assertIn(self.device.hw_address, cmd)
        self.assertIn("flac", cmd)
        self.assertIn(str(self.profile.recording.chunk_duration_seconds), cmd)

        # Check stream target construction
        # udp_url = f"udp://{LIVE_STREAM_TARGET}:{LIVE_STREAM_PORT}"
        # Defaults are silvasonic_livesound:1234
        # self.assertIn("udp://silvasonic_livesound:1234", cmd)
        # Actually cmd is a list, so we check if the url string is in the list
        found_udp = any("udp://" in arg for arg in cmd)
        self.assertTrue(found_udp, "UDP URL not found in command")

    @patch("recorder_main.subprocess.Popen")
    @patch("recorder_main.os.makedirs")
    def test_start_recording_mock_mode(self, mock_makedirs, mock_popen):
        """Test that mock mode changes input source."""
        self.profile.is_mock = True

        main.start_recording(self.profile, self.device, self.output_dir)

        args, kwargs = mock_popen.call_args
        cmd = args[0]

        self.assertIn("lavfi", cmd)
        # Check for anoisesrc
        found_anoise = any("anoisesrc" in arg for arg in cmd)
        self.assertTrue(found_anoise, "anoisesrc source not found for mock profile")


if __name__ == "__main__":
    unittest.main()
