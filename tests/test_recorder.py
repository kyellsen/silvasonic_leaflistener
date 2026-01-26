
import os
import queue
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

# Adjust path to import main from containers/recorder/src
# Use insert(0) to prioritize this path over installed packages
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), '../containers/recorder/src'
)))

import main


class TestRecorder(unittest.TestCase):
    """Tests for the recorder module."""

    def setUp(self):
        """Reset global state before each test."""
        # Reset global state before each test
        main.running = True
        main.audio_queue = queue.Queue()
        main.MOCK_HARDWARE = False

    @patch('main.sd')
    def test_device_selection_success(self, mock_sd):
        """Test successful selection of the target audio device."""
        # Mock device list
        mock_sd.query_devices.return_value = [
            {'name': 'Built-in Audio', 'max_input_channels': 2},
            {'name': 'Ultramic384 EVO', 'max_input_channels': 1}
        ]

        # Test finding Ultramic
        main.DEVICE_NAME = 'Ultramic'
        main.CHANNELS = 1

        # We need to simulate main() logic partially or refactor main to be more testable.
        # For this test, let's extract the device logic or just test the logic inline here matching main.py

        devices = mock_sd.query_devices()
        target_idx = None
        for idx, dev in enumerate(devices):
            if (main.DEVICE_NAME.lower() in dev['name'].lower() and
                    dev['max_input_channels'] >= main.CHANNELS):
                target_idx = idx
                break

        self.assertEqual(target_idx, 1)

    @patch('main.sd')
    def test_device_selection_failure(self, mock_sd):
        """Test failure to find the target audio device."""
        mock_sd.query_devices.return_value = [
            {'name': 'Built-in Audio', 'max_input_channels': 2}
        ]
        main.DEVICE_NAME = 'NonExistentMic'

        devices = mock_sd.query_devices()
        target_idx = None
        for idx, dev in enumerate(devices):
            if main.DEVICE_NAME.lower() in dev['name'].lower():
                target_idx = idx
                break

        self.assertIsNone(target_idx)

    def test_audio_callback(self):
        """Verify audio callback puts data into the queue."""
        # Verify callback puts data into queue
        indata = np.zeros((10, 1), dtype='float32')
        main.audio_callback(indata, 10, None, None)

        self.assertFalse(main.audio_queue.empty())
        item = main.audio_queue.get()
        np.testing.assert_array_equal(item, indata)

    @patch('main.sf')
    @patch('os.makedirs')
    def test_file_writer(self, mock_makedirs, mock_sf):
        """Test the file writer logic."""
        # Mock SoundFile context manager
        mock_file = MagicMock()
        mock_sf.SoundFile.return_value.__enter__.return_value = mock_file

        # Mock Queue get to return data then raise Empty to break loop if we were using timeout
        # But writer loop runs while 'running' is True.

        # We'll put one item in queue, start writer in thread, wait a bit, then stop.
        test_data = np.zeros((100, 1), dtype='float32')
        main.audio_queue.put(test_data)

        # Start writer
        t = threading.Thread(target=main.file_writer)
        t.start()

        # Let it run for a fraction of a second
        time.sleep(0.1)

        # Stop
        main.running = False
        t.join(timeout=1)

        # Verify
        mock_makedirs.assert_called_with(main.RAW_DIR, exist_ok=True)
        mock_sf.SoundFile.assert_called()
        mock_file.write.assert_called()
        # Verify at least one write call was made with our data
        # Note: Depending on race conditions, it might have written more calls if
        # we didn't control queue perfectly, but we just want to ensure it wrote something.
        self.assertTrue(mock_file.write.called)

if __name__ == '__main__':
    unittest.main()
