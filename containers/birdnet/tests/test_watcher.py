import queue
import time
from unittest.mock import MagicMock, patch

import pytest
from silvasonic_birdnet.watcher import AudioFileHandler, WatcherService


@pytest.fixture
def watcher():
    with (
        patch("silvasonic_birdnet.watcher.BirdNETAnalyzer"),
        patch("silvasonic_birdnet.watcher.Observer"),
    ):
        return WatcherService()


def test_file_handler_event():
    """Test that AudioFileHandler puts files into queue."""
    q = queue.Queue()
    handler = AudioFileHandler(q)

    event = MagicMock()
    event.is_directory = False
    event.src_path = "/data/input/test.wav"

    handler.on_closed(event)

    assert q.qsize() == 1
    assert q.get() == "/data/input/test.wav"


def test_file_handler_ignores_files():
    """Test that non-audio files are ignored."""
    q = queue.Queue()
    handler = AudioFileHandler(q)

    event = MagicMock()
    event.is_directory = False
    event.src_path = "/data/input/test.txt"

    handler.on_closed(event)
    assert q.qsize() == 0


@patch("silvasonic_birdnet.watcher.json.dump")
@patch("silvasonic_birdnet.watcher.open")
@patch("silvasonic_birdnet.watcher.os.rename")
@patch("silvasonic_birdnet.watcher.psutil")
def test_write_status(mock_psutil, mock_rename, mock_open, mock_dump, watcher):
    """Test status file writing."""
    watcher.write_status("Idle")

    mock_dump.assert_called_once()
    data = mock_dump.call_args[0][0]
    assert data["status"] == "Idle"
    assert data["service"] == "birdnet"


def test_worker_process(watcher):
    """Test the worker loop processes files."""
    # Add a file to queue
    watcher.file_queue.put("/tmp/test.wav")

    # Configure analyzer mock
    watcher.analyzer.process_file = MagicMock()

    # We need to run worker briefly then stop
    # Since worker is an infinite loop, we run it in a thread or just call the body logic?
    # We can mock _stop_event to return False once then True?
    # Or just spawn it and set stop event after sleep.

    watcher._stop_event.set()  # Stop immediately after one iter hopefully if we time it right?
    # Actually worker checks .is_set() at start of loop.
    # Better to manually invoke the inner logic or just trust the thread logic works if we let it run 1 cycle.

    # Let's extract the "process one item" logic or just mock queue.get to raise Empty eventually?
    # We'll start the thread, wait, and stop.
    watcher._stop_event.clear()

    import threading

    t = threading.Thread(target=watcher._worker, daemon=True)
    t.start()

    time.sleep(0.1)  # Give it time to pick up item

    watcher._stop_event.set()
    t.join(timeout=1.0)

    # Verify analyzer was called
    watcher.analyzer.process_file.assert_called_with("/tmp/test.wav")
